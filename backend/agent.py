
import os
from typing import TypedDict
from dotenv import load_dotenv
from gemini_service import generate_content
from langgraph.graph import StateGraph, START, END

load_dotenv()

MODEL = "gemini-3.5-flash-lite"


class AgentState(TypedDict):
    message: str
    history: str
    reply: str


def discovery_agent(state: AgentState):
    prompt = f"""
Bạn là trợ lý khám phá nhu cầu của nền tảng Y TẾ MỞ.

MỤC TIÊU:
- Hiểu vấn đề thực sự người dùng đang gặp.
- Chủ động phát hiện thông tin còn thiếu.
- Hỏi từng câu một, không hỏi dồn dập.
- Dùng tiếng Việt tự nhiên, dễ hiểu.
- Quan tâm đến hoàn cảnh, khả năng tài chính và khả năng tiếp cận y tế.
- Không tự chẩn đoán hoặc kê đơn.
- Nếu có dấu hiệu cấp cứu, hướng dẫn liên hệ cấp cứu ngay.

LỊCH SỬ:
{state["history"]}

TIN NHẮN MỚI:
{state["message"]}

Hãy phản hồi phù hợp và hỏi tối đa một câu tiếp theo nếu cần.
"""
    response = generate_content(
        model=MODEL,
        contents=prompt
    )
    return {"reply": response.text}


graph_builder = StateGraph(AgentState)
graph_builder.add_node("discovery", discovery_agent)
graph_builder.add_edge(START, "discovery")
graph_builder.add_edge("discovery", END)

agent = graph_builder.compile()


def chat(message: str, history: str = ""):
    result = agent.invoke({
        "message": message,
        "history": history,
        "reply": ""
    })
    return result["reply"]
