#!/usr/bin/env python3
"""Load-level gateway checks — requires STAGING_GATEWAY_URL or local gateway."""
import asyncio
import os
import sys

import httpx

URL = os.environ.get("STAGING_GATEWAY_URL", "http://localhost:8080")
REQUIRE = os.environ.get("STAGING_REQUIRE", "0") == "1"
CONCURRENCY = int(os.environ.get("GATEWAY_LOAD_CONCURRENCY", "32"))


async def one(client: httpx.AsyncClient, i: int) -> int:
    r = await client.post(
        f"{URL}/v1/chat/completions",
        json={"model": "phi3", "messages": [{"role": "user", "content": f"ping {i}"}], "max_tokens": 8},
        timeout=30.0,
    )
    return r.status_code


async def main() -> int:
    try:
        async with httpx.AsyncClient() as probe:
            await probe.get(f"{URL}/docs", timeout=2.0)
    except Exception as e:
        if REQUIRE:
            print(f"FAIL: gateway unreachable at {URL}: {e}")
            return 1
        print(f"SKIP: gateway unreachable at {URL}")
        return 0

    codes = []
    async with httpx.AsyncClient() as client:
        tasks = [one(client, i) for i in range(CONCURRENCY)]
        codes = await asyncio.gather(*tasks, return_exceptions=True)

    ok = sum(1 for c in codes if c in (200, 429))
    if ok == 0:
        print(f"FAIL: no 200/429 in {CONCURRENCY} requests: {codes[:5]}...")
        return 1
    print(f"test-gateway: {ok}/{CONCURRENCY} returned 200 or 429")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
