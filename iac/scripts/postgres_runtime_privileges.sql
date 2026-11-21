-- Run in a transaction as the project database owner after applying the schema.
-- Set the login passwords separately so they stay out of SQL files and output.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tangama_app_runtime') THEN
        CREATE ROLE tangama_app_runtime LOGIN NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tangama_backup_reader') THEN
        CREATE ROLE tangama_backup_reader LOGIN NOINHERIT;
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles AS roles
        WHERE rolname IN ('tangama_app_runtime', 'tangama_backup_reader')
          AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls OR NOT rolcanlogin
            OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member = roles.oid))
    ) THEN
        RAISE EXCEPTION 'Unexpected elevated PostgreSQL role settings or memberships';
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO tangama_app_runtime, tangama_backup_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tangama_app_runtime, tangama_backup_reader;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO tangama_app_runtime;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO tangama_backup_reader;

GRANT INSERT ON
    public.audit_log, public.companies, public.portal_users, public.orders, public.outbox_events,
    public.login_attempts, public.portal_admin_recovery_events, public.voice_calls, public.voice_signals,
    public.voice_recordings, public.erp_user_roles, public.erp_partners, public.erp_products,
    public.erp_sales_orders, public.erp_sales_order_lines, public.erp_purchase_orders,
    public.erp_purchase_order_lines, public.erp_financial_documents,
    public.internal_messages, public.internal_mail_delivery
TO tangama_app_runtime;

GRANT UPDATE ON
    public.portal_users, public.outbox_events, public.login_attempts, public.voice_calls,
    public.voice_signals, public.voice_recordings, public.erp_products, public.erp_purchase_orders,
    public.erp_financial_documents, public.internal_messages, public.internal_mail_delivery
TO tangama_app_runtime;

GRANT DELETE ON public.login_attempts, public.voice_signals, public.voice_recordings, public.erp_user_roles
TO tangama_app_runtime;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname IN ('tangama_app_runtime', 'tangama_backup_reader')
          AND (has_schema_privilege(rolname, 'public', 'CREATE')
            OR has_database_privilege(rolname, current_database(), 'CREATE'))
    ) THEN
        RAISE EXCEPTION 'Project accounts must not have CREATE on the database or public schema';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_tables WHERE schemaname = 'public'
          AND has_table_privilege('tangama_backup_reader', format('%I.%I', schemaname, tablename),
                                  'INSERT, UPDATE, DELETE, TRUNCATE')
    ) OR has_table_privilege('tangama_app_runtime', 'public.schema_migrations', 'INSERT, UPDATE, DELETE, TRUNCATE') THEN
        RAISE EXCEPTION 'Unexpected write privileges in the project database';
    END IF;
END $$;
