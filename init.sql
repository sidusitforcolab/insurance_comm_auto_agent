-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table for storing document metadata
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) NOT NULL, -- 'mvr', 'loss_run', 'inspection', 'policy'
    applicant_id VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content TEXT
);

-- Create embeddings table for vector storage
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536), -- Dimension for text-embedding-3-small
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create underwriting_decisions table for caching results
CREATE TABLE IF NOT EXISTS underwriting_decisions (
    id SERIAL PRIMARY KEY,
    applicant_id VARCHAR(100) UNIQUE NOT NULL,
    decision VARCHAR(20) NOT NULL, -- 'accept', 'reject'
    premium_amount DECIMAL(10,2),
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '30 days')
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_applicant_id ON documents(applicant_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_underwriting_applicant_id ON underwriting_decisions(applicant_id);

-- Create vector similarity search function
CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector) RETURNS float
LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE AS $$
BEGIN
    RETURN 1 - (a <=> b);
END;
$$;