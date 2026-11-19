-- Install atomically on an empty project. An existing relation is inspected
-- separately and is never altered by this initializer.
do $setup$
begin
    if to_regclass('public.status_calendars') is not null then
        return;
    end if;

    create table public.status_calendars (
        user_id uuid primary key references auth.users (id) on delete cascade,
        revision bigint not null check (revision >= 0),
        states jsonb,
        days jsonb not null check (jsonb_typeof(days) = 'object'),
        check (
            (states is null and revision = 0 and days = '{}'::jsonb)
            or (states is not null and jsonb_typeof(states) = 'array')
        )
    );
    alter table public.status_calendars enable row level security;
    revoke all privileges on table public.status_calendars from public, anon, authenticated, service_role;
    grant select, insert on table public.status_calendars to authenticated;
    grant update (revision, states, days) on table public.status_calendars to authenticated;

    create policy status_calendar_read_own on public.status_calendars
        for select to authenticated using (user_id = (select auth.uid()));
    create policy status_calendar_insert_own on public.status_calendars
        for insert to authenticated with check (user_id = (select auth.uid()));
    create policy status_calendar_update_own on public.status_calendars
        for update to authenticated using (user_id = (select auth.uid()))
        with check (user_id = (select auth.uid()));

    perform pg_notify('pgrst', 'reload schema');
end;
$setup$;
