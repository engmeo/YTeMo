# Clinical Knowledge Governance — Y TẾ MỞ

## Mục tiêu và ranh giới
Nền tảng quản trị nguồn/tài liệu, provenance, kiểm tra tự động, hàng đợi thẩm định,
phê duyệt theo phạm vi, version/status và audit. Đây chưa phải crawler, vector search
hay clinical decision support. Kiểm tra tự động chỉ xác minh metadata và integrity
trích xuất; không xác nhận nội dung y khoa đúng.

## Vòng đời
- DISCOVERED: đăng ký ban đầu/chưa đủ kiểm tra.
- SOURCE_VERIFIED: domain có trong Source Registry và metadata/extraction checks đạt.
- PROCESSING: đang xử lý.
- AI_REVIEWED: có báo cáo hỗ trợ; không phải phê duyệt.
- CLINICAL_APPROVED: reviewer được cấp quyền phê duyệt kèm approved_scope.
- SUPERSEDED: phiên bản đã bị thay thế.
- REJECTED: không được sử dụng.

Chỉ CLINICAL_APPROVED được phép đưa vào clinical retrieval; phải lọc tiếp theo scope,
thời gian hiệu lực, chuyên khoa và phiên bản. Bản MVP này chưa cung cấp retrieval.

## API
Tất cả route yêu cầu Supabase Bearer token:
- GET /clinical-knowledge/sources
- POST /clinical-knowledge/documents
- GET /clinical-knowledge/documents?status=...
- GET /clinical-knowledge/review-queue (reviewer only)
- GET /clinical-knowledge/documents/{id} (reviewer only; đọc nội dung gốc đã trích xuất)
- POST /clinical-knowledge/documents/{id}/review (reviewer only)

Reviewer được quản lý trong clinical_knowledge_reviewers, không tin role do client gửi.
APPROVED chỉ thành công nếu source_verified, automated checks pass và scope không rỗng.

## Triển khai
1. Chạy migration supabase/migrations/202611240001_clinical_knowledge_governance.sql.
2. Deploy backend.
3. Sau khi xác minh tư cách chuyên môn, cấp reviewer qua SQL:
   insert into public.clinical_knowledge_reviewers(user_id,role,specialties,is_active)
   values ('<AUTH_USER_UUID>','physician',array['cardiology'],true);
4. Đăng ký tài liệu cùng metadata và extracted_text.
5. Reviewer phải mở tài liệu nguồn gốc, xác minh phiên bản/hiệu lực/phạm vi và ghi rationale.

## Giới hạn cần hoàn thiện trước production
- Seed nguồn ban đầu gồm Bộ Y tế và WHO; host match chỉ là xác minh nguồn bước đầu.
- Không tự fetch URL: tránh SSRF, nội dung độc hại và vi phạm điều khoản.
- Chưa có OCR/crawler scheduler, version diff, supersession resolver hoặc vector index.
- MVP lưu extracted_text trong Postgres; tài liệu lớn nên chuyển sang private object storage.
- Cần xác minh license/tái sử dụng, kiểm thử bảo mật, E2E và chuyên gia lâm sàng.
