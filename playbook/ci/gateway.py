# gateway.py — LEARNING ARTIFACT. DO NOT DEPLOY.
# pip install fastapi uvicorn httpx
# Run single-worker only: uvicorn gateway:app --workers 1
import time

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

app = FastAPI()

# Endpoint management: client-facing alias → (upstream pool, real served model name).
# The alias MUST be translated before forwarding — vLLM rejects model names it wasn't
# started with (unless --served-model-name was set to the alias).
MODELS = {
    "phi3": {
        "upstreams": ["http://vllm-0:8000", "http://vllm-1:8000"],
        "served_name": "microsoft/Phi-3-mini-4k-instruct",
        "max_input_tokens": 4096, "max_output_tokens": 1024,   # admission limits (§6.1)
    },
}
_rr = {k: 0 for k in MODELS}   # single-process state; production uses EPP/external state

def route(alias: str):
    m = MODELS.get(alias)
    if not m:
        raise HTTPException(404, f"unknown model alias: {alias}")
    _rr[alias] = (_rr[alias] + 1) % len(m["upstreams"])
    return m["upstreams"][_rr[alias]], m

@app.post("/v1/chat/completions")
async def chat(req: Request):
    body = await req.json()
    upstream, m = route(body.get("model", "phi3"))
    body["model"] = m["served_name"]                       # alias translation
    if body.get("max_tokens", 0) > m["max_output_tokens"]: # admission: output cap
        raise HTTPException(400, "max_tokens exceeds model policy")
    t0 = time.perf_counter()
    if body.get("stream"):
        async def relay():
            async with httpx.AsyncClient(timeout=None) as c, c.stream(
                "POST", f"{upstream}/v1/chat/completions", json=body
            ) as r:
                if r.status_code != 200:  # propagate upstream failure
                    yield f'data: {{"error": "upstream {r.status_code}"}}\n\n'.encode()
                    return
                first = True
                async for chunk in r.aiter_bytes():
                    if first:
                        print(f"TTFT={time.perf_counter()-t0:.3f}s upstream={upstream}")
                        first = False
                    yield chunk
        return StreamingResponse(relay(), media_type="text/event-stream")
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{upstream}/v1/chat/completions", json=body)
        if r.status_code != 200:
            raise HTTPException(r.status_code, r.text[:500])
        return r.json()
