# Y TẾ MỞ — KIẾN TRÚC MEMORY INTELLIGENCE & HEALTHCARE COGNITIVE PLANNING

> Tài liệu kiến trúc mục tiêu và hướng dẫn triển khai. Không đồng nghĩa mọi thành phần đã có trong mã nguồn hoặc đã được xác nhận an toàn lâm sàng. Trạng thái triển khai phải được xác minh bằng Source Code, Database Schema, Migration và Tests.

## 1. Kiến trúc đích

Y TẾ MỞ được thiết kế như một **Personal Healthcare Companion Agent** có khả năng duy trì bối cảnh sức khỏe theo thời gian, nhận biết điều chưa biết, lập kế hoạch chăm sóc, điều phối tác vụ được ủy quyền, theo dõi kết quả và lập kế hoạch lại.

Healthcare là miền nghiệp vụ cốt lõi của Planning, không phải plugin gắn thêm vào một Universal Planner.

```text
                  PERSONAL HEALTHCARE COMPANION
                               |
          +--------------------+--------------------+
          |                    |                    |
          v                    v                    v
   MEMORY INTELLIGENCE  HEALTHCARE COGNITIVE   GOVERNANCE
                             PLANNING
          |                    |                    |
          v                    v                    v
   Memory Graph          Patient State         Identity/Consent
   Evidence Lineage      Belief State           Policy Engine
   Temporal Store        Goal Manager           Audit
   Conflict Engine       Clinical Reasoner      Safety Rules
   Consolidation         Active Info Planner    Human Review
   Retrieval             Plan Search            Evaluation
          |                    |
          +---------+----------+
                    v
           PATIENT-CENTRIC PLAN GRAPH
                    |
                    v
          VERIFICATION & RUNTIME GUARD
                    |
                    v
          AGENT EXECUTION / WORKFLOWS
                    |
                    v
          OBSERVATIONS & OUTCOMES
                    |
                    +----> Memory update + Replanning
```

### Ranh giới trách nhiệm

| Thành phần | Trả lời câu hỏi | Không được làm |
|---|---|---|
| Memory | Hệ thống biết gì, từ đâu, vào lúc nào, có được phép dùng không? | Tự biến suy luận thành sự thật y khoa |
| Clinical Evidence | Bằng chứng y khoa bên ngoài hỗ trợ điều gì, trong điều kiện nào? | Giả làm dữ liệu cá nhân |
| Patient State | Bức tranh hiện tại về người dùng là gì? | Xóa mất nguồn gốc hoặc bất định |
| Belief State | Điều gì có khả năng đúng và còn chưa chắc chắn? | Trình bày giả thuyết như chẩn đoán xác nhận |
| Planner | Bước tiếp theo hợp lý, hợp lệ và được phép là gì? | Tự cấp quyền thực thi |
| Runtime Guard | Hành động có còn được phép và an toàn tại thời điểm chạy? | Tin mù quáng vào quyết định của Planner |
| Executor | Thực hiện tác vụ được ủy quyền và ghi nhận kết quả | Tự mở rộng phạm vi quyền hạn |

---

# PHẦN A — MEMORY INTELLIGENCE

## 2. Memory không phải Chat History

Memory là một hệ thống quản lý tri thức cá nhân có nguồn gốc, thời gian, trạng thái xác minh, quyền sử dụng và lịch sử thay đổi.

Mỗi Memory/Claim nên mang theo các thuộc tính phù hợp:
- `owner_scope`, `subject_id`, `memory_type`
- `content` hoặc cấu trúc Claim
- `source_type`, `source_id`, `author`
- `observed_at`, `recorded_at`
- `valid_from`, `valid_to`
- `verification_status`, `confidence`
- `consent_scope`, `purpose`
- `supersedes`, `derived_from`
- `created_at`, `updated_at`, `version`

Không phải trường nào cũng bắt buộc cho mọi loại Memory. Schema thực tế phải được chuẩn hóa theo loại dữ liệu và chính sách riêng tư.

## 3. Các kiến trúc Memory nâng cao

### 3.1 Provenance-aware Memory & Evidence Lineage
**Mục đích:** truy ngược một thông tin đến nguồn ban đầu và các bước biến đổi.

```text
User statement / EHR / Lab / Clinician
                 |
                 v
            Source Record
                 |
                 v
          Normalized Claim
                 |
          +------+------+
          |             |
          v             v
     Evidence Link   Verification
          |             |
          +------+------+
                 v
           Usable Memory
```

- Lưu nguồn, thời điểm, tác giả, phương thức nhập và trạng thái xác minh.
- Tách `source fact`, `agent inference` và `derived summary`.
- Duy trì đồ thị `Claim -> Evidence -> Derived Claim`.
- Khi nguồn bị sửa/thu hồi, xác định toàn bộ Memory phụ thuộc để đánh giá lại.
- Không gán `verified` chỉ vì LLM diễn đạt tự tin.

**Kỹ thuật liên quan:** Data Provenance, Knowledge Graph, Evidence Graph, Lineage Tracking.

### 3.2 Bitemporal & Event-sourced Memory
**Mục đích:** trả lời cả “điều gì đúng vào thời điểm đó?” và “hệ thống biết điều đó từ khi nào?”.

- `Valid Time`: thời gian sự kiện có hiệu lực trong thế giới thực.
- `Transaction Time`: thời gian hệ thống ghi nhận.
- `Append-only Events`: giữ sự kiện thay đổi thay vì âm thầm ghi đè.
- `Version History`: tái dựng trạng thái tại thời điểm bất kỳ.
- `Supersession`: chỉ rõ bản ghi mới thay thế bản ghi cũ.

```text
Event 1: medication reported
   -> Event 2: dose corrected
       -> Event 3: medication discontinued
```

**Kỹ thuật liên quan:** Bitemporal Data Model, Event Sourcing, Temporal Database, CQRS (chỉ dùng khi có nhu cầu tách read/write rõ ràng).

### 3.3 Conflict-aware Memory & Truth Maintenance
**Mục đích:** phát hiện và quản lý các Claim không tương thích.

Quy trình:
1. Chuẩn hóa dữ liệu thành Claim có chủ thể, thuộc tính, giá trị và thời gian.
2. Tìm Claim có cùng chủ thể/thuộc tính và khoảng thời gian chồng lấn.
3. Phân loại: khác thời điểm, cập nhật mới, khác ngữ cảnh hay mâu thuẫn thật.
4. So sánh nguồn, độ tin cậy, trạng thái xác minh và thời gian.
5. Giữ nguyên các Claim gốc; tạo Conflict Record.
6. Chuyển người dùng/chuyên gia rà soát khi không đủ căn cứ tự giải quyết.

**Kỹ thuật liên quan:** Truth Maintenance Systems, Belief Revision, Argumentation Frameworks, Temporal Conflict Detection.

Không dùng quy tắc “bản ghi mới nhất luôn đúng”.

### 3.4 Derived Memory, Dependency Graph & Incremental Revalidation
**Mục đích:** quản lý tri thức được suy ra từ nhiều Memory.

```text
Claim A ----+
            +--> Derived Pattern C --> Candidate Insight D
Claim B ----+                             |
                                          v
                                  Review / Validation
```

- Mỗi kết quả suy dẫn có danh sách nguồn và phiên bản thuật toán.
- Ghi rõ đây là giả thuyết, mẫu hình hay kết luận đã xác minh.
- Khi A hoặc B thay đổi, đánh dấu C/D cần đánh giá lại.
- Chỉ tính toán lại phần phụ thuộc bị ảnh hưởng (`Incremental Revalidation`).

### 3.5 Memory Consolidation & Multi-timescale Memory
**Mục đích:** tổ chức lượng dữ liệu lớn mà không làm mất khả năng truy xuất nguồn.

Các lớp logic:
- `Episodic Memory`: sự kiện cụ thể theo thời gian.
- `Semantic Memory`: thông tin/khái niệm ổn định được rút ra từ nhiều nguồn.
- `Working Context`: dữ liệu ngắn hạn phục vụ tác vụ hiện tại.
- `Longitudinal Profile`: bức tranh dài hạn, luôn truy ngược được nguồn.

Consolidation phải có chính sách:
- phát hiện trùng lặp;
- gom nhóm sự kiện liên quan;
- tạo Summary có lineage;
- giữ dữ liệu gốc theo retention policy;
- yêu cầu review khi có nội dung nhạy cảm hoặc mâu thuẫn.

Không được xóa nguồn gốc chỉ để tiết kiệm token.

### 3.6 Consent-aware Retrieval & Purpose Limitation
**Mục đích:** bảo đảm Memory chỉ được truy cập đúng người, đúng phạm vi, đúng mục đích.

Trước mỗi lần đọc/ghi:
1. Xác thực user và Agent.
2. Kiểm tra ownership/tenant boundary.
3. Kiểm tra consent theo scope và purpose.
4. Lọc dữ liệu theo quyền tối thiểu cần thiết.
5. Ghi audit đối với hành động quan trọng.
6. Tôn trọng việc thu hồi consent ngay ở lần truy cập tiếp theo.

Retrieval ranking không được vượt qua authorization. Một Memory liên quan cao nhưng không được phép truy cập vẫn phải bị loại.

### 3.7 Transactional Audit & Memory Lifecycle
Memory Lifecycle tham khảo:

```text
CAPTURED -> CANDIDATE -> REVIEW_REQUIRED
                         |          |
                         v          v
                      REJECTED   APPROVED
                                    |
                                    v
                                  ACTIVE
                                    |
                    +---------------+---------------+
                    v               v               v
                SUPERSEDED       EXPIRED          DELETED
```

- Ghi Memory và Audit cần cùng transaction đối với thao tác quan trọng.
- Dùng optimistic concurrency/version check hoặc row lock khi cần.
- Review/activate/delete phải kiểm tra owner, actor, transition hợp lệ.
- Xóa mềm và retention phải phù hợp quy định dữ liệu.
- Candidate do Agent tạo không tự động trở thành Active/Verified.

## 4. Memory Retrieval Pipeline

```text
Query / Planning Request
          |
          v
Identity + Consent + Purpose Check
          |
          v
Owner / Scope Filtering
          |
          v
Temporal Validity Filtering
          |
          v
Semantic + Structured Retrieval
          |
          v
Conflict / Verification / Provenance Check
          |
          v
Relevance & Uncertainty Ranking
          |
          v
Context Assembly with Source References
          |
          v
Planner (untrusted data boundary preserved)
```

Thứ tự bắt buộc: Authorization trước Ranking. Retrieval phải trả được nguồn, thời gian, trạng thái xác minh và cảnh báo mâu thuẫn; không chỉ trả về đoạn text.

---

# PHẦN B — HEALTHCARE COGNITIVE PLANNING

## 5. Planning là một Cognitive Control Loop

Planning không phải một lần gọi LLM để tạo checklist. Đây là vòng lặp có trạng thái, mục tiêu, bằng chứng, tìm kiếm, xác minh và phản hồi:

```text
Observe
  -> Update Patient State
  -> Update Belief State
  -> Detect Needs / Goals
  -> Identify Unknowns
  -> Choose: Ask / Retrieve / Escalate / Act
  -> Generate Candidate Plans
  -> Constrain & Rank
  -> Independent Verification
  -> Human Approval (when required)
  -> Execute Authorized Tasks
  -> Observe Outcomes
  -> Update Memory / State
  -> Replan
```

Mỗi vòng lặp phải có `Plan ID`, `Plan Version`, trạng thái đầu vào, bằng chứng sử dụng, quyết định, phê duyệt và kết quả.

## 6. Patient State, Belief State & State Estimation

### Patient State
Biểu diễn có cấu trúc những gì hiện được ghi nhận: triệu chứng, tiền sử, thuốc, dị ứng, kết quả xét nghiệm, chẩn đoán, sự kiện chăm sóc, mục tiêu và bối cảnh.

Mỗi trường cần giữ nguồn, thời gian, trạng thái xác minh và độ mới.

### Belief State
Biểu diễn bất định:
- giả thuyết đang xét;
- bằng chứng ủng hộ/phản đối;
- xác suất/độ tin cậy nếu có mô hình hiệu chỉnh phù hợp;
- thông tin còn thiếu;
- mâu thuẫn chưa giải quyết;
- điều kiện khiến niềm tin phải cập nhật.

**Kỹ thuật:** Bayesian Updating, Probabilistic Graphical Models, State Estimation, POMDP-inspired planning.

POMDP chỉ nên dùng khi định nghĩa được State, Action, Observation, Transition và Reward/Cost đủ rõ. Không gọi một JSON chứa confidence là POMDP.

## 7. Goal & Intent Management

Goal có cấu trúc:
- mục tiêu do người dùng nêu và mục tiêu đã chuẩn hóa;
- ưu tiên, thời hạn, trạng thái;
- ràng buộc và sở thích;
- tiêu chí thành công;
- quan hệ phụ thuộc;
- nguồn hình thành và người phê duyệt.

Phân cấp:
`Long-term Health Goal -> Care Journey Goal -> Subgoal -> Task -> Verified Outcome`.

Cần phát hiện goal xung đột, goal không khả thi và trường hợp hệ thống đang tối ưu mục tiêu do Agent tự suy diễn thay vì mục tiêu người dùng.

## 8. Clinical Evidence & Evidence-grounded Reasoning

Clinical Evidence là nguồn tri thức y khoa bên ngoài, không phải Memory cá nhân.

Mỗi Evidence cần quản lý:
- nguồn/tổ chức/tài liệu;
- phiên bản, ngày công bố và ngày cập nhật;
- phạm vi đối tượng;
- điều kiện áp dụng/loại trừ;
- mức chất lượng và giới hạn;
- trích dẫn đoạn hỗ trợ;
- xung đột với hướng dẫn khác.

Clinical Reasoning phải liên kết Claim/Recommendation với Evidence cụ thể. Thiếu bằng chứng thì đánh dấu thiếu; không tự tạo citation. Nội dung có rủi ro cao cần chuyên gia có thẩm quyền.

## 9. Active Information Planning — Value of Information

Đôi khi hành động tốt nhất là hỏi thêm, lấy hồ sơ, đo lường hoặc chuyển chuyên gia.

Pipeline:
1. Liệt kê biến/tri thức còn thiếu.
2. Tạo các lựa chọn thu thập thông tin hợp lệ.
3. Ước lượng khả năng thông tin mới làm thay đổi quyết định.
4. Ước lượng chi phí, thời gian, rủi ro và gánh nặng cho người dùng.
5. Tính `Expected Value of Information` khi có mô hình phù hợp.
6. Chọn hỏi/thu thập/chuyển cấp hoặc tiếp tục với bất định được ghi rõ.

**Kỹ thuật:** Value of Information, Active Learning, Bayesian Experimental Design, Information Gain.

Không thu thập dữ liệu nhạy cảm nếu không cần cho quyết định.

## 10. Hierarchical, Temporal & Resource-constrained Planning

Kết hợp các lớp:
- `Strategic Planning`: mục tiêu dài hạn và Care Pathway.
- `Tactical Planning`: phân đoạn chăm sóc, phối hợp chuyên khoa.
- `Operational Planning`: tác vụ, lịch hẹn, follow-up.

Các kỹ thuật:
- `Hierarchical Task Network (HTN)`: phân rã mục tiêu thành tác vụ con theo phương pháp/điều kiện.
- `Classical Planning`: tìm chuỗi hành động từ trạng thái đầu đến trạng thái mục tiêu.
- `Temporal Planning`: biểu diễn duration, deadline, ordering và temporal constraints.
- `Constraint-based Scheduling`: phân lịch theo nguồn lực, thời gian, ưu tiên và phụ thuộc.
- `Receding-horizon Planning`: lập kế hoạch trong một horizon, quan sát lại rồi tối ưu lại.

Chúng bổ trợ nhau: HTN phân rã; temporal/constraint solver kiểm tra lịch; receding horizon cập nhật khi tình hình thay đổi.

## 11. Candidate Search, Optimization & Inference-time Compute

Không chấp nhận phương án đầu tiên chỉ vì văn bản nghe hợp lý.

Quy trình:
1. Sinh một số candidate plan theo các chiến lược khác nhau.
2. Loại candidate vi phạm hard constraints.
3. Kiểm tra tiền điều kiện, dependency và resource.
4. Chấm điểm đa mục tiêu trên các candidate hợp lệ.
5. Giữ lại phương án tốt nhất cùng lý do và trade-off.
6. Nếu không có phương án hợp lệ, hỏi thêm hoặc escalate.

Kỹ thuật tùy bài toán:
- `Beam Search`: giữ một tập candidate tốt qua từng bước.
- `Monte Carlo Tree Search`: khám phá cây hành động khi có simulator/model đánh giá.
- `Best-of-N`: sinh và đánh giá nhiều phương án độc lập.
- `Constraint Programming / SAT / SMT`: kiểm tra tính thỏa mãn ràng buộc.
- `Multi-objective Optimization`: cân bằng nhiều mục tiêu sau khi thỏa hard constraints.
- `Meta-planning`: quyết định có nên dành thêm compute/search budget hay dừng.

`Tree of Thoughts` là một pattern tìm kiếm suy luận, không tự thân là bảo đảm tính đúng. MCTS không phù hợp nếu không có transition/evaluation model đáng tin cậy.

## 12. Causal & Counterfactual Planning

Mục đích: phân biệt tương quan với quan hệ nhân quả và đánh giá hệ quả giả định của lựa chọn.

- `Causal Graph`: biểu diễn giả định nhân quả.
- `Intervention`: mô tả tác động khi thay đổi một biến.
- `Counterfactual`: xem xét điều có thể xảy ra dưới một lựa chọn khác.
- `Sensitivity Analysis`: kiểm tra kết luận có đổi khi giả định thay đổi không.

Không suy ra quan hệ nhân quả chỉ từ dữ liệu quan sát hoặc LLM. Mô hình nhân quả cần giả định, dữ liệu và xác nhận chuyên môn; dùng để hỗ trợ phân tích, không tự quyết định điều trị.

## 13. Risk-aware Planning & Hard Constraints

Tách rõ:
- `Hard Constraints`: điều kiện tuyệt đối không được vi phạm.
- `Clinical Safety Constraints`: chống chỉ định, ngưỡng cảnh báo, yêu cầu chuyên gia.
- `Authorization Constraints`: consent, vai trò và phạm vi hành động.
- `Operational Constraints`: thời gian, năng lực, nguồn lực.
- `Patient Preferences`: chi phí, khả năng tiếp cận, lựa chọn.
- `Optimization Objectives`: tối ưu trong tập phương án hợp lệ.

Không dùng điểm utility cao để bù trừ cho vi phạm hard safety constraint. Không chắc chắn hoặc vượt phạm vi thì dừng/escalate.

## 14. Independent Verification & Runtime Assurance

### Plan Verification
Một bộ kiểm tra độc lập xác minh:
- goal và preconditions;
- evidence/provenance;
- temporal/dependency constraints;
- hard safety constraints;
- authorization;
- expected outcomes;
- failure/recovery path.

### Runtime Assurance
Ngay trước và trong khi chạy:
- kiểm tra consent và quyền hiện hành;
- kiểm tra trạng thái bệnh nhân mới nhất;
- kiểm tra điều kiện dừng;
- xác minh tool/agent có quyền phù hợp;
- chặn hành động nếu dữ liệu hoặc điều kiện đã thay đổi;
- yêu cầu Human Approval khi chính sách quy định.

LLM tự phê bình chính nó không phải Independent Verification. Có thể dùng rule engine, schema validator, constraint solver, policy engine và reviewer độc lập.

## 15. Adaptive Replanning & Longitudinal Continuity

Trigger replanning:
- thông tin mới hoặc kết quả xét nghiệm;
- thay đổi triệu chứng/trạng thái;
- tác vụ thất bại hoặc bị bỏ lỡ;
- consent bị thu hồi;
- evidence/guideline thay đổi;
- người dùng đổi mục tiêu;
- chuyên gia cập nhật chỉ định.

Các phạm vi:
- `Local Replanning`: sửa một task.
- `Partial Replanning`: sửa một nhánh Care Pathway.
- `Global Replanning`: đánh giá lại chiến lược và mục tiêu dài hạn.

Giữ Plan Version cũ, nguyên nhân thay đổi, phần bị ảnh hưởng và phần không thay đổi.

## 16. Multi-perspective Evaluation & Human Oversight

Đánh giá candidate từ các góc nhìn:
- patient preference;
- clinical evidence;
- safety;
- feasibility/resources;
- privacy/consent;
- continuity/outcomes.

Có thể triển khai bằng Evaluator độc lập hoặc Agent chuyên trách. Không bắt buộc mọi góc nhìn phải là một autonomous Agent. Bất đồng quan trọng phải được lưu lại; không lấy majority vote để bỏ qua safety rule.

---

# PHẦN C — HỢP NHẤT MEMORY, PLANNING VÀ EXECUTION

## 17. Patient-centric Plan Graph

Plan là đồ thị có cấu trúc, không chỉ là danh sách text.

Một Node có thể gồm:
- `node_id`, `node_type`, `goal_id`;
- `preconditions`, `dependencies`;
- `action_spec`, `expected_effect`;
- `evidence_refs`, `memory_refs`;
- `assumptions`, `uncertainty`;
- `risk_constraints`, `authorization`;
- `schedule`, `deadline`;
- `verification_spec`, `failure_policy`;
- `execution_status`, `result_refs`.

Các quan hệ: `decomposes_to`, `depends_on`, `scheduled_before`, `blocked_by`, `verified_by`, `supersedes`.

## 18. End-to-end Cognitive Loop

| Bước | Memory | Planning | Guard/Execution |
|---|---|---|---|
| Tiếp nhận | Lưu nguồn và candidate | Xác định yêu cầu | Xác thực danh tính |
| Hiểu bối cảnh | Truy xuất có consent | Tạo Patient/Belief State | Kiểm tra quyền |
| Xác định nhu cầu | Cung cấp lịch sử liên quan | Goal/Need Detection | Escalation nếu cần |
| Thiếu thông tin | Tìm dữ liệu có thể truy cập | Value of Information | Xin consent/clarification |
| Lập kế hoạch | Cung cấp facts và lineage | Sinh/so sánh Plan Graph | Chưa thực thi |
| Xác minh | Cung cấp nguồn | Plan Verification | Policy/clinical gate |
| Thực thi | Ghi event liên quan | Theo dõi trạng thái plan | Runtime Guard + Executor |
| Theo dõi | Cập nhật observations | Outcome evaluation | Xác minh kết quả |
| Học và điều chỉnh | Version/consolidation | Replanning | Audit mọi thay đổi |

## 19. Agent và Workflow không thay thế Planner

- Planner quyết định mục tiêu, thứ tự, phụ thuộc và điều kiện.
- Agent Registry tìm năng lực thực hiện.
- Workflow/Executor chạy task đã được ủy quyền.
- Runtime Guard có quyền chặn.
- Reviewer/Clinician xử lý các quyết định cần chuyên môn.
- Memory lưu bằng chứng, sự kiện và kết quả theo lifecycle.

Một workflow cố định không đồng nghĩa có Cognitive Planning. Một Agent tự tạo checklist cũng không đồng nghĩa có Plan Search hoặc Plan Verification.

---

# PHẦN D — ĐÁNH GIÁ VÀ LỘ TRÌNH

## 20. Benchmark bắt buộc

| Nhóm | Chỉ số/câu hỏi |
|---|---|
| Memory provenance | Có truy ngược đúng nguồn không? |
| Temporal correctness | Có phân biệt valid time và recorded time không? |
| Conflict handling | Có phát hiện và không tự xóa mâu thuẫn không? |
| Consent correctness | Có chặn truy cập sau khi revoke không? |
| Belief calibration | Confidence có được hiệu chỉnh không? |
| Goal correctness | Có giữ đúng mục tiêu người dùng không? |
| Evidence correctness | Citation có thật và áp dụng đúng không? |
| Plan validity | Dependency/temporal constraints có hợp lệ không? |
| Safety | Có chặn mọi hành động vi phạm hard constraints trong test set không? |
| Verification | Có phát hiện candidate sai độc lập không? |
| Execution | Kết quả có được quan sát và đối soát không? |
| Replanning | Có cập nhật đúng phần bị ảnh hưởng không? |
| Longitudinal continuity | Có duy trì ngữ cảnh qua nhiều phiên không? |
| Escalation | Có chuyển chuyên gia đúng lúc không? |

Adversarial tests phải gồm: dữ liệu mâu thuẫn, stale data, sai đơn vị, nguồn giả, prompt injection trong hồ sơ, revoke consent giữa workflow, tool timeout, agent crash, guideline lỗi thời, plan có một bước nguy hiểm giữa nhiều bước hợp lý.

## 21. Lộ trình triển khai thực tế

### Phase 0 — Repository Audit
Đối chiếu Source Code, migrations, API, permissions và tests. Lập ma trận `Implemented / Partial / Proposed / Missing`.

### Phase 1 — Memory Reliability
Hoàn thiện provenance, temporal semantics, conflict lifecycle, consent enforcement, review, transactional audit và regression tests.

### Phase 2 — Planning Contracts
Định nghĩa Patient State, Belief State, Goal, Evidence Reference, Plan Graph, Plan Version và Execution Contract.

### Phase 3 — Deterministic Planning Core
Bắt đầu bằng rule/policy + constraint-based planning có thể kiểm thử; sau đó thêm HTN và temporal scheduling.

### Phase 4 — Search & Information Planning
Thêm candidate search, multi-objective evaluation, Value of Information và meta-planning khi có benchmark chứng minh lợi ích.

### Phase 5 — Verification & Runtime Safety
Independent verifier, runtime authorization, human approval, escalation, failure recovery.

### Phase 6 — Longitudinal Adaptation
Event-driven monitoring, partial/global replanning, outcome tracking và learning có kiểm soát.

### Phase 7 — Validation
Benchmark offline, adversarial tests, simulation, chuyên gia đánh giá và triển khai có giám sát. Không tuyên bố clinical effectiveness chỉ từ Unit Tests.

## 22. Ma trận trạng thái triển khai

Mọi module trong tài liệu phải được gắn một trong bốn trạng thái:

- `IMPLEMENTED`: có source code, integration và tests chứng minh.
- `PARTIALLY IMPLEMENTED`: đã có một phần nhưng thiếu contract, integration hoặc test.
- `PROPOSED`: thiết kế mục tiêu, chưa có bằng chứng triển khai.
- `NOT VERIFIED`: có dấu hiệu tồn tại nhưng chưa kiểm toán đủ.

Tên file/module tồn tại không đủ để đánh dấu `IMPLEMENTED`. Mỗi tuyên bố phải dẫn đến file, symbol, migration và test cụ thể.

## 23. Nguyên tắc bất biến

1. Memory không đồng nghĩa sự thật y khoa.
2. Clinical Evidence không đồng nghĩa dữ liệu cá nhân.
3. Belief không đồng nghĩa diagnosis.
4. Plan không đồng nghĩa authorization.
5. Agent không được tự mở rộng quyền.
6. Consent phải được kiểm tra tại thời điểm truy cập/thực thi.
7. Hard safety constraints không được đánh đổi bằng utility score.
8. LLM không phải verifier duy nhất.
9. Mọi suy dẫn quan trọng phải có lineage.
10. Mọi thay đổi plan quan trọng phải có version và audit.
11. Không tự học để sửa policy lâm sàng ngoài quy trình phê duyệt.
12. Khi không chắc chắn hoặc ngoài phạm vi, phải hỏi thêm hoặc chuyển cấp.

## 24. Đích kiến trúc

**A provenance-grounded, temporally-aware, consent-governed Memory Intelligence system integrated with a belief-state, evidence-grounded, risk-constrained, hierarchical and adaptive Healthcare Cognitive Planning system.**

Đây là kiến trúc mục tiêu. Chỉ những thành phần được kiểm toán bằng code, migration, integration và tests mới được xem là đã triển khai.
