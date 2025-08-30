-- Initial database setup for boilerplate project
-- This file is executed when PostgreSQL container starts for the first time

-- Create extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set timezone
SET timezone = 'UTC';

-- Create additional database for testing if needed
-- CREATE DATABASE boilerplate_test OWNER postgres;
