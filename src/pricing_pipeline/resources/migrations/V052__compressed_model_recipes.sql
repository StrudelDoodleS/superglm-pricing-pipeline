-- Apply through the administrator migration runner, which owns the transaction.
ALTER TABLE pricing.MODEL_RECIPE ADD recipe_gzip VARBINARY(MAX) NULL;
GO

-- This migration changes storage only. The transaction retains the table lock
-- while the immutable rows are rewritten and their guard is restored.
ALTER TABLE pricing.MODEL_RECIPE DISABLE TRIGGER TR_MODEL_RECIPE_IMMUTABLE;
UPDATE pricing.MODEL_RECIPE SET recipe_gzip = COMPRESS(recipe_json);
ALTER TABLE pricing.MODEL_RECIPE ENABLE TRIGGER TR_MODEL_RECIPE_IMMUTABLE;

IF EXISTS (
    SELECT 1 FROM pricing.MODEL_RECIPE
    WHERE recipe_gzip IS NULL
       OR DATALENGTH(DECOMPRESS(recipe_gzip)) <> DATALENGTH(recipe_json)
       OR DECOMPRESS(recipe_gzip) <> CONVERT(VARBINARY(MAX), recipe_json)
)
    THROW 51053, 'Recipe compression did not preserve the original JSON bytes.', 1;
GO

ALTER TABLE pricing.MODEL_RECIPE ALTER COLUMN recipe_gzip VARBINARY(MAX) NOT NULL;
ALTER TABLE pricing.MODEL_RECIPE DROP CONSTRAINT CK_MODEL_RECIPE_JSON;
ALTER TABLE pricing.MODEL_RECIPE DROP COLUMN recipe_json;
GO

-- Do not persist this column: only the compressed document occupies storage.
ALTER TABLE pricing.MODEL_RECIPE ADD
    recipe_json AS CAST(DECOMPRESS(recipe_gzip) AS NVARCHAR(MAX));
GO

-- Validate the base column directly; the decoded computed column is not stored.
ALTER TABLE pricing.MODEL_RECIPE WITH CHECK ADD CONSTRAINT CK_MODEL_RECIPE_JSON CHECK (
    ISNULL(ISJSON(CAST(DECOMPRESS(recipe_gzip) AS NVARCHAR(MAX))), 0) = 1
    AND LEFT(LTRIM(CAST(DECOMPRESS(recipe_gzip) AS NVARCHAR(MAX))), 1) = '{'
);
GO

EXEC sys.sp_updateextendedproperty @name=N'MS_Description',
    @value=N'Immutable model recipes stored as gzip. Read recipe_json for decoded canonical JSON. Revisions and hashes identify the definition, independent of compression.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'TABLE', @level1name=N'MODEL_RECIPE';
EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'Gzip-compressed canonical JSON from SQL Server NVARCHAR(MAX), using UTF-16LE bytes. recipe_sha256 still hashes the canonical UTF-8 JSON.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'TABLE', @level1name=N'MODEL_RECIPE', @level2type=N'COLUMN', @level2name=N'recipe_gzip';
EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'Canonical recipe JSON decoded from recipe_gzip when selected. This computed column does not store a second copy of the document.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'TABLE', @level1name=N'MODEL_RECIPE', @level2type=N'COLUMN', @level2name=N'recipe_json';
GO
