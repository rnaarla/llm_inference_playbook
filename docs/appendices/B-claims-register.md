# Appendix B — Claims Register (the resolve-or-remove worklist)

Per §0.3: before external publication, every [Vendor]/[Directional] row below is resolved (primary source + config located, tag upgraded) or the claim is removed from the body. Internal adoption may proceed with rows open, but each open row is a known debt.

| Claim | Tag | Status / source to confirm |
|---|---|---|
| PagedAttention 2–4× vs FasterTransformer/Orca | [Cited] | Kwon et al., SOSP '23, arXiv:2309.06180, paper config |
| FA3 ~75% util FP16 / ~1.2 PFLOPS FP8 on H100 | [Cited] | Shah et al., arXiv:2407.08608; benchmark-specific; active kernel path must be confirmed per profile |
| H100 ridge ≈295 FLOPs/byte FP16 | [Derived] | 989 TFLOPS / 3.35 TB/s — SXM5 variant |
| RadixAttention up to 6.4× prefix-heavy | [Cited→Directional] | SGLang paper; vLLM has since added prefix caching — re-benchmark |
| SGLang jump-forward ~2× structured-output latency | [Vendor] | **Number removed from body** — restore only with primary SGLang benchmark + config |
| EAGLE-3 3–6.5× low batch | [Cited→Directional] | EAGLE-3 paper; production gains lower, workload-dependent |
| TGI maintenance mode | **[Cited — resolved]** | HF Inference Endpoints docs: maintenance mode as of 2025-12-11, vLLM/SGLang recommended (verified against official docs as of 2026-06-10; re-verify per profile) |
| llm-d / prefix-aware routing case-study gains | [Vendor — number removed from body] | locate the primary case study + config before restoring any figure |
| NIXL `kv_role` semantics | **[Cited — resolved]** | vLLM NixlConnector docs: `kv_role` is effectively a placeholder; actual P/D roles set by the upper-level proxy — matches §5.7 wording |
| KServe `LLMInferenceService` CRD | **[Cited — resolved]** | KServe generative-inference docs confirm the CRD and router/scheduler features; field shapes remain profile-pinned |
| vLLM metric names used in §2.4 | **[Cited — resolved at family level]** | vLLM metrics design docs confirm the metric family (running/waiting, kv_cache_usage, prefix-cache, TTFT/ITL histograms); exact names re-verified per profile |
| MI300X ~37–66% of H100 realized | [Directional, dated] | SemiAnalysis-era; ROCm/vLLM moving fast — re-benchmark current stack |
| Blackwell FP4 production guidance (mixed precision) | [Vendor] | **Planning only** — validate per-model on eval gate before adoption |
| H200 141 GB / 4.8 TB/s; B200 192 GB; MI325X 256 GB / 6 TB/s | [Derived from specs] | vendor spec sheets |
| NVLink4 900 GB/s vs PCIe Gen5 ~128 GB/s | [Derived from specs] | bidirectional figures |
| Two all-reduces/layer in Megatron TP forward | [Cited] | Shoeybi et al., Megatron-LM |
| Mooncake KVCache-centric disaggregation | [Cited] | FAST '25; per-version behavior of NIXL/LMCache connectors still needs profile pinning |
| All CLI flags, CRD shapes, metric names, connector roles, kernel paths | — | version-sensitive; re-verify against the §0.1 profile |
