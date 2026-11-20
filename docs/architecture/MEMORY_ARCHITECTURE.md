# Memory Intelligence — Tài liệu kiến trúc toàn diện

## 1. Sứ mệnh

Memory Intelligence quản lý thông tin cần được sử dụng trong nhiều tương tác
và trong thời gian dài.

Memory phải duy trì:
- Ý nghĩa.
- Ngữ cảnh.
- Chủ sở hữu.
- Nguồn gốc.
- Mức độ xác minh.
- Giá trị theo thời gian.
- Quyền truy cập.

Memory không đơn thuần là một vector database hoặc conversation summary.

## 2. Memory Taxonomy — Phân loại ký ức

### Working Memory

Thông tin tạm thời cần cho tác vụ đang thực hiện.

Đặc điểm:
- Vòng đời ngắn.
- Liên quan trực tiếp đến tác vụ hiện tại.
- Có thể chứa intermediate results.
- Không tự động trở thành long-term memory.

### Episodic Memory

Lưu lại sự kiện và trải nghiệm.

Các trường có thể gồm:
- Event ID.
- Thời gian hoặc khoảng thời gian.
- Người tham gia.
- Bối cảnh.
- Nội dung sự kiện.
- Nguồn và bằng chứng.
- Kết quả.
- Sự kiện liên quan.

### Semantic Memory

Lưu trữ dữ kiện, khái niệm và mối quan hệ đã được tổ chức.

Ví dụ:
- Định nghĩa.
- Sở thích ổn định.
- Domain knowledge.
- Entity relationships.

Semantic Memory vẫn cần provenance và uncertainty.

### Procedural Memory

Lưu kiến thức về cách thực hiện một quy trình.

Ví dụ:
- Workflow đã xác minh.
- Procedure.
- Task sequence có thể tái sử dụng.
- Operational rules.

Procedure được đề xuất không tự động trở thành procedure đã được phê duyệt.

### Contextual Memory

Lưu ngữ cảnh cần để diễn giải thông tin khác:
- User hoặc entity context.
- Situation.
- Time.
- Source.
- Consent và access scope.
- Task liên quan.

Các nhóm có thể chồng lấn, không nhất thiết phải tương ứng với các bảng
database tách biệt.

## 3. Memory Representation — Biểu diễn ký ức

### Structured Memory

Lưu các trường dữ liệu có kiểu và quan hệ rõ ràng.

Ưu điểm:
- Validation.
- Queryability.
- Ownership rõ ràng.
- Dễ thiết lập consistency constraints.

### Vector Memory

Lưu embedding để truy xuất theo semantic similarity.

Ưu điểm:
- Tìm kiếm gần nghĩa.
- Hỗ trợ paraphrase.
- Phù hợp với nội dung phi cấu trúc.

Hạn chế:
- Similarity không chứng minh sự thật.
- Embedding có thể mất thông tin thời gian và quan hệ chính xác.
- Retrieval có thể trả về nội dung không phù hợp.

### Knowledge Graph Memory

Biểu diễn entity và relation bằng nodes và edges.

Hỗ trợ:
- Multi-hop retrieval.
- Relationship traversal.
- Entity resolution.
- Quan hệ ngữ nghĩa tường minh.

### Temporal Knowledge Graph

Bổ sung valid-time và transaction-time cho facts và relations.

Cho phép phân biệt:
- Điều gì đúng trong thế giới tại một thời điểm.
- Hệ thống biết thông tin đó khi nào.
- Khi nào bản ghi được sửa hoặc thay thế.

## 4. Memory Encoding & Extraction

Luồng xử lý:

1. Tiếp nhận source content.
2. Xác định source và ownership.
3. Trích xuất candidate facts, events và entities.
4. Giữ source reference ban đầu.
5. Chuẩn hóa biểu diễn.
6. Phát hiện dữ liệu nhạy cảm hoặc bị hạn chế.
7. Kiểm tra consent và policy.
8. Validate cấu trúc candidate.
9. Lưu hoặc yêu cầu approval.

Quá trình extraction phải giữ uncertainty và không biến suy đoán thành
dữ kiện được khẳng định.

## 5. Memory Storage Architecture

Các tầng lưu trữ có thể gồm:

- Relational Store: identity, metadata, lifecycle, permissions.
- Document Store: nội dung gốc và tài liệu có cấu trúc.
- Vector Index: embedding.
- Graph Store: quan hệ giữa entities.
- Object Storage: media và file dung lượng lớn.

Kiến trúc hybrid cần:
- Stable Memory ID.
- Cross-store consistency.
- Versioning.
- Deletion propagation.
- Access control trên mọi đường truy xuất.
- Rebuild và reconciliation.

Vector index không được trở thành đường vòng vượt qua quyền truy cập
của source store.

## 6. Memory Retrieval — Truy xuất ký ức

### Keyword Retrieval

Tìm theo từ khóa và biến thể từ vựng.

Phù hợp với identifier, tên riêng, ngày tháng và cụm từ chính xác.

### Semantic Retrieval

Sử dụng embedding để tìm nội dung liên quan về mặt ngữ nghĩa.

### Metadata Filtering

Giới hạn kết quả theo:
- Owner.
- Consent scope.
- Time.
- Source.
- Memory type.
- Verification state.
- Domain.
- Access policy.

### Graph Retrieval

Truy xuất thông qua các quan hệ trong Knowledge Graph.

### Hybrid Retrieval

Kết hợp lexical, semantic, metadata và graph retrieval.

Pipeline tham khảo:

Query
  -> Identity and Permission Checks
  -> Query Understanding
  -> Candidate Retrieval
  -> Metadata and Temporal Filtering
  -> Ranking and Reranking
  -> Conflict and Provenance Checks
  -> Context Assembly
  -> Source References

Authorization phải được kiểm tra trước khi nội dung được đưa vào context
cho các bước reasoning tiếp theo.

## 7. Memory Consolidation

Consolidation chuyển nhiều bản ghi thành biểu diễn hữu ích hơn.

Các thao tác:
- Duplicate Detection.
- Semantic Clustering.
- Event Grouping.
- Summarization.
- Entity Resolution.
- Stable Fact Extraction.
- Episodic-to-Semantic Abstraction.

Yêu cầu an toàn:
- Giữ source references.
- Giữ bản ghi gốc khi retention policy yêu cầu.
- Lưu derivation lineage.
- Không xóa mâu thuẫn.
- Không biến pattern chưa chắc chắn thành sự thật chắc chắn.
- Hỗ trợ review và rollback.

## 8. Memory Lifecycle

Một vòng đời tham khảo:

Candidate
  -> Validated
  -> Active
  -> Updated / Superseded
  -> Archived / Expired
  -> Deleted under applicable policy

Cần xác định:
- Ai có quyền tạo.
- Quy tắc cập nhật.
- Version policy.
- Expiration policy.
- Retention requirements.
- Deletion semantics.
- Audit requirements.

Deletion phải xem xét cả derived copies, indexes, caches và backups theo
retention policy và nghĩa vụ pháp lý.

## 9. Evidence & Provenance

Mỗi memory quan trọng cần truy nguyên được nguồn gốc.

Các trường có thể gồm:
- Source ID.
- Source type.
- Author hoặc origin.
- Observation time.
- Recording time.
- Verification status.
- Transformation history.
- Derivation references.
- Reviewer hoặc approval reference.

Phải phân biệt:
- User-provided statement.
- Imported record.
- Clinician-confirmed information.
- System observation.
- Model-generated inference.
- Unverified hypothesis.

Không được âm thầm hợp nhất các loại thông tin này.

## 10. Conflict-aware Memory

Mâu thuẫn có thể xuất hiện khi:
- Dữ kiện thay đổi theo thời gian.
- Hai nguồn bất đồng.
- Một nguồn không chính xác.
- Entity resolution sai.
- Ngữ cảnh khác nhau.
- Dữ liệu nhập sai.

Conflict Engine cần:
1. Phát hiện claims không tương thích.
2. Xác định subject và predicate.
3. So sánh time intervals.
4. So sánh provenance và verification.
5. Giữ lại các claims xung đột.
6. Xác định mâu thuẫn do thời gian hay do nội dung.
7. Chuyển các xung đột quan trọng chưa giải quyết sang human review.

Không giải quyết mâu thuẫn bằng cách mặc định chọn bản ghi mới nhất.

## 11. Temporal Memory

Hai khái niệm thời gian quan trọng:

- Valid Time: thời điểm dữ kiện đúng trong thế giới thực.
- Transaction Time: thời điểm hệ thống lưu hoặc thay đổi dữ kiện.

Bitemporal Modeling hỗ trợ tái dựng lịch sử và audit.

Truy vấn thời gian cần phân biệt dữ kiện hiện tại và dữ kiện từng đúng
trong quá khứ.

## 12. Memory Reasoning

Memory Reasoning sử dụng thông tin đã lưu làm đầu vào cho một quá trình
suy luận riêng.

Các khả năng:
- Context Reconstruction.
- Entity Linking.
- Multi-hop Graph Reasoning.
- Temporal Reasoning.
- Contradiction-aware Synthesis.
- Evidence Comparison.
- Knowledge-gap Detection.

Retrieved memory phải được phân biệt với inference mới do hệ thống tạo ra.

## 13. Consent, Privacy & Ownership

Memory access phải tuân thủ:
- Explicit Ownership.
- Consent Scope.
- Purpose Limitation.
- Least Privilege.
- Tenant and User Isolation.
- Retention Policy.
- Revocation.
- Audit Trail.

Consent phải được kiểm tra tại thời điểm truy xuất và sử dụng, không chỉ
ở thời điểm ingest.

## 14. Advanced Memory Intelligence

Các hướng nghiên cứu và phát triển:

- Agentic Memory Management.
- Reflective Memory.
- Predictive Memory.
- Continual Memory Learning.
- Multi-agent Shared Memory.
- GraphRAG.
- Multimodal Memory.
- Temporal Retrieval.
- Long-context Memory Compression.
- Memory-aware Planning.
- Provenance-aware Retrieval.
- Contradiction-aware RAG.

Mỗi hướng cần được đánh giá về retrieval accuracy, access isolation,
source fidelity và khả năng chống hallucination.

## 15. Ranh giới tích hợp

Memory cung cấp context và evidence có provenance, đúng quyền truy cập.

Memory không quyết định điều trị lâm sàng, không cấp quyền thực thi và
không âm thầm ghi đè phát biểu rõ ràng của người dùng.

Planning có thể yêu cầu context từ Memory nhưng không được phụ thuộc cứng
vào một thuật toán Planning cụ thể.

## 16. Các chỉ số đánh giá

- Retrieval Precision và Recall.
- Ranking Quality.
- Source Attribution Accuracy.
- Temporal Correctness.
- Conflict Detection Quality.
- Duplicate Rate.
- Consolidation Fidelity.
- Permission Leakage Tests.
- Deletion Propagation.
- Query Latency.
- Context Relevance.
