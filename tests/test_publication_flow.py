import pytest

from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.models.spec import ApprovedModelBuild
from pricing_pipeline.publishing.publish import PublicationRequest, prepare_publication


@pytest.mark.parametrize(
    "model_kind",
    ("RAW", "ROUTINE_EDIT", "EDITOR_EDIT", "MANUAL_EDIT"),
)
def test_publication_request_carries_every_supported_model_kind(model_kind):
    build = ApprovedModelBuild.model_construct(
        model_kind=model_kind,
        export_id="export-1",
        effective_from=None,
    )
    model_config = ModelBuildConfig(
        model_name="CLAIM_FREQ",
        model_label="Claim frequency",
        target_name="claim_count",
        model_type="superglm_poisson",
        deployment_slot="CLAIM_FREQ_CURRENT",
    )
    request = PublicationRequest(
        build=build,
        model_config=model_config,
        execution_name="notebook",
        execution_id=build.export_id,
        allowed_artifact_root=None,
    )

    prepared = prepare_publication(request)

    assert prepared.build.model_kind == model_kind
    assert prepared.build.export_id == build.export_id
    assert prepared.build.effective_from == build.effective_from
