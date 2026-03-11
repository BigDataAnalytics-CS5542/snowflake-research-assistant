# Completing the Snowflake VECTOR Migration

These are the remaining steps to finish the migration from VARCHAR-encoded embeddings to Snowflake's native `VECTOR(FLOAT, 768)` type with server-side similarity search.

## Prerequisites

- Snowflake account with VECTOR type support (Enterprise or EDU account)
- Access to the `CS5542_PROJECT_ROHAN_BLAKE_KENNETH` database
- The updated code from `CS_5542_Lab_6` deployed locally

## Step 1: Verify VECTOR Type Support

Run this in a Snowflake worksheet to confirm your account supports the VECTOR type:

```sql
SELECT [1.0, 2.0, 3.0]::VECTOR(FLOAT, 3);
```

If this errors, your account does not support VECTOR and you cannot proceed.

## Step 2: Run the Migration SQL on Existing Data

Open `sql/02_migrate_to_vector_type.sql` in a Snowflake worksheet and execute it. This will:

1. Add a new `EMBEDDING_VEC VECTOR(FLOAT, 768)` column
2. Cast all existing VARCHAR embeddings into it
3. Drop the old VARCHAR column and rename the new one
4. Recreate the `APP.CHUNKS_V` view
5. Run a self-similarity spot-check

**Important:** Run this against the existing database with data already loaded. If you're starting fresh, the schema file (`01_create_schema.sql`) already uses the VECTOR type and no migration is needed.

## Step 3: Verify the Migration

Run this in Snowflake — every row should return `1.0`:

```sql
USE WAREHOUSE ROHAN_BLAKE_KENNETH_WH;
USE DATABASE CS5542_PROJECT_ROHAN_BLAKE_KENNETH;

SELECT
    CHUNK_ID,
    VECTOR_COSINE_SIMILARITY(EMBEDDING, EMBEDDING) AS SELF_SIM
FROM RAW.CHUNKS
LIMIT 5;
```

Also confirm the column type changed:

```sql
DESCRIBE TABLE RAW.CHUNKS;
```

The `EMBEDDING` column should show type `VECTOR(FLOAT, 768)`, not `VARCHAR`.

## Step 4: Install Updated Dependencies

No new Python packages are needed. The existing `sentence-transformers`, `numpy`, and `snowflake-connector-python` dependencies are sufficient. The `json` import was removed from `retrieval.py` since embeddings are no longer parsed client-side.

## Step 5: Restart the Backend

```bash
# From the project root
cd snowflake-research-assistant
# Kill any running backend process, then restart
python -m backend.app
```

## Step 6: Test End-to-End

1. Open the Streamlit frontend
2. Submit a query (e.g., "What is retrieval-augmented generation?")
3. Verify that citations appear with similarity scores
4. First query should be fast — no cache warm-up delay

## Step 7: Test Re-Ingestion (Optional)

If you need to re-run the ingestion pipeline, the new `_migrate_embeddings_to_vector()` helper in `data/ingestion.py` will automatically convert embeddings from VARCHAR to VECTOR after `write_pandas` uploads. No manual SQL needed:

```bash
python data/ingestion.py --stage upload
```

## What Changed (Summary)

| File | Change |
|------|--------|
| `sql/02_migrate_to_vector_type.sql` | New — one-time migration script |
| `sql/01_create_schema.sql` | `EMBEDDING VARCHAR` → `EMBEDDING VECTOR(FLOAT, 768)` |
| `backend/retrieval.py` | `get_top_chunks()` now uses `VECTOR_COSINE_SIMILARITY()` server-side instead of fetching all rows and computing dot products in Python |
| `data/ingestion.py` | Added `_migrate_embeddings_to_vector()` post-upload helper |

## Troubleshooting

- **"Unknown function VECTOR_COSINE_SIMILARITY"**: Your Snowflake account doesn't support VECTOR. Check with your admin.
- **Cast errors during migration**: Embeddings may contain malformed JSON. Run `SELECT EMBEDDING FROM RAW.CHUNKS WHERE TRY_PARSE_JSON(EMBEDDING) IS NULL` to find bad rows.
- **View errors after migration**: Re-run the `CREATE OR REPLACE VIEW APP.CHUNKS_V` statement from the migration SQL.
