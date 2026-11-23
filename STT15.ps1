[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\YTeMo"
)

$ErrorActionPreference = "Stop"
$MigrationRelative = "supabase\migrations\202611240001_core_backend_persistence.sql"
$MigrationPath = Join-Path $RepoRoot $MigrationRelative
$CreatedByThisRun = $false

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "STT15 - BACKEND VA CO SO DU LIEU" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $RepoRoot "backend\main.py"))) {
    Write-Host "LOI: Khong tim thay backend\main.py tai $RepoRoot" -ForegroundColor Red
    return
}
if (-not (Test-Path (Join-Path $RepoRoot "backend\agent_core.py"))) {
    Write-Host "LOI: Khong tim thay backend\agent_core.py" -ForegroundColor Red
    return
}
if (-not (Test-Path (Join-Path $RepoRoot "supabase\migrations"))) {
    Write-Host "LOI: Khong tim thay supabase\migrations" -ForegroundColor Red
    return
}
if (Test-Path $MigrationPath) {
    Write-Host "DUNG: Migration da ton tai; script khong ghi de file cu." -ForegroundColor Yellow
    Write-Host $MigrationPath
    return
}

$sql = @'
-- Y TE MO - STT15: Core backend persistence
-- Additive/idempotent baseline for tables used by main.py and AgentCore.
-- This file is added to the repository only. It is NOT applied to Supabase.
-- Backend must authenticate the user and scope every query by user_id.
-- The browser must never receive SUPABASE_SECRET_KEY.

begin;

create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null default 'Cuoc tro chuyen',
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null
        references public.conversations(id) on delete cascade,
    sender_type text not null,
    content text not null,
    created_at timestamptz not null default now()
);

create table if not exists public.agent_tasks (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    conversation_id uuid
        references public.conversations(id) on delete set null,
    goal text not null,
    status text not null default 'queued'
        check (status in ('queued', 'running', 'completed', 'failed', 'cancelled')),
    plan jsonb not null default '[]'::jsonb,
    result jsonb,
    error text,
    lease_token text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.agent_task_steps (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null
        references public.agent_tasks(id) on delete cascade,
    step_key text not null,
    title text,
    tool_name text,
    input jsonb not null default '{}'::jsonb,
    status text not null default 'queued'
        check (status in ('queued', 'running', 'completed', 'failed', 'skipped')),
    output jsonb,
    attempts integer not null default 0 check (attempts >= 0),
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint agent_task_steps_task_key_unique unique (task_id, step_key)
);

create table if not exists public.agent_task_events (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null
        references public.agent_tasks(id) on delete cascade,
    event_type text not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists conversations_user_updated_idx
    on public.conversations (user_id, updated_at desc);

create index if not exists messages_conversation_created_idx
    on public.messages (conversation_id, created_at);

create index if not exists agent_tasks_user_created_idx
    on public.agent_tasks (user_id, created_at desc);

create index if not exists agent_tasks_status_updated_idx
    on public.agent_tasks (status, updated_at);

create index if not exists agent_task_steps_task_created_idx
    on public.agent_task_steps (task_id, created_at);

create index if not exists agent_task_events_task_created_idx
    on public.agent_task_events (task_id, created_at);

-- These tables are accessed through the authenticated backend only.
-- Backend derives user_id from the verified Supabase session.
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.agent_tasks enable row level security;
alter table public.agent_task_steps enable row level security;
alter table public.agent_task_events enable row level security;

revoke all on table
    public.conversations,
    public.messages,
    public.agent_tasks,
    public.agent_task_steps,
    public.agent_task_events
from public, anon, authenticated;

grant all on table
    public.conversations,
    public.messages,
    public.agent_tasks,
    public.agent_task_steps,
    public.agent_task_events
to service_role;

comment on table public.conversations is
    'Conversation metadata; ownership is enforced by authenticated backend queries.';
comment on table public.messages is
    'Conversation messages; access is mediated through the owning conversation.';
comment on table public.agent_tasks is
    'Durable, user-scoped AgentCore tasks with lease-based worker ownership.';
comment on table public.agent_task_steps is
    'Durable per-task execution steps for resume and idempotent progression.';
comment on table public.agent_task_events is
    'Append-oriented lifecycle events for AgentCore task observability.';

commit;
'@

try {
    Set-Content -LiteralPath $MigrationPath -Value $sql -Encoding UTF8
    $CreatedByThisRun = $true
    Write-Host "Da tao migration:" -ForegroundColor Green
    Write-Host $MigrationPath

    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        & git -C $RepoRoot diff --check
        if ($LASTEXITCODE -ne 0) {
            throw "git diff --check that bai."
        }
    }
    else {
        Write-Host "CANH BAO: Khong tim thay Git; bo qua git diff --check." -ForegroundColor Yellow
    }

    $PythonExe = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"
    if (-not (Test-Path $PythonExe)) {
        $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($PythonCommand) {
            $PythonExe = $PythonCommand.Source
        }
        else {
            throw "Khong tim thay Python. Khong the chay regression tests."
        }
    }

    Write-Host "`nDang chay full backend regression..." -ForegroundColor Cyan
    Push-Location $RepoRoot
    try {
        & $PythonExe -m pytest backend -q
        if ($LASTEXITCODE -ne 0) {
            throw "Backend regression that bai."
        }
    }
    finally {
        Pop-Location
    }

    Write-Host "`nSTT15 LOCAL CHECK: PASS" -ForegroundColor Green
    Write-Host "Da them migration vao repo; chua ap dung len Supabase."
    Write-Host "Truoc khi apply migration, doi chieu schema hien co tren Supabase de tranh lech schema."
    Write-Host "Khong co commit, push hoac deploy nao duoc thuc hien."
}
catch {
    Write-Host "`nSTT15 LOCAL CHECK: FAIL - $($_.Exception.Message)" -ForegroundColor Red
    if ($CreatedByThisRun -and (Test-Path $MigrationPath)) {
        Remove-Item -LiteralPath $MigrationPath -Force
        Write-Host "Da rollback file migration vua tao do kiem tra that bai." -ForegroundColor Yellow
    }
    Write-Host "Hay gui lai toan bo output loi; khong commit/deploy."
}
