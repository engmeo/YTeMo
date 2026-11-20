# Kiến trúc tích hợp Planning và Memory

## 1. Mục tiêu thiết kế

Planning và Memory là hai subsystem độc lập, phối hợp thông qua các
contract có phiên bản rõ ràng.

Memory cung cấp context và evidence.
Planning sử dụng context để tạo và đánh giá kế hoạch.

Không subsystem nào được tự ý chiếm quyền của subsystem còn lại.

## 2. Luồng tương tác logic

```text
User / Companion
       |
       v
Goal and Intent
       |
       +----------------------+
       |                      |
       v                      v
Memory Query            Planning Request
       |                      |
Authorization                 |
       |                      |
Retrieval                     |
       |                      |
Provenance                    |
       |                      |
Conflict Analysis             |
       |                      |
Context Package               |
       |                      |
       +----------+-----------+
                  |
                  v
         Planning Evaluation
                  |
           Candidate Plan
                  |
         Validation / Risk
                  |
          Decision / Review
                  |
           Plan Proposal
                  |
         Separate Authorization
                  |
          Execution Boundary
```

## 3. Memory-to-Planning Contract

Context Package nên mang theo:
- Request ID.
- Subject hoặc owner scope.
- Authorized purpose.
- Retrieved memory references.
- Facts và events liên quan.
- Source và provenance references.
- Valid-time.
- Verification state.
- Uncertainty.
- Conflict indicators.
- Retrieval timestamp.
- Memory version hoặc snapshot reference.

Không truyền một summary không truy nguyên được như thể đó là fact
đã xác minh.

## 4. Planning-to-Memory Contract

Planning có thể yêu cầu:
- Current context.
- Historical events liên quan.
- Known constraints.
- Previously attempted plans.
- Prior outcomes.
- Evidence liên quan đến goal.
- Knowledge gaps.

Planning có thể trả về:
- Plan ID.
- Goal và assumptions.
- Decisions và rationale.
- Required evidence.
- Predicted outcomes.
- Observed outcomes khi có.
- Failure và recovery events.
- References phù hợp cho quá trình memory ingestion sau này.

Plan proposal không tự động trở thành durable memory.

## 5. Evidence-aware Planning

Với mỗi input quan trọng, cần giữ:
- Source.
- Verification state.
- Time.
- Relevance.
- Uncertainty.
- Contradictions.

Planner cần có khả năng:
- Từ chối context lỗi thời.
- Yêu cầu thêm thông tin.
- Abstain khi thiếu thông tin quan trọng.
- Chuyển xung đột có ảnh hưởng lớn sang human review.
- Giải thích evidence nào ảnh hưởng đến quyết định.

## 6. Feedback Loop

Vòng phản hồi an toàn:

1. Planning đề xuất plan.
2. Governance kiểm tra proposal.
3. Execution system được cấp quyền thực hiện hành động.
4. Execution system ghi nhận observations.
5. Evidence được thu thập.
6. Memory đánh giá và ingest record đủ điều kiện.
7. Planning sử dụng outcome đã xác minh trong lần đánh giá sau.
8. Meta-cognitive components cập nhật thống kê theo evidence policy.

Không coi một hành động dự định là hành động đã hoàn thành.

## 7. Version và Consistency

Integration cần truyền phiên bản:
- Goal.
- World State.
- Memory Snapshot.
- Evidence Package.
- Plan.
- Policy.
- Strategy.

Nếu input quan trọng thay đổi, plan có thể cần revalidation hoặc replanning.

## 8. Failure Handling

- Memory unavailable: áp dụng degraded-mode policy rõ ràng.
- Evidence conflict: review hoặc abstain khi có ảnh hưởng đáng kể.
- Stale state: cập nhật context trước khi sử dụng.
- Permission denied: không truy xuất qua đường khác.
- Planning failure: trả structured failure.
- Execution failure: ghi outcome và dùng recovery boundary được cấp quyền.

## 9. Tách biệt với AgentCore

AgentCore giữ trách nhiệm riêng về:
- Durable task lifecycle.
- Lease.
- Heartbeat.
- Resumption.
- Persistence.
- Tool execution.

Planning cung cấp proposal hoặc recommendation cho integration layer
được cấp quyền. Không thay thế AgentCore hoặc vượt qua authorization.

## 10. Đánh giá mức độ tích hợp

Có các module Planning và Memory không chứng minh hai hệ thống đã
được tích hợp end-to-end.

Cần xác minh:
- Dependency wiring tại composition root.
- Runtime invocation.
- Contract compatibility.
- Error propagation.
- Authorization tests.
- End-to-end tests.
