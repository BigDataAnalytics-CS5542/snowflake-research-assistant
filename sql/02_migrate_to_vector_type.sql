-- ══════════════════════════════════════════════════════════════
-- Migration: VARCHAR embeddings → native VECTOR(FLOAT, 768)
-- ══════════════════════════════════════════════════════════════
-- Run once against an existing database where RAW.CHUNKS.EMBEDDING
-- is stored as a JSON-encoded VARCHAR.  After this migration the
-- column becomes VECTOR(FLOAT, 768) and server-side
-- VECTOR_COSINE_SIMILARITY() can be used for retrieval.
-- ══════════════════════════════════════════════════════════════

-- 1. Add a new VECTOR column alongside the existing VARCHAR one (safe if re-run)
ALTER TABLE RAW.CHUNKS
    ADD COLUMN IF NOT EXISTS EMBEDDING_VEC VECTOR(FLOAT, 768);

-- 2. Populate it by parsing the JSON string → ARRAY → VECTOR
UPDATE RAW.CHUNKS
    SET EMBEDDING_VEC = PARSE_JSON(EMBEDDING)::VECTOR(FLOAT, 768)
    WHERE EMBEDDING_VEC IS NULL;

-- 3. Drop the old VARCHAR column and rename the new one
ALTER TABLE RAW.CHUNKS DROP COLUMN EMBEDDING;
ALTER TABLE RAW.CHUNKS RENAME COLUMN EMBEDDING_VEC TO EMBEDDING;

-- 4. Recreate the application view (it references EMBEDDING)
CREATE OR REPLACE VIEW APP.CHUNKS_V AS
SELECT
    c.CHUNK_ID,
    c.PAPER_ID,
    c.CHUNK_INDEX,
    c.SECTION_NAME,
    c.TEXT_CONTENT,
    c.WORD_COUNT,
    c.EMBEDDING,
    p.TITLE,
    p.AUTHORS,
    p.PUBLICATION_YEAR,
    p.CATEGORIES,
    p.SOURCE_URL
FROM RAW.CHUNKS c
JOIN RAW.PAPERS p ON c.PAPER_ID = p.PAPER_ID;

-- 5. Spot-check: self-similarity should be 1.0 for every row
SELECT
    CHUNK_ID,
    VECTOR_COSINE_SIMILARITY(EMBEDDING, EMBEDDING) AS SELF_SIM
FROM RAW.CHUNKS
LIMIT 5;
