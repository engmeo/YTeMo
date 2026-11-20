# Kiểm kê kiến trúc từ Repository

Thời điểm tạo: 2026-11-20 11:52:58

> Báo cáo phát hiện file source và test. Sự tồn tại của file không chứng minh implementation hoàn chỉnh hoặc runtime integration.

## Các file Planning

- `backend\planning\__init__.py`
- `backend\planning\agent_integration.py`
- `backend\planning\belief_engine.py`
- `backend\planning\benchmark.py`
- `backend\planning\causal.py`
- `backend\planning\constraints.py`
- `backend\planning\contracts.py`
- `backend\planning\counterfactual.py`
- `backend\planning\decision_audit.py`
- `backend\planning\decision_engine.py`
- `backend\planning\domains\__init__.py`
- `backend\planning\domains\healthcare\__init__.py`
- `backend\planning\domains\healthcare\policy.py`
- `backend\planning\domains\robotics\__init__.py`
- `backend\planning\domains\robotics\policy.py`
- `backend\planning\execution.py`
- `backend\planning\governance.py`
- `backend\planning\hierarchical_adapter.py`
- `backend\planning\hierarchical_engine.py`
- `backend\planning\hierarchy.py`
- `backend\planning\information.py`
- `backend\planning\information_planner.py`
- `backend\planning\meta_planner.py`
- `backend\planning\models.py`
- `backend\planning\multiobjective.py`
- `backend\planning\optimization.py`
- `backend\planning\orchestrator.py`
- `backend\planning\plan_graph.py`
- `backend\planning\replanning.py`
- `backend\planning\risk.py`
- `backend\planning\robustness.py`
- `backend\planning\scheduler.py`
- `backend\planning\search.py`
- `backend\planning\temporal.py`
- `backend\planning\validation.py`
- `backend\planning\verification.py`
- `backend\planning\voi.py`
- `backend\planning\world_model.py`

## Các file kiểm thử Planning

- `backend\test_planning_causal_risk.py`
- `backend\test_planning_core.py`
- `backend\test_planning_decision_audit.py`
- `backend\test_planning_decision_contracts.py`
- `backend\test_planning_decision_evaluation.py`
- `backend\test_planning_decision_safety.py`
- `backend\test_planning_decision_selection.py`
- `backend\test_planning_execution.py`
- `backend\test_planning_governance_benchmark.py`
- `backend\test_planning_hierarchical.py`
- `backend\test_planning_hierarchical_adapter.py`
- `backend\test_planning_hierarchical_engine.py`
- `backend\test_planning_information.py`
- `backend\test_planning_multiobjective.py`
- `backend\test_planning_orchestrator.py`
- `backend\test_planning_orchestrator_contracts.py`
- `backend\test_planning_replanning_integration.py`
- `backend\test_planning_scheduler.py`
- `backend\test_planning_search.py`
- `backend\test_planning_world_model.py`
- `backend\test_planning_world_model_versioning.py`

## Các file liên quan Memory

- `backend\memory_conflict_engine.py`
- `backend\memory_engine.py`
- `backend\memory_intelligence.py`
- `backend\temporal_memory.py`
- `backend\test_memory_conflict_engine.py`
- `backend\test_memory_engine.py`
- `backend\test_memory_intelligence.py`
- `backend\test_temporal_memory.py`

## Các file kiểm thử Memory

- `backend\test_memory_conflict_engine.py`
- `backend\test_memory_engine.py`
- `backend\test_memory_intelligence.py`
- `backend\test_temporal_memory.py`

## Tổng kết

- Tổng Python files trong backend: 85
- Planning source files: 38
- Planning test files: 21
- Memory-related source files: 8
- Memory-related test files: 4

## Cách diễn giải

- Phát hiện source file: chỉ chứng minh có file code.
- Phát hiện test file: chỉ chứng minh có file kiểm thử.
- Muốn xác nhận test pass phải chạy test.
- Muốn xác nhận integration phải kiểm tra runtime call path.
- Báo cáo không kiểm tra database migrations, deployed services hoặc hạ tầng bên ngoài.
