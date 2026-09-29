-- Run as migration owner against BOTH state databases, after migrations.
-- Configure the role password privately via provider dashboard/psql \password.
-- No password is included in this source. This script grants only current application tables.
CREATE ROLE swasthyasetu_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
GRANT USAGE ON SCHEMA public TO swasthyasetu_app;
GRANT SELECT ON alembic_version, medicines, daily_medicine_activity TO swasthyasetu_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON demo_sessions, facilities, balances, records,
  transfers, stock_events, commands, budgets TO swasthyasetu_app;
-- Browser roles have no table grants. Backend enforces compound state/session scope.
-- Do not grant this role CREATE, role membership, owner rights, or BYPASSRLS.
