"""Public Python entry points for the pricing-model workflow.

Connect, register a model, fit it, save a version, then review or deploy it.
``PricingDataset`` identifies the data; ``PricingModelSpec`` maps model roles
to columns; ``ModelRecipe`` saves reusable model configuration as TOML.

Fitting writes audit evidence and local artifacts. Saving publishes a SQL
rating package. Deployment is a separate explicit operation. Implementation
owners live in ``data``, ``modeling``, ``publishing`` and ``workbench``.
"""

from __future__ import annotations

import getpass
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy import text

from pricing_pipeline.data.dataset import PricingDataset
from pricing_pipeline.data.frame_artifact import (
    ModelFrameArtifact,
    inspect_model_frame,
    load_model_frame,
    save_model_frame,
)
from pricing_pipeline.data.manifest import (
    ModelFrameManifestSpec,
    validation_split_indices,
)
from pricing_pipeline.data.transforms import (
    Clip,
    Log,
    Log1p,
    Transform,
    apply_transforms,
    normalize_transforms,
    transforms_metadata,
)
from pricing_pipeline.data.validation import Splitter, splitter_config
from pricing_pipeline.infra.config import Settings
from pricing_pipeline.infra.offline_sqlite import open_offline_sqlite
from pricing_pipeline.infra.runtime import runtime_from_env_or_module
from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.modeling.level_grouping_artifact import (
    LevelGroupingArtifact,
    save_editor_level_groupings,
)
from pricing_pipeline.modeling.level_grouping_artifact import (
    apply_level_groupings as _apply_level_groupings,
)
from pricing_pipeline.modeling.level_grouping_artifact import (
    inspect_level_groupings as _inspect_level_groupings,
)
from pricing_pipeline.modeling.level_grouping_artifact import (
    load_level_groupings as _load_level_groupings,
)
from pricing_pipeline.modeling.manual_adjustment import (
    ManualAdjustmentPolicy,
    ManualAdjustmentRule,
    ManualEditReview,
    apply_manual_adjustment_policy,
    manual_adjustment_policy_from_candidate,
)
from pricing_pipeline.modeling.monitoring import (
    ModelFitContract,
    MonitoringFitResult,
    MonitoringInvariantEvidence,
    MonitoringVariant,
    PersistedMonitoringRun,
    build_model_fit_contract,
    persist_monitoring_fit,
    run_monitoring_fit,
)
from pricing_pipeline.modeling.recipes import ModelRecipe, RecipeCapture, UnsupportedRecipeError
from pricing_pipeline.modeling.recipes.schema import capture_environment
from pricing_pipeline.modeling.standard_superglm import (
    ModelInputs,
    PrecomputedSplitter,
    canonical_row_identity_index,
    run_standard_superglm_build,
)
from pricing_pipeline.models.config import ModelBuildConfig, ValidationSplitConfig
from pricing_pipeline.models.kinds import normalise_model_kind
from pricing_pipeline.models.spec import ApprovedModelBuild
from pricing_pipeline.orchestration.publish_completed_build import (
    CompletedModelPublishResult,
    publish_completed_model_build,
)
from pricing_pipeline.publishing.deployment import deploy_rate_package
from pricing_pipeline.publishing.editor import publish_editor_submission
from pricing_pipeline.publishing.identity import clean_identifier
from pricing_pipeline.publishing.metadata import OffsetExportContract
from pricing_pipeline.publishing.rating_tables import build_export_id
from pricing_pipeline.publishing.sqlite import (
    publish_sqlite_candidate,
    register_sqlite_model,
    resolve_sqlite_model_version,
)
from pricing_pipeline.publishing.sqlserver import (
    register_pricing_model,
    resolve_model_version_for_export,
)
from pricing_pipeline.workbench.core import Candidate, Workbench
from pricing_pipeline.workbench.submission import save_editor_submission


@dataclass(frozen=True)
class NotebookContext:
    """Connection, artifact locations and write permission returned by ``connect``.

    Pass this object to notebook operations as ``pricing``. ``destination``
    identifies the connected database; local mode also exposes SQLite paths.
    """

    engine: Any
    settings: Settings
    mode: str
    write_allowed: bool
    destination: str
    database_paths: Mapping[str, Path] = field(default_factory=dict)

    def require_write(self, operation: str) -> None:
        """Stop remote mutations until the notebook explicitly enables them."""
        if not self.write_allowed:
            raise PermissionError(
                f"Remote writes are disabled for {operation}. Confirm "
                "EXPECTED_REMOTE_DATABASE and set ALLOW_REMOTE_WRITES = True."
            )


@dataclass(frozen=True)
class PricingModelSpec:
    """Declare which data columns the model uses and how fitting is evaluated.

    Supply a ``PricingDataset`` for source, key and as-at metadata. ``features``
    is an ordered list or tuple of prepared column names; the SuperGLM instance
    supplies their categorical, numeric or spline treatment.

    ``transforms`` maps output names to source-column operations. Prepare the
    fit input with ``apply_transforms(dataset.df, spec.transforms)``. An offset
    column supplies a covariate with coefficient fixed at one; its source and
    label are inferred when that column has a declared transform.

    ``validation`` accepts a split configuration or a splitter with ``split``.
    ``groups_column`` supplies groups to that splitter. ``fit_mode`` defaults
    to ``fit_reml``; ``spline_export`` chooses exact polynomial or binned output.
    Constructing a spec validates these choices without fitting or writing SQL.
    """

    name: str
    label: str
    target: str
    model_type: str
    deployment_slot: str
    features: Sequence[str]
    dataset_name: str | None = None
    source_system: str | None = None
    pk_columns: Sequence[str] | None = None
    validation: ValidationSplitConfig | Splitter = field(
        default_factory=ValidationSplitConfig.kfold
    )
    offset_column: str | None = None
    offset_source_column: str | None = None
    offset_label: str | None = None
    sample_weight_column: str | None = None
    export_weight_column: str | None = None
    data_as_of_column: str | None = None
    scoring: tuple[str, ...] = ("deviance", "nll", "gini")
    fit_mode: str = "fit_reml"
    dataset: PricingDataset | None = None
    transforms: Mapping[str, Transform] = field(default_factory=dict)
    spline_export: str = "exact"
    groups_column: str | None = None

    def __post_init__(self) -> None:
        if self.spline_export not in {"exact", "binned"}:
            raise ValueError("spline_export must be 'exact' or 'binned'")
        if self.dataset is not None:
            if not isinstance(self.dataset, PricingDataset):
                raise TypeError("dataset must be a PricingDataset")
            for name, expected in (
                ("dataset_name", self.dataset.name),
                ("source_system", self.dataset.source),
                ("pk_columns", self.dataset.key),
                ("data_as_of_column", self.dataset.as_of),
            ):
                supplied = getattr(self, name)
                if supplied is not None:
                    if name == "pk_columns":
                        if isinstance(supplied, str) or not isinstance(supplied, Sequence):
                            raise TypeError("pk_columns must be an ordered sequence of names")
                        supplied = tuple(str(value).strip() for value in supplied)
                    else:
                        supplied = str(supplied).strip()
                    if supplied != expected:
                        raise ValueError(f"{name} conflicts with the dataset")
                object.__setattr__(self, name, expected)
        object.__setattr__(self, "transforms", normalize_transforms(self.transforms))
        for name in ("features", "pk_columns"):
            values = getattr(self, name)
            if isinstance(values, str) or not isinstance(values, Sequence):
                raise TypeError(f"{name} must be an ordered sequence of names")
        for field_name in (
            "name",
            "label",
            "target",
            "model_type",
            "dataset_name",
            "source_system",
            "fit_mode",
        ):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "deployment_slot",
            _required_text(self.deployment_slot, "deployment_slot").upper(),
        )
        object.__setattr__(
            self,
            "features",
            tuple(_required_text(value, "features") for value in self.features),
        )
        object.__setattr__(
            self,
            "pk_columns",
            tuple(_required_text(value, "pk_columns") for value in self.pk_columns),
        )
        object.__setattr__(
            self,
            "scoring",
            tuple(_required_text(value, "scoring") for value in self.scoring),
        )
        for field_name in (
            "offset_column",
            "offset_source_column",
            "offset_label",
            "sample_weight_column",
            "export_weight_column",
            "data_as_of_column",
            "groups_column",
        ):
            value = getattr(self, field_name)
            object.__setattr__(
                self,
                field_name,
                None if value is None else _required_text(value, field_name),
            )
        if self.offset_column in self.transforms:
            transform = self.transforms[self.offset_column]
            for name, expected in (
                ("offset_source_column", transform.source),
                ("offset_label", transform.expression),
            ):
                supplied = getattr(self, name)
                if supplied is not None and supplied != expected:
                    raise ValueError(f"{name} conflicts with the offset transform")
                object.__setattr__(self, name, expected)
        offset_fields = (
            self.offset_column,
            self.offset_source_column,
            self.offset_label,
        )
        if any(value is not None for value in offset_fields) and not all(
            value is not None for value in offset_fields
        ):
            raise ValueError(
                "offset_column, offset_source_column, and offset_label must be configured together"
            )
        if not self.features:
            raise ValueError("features must contain at least one column")
        if len(set(self.features)) != len(self.features):
            raise ValueError("features must not contain duplicates")
        if not self.pk_columns:
            raise ValueError("pk_columns must contain at least one column")
        if len(set(self.pk_columns)) != len(self.pk_columns):
            raise ValueError("pk_columns must not contain duplicates")
        if not self.scoring:
            raise ValueError("scoring must contain at least one metric")
        if len(set(self.scoring)) != len(self.scoring):
            raise ValueError("scoring must not contain duplicates")
        if isinstance(self.validation, ValidationSplitConfig):
            if self.groups_column is not None:
                raise ValueError("groups_column requires a splitter in validation")
            if self.validation.method not in {
                "kfold",
                "train_test_split",
                "column_kfold",
                "column_holdout",
            }:
                raise ValueError(
                    f"validation method {self.validation.method!r} is not supported by "
                    "the notebook workflow; pass a splitter or use a column-based split"
                )
            if not self.validation.materialize:
                object.__setattr__(self, "validation", replace(self.validation, materialize=True))
        validation_config = self._validation_config()

        roles: dict[str, list[str]] = {}
        role_values = {
            "target": (self.target,),
            "primary key": self.pk_columns,
            "feature": self.features,
            "split": (validation_config.column,),
            "offset": (self.offset_column,),
            "offset source": (self.offset_source_column,),
            "sample weight": (self.sample_weight_column,),
            "export weight": (self.export_weight_column,),
            "data as of": (self.data_as_of_column,),
        }
        for role, columns in role_values.items():
            for column in columns:
                if column is not None:
                    roles.setdefault(column, []).append(role)
        structural_roles = {
            "target",
            "primary key",
            "feature",
            "split",
            "data as of",
        }
        overlaps = {
            column: assigned_roles
            for column, assigned_roles in roles.items()
            if len(assigned_roles) > 1 and any(role in structural_roles for role in assigned_roles)
        }
        if overlaps:
            detail = "; ".join(
                f"{column}={','.join(assigned_roles)}"
                for column, assigned_roles in sorted(overlaps.items())
            )
            raise ValueError(f"model column roles overlap: {detail}")

    def _validation_config(self) -> ValidationSplitConfig:
        if isinstance(self.validation, ValidationSplitConfig):
            return self.validation
        return splitter_config(self.validation, groups_column=self.groups_column)


@dataclass(frozen=True)
class RegisteredModel:
    """SQL model identity and source directory used by notebook operations.

    ``register_model`` also attaches a spec for fitting. ``load_registered_model``
    returns a review reference with ``spec=None``.
    """

    model_id: int
    config: ModelBuildConfig
    source_root: Path
    spec: PricingModelSpec | None

    @property
    def name(self) -> str:
        return self.config.model_name


@dataclass(frozen=True)
class BuiltCandidate:
    """A completed fit with metrics and verified references to its local artifacts.

    Returned by ``fit_model`` before the rating package is saved. Pass it to
    ``save_model_version`` for publication, or export ``recipe`` for reuse.
    """

    model: RegisteredModel
    completed_build: ApprovedModelBuild
    _retained_recipe_capture: tuple[str, str, RecipeCapture] | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @property
    def metrics(self) -> dict[str, float]:
        return dict(self.completed_build.metrics)

    @property
    def recipe(self) -> ModelRecipe:
        """Read the immutable recipe verified against this build's artifact."""
        from pricing_pipeline.workbench.artifacts import load_candidate_bundle

        build = self.completed_build
        if build.candidate_artifact_path is None:
            raise UnsupportedRecipeError(
                "recipe unavailable: build has no verified candidate artifact"
            )
        artifact = Path(build.candidate_artifact_path)
        retained = self._retained_recipe_capture
        if (
            retained is not None
            and not artifact.exists()
            and not any(path.is_symlink() for path in (artifact, *artifact.parents))
        ):
            path, digest, capture = retained
            if (
                path != build.candidate_artifact_path
                or digest != build.candidate_artifact_sha256
                or capture != build.recipe_capture
            ):
                raise ValueError("retained recipe evidence does not match completed build")
        else:
            bundle = load_candidate_bundle(
                build.candidate_artifact_path,
                expected_sha256=build.candidate_artifact_sha256,
                expected_size_bytes=build.candidate_artifact_size_bytes,
                expected_format=build.candidate_artifact_format,
                expected_python_version=build.candidate_python_version,
                expected_superglm_version=build.candidate_superglm_version,
                allowed_root=Path(build.candidate_artifact_path).parent,
            )
            if bundle.recipe_capture != build.recipe_capture:
                raise ValueError("candidate artifact recipe does not match completed build")
            capture = bundle.recipe_capture
        if capture.status != "CAPTURED":
            raise UnsupportedRecipeError(
                capture.unavailable_reason
                or "recipe unavailable: legacy build has no captured constructor recipe"
            )
        return ModelRecipe(capture.document)


def _required_text(value: Any, field_name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned


def _created_by(value: str | None) -> str:
    identity = str(value or getpass.getuser()).strip()
    if not identity:
        raise ValueError("created_by is required")
    return identity


def _new_notebook_run_key() -> str:
    """Return a compact, readable and collision-resistant notebook run key."""
    timestamp = datetime.now(UTC).strftime("%y%m%d%H%M%S")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _local_notebook_settings(root: Path) -> Settings:
    return replace(
        Settings(),
        pricing_database="local_sqlite",
        mlflow_enabled=False,
        skip_database_create=True,
        rating_export_root=root / "rating_exports",
        validation_split_artifact_root=root / "validation_splits",
        workbench_artifact_root=root,
    )


def _connect_local(local_root: str | Path | None) -> NotebookContext:
    if local_root is None or not str(local_root).strip():
        raise ValueError("local_root is required when mode='local'")
    root = Path(local_root).expanduser().resolve()
    engine, database_paths = open_offline_sqlite(root)
    return NotebookContext(
        engine=engine,
        settings=_local_notebook_settings(root),
        mode="local",
        write_allowed=True,
        destination=f"local SQLite: {root}",
        database_paths=database_paths,
    )


def _connect_remote(
    runtime_module: str | None,
    *,
    expected_database: str | None,
    allow_writes: bool,
) -> NotebookContext:
    expected = str(expected_database or "").strip()
    if not expected:
        raise ValueError("expected_remote_database is required when mode='remote'")

    runtime = runtime_from_env_or_module(runtime_module)
    engine = runtime.get_engine()
    with engine.connect() as connection:
        actual_value = connection.execute(text("SELECT DB_NAME()")).scalar_one()
    actual = str(actual_value or "").strip()
    if not actual:
        raise RuntimeError("Remote connection did not report a database name")
    if actual.casefold() != expected.casefold():
        raise RuntimeError(
            "Remote database mismatch: "
            f"expected {expected!r}, connected to {actual!r}. Writes remain disabled."
        )
    return NotebookContext(
        engine=engine,
        settings=runtime.settings,
        mode="remote",
        write_allowed=bool(allow_writes),
        destination=f"remote SQL database: {actual}",
    )


def connect(
    *,
    mode: str,
    runtime_module: str | None = None,
    local_root: str | Path | None = None,
    expected_remote_database: str | None = None,
    allow_remote_writes: bool = False,
) -> NotebookContext:
    """Open local SQLite storage or connect through a project's SQL runtime.

    Local mode creates or opens audit databases beneath ``local_root``.
    Remote mode checks the connected database against ``expected_remote_database``;
    mutating operations also require ``allow_remote_writes=True``.
    Return a ``NotebookContext`` shared by the remaining notebook operations.
    """
    selected_mode = str(mode).strip().lower()
    if selected_mode == "local":
        return _connect_local(local_root)
    if selected_mode == "remote":
        return _connect_remote(
            runtime_module,
            expected_database=expected_remote_database,
            allow_writes=allow_remote_writes,
        )
    raise ValueError("mode must be 'local' or 'remote'")


def register_model(
    pricing: NotebookContext,
    spec: PricingModelSpec,
    *,
    source_root: str | Path,
    created_by: str | None = None,
) -> RegisteredModel:
    """Create or validate the SQL registry entry and return a fitting reference.

    ``source_root`` is the model directory whose source files become build evidence.
    An existing registration must match the supplied stable model identity.
    """
    pricing.require_write("register_model")
    root = Path(source_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"source_root does not exist: {root}")
    config = ModelBuildConfig(
        model_name=spec.name,
        model_label=spec.label,
        target_name=spec.target,
        model_type=spec.model_type,
        deployment_slot=spec.deployment_slot,
        validation_split=spec._validation_config(),
    )
    identity = _created_by(created_by)
    if pricing.mode == "local":
        record = register_sqlite_model(
            pricing.engine,
            config,
            created_by=identity,
        )
        return RegisteredModel(
            model_id=int(record.model_id),
            config=config,
            source_root=root,
            spec=spec,
        )

    with pricing.engine.begin() as connection:
        record = register_pricing_model(
            connection,
            config,
            created_by=identity,
        )
    return RegisteredModel(
        model_id=int(record.model_id),
        config=config,
        source_root=root,
        spec=spec,
    )


def load_registered_model(
    pricing: NotebookContext,
    *,
    source_root: str | Path,
    deployment_slot: str,
    model_name: str | None = None,
    model_label: str | None = None,
) -> RegisteredModel:
    """Find a registered SQL model by name or label for review and deployment.

    Return a ``RegisteredModel`` with no fitting spec. Use ``register_model``
    with a ``PricingModelSpec`` when preparing a new fit.
    """
    name = None if model_name is None else _required_text(model_name, "model_name")
    label = None if model_label is None else _required_text(model_label, "model_label")
    if name is None and label is None:
        raise ValueError("provide model_name or model_label")
    slot = _required_text(deployment_slot, "deployment_slot").upper()
    root = Path(source_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"source_root does not exist: {root}")

    schemas = schema_names_from_connectable(pricing.engine)
    filters = []
    params: dict[str, str] = {}
    if name is not None:
        filters.append("model_name = :model_name")
        params["model_name"] = name
    if label is not None:
        filters.append("model_label = :model_label")
        params["model_label"] = label
    with pricing.engine.connect() as connection:
        rows = (
            connection.execute(
                text(
                    f"""
                    SELECT
                        model_id,
                        model_name,
                        model_label,
                        target_name,
                        model_type,
                        model_status
                    FROM {schemas.pricing}.PRICING_MODEL
                    WHERE {" AND ".join(filters)}
                    """
                ),
                params,
            )
            .mappings()
            .all()
        )
    if len(rows) != 1:
        selection = ", ".join(f"{key}={value!r}" for key, value in params.items())
        raise LookupError(f"model selection {selection} resolved {len(rows)} rows; expected one")
    row = rows[0]
    if str(row["model_status"]).upper() != "ACTIVE":
        raise ValueError(f"model {row['model_name']!r} is {row['model_status']!r}, not ACTIVE")
    config = ModelBuildConfig(
        model_name=str(row["model_name"]),
        model_label=str(row["model_label"] or row["model_name"]),
        target_name=str(row["target_name"]),
        model_type=str(row["model_type"]),
        deployment_slot=slot,
        validation_split=ValidationSplitConfig.kfold(),
    )
    return RegisteredModel(
        model_id=int(row["model_id"]),
        config=config,
        source_root=root,
        spec=None,
    )


def list_model_versions(
    pricing: NotebookContext,
    *,
    model: RegisteredModel,
    technical: bool = False,
) -> pd.DataFrame:
    """Return saved model versions newest first, with metrics and lineage.

    Use this list to select a package for ``load_model_version``. Listing does
    not deserialize fitted-model artifacts.
    """
    return Workbench(
        engine=pricing.engine,
        settings=pricing.settings,
        model_config=model.config,
    ).candidates(model.name, technical=technical)


def _normalise_notebook_date(value: Any, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a date, datetime, or ISO date string")
    cleaned = value.strip()
    try:
        return datetime.fromisoformat(cleaned).date()
    except ValueError:
        try:
            return date.fromisoformat(cleaned)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a date, datetime, or ISO date string") from exc


def _resolve_data_as_of(
    frame: pd.DataFrame,
    *,
    explicit: date | datetime | str | None,
    column: str | None,
) -> date:
    column_value: date | None = None
    if column is not None:
        if column not in frame.columns:
            raise ValueError(f"data-as-of column is missing from model frame: {column}")
        if frame[column].isna().any():
            raise ValueError(f"data-as-of column {column!r} contains null values")
        values = {_normalise_notebook_date(value, "data_as_of") for value in frame[column]}
        if len(values) != 1:
            raise ValueError(f"data-as-of column {column!r} must contain exactly one date")
        column_value = values.pop()

    explicit_value = None if explicit is None else _normalise_notebook_date(explicit, "data_as_of")
    if explicit_value is not None and column_value is not None and explicit_value != column_value:
        raise ValueError("explicit data_as_of does not match the configured data-as-of column")
    resolved = explicit_value or column_value
    if resolved is None:
        raise ValueError("provide data_as_of or configure PricingModelSpec.data_as_of_column")
    return resolved


def fit_model(
    pricing: NotebookContext,
    *,
    model: RegisteredModel,
    frame: pd.DataFrame,
    superglm_model: Any,
    model_kind: str = "RAW",
    data_as_of: date | datetime | str | None = None,
    created_by: str | None = None,
) -> BuiltCandidate:
    """Run cross-validation and a full fit, then return a ``BuiltCandidate``.

    ``frame`` must contain the prepared dataset, including declared transforms.
    The configured SuperGLM model is cloned before fitting. This call reserves a
    model version, records dataset/split evidence and writes local review artifacts.

    Use ``save_model_version`` to publish the rating package. Recipe revisions
    are assigned on save; this call does not deploy the model.
    """
    pricing.require_write("fit_model")
    resolved_model_kind = normalise_model_kind(model_kind)
    spec = model.spec
    if spec is None:
        raise ValueError(
            "fit_model requires a model returned by register_model(), "
            "not a review-only SQL model reference"
        )
    if spec.dataset is not None:
        spec.dataset.validate_prepared(frame, spec.transforms)
    elif spec.transforms:
        # Legacy specs may still supply provenance as individual fields.
        missing_outputs = set(spec.transforms) - set(frame.columns)
        if missing_outputs:
            raise ValueError(
                "prepared data is missing transform outputs: " + ", ".join(sorted(missing_outputs))
            )
        expected = apply_transforms(frame.drop(columns=list(spec.transforms)), spec.transforms)
        for output in spec.transforms:
            try:
                pd.testing.assert_series_equal(frame[output], expected[output], check_exact=True)
            except AssertionError as exc:
                raise ValueError(
                    f"prepared column {output!r} does not match its transform"
                ) from exc
    validation_split = spec._validation_config()
    required_columns = {
        *spec.features,
        *spec.pk_columns,
        spec.target,
        spec.offset_column,
        spec.offset_source_column,
        spec.sample_weight_column,
        spec.export_weight_column,
        spec.data_as_of_column,
        validation_split.stratify_column,
        spec.groups_column,
    }
    required_columns.discard(None)
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError("model frame is missing declared columns: " + ", ".join(missing_columns))

    resolved_data_as_of = _resolve_data_as_of(
        frame,
        explicit=data_as_of,
        column=spec.data_as_of_column,
    )
    row_ids = frame.loc[:, list(spec.pk_columns)].copy()
    identity_index = canonical_row_identity_index(row_ids)
    aligned_frame = frame.copy()
    aligned_frame.index = identity_index
    X = aligned_frame.loc[:, list(spec.features)]
    y = aligned_frame[spec.target].astype(float)
    sample_weight = None
    if spec.sample_weight_column is not None:
        column = spec.sample_weight_column
        sample_weight = aligned_frame[column].astype(float)
    offset = None
    offset_source = None
    export_weight = None
    offset_contract = None
    if spec.offset_column is not None:
        offset = aligned_frame[spec.offset_column].astype(float)
        if not np.isfinite(offset.to_numpy()).all():
            raise ValueError(
                f"offset column {spec.offset_column!r} must contain finite numeric values"
            )
        source_column = spec.offset_source_column
        offset_source = aligned_frame[source_column].copy()
        offset_contract = OffsetExportContract(
            handling="EXPORTED_FACTOR",
            source_factor_name=source_column,
            published_factor_name=clean_identifier(source_column),
            source_name=source_column,
            label=spec.offset_label,
        )
    if spec.export_weight_column is not None:
        export_weight = aligned_frame[spec.export_weight_column].astype(float)

    if isinstance(spec.validation, ValidationSplitConfig):
        resolved_split_indices = validation_split_indices(frame, validation_split)
    else:
        split_options = {}
        if spec.groups_column is not None:
            groups = frame[spec.groups_column]
            if groups.isna().any():
                raise ValueError(f"groups column {spec.groups_column!r} contains null values")
            split_options["groups"] = groups.copy()
        # A splitter sees all prepared columns, including dates and business identifiers.
        # Save the resulting positions once; fitting and publication replay those folds.
        resolved_split_indices = list(
            PrecomputedSplitter(
                spec.validation.split(frame.copy(), frame[spec.target].copy(), **split_options),
                row_count=len(frame),
            ).folds
        )
    # Own the final declared choices after input validation and before CV or full fitting.
    spec = replace(spec)
    superglm_model = superglm_model.clone_unfitted()
    try:
        recipe_capture = RecipeCapture.captured(
            ModelRecipe.from_model(superglm_model, spec=spec).document
        )
    except UnsupportedRecipeError as exc:
        recipe_capture = RecipeCapture(
            status="UNSUPPORTED", unavailable_reason=str(exc), environment=capture_environment()
        )
        warnings.warn(
            f"Model recipe unsupported: {exc}. Python fitting remains available without a verified recipe revision.",
            UserWarning,
            stacklevel=2,
        )
    resolved_run_key = _new_notebook_run_key()
    export_id = build_export_id(model.name, resolved_run_key)
    if pricing.mode == "local":
        model_version = resolve_sqlite_model_version(
            pricing.engine,
            model_name=model.name,
            export_id=export_id,
        )
    else:
        model_version = resolve_model_version_for_export(
            pricing.engine,
            model_name=model.name,
            export_id=export_id,
        )
    inputs = ModelInputs(
        X=X,
        y=y,
        sample_weight=sample_weight,
        sample_weight_name=spec.sample_weight_column,
        offset=offset,
        offset_source=offset_source,
        offset_source_name=spec.offset_source_column,
        export_weight=export_weight,
        export_weight_name=spec.export_weight_column,
        row_ids=row_ids,
    )
    artifact_root = Path(pricing.settings.workbench_artifact_root)
    if pricing.mode == "local":
        artifact_root /= "runs"
    completed_build = run_standard_superglm_build(
        pricing.engine,
        frame=frame,
        inputs=inputs,
        superglm_model=superglm_model,
        split_indices=resolved_split_indices,
        fit_mode=spec.fit_mode,
        scoring=spec.scoring,
        output_dir=artifact_root / resolved_run_key,
        model_id=model.model_id,
        model_config=(
            model.config
            if model.config.validation_split == validation_split
            else replace(model.config, validation_split=validation_split)
        ),
        model_kind=resolved_model_kind,
        model_version=model_version,
        export_id=export_id,
        effective_from=None,
        manifest_spec=ModelFrameManifestSpec(
            dataset_name=spec.dataset_name,
            source_system=spec.source_system,
            data_as_of_date=resolved_data_as_of,
            pk_columns=spec.pk_columns,
            target_column=spec.target,
            weight_column=spec.sample_weight_column,
            feature_columns=spec.features,
            offset_column=spec.offset_column,
            offset_source_column=spec.offset_source_column,
            offset_label=spec.offset_label,
            export_weight_column=spec.export_weight_column,
            data_as_of_column=spec.data_as_of_column,
        ),
        split_artifact_root=pricing.settings.validation_split_artifact_root,
        model_source_root=model.source_root,
        created_by=_created_by(created_by),
        offset_contract=offset_contract,
        input_transforms=transforms_metadata(spec.transforms) or None,
        continuous_kind="ppform" if spec.spline_export == "exact" else "binned",
        recipe_capture=recipe_capture,
    )
    return BuiltCandidate(model=model, completed_build=completed_build)


def save_model_version(
    pricing: NotebookContext,
    candidate: BuiltCandidate,
) -> CompletedModelPublishResult:
    """Publish a fitted candidate's rating package and evidence to the database.

    Verify the artifacts and reuse an equivalent publication when one exists.
    Return ``CompletedModelPublishResult`` with package identity and recipe
    revision. Activation requires a separate ``deploy_model_version`` call.
    """
    pricing.require_write("save_model_version")
    if pricing.mode == "local":
        return publish_sqlite_candidate(
            pricing.engine,
            settings=pricing.settings,
            model_id=candidate.model.model_id,
            model_config=candidate.model.config,
            completed_build=candidate.completed_build,
            created_by=candidate.completed_build.created_by,
        )
    # The remote publisher may remove a redundant incoming artifact directory.
    # Retain only evidence checked against those bytes before the cleanup occurs.
    verified_recipe = (
        candidate.recipe if candidate.completed_build.recipe_status == "CAPTURED" else None
    )
    result = publish_completed_model_build(
        pricing.engine,
        settings=pricing.settings,
        model_config=candidate.model.config,
        completed_build=candidate.completed_build,
    )
    build = candidate.completed_build
    if (
        verified_recipe is not None
        and result.was_existing
        and result.deduplicated
        and not Path(build.candidate_artifact_path).exists()
    ):
        if result.recipe_status != "CAPTURED" or result.recipe_sha256 != verified_recipe.sha256:
            raise ValueError("published recipe evidence does not match verified candidate")
        object.__setattr__(
            candidate,
            "_retained_recipe_capture",
            (build.candidate_artifact_path, build.candidate_artifact_sha256, build.recipe_capture),
        )
    return result


def load_model_version(
    pricing: NotebookContext,
    *,
    model: RegisteredModel,
    package_version: int,
):
    """Load a saved package with its verified fitted model and review evidence.

    Return a ``Candidate`` containing SQL lineage, the model bundle and the
    current deployment snapshot. Missing or changed artifacts stop loading.
    """
    if pricing.mode == "local":
        raise RuntimeError(
            "Remote mode is required for the editor; local SQLite records "
            "candidate audit evidence but does not create editable rating tables."
        )
    return Workbench(
        engine=pricing.engine,
        settings=pricing.settings,
        model_config=model.config,
    ).open(
        model.name,
        package_version=int(package_version),
    )


def open_deployed_candidate(
    pricing: NotebookContext,
    *,
    model: RegisteredModel,
):
    """Open the exact package currently deployed in the model's configured slot."""
    versions = list_model_versions(pricing, model=model, technical=True)
    if versions.empty:
        raise LookupError(f"model {model.name!r} has no published candidate packages")
    current_ids = {int(value) for value in versions["current_rate_package_id"].dropna().tolist()}
    if len(current_ids) != 1:
        raise LookupError(
            f"model {model.name!r} has no unambiguous current deployment in "
            f"slot {model.config.deployment_slot!r}"
        )
    selected = versions.loc[versions["rate_package_id"].astype(int).eq(current_ids.pop())]
    if len(selected) != 1:
        raise LookupError(
            f"the current deployment for model {model.name!r} did not resolve one package"
        )
    return load_model_version(
        pricing,
        model=model,
        package_version=int(selected.iloc[0]["package_version"]),
    )


def export_level_groupings(
    candidate: Candidate,
    *,
    editor_session: Any,
    path: str | Path,
    replace: bool = False,
) -> LevelGroupingArtifact:
    """Save editor-created categorical groupings for a later training fit.

    The artifact binds those groupings to the model and data-as-at. Extraction
    of SuperGLM's private grouping state stays in ``level_grouping_artifact``.
    """
    if not isinstance(candidate, Candidate):
        raise TypeError("candidate must come from load_model_version()")
    if str(candidate.technical.get("model_kind") or "").upper() != "RAW":
        raise ValueError("routine level groupings must be exported from a RAW candidate")
    reference_model = getattr(editor_session, "reference_model", None)
    if reference_model is not candidate.bundle.fitted_model:
        raise ValueError("editor_session must have been opened from the selected RAW candidate")
    frame_sha256 = candidate.bundle.model_frame_sha256
    if frame_sha256 is None:
        raise ValueError("selected RAW candidate has no model-frame SHA-256 evidence")
    data_as_of = candidate.technical.get("data_as_of_date")
    if data_as_of is None:
        raise ValueError("selected RAW candidate has no data-as-at evidence")
    return save_editor_level_groupings(
        editor_session,
        path,
        source_model_name=candidate.model_name,
        source_package_version=candidate.package_version,
        source_manifest_id=candidate.bundle.manifest_id,
        source_model_frame_sha256=frame_sha256,
        source_data_as_of_date=data_as_of,
        replace=replace,
    )


def load_level_groupings(
    path: str | Path,
    *,
    frame: pd.DataFrame,
    model: RegisteredModel,
) -> dict[str, Any]:
    """Load editor-exported groupings for this exact model and data-as-at."""
    if not isinstance(model, RegisteredModel) or model.spec is None:
        raise TypeError("model must come from register_model()")
    data_as_of = _resolve_data_as_of(
        frame,
        explicit=None,
        column=model.spec.data_as_of_column,
    )
    return _load_level_groupings(
        path,
        frame=frame,
        expected_model_name=model.name,
        expected_data_as_of_date=data_as_of,
        allowed_root=model.source_root,
    )


def inspect_level_groupings(path: str | Path) -> LevelGroupingArtifact:
    """Inspect grouping provenance without deserializing its Python objects."""
    return _inspect_level_groupings(path)


def apply_level_groupings(
    features: Mapping[str, Any],
    groupings: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach loaded groupings to copied SuperGLM categorical feature specs."""
    return _apply_level_groupings(features, groupings)


def publish_edits(
    pricing: NotebookContext,
    *,
    candidate,
    editor_session,
    reason: str,
    created_by: str | None = None,
):
    """Save an editor session and publish its changes as an EDITOR_EDIT child.

    The child retains the selected parent's training lineage. Supply the edit
    reason for its audit record; deployment remains a separate operation.
    """
    pricing.require_write("publish_edits")
    if pricing.mode == "local":
        raise RuntimeError(
            "Remote mode is required for the editor; local SQLite records "
            "candidate audit evidence but does not publish editor revisions."
        )
    if candidate.workbench.engine is not pricing.engine:
        raise ValueError("candidate was opened with a different notebook context")
    identity = _created_by(created_by)
    submission = save_editor_submission(
        candidate,
        editor_session=editor_session,
        reason=_required_text(reason, "reason"),
        claimed_identity=identity,
    )
    return publish_editor_submission(
        pricing.engine,
        settings=pricing.settings,
        submission_path=submission.path,
        submission_sha256=submission.sha256,
        dag_id="notebook_publish_editor_candidate",
        airflow_run_id=f"notebook__{submission.submission_id}",
        created_by=identity,
        model_config=candidate.workbench.model_config,
    )


def publish_manual_adjustment(
    pricing: NotebookContext,
    *,
    review: ManualEditReview,
    created_by: str | None = None,
):
    """Publish a reviewed relative business adjustment as a MANUAL_EDIT child."""
    pricing.require_write("publish_manual_adjustment")
    if pricing.mode == "local":
        raise RuntimeError(
            "Remote mode is required for manual adjustment publication; local SQLite "
            "can validate model-kind and lineage records but cannot publish rating tables."
        )
    if not isinstance(review, ManualEditReview):
        raise TypeError("review must come from apply_manual_adjustment_policy()")
    candidate = review.candidate
    if candidate.workbench.engine is not pricing.engine:
        raise ValueError("manual adjustment candidate was opened with a different context")

    # Reapply the canonical relative policy so later interactive session mutations
    # cannot diverge from the payload recorded in SQL.
    verified = apply_manual_adjustment_policy(candidate, review.policy)
    identity = _created_by(created_by)
    policy_payload = verified.policy.to_payload()
    submission = save_editor_submission(
        candidate,
        editor_session=verified.editor_session,
        reason=verified.policy.reason,
        claimed_identity=identity,
        model_kind="MANUAL_EDIT",
        edit_metadata={
            "manual_adjustment_policy": policy_payload,
            "manual_adjustment_policy_sha256": verified.policy.sha256,
        },
    )
    return publish_editor_submission(
        pricing.engine,
        settings=pricing.settings,
        submission_path=submission.path,
        submission_sha256=submission.sha256,
        dag_id="notebook_publish_manual_adjustment",
        airflow_run_id=f"notebook__{submission.submission_id}",
        created_by=identity,
        model_config=candidate.workbench.model_config,
    )


def deploy_model_version(
    pricing: NotebookContext,
    *,
    package: Candidate,
    reason: str,
    deployed_by: str | None = None,
):
    """Deploy a saved model version using the deployment snapshot reviewed with it."""
    pricing.require_write("deploy_model_version")
    if pricing.mode == "local":
        raise RuntimeError(
            "Remote mode is required for deployment; local SQLite is an audit "
            "workbench and cannot change a live package."
        )
    if not isinstance(package, Candidate):
        raise TypeError(
            "package must come from load_model_version(); deployment requires the "
            "champion snapshot that was visible during review"
        )
    if package.workbench.engine is not pricing.engine:
        raise ValueError("package was opened with a different notebook context")
    if "current_rate_package_id" not in package.technical:
        raise ValueError("reviewed package has no champion snapshot")
    current_rate_package_id = package.technical["current_rate_package_id"]
    model_config = package.workbench.model_config
    model_id = int(package.technical.get("model_id", -1))
    if model_id <= 0:
        raise ValueError("reviewed package has no valid SQL model_id")
    return deploy_rate_package(
        pricing.engine,
        model_config,
        rate_package_id=int(package.rate_package_id),
        expected_current_rate_package_id=(
            None if current_rate_package_id is None else int(current_rate_package_id)
        ),
        deployment_reason=_required_text(reason, "reason"),
        deployed_by=_created_by(deployed_by),
        model_id=model_id,
    )


# Compatibility names for notebooks created before the model-version vocabulary.
build_candidate = fit_model
publish_candidate = save_model_version
list_candidate_versions = list_model_versions
open_candidate = load_model_version
deploy_package = deploy_model_version


__all__ = [
    "BuiltCandidate",
    "Clip",
    "Log",
    "Log1p",
    "ManualAdjustmentPolicy",
    "ManualAdjustmentRule",
    "ManualEditReview",
    "ModelFitContract",
    "ModelFrameArtifact",
    "MonitoringFitResult",
    "MonitoringInvariantEvidence",
    "MonitoringVariant",
    "NotebookContext",
    "PersistedMonitoringRun",
    "PricingDataset",
    "PricingModelSpec",
    "RegisteredModel",
    "apply_level_groupings",
    "apply_manual_adjustment_policy",
    "apply_transforms",
    "build_candidate",
    "build_model_fit_contract",
    "connect",
    "deploy_model_version",
    "deploy_package",
    "export_level_groupings",
    "fit_model",
    "inspect_level_groupings",
    "inspect_model_frame",
    "list_candidate_versions",
    "list_model_versions",
    "load_level_groupings",
    "load_model_frame",
    "load_model_version",
    "load_registered_model",
    "manual_adjustment_policy_from_candidate",
    "open_candidate",
    "open_deployed_candidate",
    "persist_monitoring_fit",
    "publish_candidate",
    "publish_edits",
    "publish_manual_adjustment",
    "register_model",
    "run_monitoring_fit",
    "save_model_frame",
    "save_model_version",
]
