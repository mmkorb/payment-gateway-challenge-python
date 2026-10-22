"""Small load script for the payment gateway (not a test, unittest skips it).

Run: python -m tests.performance.load_test --requests 500 --concurrency 20

No pass/fail threshold: the requirements define no performance target. The
script exits non-zero only if a request returned a status other than 201.
"""

import argparse
import asyncio
import os
import statistics
import sys
import time
from collections import Counter

import httpx

from tests.e2e.test_payments_e2e import payment_request


async def send(client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> tuple[str, float]:
    async with semaphore:
        start = time.perf_counter()
        try:
            response = await client.post("/payments", json=payment_request())
            outcome = str(response.status_code)
        except httpx.HTTPError as error:
            outcome = type(error).__name__
        return outcome, (time.perf_counter() - start) * 1000


async def run(base_url: str, requests: int, concurrency: int) -> int:
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        start = time.perf_counter()
        results = await asyncio.gather(*(send(client, semaphore) for _ in range(requests)))
        elapsed = time.perf_counter() - start

    outcomes = Counter(outcome for outcome, _ in results)
    latencies = [latency for _, latency in results]
    failures = {code: n for code, n in outcomes.items() if code != "201"}
    cuts = statistics.quantiles(latencies, n=100) if len(latencies) > 1 else latencies * 99

    print(f"total requests: {requests}")
    print(f"failures per status: {failures or 'none'}")
    print(f"throughput: {requests / elapsed:.1f} req/s")
    print(
        f"latency ms: p50={cuts[49]:.1f} p95={cuts[94]:.1f} "
        f"p99={cuts[98]:.1f} max={max(latencies):.1f}"
    )
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()
    base_url = os.environ.get("GATEWAY_URL", "http://localhost:8000")
    return asyncio.run(run(base_url, args.requests, args.concurrency))


if __name__ == "__main__":
    sys.exit(main())
