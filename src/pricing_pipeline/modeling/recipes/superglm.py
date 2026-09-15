"""Supported SuperGLM constructor settings for saving and loading recipes.

All private SuperGLM access for recipes lives here. ``_config`` owns pristine
constructor templates; ``clone_unfitted`` materializes them independently after
fitting as well as before it. Read those templates, never fitted ``_specs`` or
resolved penalties. Ordered categoricals retain declared smooth labels, original
numeric positions and a pristine inner basis separately from their fitted basis.
LevelGrouping itself stores strings; typed declared domains are encoded separately.

Constructor signature guards fail on added library parameters. Resource retention
is execution-only; every other supported estimator parameter affects semantics.
Auto-detected features, custom classes and new interaction types are not portable.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from dataclasses import asdict, fields

import numpy as np
from sklearn.model_selection import GroupKFold, KFold, TimeSeriesSplit
from superglm import (
    Categorical,
    CategoricalInteraction,
    ConstraintSpec,
    LambdaPolicy,
    Numeric,
    OrderedCategorical,
    Polynomial,
    Spline,
    SuperGLM,
    distributions,
    links,
    penalties,
)
from superglm.features.grouping import LevelGrouping
from superglm.features.spline import (
    BSplineSmooth,
    CardinalCRSpline,
    CubicRegressionSpline,
    NaturalSpline,
    PSpline,
)

from pricing_pipeline.data.transforms import Clip, Log, Log1p
from pricing_pipeline.models.config import ValidationSplitConfig

from .schema import RecipeError, UnsupportedRecipeError, freeze, thaw

ESTIMATOR_FIELDS = frozenset(
    [
        "family",
        "link",
        "penalty",
        "selection_penalty",
        "spline_penalty",
        "penalty_features",
        "features",
        "splines",
        "n_knots",
        "degree",
        "categorical_base",
        "interactions",
        "active_set",
        "direct_solve",
        "discrete",
        "n_bins",
        "tol",
        "max_iter",
        "convergence",
        "retain_fit_state",
        "separation",
        "group_pricing",
        "weight_semantics",
    ]
)
SPLINE_FIELDS = frozenset(
    [
        "kind",
        "k",
        "n_knots",
        "degree",
        "knot_strategy",
        "penalty",
        "select",
        "knots",
        "discrete",
        "n_bins",
        "extrapolation",
        "boundary",
        "knot_alpha",
        "constraint",
        "m",
        "lambda_policy",
    ]
)
SPLINE_KINDS = {
    BSplineSmooth: "bs",
    PSpline: "ps",
    NaturalSpline: "ns",
    CubicRegressionSpline: "cr",
    CardinalCRSpline: "cr_cardinal",
}
OBJECT_TYPES = {
    "family": {
        n: getattr(distributions, n)
        for n in ("Poisson", "Gaussian", "Gamma", "Binomial", "Tweedie", "NegativeBinomial")
    },
    "link": {
        n: getattr(links, n)
        for n in (
            "LogLink",
            "IdentityLink",
            "LogitLink",
            "ProbitLink",
            "CloglogLink",
            "CauchitLink",
            "InverseLink",
            "InverseSquaredLink",
            "SqrtLink",
            "PowerLink",
            "NegativeBinomialLink",
        )
    },
    "penalty": {
        n: getattr(penalties, n)
        for n in ("GroupLasso", "GroupElasticNet", "SparseGroupLasso", "Ridge")
    },
    "flavor": {"Adaptive": penalties.Adaptive},
}
OBJECT_FIELDS = {
    "Poisson": (),
    "Gaussian": (),
    "Gamma": (),
    "Binomial": (),
    "Tweedie": ("p",),
    "NegativeBinomial": ("theta",),
    **{n: () for n in OBJECT_TYPES["link"]},
    "PowerLink": ("power",),
    "NegativeBinomialLink": ("theta",),
    "GroupLasso": ("lambda1", "flavor", "features"),
    "GroupElasticNet": ("lambda1", "alpha", "flavor", "features"),
    "SparseGroupLasso": ("lambda1", "alpha", "flavor", "features"),
    "Ridge": ("lambda1", "features"),
    "Adaptive": ("expon", "eps"),
}


def _plain(value, path):
    """Normalize NumPy values at every depth before validating recipe data."""
    if isinstance(value, np.ndarray):
        value = value.tolist()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, Mapping):
        value = {key: _plain(item, f"{path}.{key}") for key, item in value.items()}
    elif isinstance(value, (list, tuple)):
        value = [_plain(item, f"{path}[{i}]") for i, item in enumerate(value)]
    return thaw(freeze(value, path))


def _checked(data, allowed, path):
    if not isinstance(data, dict):
        raise RecipeError(f"{path}: expected a table")
    extra = set(data) - set(allowed)
    if extra:
        raise RecipeError(f"{path}.{min(extra)}: unknown field")
    return dict(data)


def _construct(cls, kwargs, path):
    try:
        return cls(**kwargs)
    except (TypeError, ValueError, NotImplementedError) as exc:
        raise RecipeError(f"{path}: {exc}") from exc


def _guard_signature(cls, expected, path):
    actual = set(inspect.signature(cls).parameters)
    if actual != set(expected):
        raise UnsupportedRecipeError(
            f"{path}: installed {cls.__name__} constructor changed; expected {sorted(expected)}, got {sorted(actual)}"
        )


def encode_object(obj, category, path):
    if obj is None or isinstance(obj, str):
        return obj
    name = type(obj).__name__
    if OBJECT_TYPES[category].get(name) is not type(obj):
        raise UnsupportedRecipeError(
            f"{path}: unsupported {type(obj).__module__}.{type(obj).__qualname__}"
        )
    params = OBJECT_FIELDS[name]
    _guard_signature(type(obj), params, path)
    data = {"type": name}
    for key in params:
        value = getattr(obj, key)
        data[key] = (
            encode_object(value, "flavor", f"{path}.{key}")
            if key == "flavor"
            else _plain(value, f"{path}.{key}")
        )
    return data


def decode_object(data, category, path):
    if data is None or isinstance(data, str):
        return data
    if not isinstance(data, dict):
        raise RecipeError(f"{path}: expected a name or constructor table")
    name = data.get("type")
    if not isinstance(name, str) or name not in OBJECT_TYPES[category]:
        raise UnsupportedRecipeError(f"{path}.type: unsupported {name!r}")
    kwargs = _checked(data, ("type", *OBJECT_FIELDS[name]), path)
    kwargs.pop("type")
    if "flavor" in kwargs:
        kwargs["flavor"] = decode_object(kwargs["flavor"], "flavor", f"{path}.flavor")
    return _construct(OBJECT_TYPES[category][name], kwargs, path)


def _labels(levels, path):
    values = _plain(levels, path)
    if not isinstance(values, list):
        raise RecipeError(f"{path}: expected an array of levels")
    if any(type(v) not in (str, int, float, bool) for v in values):
        raise RecipeError(f"{path}: levels must be scalar strings, numbers or booleans")
    for i, value in enumerate(values):
        if any(
            str(value) == str(other)
            or (not isinstance(value, str) and not isinstance(other, str) and value == other)
            for other in values[:i]
        ):
            raise RecipeError(f"{path}: duplicate or ambiguous level {value!r}")
    return values


def encode_grouping(grouping, path):
    if grouping is None:
        return [], None
    if type(grouping) is not LevelGrouping:
        raise UnsupportedRecipeError(f"{path}: unsupported {type(grouping).__name__}")
    groups = [
        {"name": name, "levels": list(grouping.group_to_originals[name])}
        for name in grouping.grouped_levels
    ]
    # Validate both directions rather than accepting a malformed public dataclass.
    rebuilt = decode_grouping(groups, list(grouping.all_original_levels), path)
    if rebuilt.original_to_group != grouping.original_to_group:
        raise RecipeError(f"{path}: inconsistent group membership mappings")
    return groups, list(grouping.all_original_levels)


def decode_grouping(groups, domain, path):
    if not groups:
        if domain:
            raise RecipeError(f"{path}: group_domain requires groups")
        return None
    originals = {}
    by_group = {}
    for raw in groups:
        group = _checked(raw, ("name", "levels"), path)
        if set(group) != {"name", "levels"}:
            raise RecipeError(f"{path}: each group requires name and levels")
        name = group["name"]
        if not isinstance(name, str) or not name or name in by_group:
            raise RecipeError(f"{path}: duplicate or invalid group name {name!r}")
        levels = _labels(group["levels"], path)
        if not levels:
            raise RecipeError(f"{path}: group {name} must contain levels")
        by_group[name] = [str(v) for v in levels]
        for level in levels:
            key = str(level)
            if key in originals:
                raise RecipeError(f"{path}: level {level} belongs to two groups")
            originals[key] = name
    domain = list(originals) if domain is None else _labels(domain, path + ".domain")
    if set(map(str, domain)) != set(originals):
        raise RecipeError(f"{path}: group_domain must contain every grouped level exactly once")
    return LevelGrouping(
        original_to_group=originals,
        group_to_originals=by_group,
        all_original_levels=list(map(str, domain)),
        grouped_levels=list(by_group),
    )


def encode_policy(value, path):
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: encode_policy(v, f"{path}.{k}") for k, v in value.items()}
    if type(value) is not LambdaPolicy:
        raise UnsupportedRecipeError(f"{path}: unsupported {type(value).__name__}")
    return asdict(value)


def decode_policy(value, path):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise RecipeError(f"{path}: expected a policy table")
    if "mode" in value:
        return _construct(LambdaPolicy, _checked(value, ("mode", "value"), path), path)
    return {k: decode_policy(v, f"{path}.{k}") for k, v in value.items()}


def encode_feature(feature, path):
    kind = type(feature)
    signatures = {
        Numeric: (),
        Polynomial: ("degree", "powers"),
        Categorical: ("base", "grouping", "levels", "unseen"),
        OrderedCategorical: ("values", "order", "basis", "base", "grouping", "specials"),
    }
    if kind in signatures:
        _guard_signature(kind, signatures[kind], path)
    elif kind in SPLINE_KINDS:
        _guard_signature(Spline, SPLINE_FIELDS, path)
    if kind is Numeric:
        return {"type": "Numeric"}
    if kind is Polynomial:
        return {"type": "Polynomial", "powers": list(feature.powers)}
    if kind in (Categorical, OrderedCategorical):
        groups, domain = encode_grouping(feature._grouping, path + ".groups")
        result = {
            "type": kind.__name__,
            "base": _plain(feature.base, path + ".base"),
            "groups": groups,
            "group_domain": domain,
        }
        if kind is Categorical:
            result.update(
                levels=None
                if feature._declared_levels is None
                else _labels(feature._declared_levels, path + ".levels"),
                unseen=feature.unseen,
            )
        else:
            levels = feature._declared_smooth_levels
            positions = (
                feature._original_level_to_value
                if feature._original_level_to_value is not None
                else feature._level_to_value
            )
            result.update(
                values=[
                    {
                        "level": _plain(level, path),
                        "value": float(
                            positions[str(level)]
                            if feature._original_level_to_value is not None
                            else positions[level]
                        ),
                    }
                    for level in levels
                ],
                specials=_labels(feature._special_raw, path + ".specials"),
                basis=encode_feature(feature._spline_obj, path + ".basis"),
            )
            display = _labels(feature._special_display, path + ".special_domain")
            if any(
                type(raw) is not type(label) or raw != label
                for raw, label in zip(feature._special_raw, display, strict=True)
            ):
                result["special_domain"] = display
        return result
    if kind in SPLINE_KINDS:
        result = {"type": "Spline", "kind": SPLINE_KINDS[kind]}
        for key in (
            "n_knots",
            "degree",
            "knot_strategy",
            "penalty",
            "select",
            "discrete",
            "n_bins",
            "extrapolation",
            "knot_alpha",
        ):
            result[key] = _plain(getattr(feature, key), path + "." + key)
        result.update(
            knots=_plain(
                feature._named_knots
                if feature._named_knots is not None
                else feature._explicit_knots,
                path + ".knots",
            ),
            boundary=_plain(feature._explicit_boundary, path + ".boundary"),
            m=list(feature._m_orders),
            lambda_policy=encode_policy(feature._lambda_policy, path + ".lambda_policy"),
            constraint=None
            if feature.constraint_kind is None
            else {"kind": feature.constraint_kind, "mode": feature.constraint_mode},
        )
        return result
    raise UnsupportedRecipeError(f"{path}: unsupported {kind.__module__}.{kind.__qualname__}")


def _matches_special(label, raw):
    return str(label) == str(raw) or (
        not isinstance(label, str) and not isinstance(raw, str) and label == raw
    )


def decode_feature(data, path):
    if not isinstance(data, dict):
        raise RecipeError(f"{path}: expected a feature table")
    name = data.get("type")
    if name == "Numeric":
        _checked(data, ("type",), path)
        return Numeric()
    if name == "Polynomial":
        kwargs = _checked(data, ("type", "degree", "powers"), path)
        kwargs.pop("type")
        return _construct(Polynomial, kwargs, path)
    if name in ("Categorical", "OrderedCategorical"):
        common = ("type", "base", "groups", "group_domain")
        allowed = (
            (*common, "levels", "unseen")
            if name == "Categorical"
            else (*common, "values", "order", "basis", "specials", "special_domain")
        )
        kwargs = _checked(data, allowed, path)
        kwargs.pop("type")
        kwargs["grouping"] = decode_grouping(
            kwargs.pop("groups", []), kwargs.pop("group_domain", None), path + ".groups"
        )
        if name == "Categorical":
            if kwargs.get("levels") is not None:
                kwargs["levels"] = _labels(kwargs["levels"], path + ".levels")
            return _construct(Categorical, kwargs, path)
        if "order" in kwargs:
            kwargs["order"] = _labels(kwargs["order"], path + ".order")
        if "values" in kwargs:
            entries = kwargs["values"]
            for item in entries:
                if set(_checked(item, ("level", "value"), path + ".values")) != {"level", "value"}:
                    raise RecipeError(f"{path}.values: each entry requires level and value")
                if type(item["value"]) not in (int, float):
                    raise RecipeError(f"{path}.values: positions must be finite numbers")
            _labels([v["level"] for v in entries], path + ".values")
            kwargs["values"] = {v["level"]: v["value"] for v in entries}
        if kwargs.get("specials") is not None:
            kwargs["specials"] = _labels(kwargs["specials"], path + ".specials")
        if "special_domain" in kwargs:
            domain = _labels(kwargs.pop("special_domain"), path + ".special_domain")
            specials = kwargs.get("specials") or []
            if len(domain) != len(specials) or any(
                not _matches_special(label, raw)
                for raw, label in zip(specials, domain, strict=False)
            ):
                raise RecipeError(
                    f"{path}.special_domain: must match each declared special in order"
                )
            # Public construction derives display labels from the full domain and
            # removes special positions before building the smooth. Their numeric
            # placeholders therefore have no fitting meaning.
            if "values" in kwargs:
                smooth = {
                    level: value
                    for level, value in kwargs["values"].items()
                    if not any(_matches_special(level, raw) for raw in specials)
                }
                kwargs["values"] = smooth | {label: 0.0 for label in domain}
            elif "order" in kwargs:
                smooth = [
                    level
                    for level in kwargs["order"]
                    if not any(_matches_special(level, raw) for raw in specials)
                ]
                kwargs["order"] = smooth + domain
            else:
                raise RecipeError(f"{path}.special_domain: requires values or order")
        if "basis" in kwargs:
            kwargs["basis"] = decode_feature(kwargs["basis"], path + ".basis")
        return _construct(OrderedCategorical, kwargs, path)
    if name == "Spline":
        kwargs = _checked(data, ("type", *SPLINE_FIELDS), path)
        kwargs.pop("type")
        if kwargs.get("boundary") is not None:
            kwargs["boundary"] = tuple(kwargs["boundary"])
        if isinstance(kwargs.get("m"), list):
            kwargs["m"] = tuple(kwargs["m"])
        if kwargs.get("constraint") is not None:
            kwargs["constraint"] = _construct(
                ConstraintSpec,
                _checked(kwargs["constraint"], ("kind", "mode"), path + ".constraint"),
                path + ".constraint",
            )
        if "lambda_policy" in kwargs:
            kwargs["lambda_policy"] = decode_policy(
                kwargs["lambda_policy"], path + ".lambda_policy"
            )
        return _construct(Spline, kwargs, path)
    raise UnsupportedRecipeError(f"{path}.type: unsupported {name!r}")


def encode_validation(validation):
    if type(validation) is ValidationSplitConfig:
        if validation.method == "none":
            return {"type": "none"}
        if validation.method not in ("kfold", "train_test_split", "column_kfold", "column_holdout"):
            raise UnsupportedRecipeError(
                f"validation: unsupported ValidationSplitConfig method {validation.method!r}"
            )
        data = asdict(validation)
        if any(
            data[key] is not None for key in ("splitter_class", "splitter_params", "groups_column")
        ):
            raise RecipeError(
                "validation: native split config cannot contain custom splitter settings"
            )
        for key in ("materialize", "splitter_class", "splitter_params", "groups_column"):
            data.pop(key)
        data["type"] = data.pop("method")
        return _plain(data, "validation")
    names = {
        KFold: ("n_splits", "shuffle", "random_state"),
        GroupKFold: ("n_splits", "shuffle", "random_state"),
        TimeSeriesSplit: ("n_splits", "max_train_size", "test_size", "gap"),
    }
    if type(validation) not in names:
        raise UnsupportedRecipeError(
            f"validation: unsupported {type(validation).__module__}.{type(validation).__qualname__}"
        )
    params = names[type(validation)]
    _guard_signature(type(validation), params, "validation")
    return {
        "type": type(validation).__name__,
        **{key: _plain(getattr(validation, key), "validation." + key) for key in params},
    }


def decode_validation(data):
    if not isinstance(data, dict):
        raise RecipeError("validation: expected a table")
    name = data.get("type", "kfold")
    splitters = {
        "KFold": (KFold, ("n_splits", "shuffle", "random_state")),
        "GroupKFold": (GroupKFold, ("n_splits", "shuffle", "random_state")),
        "TimeSeriesSplit": (TimeSeriesSplit, ("n_splits", "max_train_size", "test_size", "gap")),
    }
    if not isinstance(name, str):
        raise RecipeError("validation.type: expected a string")
    if name == "none":
        _checked(data, ("type",), "validation")
        return ValidationSplitConfig(method="none", n_splits=None, random_state=None, shuffle=False)
    if name in splitters:
        cls, params = splitters[name]
        kwargs = _checked(data, ("type", *params), "validation")
        kwargs.pop("type", None)
        return _construct(cls, kwargs, "validation")
    if name not in ("kfold", "train_test_split", "column_kfold", "column_holdout"):
        raise UnsupportedRecipeError(f"validation.type: unsupported {name!r}")
    allowed = {f.name for f in fields(ValidationSplitConfig)} - {
        "method",
        "materialize",
        "splitter_class",
        "splitter_params",
        "groups_column",
    }
    kwargs = _checked(data, ("type", *allowed), "validation")
    kwargs.pop("type", None)
    defaults = getattr(ValidationSplitConfig, name)
    # Factories establish the method-specific defaults; explicit exports retain
    # the complete config, including otherwise unused fields for strict parity.
    factory_params = set(inspect.signature(defaults).parameters) - {"materialize"}
    seed = _construct(
        defaults, {k: v for k, v in kwargs.items() if k in factory_params}, "validation"
    )
    resolved = asdict(seed) | kwargs | {"materialize": True}
    for key in ("train_values", "test_values"):
        resolved[key] = tuple(resolved[key])
    result = ValidationSplitConfig(**resolved)
    # Validate column/fold controls using the existing contract without data.
    if name in ("kfold",) and (type(result.n_splits) is not int or result.n_splits < 2):
        raise RecipeError("validation.n_splits: must be an integer >= 2")
    if name.startswith("column_") and not result.column:
        raise RecipeError("validation.column: required for column splits")
    return result


def encode_estimator(model):
    if type(model) is not SuperGLM:
        raise UnsupportedRecipeError(
            f"estimator: unsupported {type(model).__module__}.{type(model).__qualname__}"
        )
    _guard_signature(SuperGLM, ESTIMATOR_FIELDS, "estimator")
    config = model._config
    if not config.features_explicit or config.splines is not None:
        raise UnsupportedRecipeError(
            "estimator.features: automatic feature inference is not portable; declare features explicitly"
        )
    kwargs = config.constructor_kwargs()
    feature_data = {
        name: encode_feature(feature, f"features.{name}")
        for name, feature in config.feature_templates
    }
    if any(not isinstance(name, str) for name in feature_data):
        raise UnsupportedRecipeError("features: portable feature names must be strings")
    interactions = []
    for pair in config.interactions:
        if any(feature_data.get(name, {}).get("type") != "Categorical" for name in pair):
            raise UnsupportedRecipeError(
                "interactions: only existing categorical interactions are export-supported"
            )
        interactions.append({"type": "CategoricalInteraction", "parents": list(pair)})
    for name, interaction in config.interaction_templates:
        if type(interaction) is not CategoricalInteraction:
            raise UnsupportedRecipeError(
                f"interactions.{name}: unsupported {type(interaction).__name__}"
            )
        interactions.append(
            {
                "type": "CategoricalInteraction",
                "parents": list(interaction.parent_names),
                "name": name,
            }
        )
    for key in ("features", "splines", "interactions"):
        kwargs.pop(key)
    # Record the resolved declared link explicitly so a future family default
    # cannot reinterpret an exported recipe. This reads no fitted distribution.
    kwargs["family"] = distributions.resolve_distribution(kwargs["family"])
    kwargs["link"] = links.resolve_link(kwargs["link"], kwargs["family"])
    for key in ("family", "link", "penalty"):
        kwargs[key] = encode_object(kwargs[key], key, "estimator." + key)
    return _plain(kwargs, "estimator"), feature_data, interactions


def decode_estimator(estimator, features, feature_order, interactions):
    _guard_signature(SuperGLM, ESTIMATOR_FIELDS, "estimator")
    kwargs = _checked(
        estimator, ESTIMATOR_FIELDS - {"features", "splines", "interactions"}, "estimator"
    )
    for key in ("family", "link", "penalty"):
        if key in kwargs:
            kwargs[key] = decode_object(kwargs[key], key, "estimator." + key)
    kwargs["features"] = {
        name: decode_feature(features[name], f"features.{name}") for name in feature_order
    }
    pairs = []
    for raw in interactions:
        interaction = _checked(raw, ("type", "parents", "name"), "interactions")
        if interaction.get("type") != "CategoricalInteraction":
            raise UnsupportedRecipeError(
                f"interactions.type: unsupported {interaction.get('type')!r}"
            )
        parents = interaction.get("parents", [])
        if (
            len(parents) != 2
            or parents[0] == parents[1]
            or any(type(kwargs["features"].get(name)) is not Categorical for name in parents)
        ):
            raise RecipeError("interactions.parents: requires two declared Categorical features")
        if "name" in interaction and interaction["name"] != ":".join(parents):
            raise UnsupportedRecipeError(
                "interactions.name: custom named interactions are not portable"
            )
        if tuple(parents) in pairs:
            raise RecipeError("interactions: duplicate categorical interaction")
        pairs.append(tuple(parents))
    kwargs["interactions"] = pairs or None
    return _construct(SuperGLM, kwargs, "estimator")


TRANSFORMS = {"Log": Log, "Log1p": Log1p, "Clip": Clip}


def decode_transforms(data, order):
    result = {}
    for name in order:
        item = data[name]
        if not isinstance(item, dict) or not isinstance(item.get("type"), str):
            raise RecipeError(f"transforms.{name}: expected a transform table with a type")
        cls = TRANSFORMS.get(item.get("type"))
        if cls is None:
            raise UnsupportedRecipeError(
                f"transforms.{name}.type: unsupported {item.get('type')!r}"
            )
        kwargs = _checked(
            item,
            (("type", "source", "lower", "upper") if cls is Clip else ("type", "source")),
            f"transforms.{name}",
        )
        kwargs.pop("type")
        result[name] = _construct(cls, kwargs, f"transforms.{name}")
    return result


def encode_transforms(transforms):
    result = {}
    for name, transform in transforms.items():
        if type(transform) not in TRANSFORMS.values():
            raise UnsupportedRecipeError(
                f"transforms.{name}: unsupported {type(transform).__name__}"
            )
        result[name] = {"type": type(transform).__name__, **asdict(transform)}
    return result


def normalize_document_parts(document):
    data = document.to_dict()
    model = decode_estimator(
        data["estimator"], data["features"], data["feature_order"], data["interactions"]
    )
    estimator, features, interactions = encode_estimator(model)
    transforms = decode_transforms(data["transforms"], data["transform_order"])
    validation = decode_validation(data["validation"])
    # Validate portable roles before dataset binding. Dataset-specific role checks
    # remain the responsibility of PricingModelSpec.build's normal constructor.
    names = (
        "name",
        "label",
        "model_type",
        "deployment_slot",
        "target",
        "groups_column",
        "offset_column",
        "offset_source_column",
        "offset_label",
        "sample_weight_column",
        "export_weight_column",
    )
    for name in names:
        value = data[name]
        if value is not None and (not value.strip() or value != value.strip()):
            raise RecipeError(f"{name}: must be non-empty without surrounding whitespace")
    for name in (*features, *transforms):
        if not name.strip() or name != name.strip():
            raise RecipeError(f"features/transforms.{name}: invalid column name")
    if not data["scoring"] or len(set(data["scoring"])) != len(data["scoring"]):
        raise RecipeError("scoring: requires at least one metric without duplicates")
    if any(not metric.strip() or metric != metric.strip() for metric in data["scoring"]):
        raise RecipeError("scoring: metric names must be non-empty without surrounding whitespace")
    if type(validation) is ValidationSplitConfig and data["groups_column"] is not None:
        raise RecipeError("groups_column: requires a splitter in validation")
    offset = {
        name: data[name] for name in ("offset_column", "offset_source_column", "offset_label")
    }
    if offset["offset_column"] in transforms:
        transform = transforms[offset["offset_column"]]
        for name, expected in (
            ("offset_source_column", transform.source),
            ("offset_label", transform.expression),
        ):
            if offset[name] is not None and offset[name] != expected:
                raise RecipeError(f"{name}: conflicts with the offset transform")
            offset[name] = expected
    if any(value is not None for value in offset.values()) and any(
        value is None for value in offset.values()
    ):
        raise RecipeError(
            "offset_column, offset_source_column, offset_label: must be configured together"
        )
    roles = {
        "target": [data["target"]],
        "feature": list(features),
        "split": [validation.column] if type(validation) is ValidationSplitConfig else [],
        "offset": [offset["offset_column"]],
        "offset source": [offset["offset_source_column"]],
        "sample weight": [data["sample_weight_column"]],
        "export weight": [data["export_weight_column"]],
    }
    seen = {}
    for role, columns in roles.items():
        for column in columns:
            if column is not None:
                seen.setdefault(column, []).append(role)
    overlaps = {
        column: assigned
        for column, assigned in seen.items()
        if len(assigned) > 1 and set(assigned) & {"target", "feature", "split"}
    }
    if overlaps:
        raise RecipeError(f"model column roles overlap: {overlaps}")
    return {
        "estimator": estimator,
        "features": features,
        "interactions": interactions,
        "transforms": encode_transforms(transforms),
        "validation": encode_validation(validation),
        **offset,
    }
