"""Start with uvicorn web_app:app. Reuse the project's chat and auth endpoints."""
import json
from pathlib import Path

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from main import app, get_current_user


class Question(BaseModel):
    question: str
    answer: str


class AcademyCase(BaseModel):
    id: str
    title: str
    record: str
    questions: list[Question]
    reference: str


def require_professional(user=Depends(get_current_user)):
    metadata = user.app_metadata or {}
    if metadata.get("ytemo_role") != "professional":
        raise HTTPException(status_code=403, detail="Professional account required")
    return user


@app.get("/academy/cases")
def list_academy_cases(_user=Depends(require_professional)):
    path = Path(__file__).with_name("academy_cases.json")
    records = json.loads(path.read_text(encoding="utf-8-sig"))
    return {"cases": [AcademyCase.model_validate(item) for item in records]}
