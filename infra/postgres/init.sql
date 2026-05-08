-- ============================================================
-- ContextCore Database Schema
-- File: infra/postgres/init.sql
-- This file runs automatically when PostgreSQL starts
-- ============================================================

-- Enable the UUID extension so we can use UUID as primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLE 1: tenants
-- A "tenant" is one company/organization using the platform
-- Every other table links back to this one via tenant_id
-- ============================================================
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,  -- e.g. "acme-corp"
    tier            VARCHAR(50)  NOT NULL DEFAULT 'free', -- free | pro | enterprise
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE 2: api_keys
-- Each tenant can have multiple API keys (like Stripe does)
-- We store a hashed version, never the raw key
-- ============================================================
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    key_hash        VARCHAR(255) NOT NULL UNIQUE, -- SHA-256 hash of the real key
    name            VARCHAR(100) NOT NULL,        -- e.g. "production-key"
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE 3: documents
-- Every file uploaded by a tenant becomes a document
-- ============================================================
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename        VARCHAR(500) NOT NULL,
    file_type       VARCHAR(50) NOT NULL,          -- pdf | docx | html | md
    s3_key          VARCHAR(1000),                 -- where it lives in S3
    file_size_bytes BIGINT,
    content_hash    VARCHAR(64) NOT NULL,          -- SHA-256 of file content (for deduplication)
    status          VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    -- Status flow: uploaded → parsing → chunking → embedding → ready | failed
    error_message   TEXT,                          -- filled if status = failed
    metadata        JSONB NOT NULL DEFAULT '{}',   -- flexible extra data
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- This constraint prevents the same file from being processed twice per tenant
    UNIQUE(tenant_id, content_hash)
);

-- ============================================================
-- TABLE 4: chunks
-- Each document is split into small pieces called chunks
-- These are what get embedded and stored in Qdrant
-- ============================================================
CREATE TABLE chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,              -- 0, 1, 2, 3... order within document
    content         TEXT NOT NULL,                 -- the actual text of this chunk
    token_count     INTEGER,                       -- how many tokens this chunk uses
    qdrant_point_id VARCHAR(100),                  -- the ID in Qdrant vector DB
    metadata        JSONB NOT NULL DEFAULT '{}',   -- section title, page number, etc.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Each chunk position within a document must be unique
    UNIQUE(document_id, chunk_index)
);

-- ============================================================
-- TABLE 5: query_logs
-- Every search query ever made, stored for analytics + feedback
-- ============================================================
CREATE TABLE query_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    query_text      TEXT NOT NULL,                 -- what the user asked
    query_embedding_model VARCHAR(100),            -- which model made the embedding
    retrieved_chunk_ids   UUID[],                  -- which chunks were returned
    llm_response    TEXT,                          -- what the LLM answered
    citations       JSONB NOT NULL DEFAULT '[]',   -- list of source references
    faithfulness_score    FLOAT,                   -- hallucination guard score (0-1)
    latency_ms      INTEGER,                       -- how long the query took
    cached          BOOLEAN NOT NULL DEFAULT false,-- was this served from Redis cache?
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE 6: query_feedback
-- Users can thumbs up/down any answer
-- ============================================================
CREATE TABLE query_feedback (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    query_log_id    UUID NOT NULL REFERENCES query_logs(id) ON DELETE CASCADE,
    rating          SMALLINT NOT NULL CHECK (rating IN (-1, 1)), -- -1 = bad, 1 = good
    comment         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- These make queries fast. Without indexes, every query
-- scans the entire table (very slow at scale)
-- ============================================================

-- Find all documents for a tenant fast
CREATE INDEX idx_documents_tenant_id     ON documents(tenant_id);
-- Find documents by their processing status
CREATE INDEX idx_documents_status        ON documents(status);
-- Find all chunks belonging to a document
CREATE INDEX idx_chunks_document_id      ON chunks(document_id);
-- Find all chunks for a tenant (for deletion, migration)
CREATE INDEX idx_chunks_tenant_id        ON chunks(tenant_id);
-- Find recent queries for a tenant (for analytics dashboard)
CREATE INDEX idx_query_logs_tenant_id    ON query_logs(tenant_id);
CREATE INDEX idx_query_logs_created_at   ON query_logs(created_at DESC);
-- Find API keys by hash quickly (used on every request)
CREATE INDEX idx_api_keys_key_hash       ON api_keys(key_hash);
CREATE INDEX idx_api_keys_tenant_id      ON api_keys(tenant_id);

-- ============================================================
-- ROW-LEVEL SECURITY (RLS)
-- This is the critical multi-tenant isolation layer.
-- Even if application code has a bug, Postgres itself
-- will NEVER return data from tenant A to tenant B
-- ============================================================

-- Step 1: Turn on RLS for every tenant-scoped table
ALTER TABLE documents      ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks         ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_logs     ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys       ENABLE ROW LEVEL SECURITY;

-- Step 2: Create policies — each table only shows rows
-- where tenant_id matches the value set in app.tenant_id
CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

CREATE POLICY tenant_isolation ON chunks
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

CREATE POLICY tenant_isolation ON query_logs
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

CREATE POLICY tenant_isolation ON query_feedback
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

CREATE POLICY tenant_isolation ON api_keys
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

-- ============================================================
-- SEED DATA
-- Insert one test tenant so we can immediately test the API
-- ============================================================
INSERT INTO tenants (id, name, slug, tier)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Test Organization',
    'test-org',
    'pro'
);

-- Insert one API key for the test tenant
-- The actual key value is: "cc-test-key-12345"
-- We store only the SHA-256 hash of it in the DB
INSERT INTO api_keys (tenant_id, key_hash, name)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'a4f2c1e3b5d7890123456789abcdef0123456789abcdef0123456789abcdef01',
    'test-api-key'
);