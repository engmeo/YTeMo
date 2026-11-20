# Kiến trúc An toàn, Quyền riêng tư và Quản trị

## 1. Nguyên tắc cốt lõi

Các thành phần intelligence có thể đề xuất, xếp hạng, tổng hợp và suy luận.

Chúng không tự động có quyền truy cập dữ liệu, thay đổi policy, đưa ra
quyết định được quản lý hoặc thực thi hành động.

## 2. Phân tách quyền hạn

Cần tách biệt:
- Data Ownership.
- Consent Management.
- Memory Retrieval.
- Planning.
- Clinical Decision Authority.
- Human Approval.
- Tool Execution.
- Audit và Persistence.

Không subsystem nào được suy ra quyền hạn chỉ từ khả năng kỹ thuật.

## 3. Consent-aware Memory

Consent cần xác định:
- Subject và data scope.
- Purpose.
- Processing permissions.
- Sharing boundaries.
- Retention conditions.
- Revocation behavior.

Kiểm tra quyền tại ingestion, retrieval, downstream use và sharing.

## 4. Identity và Isolation

Enforce owner và tenant isolation tại:
- Relational queries.
- Vector search.
- Graph traversal.
- Document retrieval.
- Cache.
- Export.
- Background jobs.

Chỉ lọc sau retrieval có thể không đủ nếu dữ liệu trái phép đã lọt vào
intermediate model context.

## 5. Provenance và Evidence

Duy trì khả năng truy nguyên từ thông tin được tạo ra đến source.

Không âm thầm nâng cấp:
- Unverified thành verified.
- Inference thành observation.
- User statement thành clinician-confirmed fact.
- Predicted outcome thành observed outcome.

## 6. Planning Safety

Safety constraints phải:
- Tường minh.
- Có version.
- Được kiểm tra độc lập.
- Có audit.
- Không bị tác động bởi áp lực tối ưu reward.

Meta-cognitive learning không được tự ý nới lỏng hard constraints.

## 7. Human Review

Cần escalation khi:
- Evidence quan trọng mâu thuẫn.
- High-impact uncertainty còn tồn tại.
- Thiếu approval bắt buộc.
- Vượt policy threshold.
- Không thể xác định proposal có hợp lệ hay không.

Human review là một hành động quản trị, không chỉ là status label.

## 8. Execution Authorization

Plan không phải execution command.

Execution cần:
- Authorized caller.
- Valid task identity.
- Applicable permissions.
- Policy validation.
- Required approvals.
- Runtime safety checks.
- Auditable outcome recording.

## 9. Auditability

Audit record nên lưu:
- Actor.
- Action.
- Timestamp.
- Object versions liên quan.
- Evidence references.
- Policy version.
- Decision rationale.
- Approval và rejection.
- Outcome.

Audit storage cũng cần access control và retention policy.

## 10. Security Threat Model

Cần xem xét:
- Prompt injection trong retrieved documents.
- Malicious hoặc corrupted source data.
- Cross-user retrieval leakage.
- Stale hoặc revoked consent.
- Data poisoning.
- Embedding inversion và leakage.
- Unauthorized tool execution.
- Policy bypass.
- Model-generated false provenance.
- Confused-deputy integration errors.

## 11. Ranh giới lâm sàng

Planning và Memory là hạ tầng hỗ trợ. Chúng không độc lập xác lập chẩn đoán,
kê đơn hoặc thay thế chuyên môn của nhân viên y tế đủ năng lực.

Sử dụng lâm sàng cần validation phù hợp, qualified oversight, regulatory
assessment và deployment governance.
