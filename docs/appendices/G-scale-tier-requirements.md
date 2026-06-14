# Appendix G — Scale Tier [T2] Requirements

Hyperscale requirements extracted from the core playbook. Adopt when tagged **[T2]** in the body.

## T2: TCP half-open mitigation

Client disconnects are often silent (mobile clients dropping without FIN/RST). If the gateway does not notice, the engine bleeds decode capacity. Tune **HTTP/2 PING frames and TCP keepalives** at the Envoy layer to detect dead connections in <5s and forcibly sever upstream streams.

## T2: CUDA graph bucketization

Dynamic batching and sequence-length variation cause CUDA graph memory pools to splinter. Mandate custom graph management: heavily bucketized graph capturing and padding to power-of-2 sequence lengths to prevent VRAM OOMs and host-device sync overhead.

## T2: C++ scheduler backends

At hundreds of in-flight requests, Python GIL in the scheduling loop caps QPS and thrashes TPOT. Mandate C++ core schedulers (vLLM V1, TensorRT-LLM); avoid Python-bound control loops on the critical path.

## T2: GPU clock lock

An 8-GPU TP group is only as fast as its hottest chip. Lock application clocks (`nvidia-smi -lgc <target_freq>`) fleet-wide to prevent thermal throttling from destabilizing TPOT.

## T2: NUMA pinning

Launching kernels from the wrong CPU socket across UPI/QPI ruins tail latency. Bind the engine to the CPU socket matching the GPU PCIe switch and NIC:

```bash
numactl --cpunodebind=0 --membind=0 vllm serve ...
```

## T2: GDS KV offload

Bouncing disaggregated KV cache through the CPU is unacceptable at scale. Mandate **GPU-Direct Storage (GDS / libcufile)** for direct PCIe-to-GPU NVMe KV-cache swapping.

## T2: Tiered XID handling

Cordoning nodes on any XID error is too blunt:

1. **Recoverable** (XID 13, 31): restart engine container.
2. **Fatal** (XID 79, 94): cordon, taint, drain.

## T2: Fabric micro-payload and IB AR/SHARP

- Run NCCL all-reduce with `-b 8 -e 2M` for decode-sized TP payloads; enforce `NCCL_ALGO=Tree`, `NCCL_PROTO=Simple`.
- Mandate InfiniBand Adaptive Routing (AR) and SHARP to prevent single-link drops from stalling PP/EP pipelines.

## T2: DHT prefix routing

Polling EPP via Gateway API is too slow for dynamic prefix states. Use an **inverted index (DHT like Redis)** populated by the engine block manager so the gateway maps prompt sequences to node/GPU block addresses in real time (target 90%+ prefix hit rates).

## T2: LoRA batch-by-ID

Adapter hot-swap (host→device copy) incurs PCIe penalties. Mandate **batching by LoRA ID** — stall requests briefly to accrue a batch for the same adapter before activation.
