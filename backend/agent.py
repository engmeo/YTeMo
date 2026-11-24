import os
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from gemini_service import generate_content

try:
    from model_intelligence import ModelGatewayError, generate_companion_response
except ImportError:  # pragma: no cover - preserves older deployment layout
    ModelGatewayError = RuntimeError
    generate_companion_response = None

load_dotenv()

MODEL = "openrouter/free"


class AgentState(TypedDict):
    message: str
    history: str
    evidence_context: str
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

BẰNG CHỨNG LÂM SÀNG ĐƯỢC TRUY XUẤT TỪ HỆ THỐNG (CÓ THỂ RỖNG):
{state.get("evidence_context", "")}

QUY TẮC BẰNG CHỨNG BẮT BUỘC:
- Chỉ trình bày nhận định y khoa như thông tin có căn cứ khi evidence context có claim đã được duyệt và citation tương ứng.
- Mọi nhận định dựa trên claim phải nêu tên tài liệu, phiên bản nếu có, trang và trích dẫn nguồn.
- Không suy diễn rộng hơn population, jurisdiction, scope hoặc thời hạn hiệu lực được duyệt.
- Nếu evidence context rỗng, có abstention=true hoặc retrieval lỗi: nói rõ chưa truy xuất được bằng chứng đã thẩm định; không tự lấp chỗ trống bằng kiến thức mô hình, không chẩn đoán, không kê đơn, không đề xuất liều hoặc thay đổi điều trị.
- Nếu thiếu dữ kiện người bệnh, hỏi tối đa một câu cần thiết; với dấu hiệu cấp cứu, hướng dẫn liên hệ cấp cứu ngay.
- Trình bày mâu thuẫn chưa được giải quyết như bất đồng, không tự chọn một hướng.

Hãy phản hồi phù hợp và hỏi tối đa một câu tiếp theo nếu cần.
"""
    gateway_enabled = bool(
        os.getenv("YTEMO_MODEL_BACKEND") or os.getenv("OPENROUTER_API_KEY")
    )
    if gateway_enabled and generate_companion_response:
        try:
            result = generate_companion_response(
                prompt,
                state["message"],
                state.get("evidence_context", ""),
            )
            print(
                "MODEL_GATEWAY:",
                result.get("profile"),
                result.get("model"),
                result.get("latency_ms"),
                "ms",
                flush=True,
            )
            return {"reply": result["text"]}
        except ModelGatewayError:
            # No silent fallback to a different provider/model or a paid route.
            raise

    # Compatibility fallback for deployments still using the existing provider.
    response = generate_content(
        model=os.getenv("OPENROUTER_MODEL", MODEL),
        contents=prompt,
        max_attempts=1,
    )
    return {"reply": response.text}


graph_builder = StateGraph(AgentState)
graph_builder.add_node("discovery", discovery_agent)
graph_builder.add_edge(START, "discovery")
graph_builder.add_edge("discovery", END)

agent = graph_builder.compile()


def chat(message: str, history: str = "", evidence_context: str = ""):
    result = agent.invoke({
        "message": message,
        "history": history,
        "evidence_context": evidence_context,
        "reply": ""
    })
    return result["reply"]
