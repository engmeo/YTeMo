"""Y TE MO Agent Core v1.

A durable, user-scoped task runtime built on the existing Supabase backend.
Only explicitly registered tools can execute. The initial tools are local,
read-only planning helpers; no external healthcare action is performed.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Callable
import time
import threading
from gemini_service import get_gemini_client, generate_content, GeminiServiceError


ALLOWED_TOOLS = {"extract_missing_information", "build_research_checklist"}
MAX_STEPS = 8
LEASE_MINUTES = 15
HEARTBEAT_SECONDS = 60
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_value(value: Any) -> Any:
    """Ensure values sent to Supabase are JSON serializable."""
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def extract_missing_information(payload: dict[str, Any]) -> dict[str, Any]:
    goal = str(payload.get("goal", "")).strip()
    lower = goal.lower()
    prompts = []
    # Generic intake prompts only; this tool does not infer a diagnosis.
    if not any(x in lower for x in ("ở đâu", "tỉnh", "thành phố", "quận", "huyện")):
        prompts.append("Người dùng đang ở tỉnh/thành phố nào?")
    if not any(x in lower for x in ("bảo hiểm", "bhyt")):
        prompts.append("Người dùng có bảo hiểm y tế không?")
    if not any(x in lower for x in ("ngân sách", "chi phí", "triệu", "đồng", "khả năng chi trả")):
        prompts.append("Mức chi phí người dùng có thể chi trả là bao nhiêu?")
    return {
        "missing_information": prompts,
        "note": "Đây là các thông tin cần hỏi thêm, không phải kết luận y khoa."
    }


def build_research_checklist(payload: dict[str, Any]) -> dict[str, Any]:
    goal = str(payload.get("goal", "")).strip()
    return {
        "research_topics": [
            {"topic": "Quyền lợi và điều kiện BHYT", "evidence_required": ["văn bản chính thức", "ngày hiệu lực", "đối tượng áp dụng"]},
            {"topic": "Chi phí và các khoản có thể phát sinh", "evidence_required": ["bảng giá có nguồn", "thời điểm cập nhật", "phạm vi dịch vụ"]},
            {"topic": "Cơ sở y tế và khả năng tiếp cận", "evidence_required": ["địa chỉ chính thức", "dịch vụ được cung cấp", "điều kiện tiếp nhận"]}
        ],
        "goal": goal,
        "warning": "Đây là danh sách hướng nghiên cứu; chưa có dữ liệu bên ngoài nào được tra cứu hoặc xác minh."
    }


TOOL_REGISTRY: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "extract_missing_information": extract_missing_information,
    "build_research_checklist": build_research_checklist,
}


class AgentCoreError(Exception):
    pass


class AgentCore:
    def __init__(self, db_client, gemini_client=None, model: str = MODEL):
        self.db = db_client
        self.gemini = gemini_client
        self.model = model

    def _gemini_client(self):
        if self.gemini is None:
            try:
                self.gemini = get_gemini_client()
            except GeminiServiceError as exc:
                raise AgentCoreError(str(exc)) from exc
        return self.gemini

    def _generate_content(self, prompt: str):
        try:
            return generate_content(
                model=self.model,
                contents=prompt,
                client=self._gemini_client(),
            )
        except GeminiServiceError as exc:
            raise AgentCoreError(str(exc)) from exc

    def _event(self, task_id: str, event_type: str, payload: dict[str, Any]):
        self.db.table("agent_task_events").insert({
            "task_id": task_id,
            "event_type": event_type,
            "payload": _json_value(payload),
        }).execute()

    def _update_task(
        self,
        task_id: str,
        user_id: str,
        values: dict[str, Any],
        lease_token: str | None = None,
    ):
        values = dict(values)
        values["updated_at"] = utc_now()

        query = (
            self.db.table("agent_tasks")
            .update(values)
            .eq("id", task_id)
            .eq("user_id", user_id)
        )

        if lease_token is not None:
            query = query.eq("lease_token", lease_token)

        result = query.select("id").execute()

        if lease_token is not None and not result.data:
            raise AgentCoreError(
                "Worker da mat quyen so huu task; dung cap nhat."
            )

    def _claim_task(self, task_id: str, user_id: str):
        token = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        values = {
            "status": "running",
            "error": None,
            "lease_token": token,
            "updated_at": now.isoformat(),
        }

        # First: claim queued or failed tasks atomically.
        result = (
            self.db.table("agent_tasks")
            .update(values)
            .eq("id", task_id)
            .eq("user_id", user_id)
            .in_("status", ["queued", "failed"])
            .select("*")
            .execute()
        )

        if result.data:
            return result.data[0]

        # Second: reclaim a running task only after its lease expires.
        cutoff = (now - timedelta(minutes=LEASE_MINUTES)).isoformat()

        result = (
            self.db.table("agent_tasks")
            .update(values)
            .eq("id", task_id)
            .eq("user_id", user_id)
            .eq("status", "running")
            .lt("updated_at", cutoff)
            .select("*")
            .execute()
        )

        return result.data[0] if result.data else None

    def _heartbeat(self, task_id: str, user_id: str, lease_token: str):
        result = (
            self.db.table("agent_tasks")
            .update({"updated_at": utc_now()})
            .eq("id", task_id)
            .eq("user_id", user_id)
            .eq("status", "running")
            .eq("lease_token", lease_token)
            .select("id")
            .execute()
        )

        if not result.data:
            raise AgentCoreError(
                "Worker da mat lease; khong duoc tiep tuc task."
            )

    def create_task(self, user_id: str, goal: str, conversation_id: str | None = None) -> dict[str, Any]:
        goal = goal.strip()
        if not goal:
            raise ValueError("Mục tiêu không được để trống.")
        if len(goal) > 4000:
            raise ValueError("Mục tiêu không được vượt quá 4000 ký tự.")
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "goal": goal,
            "status": "queued",
            "plan": [],
            "result": None,
            "error": None,
        }
        inserted = self.db.table("agent_tasks").insert(row).execute()
        if not inserted.data:
            raise AgentCoreError("Không thể tạo task.")
        self._event(row["id"], "task.created", {"goal_length": len(goal)})
        return inserted.data[0]

    def get_task(self, user_id: str, task_id: str) -> dict[str, Any] | None:
        result = (self.db.table("agent_tasks").select("*")
                  .eq("id", task_id).eq("user_id", user_id).limit(1).execute())
        return result.data[0] if result.data else None

    def list_tasks(self, user_id: str, limit: int = 30) -> list[dict[str, Any]]:
        result = (self.db.table("agent_tasks").select(
            "id,conversation_id,goal,status,created_at,updated_at,error"
        ).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute())
        return result.data or []

    def _make_plan(self, goal: str) -> list[dict[str, Any]]:
        prompt = f"""
Bạn là bộ lập kế hoạch của Y TẾ MỞ. Chỉ lập kế hoạch, không đưa ra chẩn đoán,
không kê đơn, không khẳng định quyền lợi hay giá khi chưa có nguồn.
Trả về DUY NHẤT JSON dạng:
{{"steps":[{{"key":"step_1","title":"...","tool":"extract_missing_information","input":{{}}}}]}}
Chỉ được dùng đúng hai tool:
- extract_missing_information: tìm thông tin người dùng còn thiếu, input phải là {{"goal":"..."}}
- build_research_checklist: tạo danh sách nội dung cần xác minh, input phải là {{"goal":"..."}}
Tạo từ 2 đến 4 bước hợp lý, key duy nhất. Không tạo tool khác.
Mục tiêu: {goal}
"""
        response = self._generate_content(prompt)
        raw = (response.text or "").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
        try:
            data = json.loads(raw)
        except Exception as exc:
            raise AgentCoreError("Planner không trả về JSON hợp lệ.") from exc
        steps = data.get("steps")
        if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
            raise AgentCoreError("Kế hoạch không hợp lệ hoặc vượt giới hạn số bước.")
        clean, seen = [], set()
        for item in steps:
            if not isinstance(item, dict):
                raise AgentCoreError("Một bước trong kế hoạch không hợp lệ.")
            key = str(item.get("key", "")).strip()
            title = str(item.get("title", "")).strip()
            tool = str(item.get("tool", "")).strip()
            tool_input = item.get("input", {})
            if not key or key in seen or not title or tool not in ALLOWED_TOOLS:
                raise AgentCoreError("Kế hoạch chứa bước thiếu thông tin hoặc tool không được phép.")
            if not isinstance(tool_input, dict):
                raise AgentCoreError("Dữ liệu đầu vào của tool phải là object.")
            # The goal is injected by the runtime, not trusted to the LLM.
            clean.append({"key": key, "title": title, "tool": tool,
                          "input": {"goal": goal}})
            seen.add(key)
        return clean

    def _run_tool_with_heartbeat(
        self,
        tool,
        payload: dict[str, Any],
        task_id: str,
        user_id: str,
        lease_token: str,
    ):
        stop_event = threading.Event()
        heartbeat_errors = []

        def heartbeat_loop():
            while not stop_event.wait(HEARTBEAT_SECONDS):
                try:
                    self._heartbeat(task_id, user_id, lease_token)
                except Exception as exc:
                    heartbeat_errors.append(exc)
                    stop_event.set()
                    return

        heartbeat_thread = threading.Thread(
            target=heartbeat_loop,
            name=f"agent-heartbeat-{task_id}",
            daemon=True,
        )
        heartbeat_thread.start()

        try:
            output = tool(payload)
        finally:
            stop_event.set()
            heartbeat_thread.join()

        if heartbeat_errors:
            raise AgentCoreError(
                "Worker da mat lease trong khi tool dang chay; "
                "khong duoc luu ket qua."
            ) from heartbeat_errors[0]

        return output

    def run_task(self, user_id: str, task_id: str) -> dict[str, Any]:
        task = self.get_task(user_id, task_id)
        if not task:
            raise AgentCoreError("Kh?ng t?m th?y task.")
        if task["status"] == "completed":
            return task

        claimed_task = self._claim_task(task_id, user_id)
        if not claimed_task:
            current = self.get_task(user_id, task_id)
            if current and current["status"] in {"running", "completed"}:
                return current
            if not current:
                raise AgentCoreError("Kh?ng t?m th?y task.")
            raise AgentCoreError(
                f"Kh?ng th? nh?n task ? tr?ng th?i: {current['status']}."
            )

        task = claimed_task
        lease_token = task["lease_token"]

        try:
            self._heartbeat(task_id, user_id, lease_token)
            self._event(task_id, "task.started_or_resumed", {})

            plan = task.get("plan") or self._make_plan(task["goal"])
            if not task.get("plan"):
                self._update_task(
                    task_id, user_id, {"plan": plan}, lease_token
                )
                self._event(task_id, "plan.created", {"steps": plan})

            outputs = []
            for step in plan:
                self._heartbeat(task_id, user_id, lease_token)

                existing = (
                    self.db.table("agent_task_steps")
                    .select("*")
                    .eq("task_id", task_id)
                    .eq("step_key", step["key"])
                    .limit(1)
                    .execute()
                )

                if existing.data and existing.data[0]["status"] == "completed":
                    outputs.append({
                        "step": step["key"],
                        "output": existing.data[0].get("output")
                    })
                    continue

                if step["tool"] not in TOOL_REGISTRY:
                    raise AgentCoreError(
                        "Tool kh?ng n?m trong registry ???c ph?p."
                    )

                step_row = {
                    "task_id": task_id,
                    "step_key": step["key"],
                    "title": step["title"],
                    "tool_name": step["tool"],
                    "input": _json_value(step["input"]),
                    "status": "running",
                    "attempts": (
                        existing.data[0].get("attempts", 0) + 1
                    ) if existing.data else 1,
                }

                if existing.data:
                    (
                        self.db.table("agent_task_steps")
                        .update(step_row)
                        .eq("id", existing.data[0]["id"])
                        .execute()
                    )
                else:
                    self.db.table("agent_task_steps").insert(step_row).execute()

                self._event(
                    task_id,
                    "step.started",
                    {"step_key": step["key"], "tool": step["tool"]}
                )

                output = self._run_tool_with_heartbeat(
                    TOOL_REGISTRY[step["tool"]],
                    step["input"],
                    task_id,
                    user_id,
                    lease_token,
                )
                output = _json_value(output)

                # Verify ownership again before saving the tool result.
                self._heartbeat(task_id, user_id, lease_token)

                (
                    self.db.table("agent_task_steps")
                    .update({
                        "status": "completed",
                        "output": output,
                        "completed_at": utc_now()
                    })
                    .eq("task_id", task_id)
                    .eq("step_key", step["key"])
                    .execute()
                )

                self._event(
                    task_id, "step.completed", {"step_key": step["key"]}
                )
                outputs.append({
                    "step": step["key"],
                    "title": step["title"],
                    "output": output
                })

            result = {
                "summary": (
                    "Agent Core ?? ho?n th?nh c?c b??c l?p k? ho?ch "
                    "v? ph?n t?ch n?i b?."
                ),
                "steps": outputs,
                "limitations": [
                    "Ch?a truy v?n d? li?u b?nh vi?n ho?c ch?nh s?ch b?n ngo?i.",
                    "Ch?a x?c minh gi?, quy?n l?i BHYT ho?c t?nh ph? h?p ?i?u tr?.",
                    "Kh?ng thay th? t? v?n c?a b?c s? ho?c c? quan b?o hi?m."
                ]
            }

            self._heartbeat(task_id, user_id, lease_token)
            self._update_task(
                task_id,
                user_id,
                {"status": "completed", "result": result, "lease_token": None},
                lease_token
            )
            self._event(
                task_id, "task.completed", {"completed_steps": len(outputs)}
            )

        except Exception as exc:
            # A worker that lost its lease must not overwrite the new owner.
            try:
                self._update_task(
                    task_id,
                    user_id,
                    {
                        "status": "failed",
                        "error": str(exc)[:1000],
                        "lease_token": None
                    },
                    lease_token
                )
                self._event(
                    task_id, "task.failed", {"error": str(exc)[:500]}
                )
            except Exception:
                pass
            raise

        return self.get_task(user_id, task_id) or {}
