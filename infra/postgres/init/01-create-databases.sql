-- Create one DEDICATED database per service on the shared Postgres instance.
-- Golden rule: a service never reads another service's database (logical isolation).
-- Runs automatically (via psql) on the first start of the postgres container.
-- Idempotent: \gexec only emits CREATE DATABASE when the database is missing.

SELECT 'CREATE DATABASE user_svc'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'user_svc')\gexec

SELECT 'CREATE DATABASE interaction_svc'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'interaction_svc')\gexec

SELECT 'CREATE DATABASE stories_svc'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'stories_svc')\gexec

SELECT 'CREATE DATABASE realtime_svc'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'realtime_svc')\gexec

SELECT 'CREATE DATABASE keycloak'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak')\gexec
