import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from supabase import create_client

from agent import chat
from agent_core import AgentCore, AgentCoreError

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]

# Public/publishable client: used only to validate user sessions.
auth_client = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)

# Secret-key client: backend only. Never expose this key to the browser.
db_client = create_client(
    SUPABASE_URL,
    os.environ["SUPABASE_SECRET_KEY"]
)

agent_core = AgentCore(db_client)

app = FastAPI(
    title="Y TE MO API",
    description="Backend for CareCommons",
    version="0.5.0"
)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

security = HTTPBearer()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[str] = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    try:
        result = auth_client.auth.get_user(token)
        if not result.user:
            raise HTTPException(status_code=401, detail="Invalid session")
        return result.user
    except HTTPException:
        raise
    except Exception as e:
        print("AUTH ERROR:", repr(e), flush=True)
        raise HTTPException(status_code=401, detail="Authentication failed")


@app.get("/")
def root():
    return {"platform": "Y TE MO", "status": "running", "version": "0.5.0"}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/public-config")
def public_config():
    # Supabase URL + publishable key are designed for browser use.
    # The Supabase secret key and Gemini API key are never returned here.
    return {
        "supabase_url": SUPABASE_URL,
        "supabase_publishable_key": SUPABASE_PUBLISHABLE_KEY
    }


@app.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: str,
    user=Depends(get_current_user)
):
    user_id = str(user.id)
    owned = (
        db_client.table("conversations")
        .select("id")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not owned.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = (
        db_client.table("messages")
        .select("sender_type, content, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .limit(100)
        .execute()
    )
    return {"conversation_id": conversation_id, "messages": result.data}


@app.post("/chat")
def chat_endpoint(request: ChatRequest, user=Depends(get_current_user)):
    user_id = str(user.id)

    # 1. Find or create a conversation owned by the authenticated user.
    if request.conversation_id:
        conversations = (
            db_client.table("conversations")
            .select("id")
            .eq("id", request.conversation_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not conversations.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id = request.conversation_id
    else:
        created = (
            db_client.table("conversations")
            .insert({
                "user_id": user_id,
                "title": request.message[:80],
                "status": "active"
            })
            .execute()
        )
        if not created.data:
            raise HTTPException(status_code=500, detail="Could not create conversation")
        conversation_id = created.data[0]["id"]

    # 2. Load prior context before saving the new user message.
    previous = (
        db_client.table("messages")
        .select("sender_type, content")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .limit(30)
        .execute()
    )
    history = "\n".join(
        f'{item["sender_type"]}: {item["content"]}'
        for item in previous.data
    )

    # 3. Save user message.
    db_client.table("messages").insert({
        "conversation_id": conversation_id,
        "sender_type": "user",
        "content": request.message
    }).execute()

    # 4. Call the discovery agent.
    try:
        reply = chat(request.message, history)
    except Exception as e:
        print("GEMINI ERROR:", repr(e), flush=True)
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable"
        )

    # 5. Save assistant response.
    db_client.table("messages").insert({
        "conversation_id": conversation_id,
        "sender_type": "assistant",
        "content": reply
    }).execute()

    # 6. Update conversation timestamp.
    db_client.table("conversations").update({
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", conversation_id).eq("user_id", user_id).execute()

    return {"conversation_id": conversation_id, "reply": reply}


class AgentTaskRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[str] = None


def _run_agent_task(user_id: str, task_id: str):
    # BackgroundTasks is a convenience for the first deployment.
    # Durable state is in Supabase; /resume can recover after a process restart.
    try:
        agent_core.run_task(user_id, task_id)
    except Exception as e:
        print("AGENT TASK ERROR:", repr(e), flush=True)


def _recover_agent_tasks_on_startup():
    """Recover queued and expired-running tasks after backend startup."""
    try:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(minutes=15)
        ).isoformat()

        queued_result = (
            db_client.table("agent_tasks")
            .select("id,user_id,status,updated_at")
            .eq("status", "queued")
            .order("created_at")
            .limit(100)
            .execute()
        )

        expired_result = (
            db_client.table("agent_tasks")
            .select("id,user_id,status,updated_at")
            .eq("status", "running")
            .lt("updated_at", cutoff)
            .order("updated_at")
            .limit(100)
            .execute()
        )

        candidates = {}
        for task in (queued_result.data or []) + (expired_result.data or []):
            candidates[str(task["id"])] = task

        print(
            "STARTUP RECOVERY: queued=",
            len(queued_result.data or []),
            "expired_running=",
            len(expired_result.data or []),
            "unique_candidates=",
            len(candidates),
            flush=True
        )

        if candidates:
            print(
                "STARTUP RECOVERY: starting bounded workers (max=2)",
                flush=True
            )
            with ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix="agent-recovery"
            ) as pool:
                futures = [
                    pool.submit(
                        _run_agent_task,
                        str(task["user_id"]),
                        str(task["id"])
                    )
                    for task in candidates.values()
                ]
                for future in futures:
                    try:
                        future.result()
                    except Exception as task_exc:
                        print(
                            "STARTUP RECOVERY TASK ERROR:",
                            repr(task_exc),
                            flush=True
                        )

        print("STARTUP RECOVERY: scan completed", flush=True)

    except Exception as exc:
        print("STARTUP RECOVERY ERROR:", repr(exc), flush=True)


@app.on_event("startup")
def start_agent_task_recovery():
    recovery_thread = threading.Thread(
        target=_recover_agent_tasks_on_startup,
        name="agent-task-startup-recovery",
        daemon=True,
    )
    recovery_thread.start()
    print("STARTUP RECOVERY: background scan started", flush=True)


@app.post("/agent/tasks", status_code=202)
def create_agent_task(
    request: AgentTaskRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user)
):
    user_id = str(user.id)
    if request.conversation_id:
        owned = (db_client.table("conversations").select("id")
                 .eq("id", request.conversation_id).eq("user_id", user_id)
                 .limit(1).execute())
        if not owned.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        task = agent_core.create_task(user_id, request.goal, request.conversation_id)
        background_tasks.add_task(_run_agent_task, user_id, task["id"])
        return {"task": task, "message": "Task đã được tiếp nhận."}
    except Exception as e:
        print("CREATE AGENT TASK ERROR:", repr(e), flush=True)
        raise HTTPException(status_code=503, detail="Không thể tạo task lúc này")


@app.get("/agent/tasks")
def list_agent_tasks(user=Depends(get_current_user)):
    try:
        return {"tasks": agent_core.list_tasks(str(user.id))}
    except Exception as e:
        print("LIST AGENT TASKS ERROR:", repr(e), flush=True)
        raise HTTPException(status_code=503, detail="Không thể tải danh sách task")


@app.get("/agent/tasks/{task_id}")
def get_agent_task(task_id: str, user=Depends(get_current_user)):
    try:
        task = agent_core.get_task(str(user.id), task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        steps = (db_client.table("agent_task_steps").select("*")
                 .eq("task_id", task_id).order("created_at").execute())
        events = (db_client.table("agent_task_events").select("*")
                  .eq("task_id", task_id).order("created_at").limit(100).execute())
        return {"task": task, "steps": steps.data or [], "events": events.data or []}
    except HTTPException:
        raise
    except Exception as e:
        print("GET AGENT TASK ERROR:", repr(e), flush=True)
        raise HTTPException(status_code=503, detail="Không thể tải task")


@app.post("/agent/tasks/{task_id}/resume", status_code=202)
def resume_agent_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user)
):
    user_id = str(user.id)
    task = agent_core.get_task(user_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] == "completed":
        return {"task": task, "message": "Task đã hoàn thành."}
    background_tasks.add_task(_run_agent_task, user_id, task_id)
    return {"task_id": task_id, "message": "Đã đưa task vào hàng đợi tiếp tục."}
