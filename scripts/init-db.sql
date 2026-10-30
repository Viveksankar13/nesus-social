-- Initialize the socialmedia database
-- This file runs on first Postgres container startup only.
-- Alembic handles the actual schema; this just ensures extensions.

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
