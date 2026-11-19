-- Called once via the authorized project connection. Leave existing objects intact.
do $setup$
declare
    granted_role name;
begin
    if pg_catalog.to_regclass('public.status_calendars') is not null
       or pg_catalog.to_regtype('public.status_calendars') is not null then
        return;
    end if;

    create table public.status_calendars (
        id boolean primary key check (id),
        revision bigint not null check (revision >= 0),
        states jsonb,
        days jsonb not null check (jsonb_typeof(days) = 'object'),
        check (
            (states is null and revision = 0 and days = '{}'::jsonb)
            or (states is not null and jsonb_typeof(states) = 'array')
        )
    );
    alter table public.status_calendars enable row level security;
    revoke all on table public.status_calendars from public, anon, authenticated, service_role;

    -- A project can grant other roles access to newly created tables by default.
    for granted_role in
        select distinct r.rolname
        from pg_catalog.pg_class c
        cross join lateral pg_catalog.aclexplode(c.relacl) a
        join pg_catalog.pg_roles r on r.oid = a.grantee
        where c.oid = 'public.status_calendars'::regclass and a.grantee <> c.relowner
    loop
        execute format('revoke all on table public.status_calendars from %I', granted_role);
    end loop;
end;
$setup$;
