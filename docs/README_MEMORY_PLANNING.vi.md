# Y TẾ MỞ — Kiến trúc Memory và Healthcare Cognitive Planning

**Loại tài liệu:** Tài liệu thiết kế kiến trúc  
**Phạm vi:** Memory Intelligence, Healthcare Cognitive Planning và tích hợp Companion  
**Trạng thái:** Định hướng kiến trúc; cần đối chiếu với mã nguồn trước khi xác nhận triển khai

> **Nguyên tắc:** Phải phân biệt rõ chức năng đã được triển khai, chức năng mới có một phần nền tảng, thiết kế dự kiến và chức năng chưa được kiểm chứng. Sơ đồ kiến trúc không phải bằng chứng rằng hệ thống đã triển khai hoặc an toàn về mặt lâm sàng.

---

## 1. Tầm nhìn kiến trúc

Y TẾ MỞ được định hướng trở thành một **Personal Healthcare Companion** có khả năng đồng hành lâu dài với người dùng, không chỉ là một chatbot trả lời câu hỏi.

Hệ thống cần có khả năng:

1. Duy trì hiểu biết theo thời gian về bối cảnh sức khỏe của người dùng, có kiểm soát `consent` và nguồn gốc dữ liệu.
2. Hiểu mục tiêu, nhu cầu, giới hạn, mức độ không chắc chắn và những thay đổi theo thời gian.
3. Xây dựng, so sánh và đánh giá kế hoạch chăm sóc dựa trên bối cảnh người dùng và bằng chứng lâm sàng.
4. Phối hợp các hành động được cho phép giữa `Agents`, công cụ, dịch vụ y tế và chuyên gia.
5. Theo dõi kết quả và điều chỉnh kế hoạch khi có thông tin mới.
6. Giải thích, kiểm toán và xác minh các quyết định, hành động quan trọng.
7. Nhận biết khi thiếu dữ liệu, thiếu năng lực hoặc cần chuyên gia; không tự bịa ra câu trả lời.

Hai năng lực nhận thức trung tâm:

- **Memory Intelligence:** quản lý hệ thống biết những gì, thông tin đến từ đâu, thay đổi thế nào và có được phép sử dụng hay không.
- **Healthcare Cognitive Planning:** xác định việc gì nên xảy ra tiếp theo, vì sao, theo thứ tự nào, trong điều kiện nào và cần mức phê duyệt nào.

`Memory` và `Planning` là hai phân hệ riêng biệt nhưng tích hợp chặt chẽ. Không phân hệ nào được âm thầm thay thế trách nhiệm của phân hệ còn lại.

## 2. Kiến trúc tổng thể

```text
PERSONAL HEALTHCARE COMPANION
│
├── MEMORY INTELLIGENCE
│   ├── Memory Ingestion
│   ├── Provenance & Evidence
│   ├── Temporal Memory
│   ├── Conflict Detection & Resolution
│   ├── Derived Memory & Lineage
│   ├── Consolidation
│   ├── Review & Lifecycle Management
│   ├── Consent-aware Retrieval
│   └── Transactional Audit
│
├── HEALTHCARE COGNITIVE PLANNING
│   ├── Patient State & Belief State
│   ├── Goal & Intent Management
│   ├── Clinical Context & Evidence Reasoning
│   ├── Active Information Planning
│   ├── Hierarchical & Temporal Planning
│   ├── Search & Optimization
│   ├── Risk-aware Plan Evaluation
│   ├── Independent Verification
│   ├── Runtime Assurance
│   └── Longitudinal Adaptive Replanning
│
├── EXECUTION & COORDINATION
│   ├── Agent Registry
│   ├── Agent Execution Runtime
│   ├── Workflow Coordination
│   ├── Tool & Service Integration
│   └── Human Approval & Escalation
│
└── GOVERNANCE & EVALUATION
    ├── Identity & Ownership
    ├── Consent & Permissions
    ├── Clinical Knowledge Governance
    ├── Audit & Observability
    ├── Safety Policies
    └── Simulation & Benchmarking
```

Healthcare là lĩnh vực trung tâm của Planning trong Y TẾ MỞ. Trạng thái sức khỏe, bằng chứng lâm sàng, mục tiêu chăm sóc và ràng buộc an toàn phải là các khái niệm cốt lõi của `Healthcare Cognitive Planning`, không phải tính năng tùy chọn được thêm vào sau khi tạo một tác vụ chung.

---

# PHẦN I — MEMORY INTELLIGENCE

## 3. Nguyên tắc thiết kế Memory

`Memory` không chỉ là tập hợp các bản tóm tắt hội thoại. Đây là hệ thống lưu trữ thông tin có kiểm soát, có phiên bản và có thể truy xuất nguồn gốc, nhằm hỗ trợ Companion.

Hệ thống phải phân biệt:

- Thông tin do người dùng cung cấp.
- Thông tin nhập từ hồ sơ y tế.
- Thông tin được chuyên gia có chuyên môn xác nhận.
- Giả thuyết hoặc suy luận do Agent tạo ra.
- Thông tin được suy ra từ các Memory khác.
- Thông tin mâu thuẫn, hết hạn, bị thu hồi hoặc đã được thay thế.

**Nguyên tắc bắt buộc:** Một bản ghi Memory không tự động trở thành sự thật lâm sàng. Việc lưu một suy luận không có nghĩa suy luận đó đã được xác minh về mặt y khoa.

## 4. Các kiến trúc Memory nâng cao

### 4.1. Provenance-aware Memory — Memory có nguồn gốc

Mỗi Memory quan trọng cần lưu nguồn gốc và quan hệ dẫn xuất.

Metadata nên có:

- Loại nguồn và mã nguồn.
- Tác giả hoặc chủ thể chịu trách nhiệm, nếu biết.
- Thời điểm tạo và thời điểm quan sát.
- Trạng thái xác minh.
- Độ tin cậy hoặc mức độ không chắc chắn, khi phù hợp.
- Tham chiếu bằng chứng.
- Quan hệ dẫn xuất.
- Điều kiện hết hạn hoặc thời hạn hiệu lực.
- Chủ sở hữu và phạm vi truy cập.

Nhờ đó, hệ thống phân biệt được triệu chứng do người dùng tự khai báo với kết quả xét nghiệm hoặc chẩn đoán được chuyên gia xác nhận.

**Mẫu kiến trúc:** `Provenance Graph` và `Evidence Lineage`.

### 4.2. Temporal & Versioned Memory — Memory theo thời gian và phiên bản

Thông tin sức khỏe thay đổi theo thời gian. Memory cần giữ được cả trạng thái hiện tại lẫn lịch sử.

Các khái niệm quan trọng:

- `Valid Time`: thời điểm thông tin đúng trong thực tế.
- `Transaction Time`: thời điểm hệ thống tiếp nhận hoặc lưu thông tin.
- `Version History`: lịch sử các lần thay đổi.
- `Supersession`: bản ghi nào thay thế bản ghi trước.
- `Historical Reconstruction`: hệ thống đã biết gì tại một thời điểm trong quá khứ.

Cách này giúp suy luận theo chiều dài thời gian mà không viết lại lịch sử.

**Mẫu kiến trúc:** `Bitemporal Data Modeling`, lịch sử phiên bản chỉ bổ sung và truy vấn theo thời gian.

### 4.3. Conflict-aware Memory — Memory nhận diện mâu thuẫn

Hệ thống phải phát hiện các thông tin không tương thích thay vì âm thầm chọn một thông tin.

Ví dụ:

- Danh sách thuốc khác nhau.
- Ngày tháng không khớp.
- Triệu chứng hoặc tình trạng sức khỏe thay đổi.
- Hai nguồn cung cấp giá trị khác nhau.
- Hồ sơ mới thay thế thông tin cũ.

Việc xử lý mâu thuẫn cần giữ lại các khẳng định gốc, so sánh nguồn gốc và thời hạn hiệu lực, đồng thời ghi nhận quyết định xử lý.

Không được giải quyết mâu thuẫn chỉ bằng cách chọn bản ghi được ghi gần nhất.

**Mẫu kiến trúc:** phát hiện mâu thuẫn ở cấp `Claim`, so sánh bằng chứng và chính sách giải quyết tường minh.

### 4.4. Derived Memory & Lineage — Memory suy dẫn và quan hệ nguồn

Hệ thống có thể tạo bản tóm tắt hoặc mẫu hình hữu ích từ các Memory đã có.

```text
Quan sát gốc
    │
    ▼
Mẫu hình được suy ra
    │
    ▼
Diễn giải giả định
    │
    ▼
Rà soát hoặc xác nhận
```

Mỗi thông tin suy dẫn phải xác định các bản ghi nguồn và phương pháp suy dẫn.

Nếu nguồn bị sửa, thu hồi hoặc mất hiệu lực, các Memory phụ thuộc phải được xác định để đánh giá lại.

**Mẫu kiến trúc:** `Derivation Graph`, theo dõi phụ thuộc và vô hiệu hóa theo quan hệ nguồn.

### 4.5. Memory Lifecycle & Human Review — Vòng đời Memory và rà soát

Memory cần có vòng đời rõ ràng.

```text
CAPTURED
   │
   ▼
CANDIDATE
   │
   ├── Cần làm rõ
   ├── Đang mâu thuẫn
   ├── Hết hạn
   ├── Bị từ chối
   │
   ▼
REVIEWED
   │
   ▼
APPROVED / ACTIVE
   │
   ▼
SUPERSEDED / EXPIRED / DELETED
```

Trạng thái và chuyển đổi cụ thể phải tuân theo Schema cơ sở dữ liệu và chính sách ứng dụng hiện có.

Thông tin do Agent tạo ra không được tự động trở thành Memory đã xác minh.

### 4.6. Consent-aware Memory Access — Truy cập Memory theo Consent

Việc đọc và thay đổi Memory phải tuân thủ:

- Quyền sở hữu của người dùng.
- Danh tính và phạm vi của Agent.
- Nhóm dữ liệu Memory.
- Trạng thái `consent`.
- Mục đích truy cập.
- Quy tắc lưu giữ và hết hạn.
- Thu hồi quyền và xóa dữ liệu.

Phải kiểm tra `consent` tại thời điểm sử dụng, không được giả định rằng quyền truy cập vẫn còn hiệu lực chỉ vì trước đó từng được cho phép.

### 4.7. Transactional Memory & Audit — Memory giao dịch và kiểm toán

Các thay đổi Memory quan trọng nên được thực hiện nguyên tử cùng bản ghi kiểm toán tương ứng.

Không để xảy ra trạng thái Memory đã cập nhật nhưng thiếu bản ghi `audit`.

Thông tin kiểm toán nên có:

- Chủ thể thực hiện.
- Hành động.
- Memory đích.
- Trạng thái trước và sau, khi phù hợp.
- Lý do.
- Thời điểm.
- Mã yêu cầu hoặc mã tương quan liên quan.

### 4.8. Memory Retrieval for Planning — Truy xuất Memory cho Planning

Planning phải truy xuất Memory theo quyết định đang cần xử lý, không tải toàn bộ dữ liệu một cách máy móc.

Các tiêu chí:

- Mức liên quan đến mục tiêu hiện tại.
- Phạm vi chủ sở hữu và `consent`.
- Độ tin cậy của nguồn.
- Trạng thái xác minh.
- Hiệu lực theo thời gian.
- Mâu thuẫn.
- Hết hạn.
- Khả năng ảnh hưởng đến quyết định hiện tại.

Planner phải có khả năng yêu cầu làm rõ khi Memory thiếu hoặc mâu thuẫn.

## 5. Các module Memory đã được nhận diện trong Repository

Kết quả kiểm kê tên file cho thấy có các module:

| Module | Trách nhiệm kiến trúc | Đánh giá hiện tại |
|---|---|---|
| `memory_engine.py` | Ghi, truy xuất, rà soát và xóa Memory | Có module; cần kiểm toán source để xác nhận đầy đủ hành vi |
| `memory_conflict_engine.py` | Phát hiện mâu thuẫn giữa Claim và Evidence | Có module; cần kiểm toán source |
| `memory_intelligence.py` | Suy dẫn, lineage và ứng viên hợp nhất/trùng lặp | Có module; cần kiểm toán source |
| `temporal_memory.py` | Lịch sử phiên bản và hiệu lực theo thời gian | Có module; cần kiểm toán source |
| `companion_core.py` | Trạng thái Companion, sự kiện và thao tác liên quan Consent | Có module; cần kiểm toán tích hợp |
| `supabase_companion_repository.py` | Repository lưu trữ Companion | Có module; cần kiểm toán tích hợp |

Sự tồn tại của các module không chứng minh rằng mọi năng lực Memory nâng cao ở trên đã hoàn thiện.

Trước khi mở rộng Memory, cần kiểm tra triển khai thực tế, Database Migration, Repository Contract, API Integration và Tests.

---

# PHẦN II — HEALTHCARE COGNITIVE PLANNING

## 6. Nguyên tắc thiết kế Planning

`Healthcare Cognitive Planning` chịu trách nhiệm xác định việc gì nên diễn ra, vì sao, khi nào, trong điều kiện nào và cần mức phê duyệt nào.

Không được giản lược Planning thành:

- Danh sách tác vụ do LLM tạo ra.
- Một Workflow cố định.
- Một tập hợp Specialist Agents.
- Một chuỗi gọi công cụ.
- Một mô hình tự đánh giá kết quả của chính nó.

Planning phải tính đến trạng thái sức khỏe đang thay đổi, bằng chứng, bất định, ràng buộc lâm sàng, thời gian, nguồn lực, lựa chọn cá nhân và an toàn.

## 7. Patient State & Belief-State Planning — Lập kế hoạch theo trạng thái và niềm tin

### Patient State

Đại diện cho thông tin hiện có về người dùng, bao gồm:

- Triệu chứng và quan sát.
- Tiền sử sức khỏe.
- Thuốc và dị ứng.
- Kết quả xét nghiệm và chẩn đoán hình ảnh.
- Sự kiện chăm sóc liên quan.
- Bối cảnh chăm sóc hiện tại.
- Nguồn gốc và hiệu lực dữ liệu.

### Belief State

Đại diện cho hiểu biết chưa chắc chắn của hệ thống về người dùng.

Có thể bao gồm:

- Các giả thuyết cạnh tranh.
- Độ tin cậy hoặc xác suất.
- Thông tin còn thiếu.
- Mâu thuẫn.
- Mức độ không chắc chắn về trạng thái hiện tại.
- Bằng chứng có thể làm thay đổi đánh giá.

Hệ thống không được biến giả thuyết chưa xác minh thành sự thật y khoa.

**Nền tảng nâng cao:** `Bayesian Reasoning`, `Probabilistic State Estimation` và cách tiếp cận lấy cảm hứng từ `POMDP`.

Chỉ nên triển khai POMDP đầy đủ khi có thể xác định và đánh giá có ý nghĩa các mô hình trạng thái, hành động, quan sát và chuyển trạng thái.

## 8. Goal & Intent Management — Quản lý mục tiêu và ý định

Mục tiêu phải có cấu trúc, được duy trì và có thể điều chỉnh.

Một Goal có thể gồm:

- Mã định danh và chủ sở hữu.
- Mục tiêu do người dùng nêu.
- Mục tiêu đã chuẩn hóa.
- Mức ưu tiên.
- Khoảng thời gian.
- Ràng buộc.
- Quan hệ phụ thuộc.
- Tiêu chí thành công.
- Yêu cầu bằng chứng.
- Trạng thái hiện tại.
- Yêu cầu phê duyệt.

Goal có thể phân cấp:

```text
Mục tiêu sức khỏe dài hạn
       │
       ▼
Mục tiêu theo giai đoạn chăm sóc
       │
       ▼
Mục tiêu trung gian
       │
       ▼
Tác vụ vận hành
       │
       ▼
Kết quả đã xác minh
```

Planner phải phát hiện mục tiêu xung đột và phân biệt lựa chọn của người dùng với yêu cầu chuyên môn.

## 9. Clinical Reasoning & Evidence Planning — Suy luận lâm sàng và lập kế hoạch dựa trên bằng chứng

Clinical Reasoning phải sử dụng bằng chứng có kiểm soát và có thể truy xuất, không dựa vào phát biểu thiếu căn cứ do mô hình tạo ra.

Hệ thống cần xem xét:

- Hướng dẫn lâm sàng.
- Nguồn bằng chứng và phiên bản công bố.
- Điều kiện áp dụng cho nhóm đối tượng.
- Chống chỉ định và điều kiện loại trừ.
- Chất lượng và mức độ không chắc chắn của bằng chứng.
- Khuyến nghị mâu thuẫn.
- Nhu cầu chuyên gia rà soát.

Mọi khuyến nghị có ý nghĩa lâm sàng phải truy xuất được bằng chứng hỗ trợ hoặc được đánh dấu rõ là chưa chắc chắn.

Planning Engine không được tự ý chẩn đoán, kê đơn hoặc thay đổi điều trị vượt quá phạm vi được cho phép.

## 10. Active Information Planning — Lập kế hoạch thu thập thông tin chủ động

Đôi khi bước tiếp theo tốt nhất không phải là can thiệp, mà là thu thập thêm thông tin.

Planner cần:

1. Xác định thông tin còn thiếu.
2. Đánh giá thông tin đó có thể làm thay đổi quyết định hay không.
3. Xác định nguồn thông tin được phép sử dụng.
4. Ước lượng giá trị và chi phí thu thập.
5. Kiểm tra `consent` và quyền hạn.
6. Yêu cầu làm rõ, hồ sơ hoặc ý kiến chuyên gia.
7. Cập nhật Patient State và Belief State.
8. Đánh giá lại kế hoạch.

**Nền tảng nâng cao:**

- `Value of Information`.
- `Active Learning`.
- `Bayesian Experimental Design`.
- Tìm kiếm dựa trên mức tăng thông tin.

Không được yêu cầu dữ liệu nhạy cảm không cần thiết chỉ vì hệ thống có thể thu thập dữ liệu đó.

## 11. Hierarchical & Temporal Planning — Lập kế hoạch phân cấp và theo thời gian

Kế hoạch chăm sóc vận hành ở nhiều thang thời gian.

| Cấp Planning | Trách nhiệm |
|---|---|
| Strategic | Mục tiêu sức khỏe dài hạn và định hướng chăm sóc |
| Tactical | Giai đoạn chăm sóc, phối hợp chuyên khoa và chiến lược theo dõi |
| Operational | Tác vụ cụ thể, lịch hẹn, nhắc việc và hành động được phép |

Temporal Planning cần biểu diễn:

- Điều kiện tiên quyết.
- Ràng buộc thứ tự.
- Khoảng thời gian.
- Thời lượng.
- Hạn chót.
- Theo dõi định kỳ.
- Kết quả xuất hiện trễ.
- Gián đoạn.
- Sắp xếp lại lịch.
- Quan hệ phụ thuộc.

**Nền tảng nâng cao:**

- `Hierarchical Task Network (HTN) Planning`.
- `Classical Planning`.
- `Temporal Planning`.
- `Constraint-based Scheduling`.
- `Receding-horizon Planning`.

Đây là các phương pháp bổ trợ nhau. Hệ thống phải lựa chọn phương pháp theo cấu trúc bài toán.

## 12. Search-based & Inference-time Planning — Tìm kiếm phương án và suy luận thích ứng

Hệ thống cần tạo và so sánh nhiều kế hoạch ứng viên thay vì chấp nhận câu trả lời hợp lý đầu tiên.

Các kỹ thuật có thể sử dụng:

- `Best-of-N Candidate Generation`.
- Tìm kiếm theo phong cách `Tree of Thoughts`.
- `Beam Search`.
- `Monte Carlo Tree Search`, khi có mô hình tìm kiếm phù hợp.
- `Constraint Solving`.
- `Multi-objective Optimization`.
- `Classical Symbolic Search`.
- `HTN Decomposition`.

Các phương án phải được so sánh theo ràng buộc bắt buộc, quy tắc lâm sàng, lựa chọn người dùng, giới hạn nguồn lực và mức độ không chắc chắn.

### Meta-Planning

Meta-Planning quyết định mức tài nguyên cần đầu tư cho việc lập kế hoạch.

Nó cần xác định:

- Một kế hoạch xác định đơn giản đã đủ hay chưa.
- Có cần tìm kiếm sâu hơn không.
- Có nên truy xuất thêm bằng chứng không.
- Có cần thuật toán chuyên biệt theo miền không.
- Có cần xác minh độc lập không.
- Có cần chuyển cho con người không.

**Nền tảng nâng cao:** `Adaptive Computation` và `Inference-time Scaling`.

Tăng tính toán không tự động tạo ra kế hoạch tốt hoặc an toàn hơn. Việc tìm kiếm thêm phải đem lại lợi ích đo lường được.

## 13. Causal & Counterfactual Planning — Lập kế hoạch theo nhân quả và phản thực

Hệ thống cần phân biệt tương quan với quan hệ nhân quả.

Causal Reasoning có thể hỗ trợ:

- So sánh các cách giải thích có thể có.
- Kiểm tra giả định.
- Đánh giá các kịch bản thay thế.
- Xác định quan sát nào có thể phân biệt các giả thuyết.
- Hiểu hậu quả có thể xảy ra khi một yếu tố thay đổi.

Kết quả Counterfactual phải được trình bày như phân tích có điều kiện, không phải dự đoán đã được chứng minh hoặc hiệu quả điều trị đã được xác lập.

**Nền tảng nâng cao:** `Causal Graphs`, `Structural Causal Models` và `Counterfactual Reasoning`.

## 14. Risk-aware & Constrained Planning — Lập kế hoạch có ràng buộc và nhận thức rủi ro

Đánh giá kế hoạch phải tách điều kiện bắt buộc khỏi sở thích.

### Hard Constraints

Các điều kiện bắt buộc không được vi phạm.

### Clinical Safety Constraints

Các điều kiện lâm sàng yêu cầu hạn chế, xác minh hoặc chuyển cấp.

### Operational Constraints

Khả năng sẵn có, nguồn lực, quyền hạn, thời gian và năng lực thực thi.

### Patient Preferences

Chi phí, sự thuận tiện, khả năng tiếp cận và lựa chọn cá nhân.

### Optimization Objectives

Hệ thống chỉ được tối ưu trong tập phương án đã thỏa mãn các yêu cầu bắt buộc.

Điểm tiện ích cao không được phép bù trừ cho việc vi phạm ràng buộc an toàn cứng.

## 15. Multi-perspective Planning — Lập kế hoạch từ nhiều góc nhìn

Một kế hoạch ứng viên cần được đánh giá từ nhiều góc nhìn độc lập:

- Góc nhìn người dùng.
- Góc nhìn lâm sàng.
- Góc nhìn bằng chứng.
- Góc nhìn an toàn.
- Góc nhìn vận hành.
- Góc nhìn quyền riêng tư và `consent`.

Các góc nhìn này có thể được triển khai thành những Evaluator chuyên biệt thay vì bắt buộc tạo Agent tự chủ riêng.

Bất đồng phải được biểu diễn tường minh. Một điểm đồng thuận tổng hợp không đủ để ghi đè quy tắc an toàn lâm sàng bắt buộc.

## 16. Formal Verification & Runtime Assurance — Xác minh hình thức và bảo đảm an toàn khi thực thi

Xác minh lúc lập kế hoạch và kiểm soát an toàn lúc thực thi là hai trách nhiệm khác nhau.

### Plan Verification

Kiểm tra:

- Điều kiện tiên quyết.
- Quan hệ phụ thuộc.
- Ràng buộc cứng.
- Yêu cầu bằng chứng.
- Yêu cầu quyền hạn.
- Kết quả kỳ vọng.
- Cách xử lý thất bại.
- Tính đầy đủ của kế hoạch.

### Runtime Assurance

Trước và trong khi thực thi, kiểm tra:

- `Consent` hiện tại.
- Quyền hiện tại.
- Patient State mới nhất có liên quan.
- Hành động có được phép hay không.
- Điều kiện có thay đổi không.
- Có tín hiệu an toàn yêu cầu dừng không.
- Có cần con người phê duyệt không.

Lớp an toàn phải có quyền chặn thực thi ngay cả khi Planner đề xuất tiếp tục.

Khi phù hợp, sử dụng `Formal Specifications`, `Invariants`, kiểm tra chuyển trạng thái và xác minh độc lập.

LLM tự rà soát kế hoạch của chính nó không phải bằng chứng đầy đủ về tính đúng đắn.

## 17. Adaptive Replanning & Longitudinal Continuity — Lập kế hoạch lại thích ứng và duy trì liên tục

Kế hoạch phải thay đổi khi:

- Có thông tin sức khỏe mới.
- Người dùng báo cáo thay đổi.
- Có kết quả xét nghiệm mới.
- Một tác vụ thất bại.
- Người dùng bỏ lỡ lịch hẹn.
- `Consent` thay đổi hoặc bị thu hồi.
- Hướng dẫn lâm sàng thay đổi.
- Chuyên gia đưa ra chỉ dẫn mới.
- Mục tiêu hoặc giới hạn của người dùng thay đổi.

Hệ thống cần phân biệt:

- `Local Replanning`: điều chỉnh một tác vụ hoặc quan hệ phụ thuộc.
- `Partial Replanning`: điều chỉnh một kế hoạch theo giai đoạn chăm sóc.
- `Global Replanning`: đánh giá lại mục tiêu dài hạn và chiến lược chăm sóc tổng thể.

Mỗi lần sửa đổi phải giữ lịch sử kế hoạch và giải thích lý do thay đổi.

## 18. Learning & Meta-Planning Improvement — Học hỏi và cải thiện Meta-Planning

Hệ thống cần học từ:

- Kế hoạch thất bại.
- Lỗi thực thi.
- Giả định sai.
- Phản hồi người dùng.
- Sửa đổi từ chuyên gia.
- Nút thắt lặp lại.
- Kết quả theo dõi.
- Các mẫu hình chuyển cấp.

Việc học cần cải thiện lựa chọn chiến lược, phân bổ tài nguyên và chất lượng kế hoạch.

Không được âm thầm sửa đổi chính sách lâm sàng, quy tắc chống chỉ định hoặc kiến thức y khoa. Những thay đổi đó cần quy trình xác minh và phê duyệt có kiểm soát.

---

# PHẦN III — BIỂU DIỄN KẾ HOẠCH VÀ THỰC THI

## 19. Patient-centric Plan Graph — Đồ thị kế hoạch lấy người dùng làm trung tâm

Kế hoạch nên được biểu diễn bằng đồ thị có cấu trúc thay vì văn bản tự do.

```text
Goal
 └── Care Pathway
      ├── Subgoal
      │    ├── Task
      │    │    ├── Preconditions
      │    │    ├── Authorized Action
      │    │    ├── Expected Effect
      │    │    ├── Evidence
      │    │    ├── Risk Constraints
      │    │    └── Verification
      │    └── Dependencies
      └── Outcome Criteria
```

Một Node trong Plan Graph cần hỗ trợ:

- Mã định danh ổn định.
- Loại Node.
- Chủ sở hữu và Domain.
- Node cha và quan hệ phụ thuộc.
- Điều kiện tiên quyết.
- Đặc tả hành động.
- Hiệu ứng kỳ vọng.
- Tham chiếu bằng chứng.
- Giả định.
- Rủi ro và ràng buộc.
- Năng lực cần thiết.
- Yêu cầu quyền thực thi.
- Ràng buộc thời gian.
- Chính sách khi thất bại.
- Tiêu chí xác minh.
- Trạng thái thực thi.

## 20. Plan Versioning & Provenance — Phiên bản và nguồn gốc kế hoạch

Mỗi thay đổi có ý nghĩa của kế hoạch cần tạo phiên bản có thể truy xuất.

Hệ thống cần giữ:

- Goal ban đầu.
- Snapshot hoặc tham chiếu Patient State.
- Các Memory được sử dụng.
- Các Evidence được sử dụng.
- Giả định.
- Phiên bản Planner và thuật toán.
- Kết quả xác minh.
- Bản ghi phê duyệt.
- Sự kiện thực thi.
- Kết quả quan sát.
- Lý do sửa đổi.

Điều này hỗ trợ tái lập, kiểm toán và đánh giá theo thời gian.

## 21. Execution & Multi-Agent Coordination — Thực thi và điều phối nhiều Agent

Planning Engine xác định kế hoạch dự kiến. Execution Runtime xác định cách thực hiện các tác vụ đã được cho phép.

Các trách nhiệm gồm:

- Ghép năng lực phù hợp.
- Chọn Agent và công cụ.
- Lập lịch theo quan hệ phụ thuộc.
- Quản lý Lease và trạng thái tác vụ.
- Chính sách Retry và Timeout.
- Xử lý thất bại.
- Bù trừ hành động khi phù hợp.
- Phê duyệt của con người.
- Xác minh kết quả thực thi.

Agent không được nhận quyền hạn vượt quá yêu cầu của tác vụ.

Thành công thực thi phải dựa trên kết quả quan sát và xác minh, không chỉ dựa vào phản hồi công cụ thành công hoặc lời khẳng định hoàn thành từ Agent.

---

# PHẦN IV — TÍCH HỢP MEMORY VÀ PLANNING

## 22. Memory Integration Contract — Hợp đồng tích hợp Memory

Memory phải có thể được truy vấn trong toàn bộ vòng đời Planning.

| Giai đoạn Planning | Memory cung cấp |
|---|---|
| Xây dựng Patient State | Lịch sử liên quan, nguồn gốc và hiệu lực theo thời gian |
| Chọn Goal | Mục tiêu, sở thích và nhu cầu chưa giải quyết |
| Tạo kế hoạch | Sự kiện, giới hạn và kết quả trước đây |
| Đánh giá kế hoạch | Thất bại, điều chỉnh và kết quả trước đây |
| Thực thi | Consent hiện tại, quyền và bối cảnh liên quan |
| Theo dõi | Quan sát dài hạn và thay đổi |
| Lập kế hoạch lại | Thông tin mới, mâu thuẫn và bản ghi bị thay thế |
| Follow-up | Tác vụ đang chờ, lịch sử chăm sóc và mục tiêu chưa hoàn thành |

### Các biện pháp bảo vệ bắt buộc

- Truy xuất phải giới hạn theo chủ sở hữu.
- `Consent` phải được kiểm tra theo phạm vi yêu cầu.
- Thông tin hết hạn không được coi là hiện tại.
- Thông tin mâu thuẫn phải được giữ lại để đánh giá.
- Suy luận phải giữ nguồn gốc.
- Bằng chứng lâm sàng không được thay thế bằng Memory cá nhân.
- Ghi Memory phải tuân theo vòng đời rà soát và kiểm toán.
- Thu hồi `consent` phải ngăn việc sử dụng trái phép tiếp theo.

## 23. Clinical Evidence Không Đồng Nhất Với Memory

Các hệ thống này có trách nhiệm khác nhau.

**Memory** ghi nhận những gì đã biết về một người dùng cụ thể và thông tin đó được thu thập bằng cách nào.

**Clinical Evidence** ghi nhận nguồn y khoa bên ngoài hỗ trợ điều gì, trong điều kiện nào và có giới hạn gì.

**Patient State** kết hợp thông tin liên quan đến người dùng thành biểu diễn hiện tại có thể truy xuất nguồn gốc.

**Belief State** thể hiện mức độ không chắc chắn của biểu diễn đó.

**Planning** sử dụng các đầu vào này để đánh giá những bước tiếp theo có thể thực hiện.

Việc tách biệt các trách nhiệm giúp tránh coi hồi ức cá nhân, giả thuyết của Agent và hướng dẫn lâm sàng là cùng một loại dữ liệu.

---

# PHẦN V — BENCHMARK VÀ XÁC MINH

## 24. Planning Benchmark

Y TẾ MỞ cần xây dựng bộ đánh giá riêng, có thể tái lập.

| Nhóm đánh giá | Năng lực cần kiểm tra |
|---|---|
| Patient-state correctness | Xây dựng trạng thái chính xác, có nguồn gốc |
| Belief calibration | Biểu diễn mức độ không chắc chắn phù hợp |
| Goal correctness | Hiểu đúng mục tiêu và lựa chọn |
| Active information planning | Phát hiện và yêu cầu thông tin còn thiếu hữu ích |
| Plan correctness | Tạo kế hoạch hợp lệ và khả thi |
| Evidence correctness | Sử dụng bằng chứng phù hợp, truy xuất được |
| Temporal correctness | Tuân thủ thứ tự và thời gian |
| Risk correctness | Phát hiện kế hoạch bị cấm hoặc không an toàn |
| Execution correctness | Chỉ thực thi hành động được cho phép |
| Verification correctness | Phát hiện kế hoạch sai và kết quả thất bại |
| Consent correctness | Tôn trọng thay đổi và thu hồi quyền |
| Longitudinal continuity | Duy trì bối cảnh và thích nghi qua nhiều phiên |
| Escalation correctness | Yêu cầu chuyên gia có chuyên môn khi cần |
| Outcome evaluation | Đo kết quả thực tế so với tiêu chí đã xác định |

## 25. Adversarial & Failure Testing — Kiểm thử đối kháng và thất bại

Cần kiểm thử các trường hợp:

- Thiếu thông tin người dùng.
- Hồ sơ mâu thuẫn.
- Thông tin hết hạn.
- Memory do Agent tạo ra nhưng sai.
- Đầu vào giả hoặc bị thao túng.
- Thông tin mới xuất hiện trong lúc thực thi.
- Thu hồi `consent` giữa Workflow.
- Agent lỗi hoặc công cụ không khả dụng.
- Mục tiêu không thể đạt được.
- Quan hệ phụ thuộc không hợp lệ.
- Hướng dẫn lâm sàng lỗi thời.
- Khuyến nghị chuyên gia mâu thuẫn.
- Hành động không an toàn được đề xuất trong một kế hoạch nhìn chung có vẻ hợp lý.
- Tác vụ bị gián đoạn và cần phục hồi.
- Lập kế hoạch lại liên tục nhưng không có tiến triển.

## 26. Bốn cấp độ đánh giá

1. **Plan Correctness:** Kế hoạch đề xuất có hợp lệ không?
2. **Execution Correctness:** Hệ thống có thực thi đúng kế hoạch được cho phép không?
3. **Safety Correctness:** Hệ thống có ngăn hành động bị cấm và chuyển cấp phù hợp không?
4. **Longitudinal Outcome:** Hệ thống có duy trì tính liên tục và đo lường tiến triển có ý nghĩa theo thời gian không?

Một Unit Test thành công không chứng minh hiệu quả lâm sàng. Kết quả mô phỏng không chứng minh an toàn trong thực tế.

---

# PHẦN VI — HIỆN TRẠNG VÀ LỘ TRÌNH TRIỂN KHAI

## 27. Kiểm kê Repository hiện tại

Kết quả kiểm kê ban đầu nhận diện các module:

### Memory

- `backend/memory_engine.py`
- `backend/memory_conflict_engine.py`
- `backend/memory_intelligence.py`
- `backend/temporal_memory.py`

### Companion và điều phối

- `backend/companion_core.py`
- `backend/supabase_companion_repository.py`
- `backend/proactive_engine.py`
- `backend/agent_core.py`
- `backend/agent_foundation.py`
- `backend/agent_registry.py`

### Các file Test đã nhận diện

- `backend/test_memory_engine.py`
- `backend/test_memory_conflict_engine.py`
- `backend/test_memory_intelligence.py`
- `backend/test_temporal_memory.py`
- `backend/test_companion_core.py`
- `backend/test_proactive_engine.py`
- `backend/test_agent_core.py`
- `backend/test_agent_foundation.py`
- `backend/test_agent_registry.py`

Đây mới là kết quả kiểm kê tên file, chưa phải kiểm toán đầy đủ cách triển khai.

## 28. Các năng lực Planning cần kiểm toán

Không được giả định các năng lực sau đã tồn tại chỉ vì đã có module Task hoặc Workflow:

- Mô hình Patient State có cấu trúc.
- Biểu diễn Belief State.
- Phân cấp mục tiêu lâm sàng.
- Healthcare Plan Graph.
- Temporal Planning.
- HTN Planning.
- Search-based Plan Generation.
- Active Information Planning.
- Causal và Counterfactual Reasoning.
- Risk-sensitive Optimization.
- Xác minh kế hoạch độc lập.
- Runtime Assurance.
- Adaptive Replanning.
- Plan Versioning và Provenance.
- Đánh giá kết quả dài hạn.
- Planning-specific Benchmarks.

## 29. Lộ trình triển khai đề xuất

### Giai đoạn 0 — Kiểm toán Repository và kiến trúc

- Kiểm tra các module Memory, Agent, Companion và Proactive.
- Kiểm tra Database Schema và Migration.
- Xác định trách nhiệm bị trùng lặp.
- Xác định Contract và Test Coverage còn thiếu.
- Lập ma trận hiện trạng đã được xác minh.

### Giai đoạn 1 — Hoàn thiện nền tảng Memory

- Xác minh Provenance và Evidence Lineage.
- Xác minh Temporal Semantics.
- Xác minh Conflict Lifecycle.
- Xác minh Consent Enforcement.
- Xác minh ranh giới Retrieval và Review.
- Xác minh Transactional Audit.
- Bổ sung Regression Tests còn thiếu.

### Giai đoạn 2 — Nền tảng Planning

- Định nghĩa Contract cho Patient State và Belief State.
- Định nghĩa mô hình Goal và Care Plan.
- Định nghĩa Plan Graph và Plan Version.
- Định nghĩa giao diện tích hợp Memory và Evidence.
- Định nghĩa Contract cho Authorization và Verification.

### Giai đoạn 3 — Planning Portfolio

- Bắt đầu bằng Deterministic Planning và Constraint-based Planning.
- Bổ sung Hierarchical và Temporal Planning.
- Bổ sung Candidate Search và Plan Comparison.
- Bổ sung lựa chọn ngân sách suy luận thích ứng.
- Bổ sung Active Information Planning khi có thể đo lường hiệu quả.

### Giai đoạn 4 — An toàn và thực thi

- Bổ sung kiểm định kế hoạch độc lập.
- Bổ sung Runtime Authorization Checks.
- Bổ sung Human Approval và Escalation.
- Kết nối với Agent Execution Runtime hiện có.
- Bổ sung đối soát trạng thái và phục hồi thực thi.

### Giai đoạn 5 — Thích nghi dài hạn

- Bổ sung Monitoring theo sự kiện.
- Bổ sung Partial và Global Replanning.
- Bổ sung so sánh Plan Version.
- Bổ sung Outcome Tracking.
- Bổ sung học có kiểm soát từ thất bại và phản hồi.

### Giai đoạn 6 — Benchmark và hoàn thiện

- Xây dựng tình huống kiểm thử xác định.
- Xây dựng tình huống đối kháng.
- Đo Plan và Execution Correctness.
- Đo Safety và Consent Correctness.
- Đo Longitudinal Continuity.
- Kiểm tra thay đổi bằng Regression Benchmarks.

---

## 30. Các nguyên tắc kỹ thuật không được vi phạm

1. Không tuyên bố năng lực đã triển khai nếu chưa có bằng chứng từ Source Code và Tests.
2. Không coi suy luận do Agent tạo ra là sự thật lâm sàng đã xác minh.
3. Không coi kế hoạch được tạo ra là quyền tự động thực thi.
4. Không cho phép Planner bỏ qua Consent hoặc Runtime Safety Controls.
5. Không để LLM là bộ xác minh duy nhất cho kế hoạch có rủi ro cao.
6. Không âm thầm loại bỏ thông tin mâu thuẫn hoặc đã bị thay thế.
7. Không cho phép Self-learning sửa đổi chính sách lâm sàng thiếu kiểm soát.
8. Giữ Provenance cho Plan, Memory và Evidence.
9. Công khai thông tin còn thiếu và năng lực chưa được hỗ trợ.
10. Đánh giá thực thi và kết quả dài hạn, không chỉ đánh giá văn bản được tạo ra.

## 31. Định hướng kiến trúc cuối cùng

Mục tiêu không đơn thuần là một Planner phức tạp hơn.

Mục tiêu là một:

**Memory-grounded, Evidence-aware, Belief-state, Risk-constrained, Longitudinal Healthcare Cognitive Planning and Control System.**

Hệ thống cần hiểu bối cảnh người dùng đang thay đổi, nhận ra điều mình chưa biết, thu thập thông tin hữu ích khi được phép, xây dựng và xác minh kế hoạch, điều phối thực thi được ủy quyền, theo dõi kết quả thực tế và thích nghi một cách có trách nhiệm.

Tài liệu này mô tả kiến trúc mục tiêu. Nó không khẳng định mọi thành phần đã được triển khai, xác nhận lâm sàng hoặc sẵn sàng cho môi trường Production.

Mọi quyết định kỹ thuật tiếp theo phải dựa trên kiểm toán Repository, không dựa trên giả định.
