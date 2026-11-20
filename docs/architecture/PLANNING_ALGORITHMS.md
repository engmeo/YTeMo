# Planning — Thuật toán và nền tảng toán học

## 1. Graph Search

### Breadth-First Search (BFS)

Khám phá node theo từng mức độ sâu.

Ưu điểm:
- Đầy đủ trong không gian hữu hạn với branching hữu hạn.
- Tìm lời giải nông nhất khi chi phí mọi action bằng nhau.

Hạn chế:
- Tốn bộ nhớ khi branching factor lớn.

### Depth-First Search (DFS)

Đi sâu vào một nhánh trước khi quay lui.

Ưu điểm:
- Bộ nhớ thường thấp hơn BFS.

Hạn chế:
- Có thể mắc kẹt trong nhánh rất sâu.
- Không đảm bảo lời giải ngắn nhất.

### Uniform-cost Search

Mở rộng node có tổng chi phí đường đi thấp nhất g(n).

Phù hợp khi chi phí action khác nhau và không âm.

## 2. Dijkstra và A*

Dijkstra ưu tiên node có chi phí tích lũy nhỏ nhất:

f(n) = g(n)

A* kết hợp chi phí đã đi và heuristic:

f(n) = g(n) + h(n)

Trong đó:
- g(n): chi phí đã phát sinh.
- h(n): ước lượng chi phí còn lại.

Heuristic admissible giúp A* đảm bảo tối ưu trong các giả định chuẩn.
Consistency là một thuộc tính quan trọng khác.

Hạn chế:
- Heuristic yếu làm A* gần với uniform-cost search.
- Heuristic không admissible có thể làm mất tính tối ưu.
- Branching factor lớn gây tăng bộ nhớ.
- State abstraction sai có thể tạo lời giải không hợp lệ.

## 3. Greedy Best-first Search

Chọn node có heuristic h(n) thấp nhất.

Có thể nhanh nhưng không đảm bảo tối ưu vì bỏ qua chi phí đã phát sinh.

## 4. Beam Search

Ở mỗi độ sâu, chỉ giữ lại k candidate tốt nhất.

Ưu điểm:
- Giới hạn kích thước frontier.
- Hữu ích với không gian tìm kiếm lớn.

Hạn chế:
- Có thể loại bỏ nhánh dẫn đến global optimum.
- Phụ thuộc vào scoring và beam width.
- Không đảm bảo complete hoặc optimal nói chung.

## 5. Monte Carlo Tree Search (MCTS)

MCTS thường gồm bốn bước:

1. Selection: đi qua cây hiện có để chọn node.
2. Expansion: thêm node con.
3. Simulation: ước lượng kết quả từ trạng thái được chọn.
4. Backpropagation: cập nhật thống kê trên đường đi.

Một công thức UCT phổ biến:

UCT(i) = Q(i) / N(i)
         + c * sqrt(ln N(parent) / N(i))

Trong đó:
- Q(i): tổng reward.
- N(i): số lần thăm node.
- c: hệ số exploration.

Hạn chế:
- Chất lượng rollout ảnh hưởng kết quả.
- Không gian action lớn gây tốn tính toán.
- Graph search xác định không tự động là POMDP solver.
- Reward model sai có thể dẫn tới quyết định sai.

## 6. Hierarchical Task Network (HTN)

Abstract task được thay thế bằng subtasks thông qua decomposition method.

Một HTN engine cần:
- Method applicability.
- Tie-breaking rõ ràng.
- Cycle detection.
- Maximum depth.
- Expansion limits.
- Dependency validation.
- Decomposition trace.

HTN giúp tận dụng cấu trúc công việc có sẵn nhưng method library sai có
thể tạo ra kế hoạch sai có hệ thống.

## 7. Topological Sorting

Với directed acyclic graph, Topological Sorting tìm thứ tự sao cho mọi
prerequisite xuất hiện trước task phụ thuộc vào nó.

Kahn's Algorithm liên tục loại bỏ node có indegree bằng 0.

Nếu tồn tại cycle, không thể tạo topological ordering hợp lệ.

Độ phức tạp: O(V + E).

## 8. Belief Updating

Với giả thuyết H và bằng chứng E:

P(H | E) = P(E | H) P(H) / P(E)

Với phân phối rời rạc:

P(E) = sum_h P(E | h) P(h)

Yêu cầu:
- Likelihood model phải có ý nghĩa.
- Phải xem xét sự phụ thuộc giữa evidence.
- Prior phải rõ ràng.
- Không coi thiếu evidence là evidence phủ định.

Phân phối đã chuẩn hóa không mặc nhiên là xác suất đã calibration.

## 9. Entropy và Information Gain

Shannon entropy:

H(X) = -sum_x P(x) log2 P(x)

Information Gain:

IG = H(X) - H(X | E)

Entropy đo độ bất định trong một phân phối cụ thể. Nó không tự đo tính
đúng đắn, rủi ro lâm sàng hay sự thật.

## 10. Value of Information (VOI)

Một dạng tổng quát:

VOI = ExpectedUtility(with information)
      - ExpectedUtility(without information)
      - InformationAcquisitionCost

Thông tin có giá trị khi nó có khả năng cải thiện quyết định đủ để bù
chi phí và thời gian thu thập.

## 11. Pareto Optimization

Với các objective cần minimize f1 ... fm, candidate x dominates y khi:

- fi(x) <= fi(y) với mọi objective.
- Có ít nhất một objective tốt hơn nghiêm ngặt.

Pareto Frontier giữ lại các candidate không bị dominated.

### Epsilon Dominance

Cho phép sai khác trong một ngưỡng epsilon để giảm độ nhạy với chênh lệch
số học nhỏ.

### Crowding Distance

Ước lượng mức độ cô lập của candidate trong Pareto front để duy trì
sự đa dạng.

## 12. Online Statistics — Welford's Algorithm

Với observation mới x:

n' = n + 1
delta = x - mean
mean' = mean + delta / n'
delta2 = x - mean'
M2' = M2 + delta * delta2

Sample variance:

variance = M2 / (n - 1)

Ưu điểm:
- Cập nhật một lượt.
- Không cần giữ toàn bộ lịch sử.
- Ổn định số học hơn cách tính tổng bình phương đơn giản.

Không tự giải quyết được sampling bias, non-stationarity hoặc dữ liệu
chưa được xác minh.

## 13. Upper Confidence Bound (UCB)

Một dạng UCB1:

UCB(i) = mean_reward(i)
         + c * sqrt(ln(total_trials) / trials(i))

Cân bằng exploitation và exploration.

Cần chú ý:
- Giả định về reward distribution.
- Chiến lược thay đổi theo thời gian.
- Safety constraints phải được áp dụng độc lập với reward ranking.
- Exploration không được phép vi phạm safety policy.

## 14. Temporal Constraint Networks

Simple Temporal Network biểu diễn:

l <= t_j - t_i <= u

Các ràng buộc tạo thành graph của những mốc thời gian.

Consistency checking xác định liệu tất cả ràng buộc có thể đồng thời
được thỏa mãn hay không.

## 15. Robust Optimization

Một dạng bài toán:

minimize_x max_{u in U} f(x, u)

U là tập bất định.

Robust optimization bảo vệ trước các bất định đã mô hình hóa, nhưng
có thể quá bảo thủ nếu U không thực tế.

## 16. Causal Models

Structural Causal Model:

X_i = f_i(PA_i, U_i)

Trong đó:
- PA_i: các biến cha.
- U_i: nhiễu ngoại sinh.
- f_i: structural function.

Intervention do(X=x) khác với conditioning thông thường.

Kết luận nhân quả cần giả định có cơ sở và khả năng identification.
Causal graph không tự chứng minh causal effect.

## 17. POMDP

POMDP thường được định nghĩa:

(S, A, T, O, Z, R, gamma)

- S: trạng thái.
- A: hành động.
- T: transition model.
- O: observation.
- Z: observation model.
- R: reward.
- gamma: discount factor.

Belief State biểu diễn sự không chắc chắn về hidden state. Exact solution
có thể rất tốn tính toán nên thường cần phương pháp xấp xỉ.

## 18. Tiêu chí lựa chọn thuật toán

Cần xem xét:
- Kích thước state space.
- Branching factor.
- Planning horizon.
- Mức độ quan sát được.
- Chi phí action.
- Compute budget.
- Yêu cầu optimality.
- Safety constraints.
- Chất lượng model.
- Yêu cầu giải thích và audit.

Không có một thuật toán tối ưu cho mọi bài toán Planning.
