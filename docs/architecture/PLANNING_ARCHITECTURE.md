# Planning Intelligence — Tài liệu kiến trúc toàn diện

## 1. Sứ mệnh

Planning Intelligence chuyển đổi mục tiêu, trạng thái, ràng buộc, bằng chứng
và mức độ không chắc chắn thành những kế hoạch có cấu trúc, có thể kiểm tra
và có thể đánh giá.

Planning không mặc nhiên sở hữu quyền thực thi công việc, quản lý tool,
lease, heartbeat hoặc persistence. Những trách nhiệm đó thuộc về tầng
thực thi và hệ thống quản lý tác vụ phù hợp.

## 2. Goal & Intent Intelligence

### Vấn đề cần giải quyết

Yêu cầu người dùng có thể rộng, thiếu thông tin, chứa nhiều mục tiêu hoặc
có những mục tiêu xung đột nhau.

Planner cần chuyển yêu cầu thành biểu diễn mục tiêu rõ ràng trước khi
tìm kiếm phương án.

### Các thành phần

- Goal Representation: biểu diễn mục tiêu.
- Goal Decomposition: chia mục tiêu lớn thành mục tiêu con.
- Goal Prioritization: xác định thứ tự ưu tiên.
- Goal Dependency: mô tả quan hệ phụ thuộc.
- Goal Conflict Resolution: phát hiện và xử lý mục tiêu xung đột.
- Goal Lifecycle: quản lý trạng thái mục tiêu.

### Kiến trúc nâng cao

- Goal Graph.
- AND/OR Graph.
- Hierarchical Goal Network.
- Utility-based Prioritization.
- Constraint-based Goal Resolution.
- Intent Inference có biểu diễn uncertainty.

### Giới hạn

Intent Inference chỉ đưa ra giả thuyết về ý định. Nó không được tự ý thay
thế yêu cầu rõ ràng hoặc suy diễn quyền cho phép của người dùng.

## 3. State & World Modeling

### Vấn đề

Kế hoạch phụ thuộc vào trạng thái hiện tại. Khi dữ kiện, tài nguyên hoặc
điều kiện thay đổi, những giả định cũ có thể không còn đúng.

### Thành phần

- State Representation: biểu diễn trạng thái.
- State Abstraction: trừu tượng hóa trạng thái.
- Transition Model: mô hình chuyển trạng thái.
- Preconditions: điều kiện trước khi thực hiện hành động.
- Effects: kết quả dự kiến của hành động.
- Prediction: dự đoán trạng thái tiếp theo.
- Observation Comparison: so sánh dự đoán với quan sát.
- State Versioning: quản lý phiên bản trạng thái.

### Hướng nâng cao

- Model-based Planning.
- Probabilistic State Estimation.
- Learned Transition Models.
- Latent World Models.
- Ensemble Prediction.
- Uncertainty Estimation.
- Dynamic State Abstraction.

Mô hình chuyển trạng thái dựa trên luật không đồng nghĩa với World Model
được học từ dữ liệu.

## 4. Classical & Heuristic Planning

### Classical Planning

Một bài toán lập kế hoạch có thể được mô tả bởi:

- S0: trạng thái ban đầu.
- G: điều kiện mục tiêu.
- A: tập hành động.
- Pre(a): điều kiện tiên quyết của hành động.
- Eff(a): tác động của hành động.
- c(a): chi phí hành động.

Hành động chỉ hợp lệ khi các điều kiện tiên quyết được đáp ứng.

### STRIPS và PDDL

STRIPS mô tả hành động bằng preconditions, add effects và delete effects.

PDDL mở rộng cách mô tả bài toán lập kế hoạch với kiểu dữ liệu, predicates,
numeric fluents và temporal constructs.

### Các hướng tìm kiếm

- Forward Search: tìm từ trạng thái ban đầu.
- Backward Search: suy luận ngược từ mục tiêu.
- Partial-order Planning: chỉ xác định thứ tự bắt buộc.
- Constraint-based Planning: giải bài toán dựa trên ràng buộc.

## 5. Hierarchical & Multi-Level Planning

### Vấn đề

Mục tiêu dài hạn thường quá phức tạp để giải quyết bằng một chuỗi hành động
phẳng.

### Hierarchical Task Network (HTN)

HTN phân rã một abstract task thành các subtask thông qua decomposition
methods cho đến khi thu được primitive tasks.

Các thành phần:
- Abstract Task.
- Primitive Task.
- Decomposition Method.
- Method Applicability.
- Subtask Ordering.
- Dependency Graph.
- Decomposition Trace.

### Ba tầng lập kế hoạch

- Strategic Planning: xác định mục tiêu và định hướng tổng thể.
- Tactical Planning: lựa chọn phương pháp và các mục tiêu trung gian.
- Operational Planning: tạo các bước hành động cụ thể.

### Điều kiện kiểm soát

- Phát hiện decomposition cycle.
- Giới hạn độ sâu và số node.
- Kiểm tra định danh task.
- Kiểm tra dependency.
- Lưu decomposition trace.
- Validate kế hoạch sau khi chuyển đổi.

HTN decomposition không phải là execution.

## 6. Plan Graph & Dependency Intelligence

Plan có thể được biểu diễn bằng directed graph.

- Node: task hoặc action.
- Edge: dependency hoặc thứ tự.
- Critical Path: chuỗi phụ thuộc quyết định thời gian tối thiểu.
- Topological Sorting: tìm thứ tự hợp lệ.
- Cycle Detection: phát hiện phụ thuộc vòng.

Hướng mở rộng:
- Conditional Branches.
- AND/OR Dependencies.
- Dynamic Graph Updates.
- Resource-constrained Critical Path.
- Partial-order Execution.

## 7. Search Intelligence

Search khám phá các trạng thái hoặc kế hoạch ứng viên.

Nhóm thuật toán:
- Breadth-First Search.
- Depth-First Search.
- Uniform-cost Search.
- Best-first Search.
- A*.
- Beam Search.
- Monte Carlo Tree Search.
- Anytime Search.
- Bounded Search.

Việc lựa chọn phụ thuộc vào branching factor, độ sâu, chi phí hành động,
chất lượng heuristic, tài nguyên và yêu cầu tối ưu.

Chi tiết nằm trong PLANNING_ALGORITHMS.md.

## 8. Belief & Decision Intelligence

### Belief State

Belief State biểu diễn sự không chắc chắn về trạng thái thế giới hoặc
các giả thuyết có thể xảy ra.

### Decision Engine

Một decision candidate có thể bao gồm:
- Action.
- Expected Utility.
- Cost.
- Risk.
- Uncertainty.
- Preconditions.
- Evidence References.
- Human Approval Requirements.

### POMDP-oriented Planning

Partially Observable Markov Decision Process sử dụng:
- S: states.
- A: actions.
- O: observations.
- T: transition probabilities.
- Z: observation probabilities.
- R: reward function.
- b: belief state.

Belief update kết hợp belief trước đó, action và observation.

Có belief-state primitive không đồng nghĩa với việc đã có POMDP solver
hoàn chỉnh.

## 9. Information & Value-of-Information Planning

Planner có thể cần thêm thông tin trước khi đưa ra quyết định.

Các năng lực:
- Information Gap Detection.
- Evidence Request Generation.
- Information-gathering Actions.
- Value of Information (VOI).
- Expected Decision Loss Reduction.
- Information Acquisition Cost.

Thông tin bổ sung chỉ hữu ích khi lợi ích kỳ vọng đủ lớn để bù chi phí,
thời gian và rủi ro thu thập.

## 10. Causal & Counterfactual Reasoning

### Causal Modeling

Causal Graph biểu diễn các quan hệ nhân quả được giả định.

Structural Causal Model mô tả biến thông qua structural equations.

### Counterfactual Reasoning

Đặt câu hỏi: điều gì có thể xảy ra nếu một điều kiện hoặc hành động khác đi?

Giới hạn:
- Correlation không đồng nghĩa với causation.
- Giả định nhân quả phải được công khai.
- Hệ số do người dùng nhập không phải causal discovery.
- Kết quả counterfactual phụ thuộc vào độ đúng của mô hình.

## 11. Multi-Objective Optimization

Kế hoạch thực tế thường có nhiều mục tiêu:

- Giảm chi phí.
- Giảm thời gian.
- Giảm rủi ro.
- Tăng utility.
- Tăng độ tin cậy.

### Pareto Optimality

Một candidate bị dominated nếu một candidate khác tốt hơn hoặc bằng ở mọi
objective và tốt hơn nghiêm ngặt ở ít nhất một objective.

Pareto Frontier giữ lại các phương án không bị dominated thay vì ép mọi
trade-off thành một điểm số duy nhất.

Các hướng mở rộng:
- Epsilon Dominance.
- Crowding Distance.
- Evolutionary Multi-objective Optimization.
- Constraint-aware Dominance.
- Robust Pareto Optimization.

## 12. Temporal & Resource Planning

Temporal Planning xử lý:
- Start time.
- End time.
- Duration.
- Deadline.
- Precedence Constraints.
- Concurrent Tasks.
- Time Windows.

Resource Planning xử lý:
- Capacity.
- Consumption.
- Availability.
- Shared Resources.
- Resource Conflicts.

Các hướng nâng cao:
- Simple Temporal Networks.
- Constraint Programming.
- Mixed-integer Optimization.
- Resource-constrained Scheduling.

## 13. Risk & Robustness

Risk-aware Planning đánh giá hiệu quả và những kết quả bất lợi.

Các phương pháp:
- Risk Thresholds.
- Worst-case Analysis.
- Scenario-based Planning.
- Sensitivity Analysis.
- Robust Optimization.
- Chance Constraints.
- Distributionally Robust Optimization.
- Failure-mode Analysis.

Điểm risk do caller cung cấp không mặc nhiên là xác suất thất bại thực tế
đã được hiệu chuẩn.

## 14. Adaptive Execution & Recovery

Planning cần phản ứng khi thực tế khác với dự đoán.

Luồng xử lý:
1. Khởi tạo execution state.
2. Theo dõi trạng thái từng bước.
3. Ghi nhận bắt đầu và hoàn thành.
4. Thu thập kết quả và evidence.
5. So sánh dự đoán với quan sát.
6. Phát hiện deviation.
7. Đề xuất continue, retry, replan, pause hoặc human review.
8. Lưu audit trace.

Planner có thể đề xuất recovery. Hệ thống thực thi phải kiểm tra quyền
và thực hiện riêng.

## 15. Meta-Cognitive Intelligence

Meta-Cognition đánh giá chính quá trình lập kế hoạch.

Các năng lực:
- Strategy Performance Tracking.
- Evidence-based Online Learning.
- Adaptive Strategy Selection.
- Failure Analysis.
- Metareasoning.
- Compute and Latency Budgeting.
- Introspection Trace.

Chỉ học từ outcome đã xác minh theo policy. Không tự ý nới lỏng safety
constraints.

## 16. Multi-Agent Planning

Phối hợp nhiều planner hoặc agent.

Các bài toán:
- Task Allocation.
- Shared Goal Decomposition.
- Resource Competition.
- Coordination.
- Negotiation.
- Plan Merging.
- Conflict Resolution.
- Partial Observability.
- Communication Overhead.

Các mô hình:
- Centralized Planning.
- Decentralized Planning.
- Contract Net Protocol.
- Distributed Constraint Optimization.
- Cooperative Game Theory.

AgentCore vẫn là ranh giới lifecycle và execution độc lập.

## 17. Verification & Governance

Validation kiểm tra plan có thỏa mãn các ràng buộc đã khai báo không.

Verification kiểm tra một thuộc tính có đúng dưới mô hình xác định không.

Các phương pháp:
- Preconditions and Postconditions.
- Invariant Checking.
- Dependency Validation.
- Temporal Logic.
- Model Checking.
- Runtime Verification.
- Safety Cases.
- Human Approval Gates.

Plan hợp lệ theo policy phần mềm không tự động đồng nghĩa với phù hợp
về mặt lâm sàng.

## 18. Advanced & Emerging Planning

Các hướng nghiên cứu và nâng cấp:

- LLM-guided Planning.
- Neuro-symbolic Planning.
- Learning-based Heuristic Generation.
- Model-based Reinforcement Learning.
- World-model-based Planning.
- Inference-time Compute Scaling.
- Anytime Planning.
- Long-horizon Planning.
- Continual Adaptation.
- Retrieval-augmented Planning.
- Risk-sensitive Planning.
- Robust Planning under Distribution Shift.

Đây là hướng phát triển, không phải tuyên bố đã triển khai.

## 19. Ranh giới tích hợp

Planning nhận goal, state, constraints và evidence có cấu trúc.

Planning trả về plan, evaluation, trace và recommendation.

Planning Core không trực tiếp:
- Sở hữu Supabase persistence.
- Dispatch tool tùy ý.
- Quản lý execution lease.
- Bỏ qua AgentCore.
- Thay đổi consent.
- Vượt qua governance policy.

Tích hợp phải thông qua contract và composition layer rõ ràng.
