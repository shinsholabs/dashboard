create table if not exists public.daily_visitors (
    visit_date date not null,
    visitor_id text not null check (visitor_id ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default now(),
    primary key (visit_date, visitor_id)
);

alter table public.daily_visitors enable row level security;

revoke all on table public.daily_visitors from anon, authenticated;
grant select on table public.daily_visitors to service_role;

create or replace function public.record_daily_visit(p_visitor_id text)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    if p_visitor_id !~ '^[0-9a-f]{64}$' then
        raise exception 'Invalid visitor identifier';
    end if;

    insert into public.daily_visitors (visit_date, visitor_id)
    values ((now() at time zone 'Asia/Seoul')::date, p_visitor_id)
    on conflict (visit_date, visitor_id) do nothing;
end;
$$;

revoke all on function public.record_daily_visit(text) from public;
grant execute on function public.record_daily_visit(text) to anon;

comment on table public.daily_visitors is
    'Anonymous daily unique visitors for the public Streamlit app';

comment on function public.record_daily_visit(text) is
    'Records one anonymous visitor per Korean calendar date';
