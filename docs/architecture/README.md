# Y TẾ MỞ — Bản đồ tri thức kiến trúc

> Ngôn ngữ: Tiếng Việt. Các thuật ngữ chuyên ngành, tên thuật toán,
> tên API và định danh kỹ thuật được giữ nguyên tiếng Anh khi cần thiết.

## 1. Mục đích

Bộ tài liệu này mô tả toàn diện kiến trúc, thuật toán, nền tảng toán học,
cấu trúc dữ liệu, luồng xử lý, cơ chế quản trị và lộ trình phát triển
của hai hệ thống cốt lõi:

- Planning Intelligence — năng lực lập kế hoạch và ra quyết định.
- Memory Intelligence — năng lực quản lý, lưu trữ, truy xuất và khai thác
  ký ức, dữ kiện và bằng chứng.

Mục tiêu không phải chỉ liệt kê tên module. Developer cần hiểu:
- Kiến trúc giải quyết vấn đề gì.
- Nguyên lý hoạt động.
- Các thành phần bên trong.
- Thuật toán và công thức liên quan.
- Cách những thành phần phối hợp.
- Ưu điểm và giới hạn.
- Trạng thái triển khai thực tế.
- Hướng nâng cấp.

## 2. Sơ đồ kiến trúc tổng thể

```text
             PERSONAL HEALTHCARE COMPANION
                         |
               Goal / Intent / Context
                         |
           +-------------+-------------+
           |                           |
     MEMORY INTELLIGENCE         PLANNING INTELLIGENCE
           |                           |
     Memory Encoding             Goal & Intent
     Episodic Memory             World Model
     Semantic Memory             Hierarchical Planning
     Knowledge Graph             Search & Optimization
     Temporal Memory             Decision Intelligence
     Hybrid Retrieval             Risk & Robustness
     Consolidation                Execution Monitoring
     Evidence / Provenance        Replanning / Recovery
     Consent / Governance         Verification / Governance
           |                           |
           +-------------+-------------+
                         |
                Evidence-aware Context
                         |
                Plan / Decision Proposal
                         |
                Validation & Governance
                         |
                 Human Review Boundary
                         |
                Authorized Execution
```

Đây là sơ đồ kiến trúc logic mục tiêu. Sơ đồ không khẳng định tất cả
các kết nối đã được triển khai trong ứng dụng thực tế.

## 3. Danh mục tài liệu

| Tài liệu | Nội dung |
|---|---|
| PLANNING_ARCHITECTURE.md | Toàn bộ kiến trúc Planning |
| PLANNING_ALGORITHMS.md | Thuật toán và nền tảng toán học của Planning |
| MEMORY_ARCHITECTURE.md | Toàn bộ kiến trúc Memory |
| MEMORY_ALGORITHMS.md | Thuật toán và phương pháp xử lý Memory |
| PLANNING_MEMORY_INTEGRATION.md | Cách Planning và Memory phối hợp |
| SAFETY_AND_GOVERNANCE.md | An toàn, quyền riêng tư và quản trị |
| ARCHITECTURE_STATUS.md | Kiểm tra trạng thái triển khai |
| ARCHITECTURE_ROADMAP.md | Lộ trình phát triển |
| ARCHITECTURE_INVENTORY.md | Danh sách source code và test được phát hiện |

## 4. Nguyên tắc kiến trúc

### 4.1. Tách biệt trách nhiệm

Planning chịu trách nhiệm lập kế hoạch và đánh giá phương án.

Memory chịu trách nhiệm quản lý thông tin, bằng chứng, lịch sử và ngữ cảnh.

Hai hệ thống phối hợp qua các hợp đồng dữ liệu rõ ràng, không chiếm quyền
quản lý vòng đời của nhau.

### 4.2. Domain-neutral Core

Planning Core không phụ thuộc trực tiếp vào Healthcare, Robotics, Finance,
Supabase, FastAPI hoặc một miền nghiệp vụ cụ thể.

Các chính sách và adapter theo từng miền phải nằm tại ranh giới tích hợp.

### 4.3. Evidence-aware

- Dữ liệu truy xuất được không mặc nhiên là dữ liệu đã xác minh.
- Dự đoán không phải quan sát thực tế.
- Điểm số không mặc nhiên là xác suất đã hiệu chuẩn.
- Kế hoạch được tạo không đồng nghĩa với quyền thực thi.

### 4.4. Có vòng đời và khả năng kiểm toán

Các đối tượng quan trọng cần có định danh, phiên bản, nguồn gốc, trạng thái,
quy tắc cập nhật và lịch sử thay đổi.

### 4.5. Có thể thay thế thành phần

Storage, embedding model, retrieval strategy, planning strategy và domain
adapter cần được thiết kế thông qua các contract ổn định.

## 5. Quy ước trạng thái

| Trạng thái | Ý nghĩa |
|---|---|
| IMPLEMENTED | Đã có triển khai thực tế và có bằng chứng kiểm tra |
| PARTIALLY IMPLEMENTED | Đã triển khai một phần |
| DESIGNED | Đã có thiết kế nhưng chưa triển khai đầy đủ |
| PLANNED | Nằm trong định hướng tương lai |
| NOT VERIFIED | Chưa đủ bằng chứng để kết luận |

Không được đánh dấu một kiến trúc là IMPLEMENTED chỉ vì có tên module
hoặc tên thuật toán trong source code.

## 6. Phân biệt các khái niệm

- Plan: bản kế hoạch có cấu trúc.
- Planner: thành phần tạo hoặc đánh giá kế hoạch.
- World Model: mô hình biểu diễn và dự đoán trạng thái thế giới.
- Belief State: trạng thái niềm tin thể hiện sự không chắc chắn.
- Memory Item: một đơn vị thông tin được quản lý trong Memory.
- Evidence: bằng chứng hỗ trợ hoặc phản bác một nhận định.
- Provenance: nguồn gốc và lịch sử hình thành dữ liệu.
- Consolidation: quá trình tổng hợp và tổ chức lại ký ức.
- Retrieval: truy xuất thông tin phù hợp với truy vấn.
- Replanning: lập lại kế hoạch khi trạng thái hoặc bằng chứng thay đổi.
