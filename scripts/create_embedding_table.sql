-- Create paper_embeddings table for semantic search
-- Stores full PDF text and vector embeddings for each paper
-- Note: No index on vector columns — pgvector 0.7.0 has 2000-dim limit for IVFFlat/HNSW.
-- With ~320 rows, sequential cosine similarity scan is fast enough (< 10ms).

CREATE TABLE IF NOT EXISTS paper_embeddings (
    paper_id VARCHAR(255) PRIMARY KEY,
    full_text TEXT,
    embedding VECTOR(3840),
    abstract_embedding VECTOR(3840),
    updated_at TIMESTAMP DEFAULT NOW()
);
