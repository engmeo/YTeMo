# Memory — Thuật toán và nền tảng toán học

## 1. Embedding-based Semantic Retrieval

Encoder chuyển text hoặc input được hỗ trợ thành vector:

e = Encoder(x)

Một phép đo phổ biến là cosine similarity:

cos(u,v) = (u . v) / (||u|| ||v||)

Similarity cao biểu thị vector gần nhau theo embedding model cụ thể.
Nó không chứng minh dữ kiện là đúng.

Cần theo dõi embedding model version, normalization và thay đổi model.

## 2. Approximate Nearest Neighbor Search

Các họ index phổ biến:
- HNSW.
- IVF.
- Product Quantization.
- Tree-based ANN.

ANN đánh đổi một phần độ chính xác để tăng tốc độ truy xuất và hiệu quả
sử dụng bộ nhớ.

Cần đo recall@k so với exact nearest-neighbor, latency và chi phí duy trì
index.

## 3. Lexical Retrieval

BM25 xếp hạng tài liệu dựa trên term frequency, inverse document frequency
và chuẩn hóa độ dài tài liệu.

Phù hợp với thuật ngữ chính xác và từ hiếm.

Có thể thất bại khi truy vấn sử dụng synonym hoặc paraphrase.

## 4. Hybrid Retrieval

Hybrid Retrieval kết hợp candidate từ lexical và semantic search.

Một phương pháp hợp nhất thứ hạng là Reciprocal Rank Fusion:

RRF(d) = sum_i 1 / (k + rank_i(d))

rank_i(d) là thứ hạng của tài liệu trong hệ thống retrieval thứ i.

Cần đánh giá trên tập truy vấn đại diện thay vì mặc định hybrid luôn tốt hơn.

## 5. Reranking

Reranker đánh giá trực tiếp cặp query-document.

Pipeline:
1. Lấy candidate set rộng.
2. Kiểm tra permission và metadata.
3. Rerank candidate.
4. Kiểm tra temporal và provenance constraints.
5. Chọn context theo token hoặc size budget.

Reranking có thể cải thiện relevance nhưng không sửa được source data sai.

## 6. Knowledge Graph Construction

Entity Extraction tìm các entity ứng viên.

Entity Resolution xác định hai cách nhắc đến có cùng chỉ một entity không.

Relation Extraction phát hiện quan hệ ứng viên.

Biểu diễn graph:

G = (V, E)

- V: entities hoặc concepts.
- E: typed relationships.

Cần kiểm soát:
- Entity identity confidence.
- Relationship provenance.
- Temporal validity.
- Duplicate và alias management.
- Conflict preservation.

## 7. Graph Traversal và GraphRAG

Các phương pháp:
- Bounded Neighborhood Traversal.
- Typed Path Constraints.
- Personalized PageRank.
- Entity-centered Expansion.
- Multi-hop Relation Queries.

GraphRAG kết hợp graph structure với text retrieval và language-model
synthesis.

Graph chỉ đáng tin bằng chất lượng extraction và source validation.

## 8. Temporal và Bitemporal Modeling

Temporal fact có thể được biểu diễn:

(subject, predicate, object, valid_from, valid_to)

Bitemporal record bổ sung:

(transaction_from, transaction_to)

Điều này phân biệt thời gian trong thế giới thực và thời gian hệ thống
ghi nhận.

Temporal consistency checks cần phát hiện các facts xung đột về thời gian.

## 9. Deduplication

Các tín hiệu:
- Exact normalized hash.
- Canonical identifiers.
- Field-level equality.
- Token similarity.
- Embedding similarity.

Deduplication phải thận trọng. Hai sự kiện tương tự vẫn có thể là hai
sự kiện khác nhau.

## 10. Clustering và Consolidation

Các phương pháp:
- K-means.
- Hierarchical Clustering.
- Density-based Clustering.
- Graph Community Detection.

Consolidation phải giữ:
- Original Record IDs.
- Source References.
- Confidence và Verification State.
- Transformation Version.
- Reviewer và Approval History.

## 11. Memory Decay và Relevance

Một hàm giảm trọng số theo thời gian:

w(t) = exp(-lambda * delta_t)

Có thể giảm độ ưu tiên truy xuất khi thông tin cũ hơn.

Tuy nhiên, tuổi của dữ kiện không chứng minh dữ kiện sai. Thông tin lịch sử,
dữ kiện ổn định và hồ sơ cần lưu trữ không được xóa chỉ vì decay.

Decay là cơ chế ranking/prioritization, trừ khi retention policy riêng
cho phép deletion.

## 12. Bayesian Evidence Combination

Với evidence E và hypothesis H:

P(H | E) proportional to P(E | H) P(H)

Kết hợp evidence độc lập cần có giả định độc lập hợp lý. Không đếm nhiều
nguồn tương quan như nhiều xác nhận độc lập.

## 13. Contradiction Detection

Các kỹ thuật:
- Rule-based Incompatibility Checks.
- Temporal Overlap Checks.
- Entity và Predicate Normalization.
- Natural-language Inference.
- Source Comparison.
- Human Adjudication.

Automated Contradiction Detection nên tạo candidate để review, không
âm thầm xóa claims đối lập.

## 14. Memory Compression

Các phương pháp:
- Extractive Summarization.
- Abstractive Summarization.
- Hierarchical Summaries.
- Event Timelines.
- Semantic Clustering.
- Structured Fact Extraction.

Cần đánh giá:
- Information Loss.
- Temporal Distortion.
- Attribution Errors.
- Unsupported Inferences.
- Loss of Uncertainty.

## 15. Memory Evaluation

Retrieval:
- Precision@k.
- Recall@k.
- MRR.
- nDCG.
- Hit Rate.

Faithfulness:
- Source Attribution Accuracy.
- Claim Support Rate.
- Contradiction Preservation.
- Temporal Correctness.

Governance:
- Unauthorized Retrieval Rate.
- Cross-user Leakage Tests.
- Revocation Effectiveness.
- Deletion Propagation.

Operational:
- Latency.
- Storage Growth.
- Index Refresh Time.
- Cost per Query.
