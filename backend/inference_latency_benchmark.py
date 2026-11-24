"""Measure TTFT and end-to-end latency on an OpenAI-compatible inference server.

Use synthetic or de-identified prompts only. This benchmark does not score
clinical correctness; it exports responses for blinded human review.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import time
from pathlib import Path
from urllib.request import Request, urlopen


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return ordered[index]


def completion_endpoint(base_url: str) -> str:
    value = base_url.rstrip("/")
    if value.endswith("/v1/chat/completions"):
        return value
    if value.endswith("/v1"):
        return value + "/chat/completions"
    return value + "/v1/chat/completions"


def _estimate_tokens(text: str) -> int:
    return len(text.split())


def stream_completion(
    endpoint: str,
    model: str,
    prompt: str,
    api_key: str | None = None,
    max_tokens: int = 256,
    timeout_seconds: int = 120,
) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "stream_options": {"include_usage": True},
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    first_token_at = None
    chunks: list[str] = []
    usage = None
    with urlopen(request, timeout=timeout_seconds) as response:
        while True:
            raw_line = response.readline()
            if not raw_line:
                break
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            if not data:
                continue
            event = json.loads(data)
            if event.get("usage"):
                usage = event["usage"]
            choices = event.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content")
            if isinstance(content, str) and content:
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                chunks.append(content)
    finished = time.perf_counter()
    output = "".join(chunks)
    if not output.strip():
        raise RuntimeError("Inference endpoint returned no streamed text.")
    elapsed = finished - started
    ttft = (first_token_at - started) if first_token_at is not None else elapsed
    actual_tokens = (usage or {}).get("completion_tokens")
    token_count = int(actual_tokens) if actual_tokens is not None else _estimate_tokens(output)
    return {
        "ttft_seconds": round(ttft, 4),
        "total_seconds": round(elapsed, 4),
        "completion_tokens": token_count,
        "token_count_is_estimate": actual_tokens is None,
        "tokens_per_second": round(token_count / max(elapsed - ttft, 0.001), 3),
        "output": output,
    }


def load_prompts(path: Path) -> list[str]:
    prompts = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        prompt = item.get("prompt") if isinstance(item, dict) else None
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Line {line_number} must contain a non-empty 'prompt'.")
        prompts.append(prompt.strip())
    if not prompts:
        raise ValueError("Prompt file is empty.")
    return prompts


def summarize(samples: list[dict]) -> dict:
    ttft = [row["ttft_seconds"] for row in samples]
    total = [row["total_seconds"] for row in samples]
    speed = [row["tokens_per_second"] for row in samples]
    return {
        "samples": len(samples),
        "ttft_p50_seconds": percentile(ttft, 0.50),
        "ttft_p95_seconds": percentile(ttft, 0.95),
        "total_p50_seconds": percentile(total, 0.50),
        "total_p95_seconds": percentile(total, 0.95),
        "tokens_per_second_p50": percentile(speed, 0.50),
        "tokens_per_second_p95": percentile(speed, 0.95),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("YTEMO_BENCHMARK_BASE_URL"))
    parser.add_argument("--api-key", default=os.getenv("YTEMO_BENCHMARK_API_KEY"))
    parser.add_argument("--model", default=os.getenv("YTEMO_BENCHMARK_MODEL"))
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", type=Path, default=Path("inference-benchmark-results.json"))
    args = parser.parse_args()
    if not args.base_url or not args.model:
        parser.error("Provide --base-url and --model or set YTEMO_BENCHMARK_BASE_URL / YTEMO_BENCHMARK_MODEL.")
    if args.runs < 1 or args.runs > 20:
        parser.error("--runs must be between 1 and 20.")

    prompts = load_prompts(args.prompts)
    endpoint = completion_endpoint(args.base_url)
    samples = []
    for prompt_index, prompt in enumerate(prompts, 1):
        for run_index in range(1, args.runs + 1):
            result = stream_completion(
                endpoint, args.model, prompt, args.api_key,
                args.max_tokens, args.timeout,
            )
            samples.append({
                "prompt_index": prompt_index,
                "run_index": run_index,
                "prompt": prompt,
                **result,
            })
            print(
                f"prompt={prompt_index}/{len(prompts)} run={run_index}/{args.runs} "
                f"ttft={result['ttft_seconds']:.3f}s total={result['total_seconds']:.3f}s "
                f"tokens/s={result['tokens_per_second']:.2f}",
                flush=True,
            )

    report = {
        "model": args.model,
        "endpoint": endpoint,
        "runs_per_prompt": args.runs,
        "max_tokens": args.max_tokens,
        "summary": summarize(samples),
        "samples": samples,
        "quality_note": (
            "Latency metrics are not a quality or clinical-safety score. "
            "Review outputs blindly against the same prompt set using qualified reviewers."
        ),
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote:", args.output)


if __name__ == "__main__":
    main()
