-- Identify the private, single-calendar schema without reading calendar records.
with target as (
    select c.* from pg_catalog.pg_class c
    join pg_catalog.pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'status_calendars'
), columns_found as (
    select a.* from pg_catalog.pg_attribute a join target t on t.oid = a.attrelid
    where a.attnum > 0 and not a.attisdropped
), expected_columns (name, type_oid, required) as (
    values ('id', 'boolean'::regtype, true), ('revision', 'bigint'::regtype, true),
           ('states', 'jsonb'::regtype, false), ('days', 'jsonb'::regtype, true)
), constraints_found as (
    select c.*, pg_catalog.pg_get_expr(c.conbin, c.conrelid) as expression
    from pg_catalog.pg_constraint c join target t on c.conrelid = t.oid
), expected_checks (expression) as (
    values ('id'), ('(revision >= 0)'), ($check$(jsonb_typeof(days) = 'object'::text)$check$),
           ($check$(((states IS NULL) AND (revision = 0) AND (days = '{}'::jsonb)) OR ((states IS NOT NULL) AND (jsonb_typeof(states) = 'array'::text)))$check$)
)
select case
    when not exists (select from target) and pg_catalog.to_regtype('public.status_calendars') is null then 'missing'
    when exists (
        select from target t
        where t.relkind = 'r' and t.relpersistence = 'p' and t.relrowsecurity and not t.relforcerowsecurity
          and not t.relhasrules and not t.relispartition
          and not exists (select from pg_catalog.pg_inherits where t.oid in (inhparent, inhrelid))
          and not exists (select from pg_catalog.pg_trigger where tgrelid = t.oid and not tgisinternal)
          and not exists (select from pg_catalog.pg_policy where polrelid = t.oid)
          and not exists (select from pg_catalog.aclexplode(t.relacl) g where g.grantee <> t.relowner)
          and not exists (
              select from columns_found a cross join lateral pg_catalog.aclexplode(a.attacl) g
              where g.grantee <> t.relowner
          )
          and not exists (
              select from pg_catalog.pg_roles api
              where api.rolname in ('anon', 'authenticated', 'service_role')
                and (pg_catalog.pg_has_role(api.oid, t.relowner, 'MEMBER')
                     or pg_catalog.has_table_privilege(api.oid, t.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                     or pg_catalog.has_any_column_privilege(api.oid, t.oid, 'SELECT,INSERT,UPDATE,REFERENCES'))
          )
    )
    and not exists (
        select from expected_columns e full join columns_found a on a.attname = e.name
        where e.name is null or a.attname is null or a.atttypid <> e.type_oid or a.attnotnull <> e.required
           or a.attgenerated <> '' or a.attidentity <> '' or a.atthasdef
    )
    and exists (
        select from constraints_found c join columns_found a on a.attname = 'id'
        where c.contype = 'p' and c.conkey = array[a.attnum] and not c.condeferrable
    )
    and (select count(*) from constraints_found where contype <> 'n') = 5
    and not exists (select from constraints_found where not convalidated)
    and not exists (
        select expression from expected_checks except select expression from constraints_found where contype = 'c'
    ) then 'ready'
    else 'review'
end as status;
