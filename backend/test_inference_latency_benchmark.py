import pytest

from inference_latency_benchmark import completion_endpoint, percentile, summarize


def test_completion_endpoint_normalizes_openai_compatible_base_url():
    assert completion_endpoint("http://localhost:8001/v1/") == "http://localhost:8001/v1/chat/completions"
    assert completion_endpoint("http://localhost:8001") == "http://localhost:8001/v1/chat/completions"
    assert completion_endpoint("http://localhost:8001/v1/chat/completions") == "http://localhost:8001/v1/chat/completions"


def test_percentile_uses_nearest_rank_and_handles_empty_values():
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.50) == 2.0
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.95) == 4.0
    assert percentile([], 0.95) is None


def test_summary_reports_latency_and_token_rate():
    result = summarize([
        {"ttft_seconds": 0.2, "total_seconds": 1.0, "tokens_per_second": 20.0},
        {"ttft_seconds": 0.4, "total_seconds": 2.0, "tokens_per_second": 10.0},
    ])
    assert result["samples"] == 2
    assert result["ttft_p50_seconds"] == 0.2
    assert result["total_p95_seconds"] == 2.0
