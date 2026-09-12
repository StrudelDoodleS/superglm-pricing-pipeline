CREATE TABLE pricing.MODEL_RECIPE (
    recipe_id BIGINT IDENTITY(1, 1) NOT NULL,
    model_id INT NOT NULL,
    recipe_revision INT NOT NULL,
    recipe_sha256 CHAR(64) COLLATE Latin1_General_100_BIN2 NOT NULL,
    recipe_format_version INT NOT NULL,
    recipe_json NVARCHAR(MAX) NOT NULL,
    created_ts DATETIME2(3) NOT NULL CONSTRAINT DF_MODEL_RECIPE_CREATED_TS DEFAULT SYSUTCDATETIME(),
    created_by NVARCHAR(128) NOT NULL,
    CONSTRAINT PK_MODEL_RECIPE PRIMARY KEY (recipe_id),
    CONSTRAINT FK_MODEL_RECIPE_MODEL FOREIGN KEY (model_id) REFERENCES pricing.PRICING_MODEL(model_id),
    CONSTRAINT UQ_MODEL_RECIPE_REVISION UNIQUE (model_id, recipe_revision),
    CONSTRAINT UQ_MODEL_RECIPE_SHA256 UNIQUE (model_id, recipe_sha256),
    CONSTRAINT UQ_MODEL_RECIPE_MODEL_ID UNIQUE (model_id, recipe_id),
    CONSTRAINT CK_MODEL_RECIPE_REVISION CHECK (recipe_revision > 0),
    CONSTRAINT CK_MODEL_RECIPE_FORMAT CHECK (recipe_format_version = 1),
    CONSTRAINT CK_MODEL_RECIPE_JSON CHECK (ISJSON(recipe_json) = 1 AND LEFT(LTRIM(recipe_json), 1) = '{'),
    CONSTRAINT CK_MODEL_RECIPE_SHA256 CHECK (LEN(recipe_sha256) = 64 AND recipe_sha256 NOT LIKE '%[^0-9a-f]%')
);
GO
ALTER TABLE pricing.MODEL_RUN ADD
    recipe_id BIGINT NULL,
    recipe_status VARCHAR(16) NOT NULL CONSTRAINT DF_MODEL_RUN_RECIPE_STATUS DEFAULT 'LEGACY',
    recipe_unavailable_reason NVARCHAR(2000) NULL;
GO
ALTER TABLE pricing.MODEL_RUN ADD
    CONSTRAINT FK_MODEL_RUN_RECIPE FOREIGN KEY (model_id, recipe_id)
        REFERENCES pricing.MODEL_RECIPE(model_id, recipe_id);
GO
ALTER TABLE pricing.MODEL_RUN ADD
    CONSTRAINT CK_MODEL_RUN_RECIPE_STATUS CHECK (
        (recipe_status = 'CAPTURED' AND recipe_id IS NOT NULL AND recipe_unavailable_reason IS NULL)
        OR (recipe_status = 'LEGACY' AND recipe_id IS NULL AND recipe_unavailable_reason IS NULL)
        OR (recipe_status = 'UNSUPPORTED' AND recipe_id IS NULL
            AND recipe_unavailable_reason IS NOT NULL AND LEN(LTRIM(RTRIM(recipe_unavailable_reason))) > 0)
    );
GO
-- Recipe and normalized split identity now participate in publication equality.
-- Writers lock PRICING_MODEL WITH (UPDLOCK, HOLDLOCK) before lookup and insertion.
-- A table-local uniqueness key cannot include the normalized split-set link.
DROP INDEX UX_MODEL_RUN_EQUIVALENT_SUCCESS ON pricing.MODEL_RUN;
CREATE INDEX IX_MODEL_RUN_EQUIVALENT_SUCCESS
ON pricing.MODEL_RUN (model_id, manifest_id, model_kind, model_equivalence_sha256)
INCLUDE (recipe_id, recipe_status)
WHERE model_equivalence_sha256 IS NOT NULL AND run_status = 'SUCCESS';
GO
CREATE OR ALTER TRIGGER pricing.TR_MODEL_RECIPE_IMMUTABLE
ON pricing.MODEL_RECIPE AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (SELECT 1 FROM deleted)
        THROW 51047, 'Model recipes are immutable.', 1;
END;
GO
CREATE OR ALTER TRIGGER pricing.TR_MODEL_RUN_RECIPE_IMMUTABLE
ON pricing.MODEL_RUN AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT historical.model_run_id, historical.recipe_id, historical.recipe_status, historical.recipe_unavailable_reason
        FROM deleted AS historical WHERE historical.run_status = 'SUCCESS'
        EXCEPT
        SELECT current_run.model_run_id, current_run.recipe_id, current_run.recipe_status, current_run.recipe_unavailable_reason
        FROM inserted AS current_run
    )
        THROW 51048, 'Published run recipe links are immutable.', 1;
END;
GO
EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'Immutable canonical model recipes. Revisions are allocated per registered model during publication; builds retain their own dataset and execution evidence.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'TABLE', @level1name=N'MODEL_RECIPE';
EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'Automatically allocated declared recipe revision. Reverting to the same canonical recipe reuses its revision; it is distinct from model_version and package_version.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'TABLE', @level1name=N'MODEL_RECIPE', @level2type=N'COLUMN', @level2name=N'recipe_revision';
EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'CAPTURED links a verified recipe. Historical rows remain LEGACY. UNSUPPORTED preserves Python fitting with an explicit unavailable reason.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'TABLE', @level1name=N'MODEL_RUN', @level2type=N'COLUMN', @level2name=N'recipe_status';
GO
