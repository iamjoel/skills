-- Inspect catalog metadata only. Unknown definitions are left for review.
with target as (
    select c.*
    from pg_catalog.pg_class c
    join pg_catalog.pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'status_calendars'
), columns_found as (
    select a.* from pg_catalog.pg_attribute a join target t on t.oid = a.attrelid
    where a.attnum > 0 and not a.attisdropped
), required_columns (name, type_oid, required) as (
    values ('user_id', 'pg_catalog.uuid'::regtype, true),
           ('revision', 'pg_catalog.int8'::regtype, true),
           ('states', 'pg_catalog.jsonb'::regtype, false),
           ('days', 'pg_catalog.jsonb'::regtype, true)
), constraints_found as (
    select c.*, pg_catalog.pg_get_expr(c.conbin, c.conrelid) as expression
    from pg_catalog.pg_constraint c join target t on c.conrelid = t.oid
), required_checks (expression) as (
    values ('(revision >= 0)'),
           ($expr$(jsonb_typeof(days) = 'object'::text)$expr$),
           ($expr$(((states IS NULL) AND (revision = 0) AND (days = '{}'::jsonb)) OR ((states IS NOT NULL) AND (jsonb_typeof(states) = 'array'::text)))$expr$)
), auth_role as (
    select oid, rolsuper, rolbypassrls from pg_catalog.pg_roles where rolname = 'authenticated'
), grants_found as (
    select '*' as scope, acl.grantee, acl.privilege_type, acl.is_grantable
    from target t cross join lateral pg_catalog.aclexplode(t.relacl) acl
    where acl.grantee <> t.relowner
    union all
    select a.attname::text, acl.grantee, acl.privilege_type, acl.is_grantable
    from columns_found a join target t on t.oid = a.attrelid
    cross join lateral pg_catalog.aclexplode(a.attacl) acl
    where acl.grantee <> t.relowner
), required_grants (scope, privilege_type) as (
    values ('*', 'SELECT'), ('*', 'INSERT'), ('revision', 'UPDATE'), ('states', 'UPDATE'), ('days', 'UPDATE')
), policies as (
    select p.*,
           regexp_replace(pg_catalog.pg_get_expr(p.polqual, p.polrelid), '[[:space:]]+', '', 'g') as using_expr,
           regexp_replace(pg_catalog.pg_get_expr(p.polwithcheck, p.polrelid), '[[:space:]]+', '', 'g') as check_expr
    from pg_catalog.pg_policy p join target t on t.oid = p.polrelid
), owner_tests (expression) as (
    values ('(user_id=auth.uid())'), ('(auth.uid()=user_id)'),
           ('(user_id=(SELECTauth.uid()ASuid))'), ('((SELECTauth.uid()ASuid)=user_id)'),
           ('(user_id=(SELECTauth.uid()))'), ('((SELECTauth.uid())=user_id)')
)
select case
    when not exists (select from target) and not exists (
        select from pg_catalog.pg_type typ join pg_catalog.pg_namespace n on n.oid = typ.typnamespace
        where n.nspname = 'public' and typ.typname = 'status_calendars'
    ) then 'missing'
    when exists (
        select from target t cross join auth_role r
        where t.relkind = 'r' and t.relpersistence = 'p' and t.relrowsecurity
          and not t.relhasrules and not t.relispartition
          and not exists (select from pg_catalog.pg_inherits where t.oid in (inhparent, inhrelid))
          and not exists (select from pg_catalog.pg_trigger where tgrelid = t.oid and not tgisinternal)
          and not r.rolsuper and not r.rolbypassrls and not pg_catalog.pg_has_role(r.oid, t.relowner, 'MEMBER')
          and not pg_catalog.has_table_privilege(r.oid, t.oid, 'UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
          and not (select pg_catalog.has_column_privilege(r.oid, t.oid, a.attnum, 'UPDATE')
                   from columns_found a where a.attname = 'user_id')
          and not exists (
              select from pg_catalog.pg_roles member
              where member.oid <> t.relowner and not member.rolsuper and member.rolbypassrls
                and pg_catalog.pg_has_role(member.oid, r.oid, 'USAGE')
          )
          and not exists (
              select from pg_catalog.pg_roles api where api.rolname in ('anon', 'service_role')
              and (pg_catalog.has_table_privilege(api.oid, t.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                   or pg_catalog.has_any_column_privilege(api.oid, t.oid, 'SELECT,INSERT,UPDATE,REFERENCES'))
          )
    )
    and not exists (
        select from required_columns e full join columns_found a on a.attname = e.name
        where e.name is null or a.attname is null or a.atttypid <> e.type_oid or a.attnotnull <> e.required
           or a.attgenerated <> '' or a.attidentity <> '' or a.atthasdef
    )
    and exists (
        select from constraints_found c join columns_found a on a.attname = 'user_id'
        where c.contype = 'p' and c.conkey = array[a.attnum] and not c.condeferrable
    )
    and exists (
        select from constraints_found c join columns_found a on a.attname = 'user_id'
        join pg_catalog.pg_attribute u on u.attrelid = pg_catalog.to_regclass('auth.users')
            and u.attname = 'id' and not u.attisdropped
        where c.contype = 'f' and c.conkey = array[a.attnum] and c.confrelid = u.attrelid
          and c.confkey = array[u.attnum] and c.confdeltype = 'c' and not c.condeferrable
    )
    and (select count(*) from constraints_found where contype <> 'n') = 5
    and not exists (select from constraints_found where not convalidated)
    and not exists (
        select expression from required_checks except select expression from constraints_found where contype = 'c'
    )
    and not exists (
        select from required_grants e full join grants_found g using (scope, privilege_type)
        where e.scope is null or g.scope is null or g.grantee <> (select oid from auth_role) or g.is_grantable
    )
    and (select count(*) = 3 and count(distinct polcmd) = 3 from policies)
    and not exists (
        select from policies p where (
            p.polpermissive and p.polroles = array[(select oid from auth_role)]
            and case p.polcmd
                when 'r' then p.using_expr in (select expression from owner_tests) and p.check_expr is null
                when 'a' then p.using_expr is null and p.check_expr in (select expression from owner_tests)
                when 'w' then p.using_expr in (select expression from owner_tests)
                    and coalesce(p.check_expr, p.using_expr) in (select expression from owner_tests)
                else false
            end
        ) is not true
    )
    -- A look-alike user-defined operator or function can deparse like a built-in.
    and not exists (
        select from pg_catalog.pg_depend d join policies p
            on d.classid = 'pg_catalog.pg_policy'::regclass and d.objid = p.oid
        where not ((d.refclassid = 'pg_catalog.pg_class'::regclass and d.refobjid = p.polrelid)
                   or (d.refclassid = 'pg_catalog.pg_proc'::regclass
                       and d.refobjid = pg_catalog.to_regprocedure('auth.uid()')))
    ) then 'ready'
    else 'review'
end as status;
