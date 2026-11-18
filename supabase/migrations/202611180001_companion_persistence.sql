-- Y TẾ MỞ — Companion Persistence v1
-- Ngày tạo: 2026-11-18
--
-- Mục đích:
--   1. Lưu bền vững consent, context, needs, events và proactive proposals.
--   2. Không cho trình duyệt truy cập trực tiếp các bảng này.
--   3. Backend sử dụng SUPABASE_SECRET_KEY và phải tự kiểm tra user_id
--      lấy từ token đã xác thực; tuyệt đối không tin user_id từ request body.
--
-- LƯU Ý:
--   - service_role/secret key bỏ qua RLS. RLS không thay thế kiểm tra quyền
--     trong backend.
--   - Việc đọc context còn phải kiểm tra consent scope ở tầng ứng dụng.
--   - Thu hồi consent phải ngăn việc sử dụng context; chính sách xóa vật lý/
--     thời hạn lưu trữ cần được triển khai riêng.
--   - Chạy migration sau khi đã kiểm tra bản sao lưu và đúng Supabase project.

begin;

create table if not exists public.companion_consents (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    scope text not null check (
        scope in (
            'BASIC_PROFILE',
            'CARE_NEEDS',
            'HEALTH_CONTEXT',
            'FOLLOW_UP',
            'PROACTIVE_CONTACT'
        )
    ),
    granted boolean not null default false,
    granted_at timestamptz,
    revoked_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint companion_consents_user_scope_unique unique (user_id, scope),
    constraint companion_consents_timestamp_check check (
        (granted = true and revoked_at is null)
        or
        (granted = false)
    )
);

create table if not exists public.companion_context (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    scope text not null check (
        scope in (
            'BASIC_PROFILE',
            'CARE_NEEDS',
            'HEALTH_CONTEXT',
            'FOLLOW_UP',
            'PROACTIVE_CONTACT'
        )
    ),
    context_type text not null,
    content jsonb not null default '{}'::jsonb,
    source text,
    confidence numeric(5,4) check (
        confidence is null or (confidence >= 0 and confidence <= 1)
    ),
    observed_at timestamptz,
    expires_at timestamptz,
    deleted_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.companion_needs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null,
    description text,
    status text not null default 'OPEN' check (
        status in ('OPEN', 'IN_PROGRESS', 'WAITING', 'RESOLVED', 'PAUSED')
    ),
    priority text not null default 'NORMAL' check (
        priority in ('LOW', 'NORMAL', 'HIGH')
    ),
    next_step text,
    due_at timestamptz,
    resolved_at timestamptz,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.companion_events (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    event_type text not null,
    payload jsonb not null default '{}'::jsonb,
    occurred_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create table if not exists public.proactive_proposals (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    trigger_type text not null,
    dedupe_key text,
    title text not null,
    description text,
    status text not null default 'PROPOSED' check (
        status in ('PROPOSED', 'DISMISSED', 'ACCEPTED', 'EXPIRED')
    ),
    payload jsonb not null default '{}'::jsonb,
    expires_at timestamptz,
    accepted_at timestamptz,
    dismissed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Các chỉ mục phục vụ truy vấn theo người dùng và thời gian.
create index if not exists companion_consents_user_id_idx
    on public.companion_consents (user_id);

create index if not exists companion_context_user_created_idx
    on public.companion_context (user_id, created_at desc);

create index if not exists companion_context_user_scope_idx
    on public.companion_context (user_id, scope);

create index if not exists companion_needs_user_status_idx
    on public.companion_needs (user_id, status, created_at desc);

create index if not exists companion_events_user_occurred_idx
    on public.companion_events (user_id, occurred_at desc);

create index if not exists proactive_proposals_user_status_idx
    on public.proactive_proposals (user_id, status, created_at desc);

create unique index if not exists proactive_proposals_active_dedupe_idx
    on public.proactive_proposals (user_id, dedupe_key)
    where status = 'PROPOSED' and dedupe_key is not null;

-- Các bảng này chỉ được truy cập qua backend đã xác thực.
-- Không cấp quyền trực tiếp cho anon/authenticated để tránh client bỏ qua
-- kiểm tra consent tại tầng ứng dụng.
alter table public.companion_consents enable row level security;
alter table public.companion_context enable row level security;
alter table public.companion_needs enable row level security;
alter table public.companion_events enable row level security;
alter table public.proactive_proposals enable row level security;

revoke all on table
    public.companion_consents,
    public.companion_context,
    public.companion_needs,
    public.companion_events,
    public.proactive_proposals
from public, anon, authenticated;

grant all on table
    public.companion_consents,
    public.companion_context,
    public.companion_needs,
    public.companion_events,
    public.proactive_proposals
to service_role;

comment on table public.companion_consents is
    'Consent theo từng phạm vi; backend phải kiểm tra trước khi đọc/ghi context.';
comment on table public.companion_context is
    'Ngữ cảnh có kiểm soát consent; không dùng làm hồ sơ bệnh án đã xác minh.';
comment on table public.companion_needs is
    'Các nhu cầu hỗ trợ theo thời gian của Companion.';
comment on table public.companion_events is
    'Sự kiện nghiệp vụ của Companion; tách biệt với audit_events hệ thống hiện có.';
comment on table public.proactive_proposals is
    'Đề xuất hỗ trợ chủ động; lưu đề xuất, không tự gửi thông báo ra ngoài.';

commit;
