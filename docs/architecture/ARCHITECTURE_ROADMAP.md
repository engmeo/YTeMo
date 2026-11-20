# Lộ trình phát triển kiến trúc Y TẾ MỞ

## Nguyên tắc

Ưu tiên correctness, observability, security và integration contracts
trước khi bổ sung thêm thuật toán.

Một thuật toán phức tạp nhưng thiếu dữ liệu đáng tin cậy, validation và
evaluation không tạo nên một hệ thống production tốt.

## Track A — Planning

### A1. Foundation và Contracts
- Ổn định public API.
- Domain-neutral Core.
- Versioned Models.
- Input Validation.
- Deterministic behavior khi cần.

### A2. World và State Intelligence
- State Versioning.
- Transition Model Evaluation.
- Prediction Error Tracking.
- Observation Reconciliation.
- Uncertainty Representation.

### A3. Hierarchical Planning
- HTN Method Applicability.
- Decomposition Trace.
- Dependency Constraints.
- Bounded Search.
- Plan Conversion và Validation.

### A4. Decision và Search
- Decision Evaluation.
- Belief Update Validation.
- Search Strategy Benchmarking.
- Anytime và Bounded Search.
- Evidence-aware Abstention.

### A5. Optimization và Robustness
- Multi-objective Benchmarks.
- Constraint Handling.
- Scenario Analysis.
- Sensitivity và Robustness Tests.
- Resource-aware Planning.

### A6. Execution Feedback Boundary
- Monitoring Contracts.
- Outcome Evidence.
- Recovery Recommendations.
- AgentCore Integration qua explicit interfaces.

### A7. Meta-Cognition
- Verified Outcome Tracking.
- Strategy Evaluation.
- Resource-aware Metareasoning.
- Drift Detection.
- Safety-isolated Learning.

### A8. Multi-Agent Planning
- Agent Capability Contracts.
- Task Allocation.
- Conflict Handling.
- Coordination Protocols.
- Failure Isolation.

### A9. Verification và Evaluation
- Property-based Tests.
- Invariant Tests.
- Benchmarks.
- Integration Tests.
- Runtime Observability.

## Track B — Memory

### B1. Memory Foundation
- Canonical Memory Identity.
- Typed Memory Contracts.
- Ownership và Access Scope.
- Source References.
- Lifecycle.

### B2. Evidence và Conflict
- Evidence Records.
- Verification Status.
- Conflict Detection.
- Conflict Preservation.
- Resolution Workflow.

### B3. Temporal và Versioned Memory
- Valid Time.
- Transaction Time.
- Version History.
- Historical Reconstruction.

### B4. Derivation Lineage
- Source-to-derived Relationships.
- Transformation Version.
- Provenance Graph.
- Reproducibility.

### B5. Consolidation
- Candidate Generation.
- Deduplication.
- Clustering.
- Summarization.
- Human Review.
- Rollback.

### B6. Hybrid Retrieval
- Lexical Retrieval.
- Vector Retrieval.
- Metadata Filtering.
- Graph Retrieval.
- Reranking.
- Permission-aware Context Assembly.

### B7. Governance và Isolation
- Consent Enforcement.
- Owner Isolation.
- Revocation.
- Deletion Propagation.
- Audit.

### B8. Advanced Memory
- Temporal Graph.
- GraphRAG.
- Multimodal Memory.
- Agentic Memory.
- Continual Evaluation.

## Track C — System Integration

- Companion-to-Memory Contracts.
- Companion-to-Planning Contracts.
- Planning-Memory Context Exchange.
- AgentCore Execution Boundary.
- Event-driven Feedback.
- End-to-end Authorization Tests.
- Observability và Failure Recovery.

## Track D — Evaluation

Planning Metrics:
- Plan Validity.
- Goal Achievement.
- Search Cost.
- Planning Latency.
- Resource Usage.
- Risk Violations.
- Recovery Success.
- Strategy Performance.

Memory Metrics:
- Retrieval Precision và Recall.
- Evidence Attribution.
- Temporal Correctness.
- Conflict Detection.
- Consolidation Fidelity.
- Access Isolation.
- Deletion Propagation.

System Metrics:
- End-to-end Latency.
- Integration Reliability.
- Failure Recovery.
- Audit Completeness.
- Permission Violations.

## Release Gates

Không đánh dấu subsystem production-ready nếu chưa:
1. Ổn định contracts.
2. Vượt qua core tests.
3. Vượt qua integration tests.
4. Vượt qua security và authorization tests.
5. Tài liệu hóa failure modes.
6. Có observability.
7. Tài liệu hóa operational limitations.
8. Hoàn thành domain validation cần thiết.
