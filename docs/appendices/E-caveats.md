# Appendix E — Caveats
- Vendor "up to" figures are ceilings from vendor-optimal configs; the body text treats them as footnotes, not planning numbers.
- Speculative decoding and disaggregation are conditional wins with explicit preconditions and rollbacks (§4.3, §5.7).
- Goodput is gameable (delayed token delivery smooths tails) — monitor P99 and token-level SLOs alongside it.
- The 405B/671B MoE multi-node topology companion (NVLink-domain planning, rail-optimized IB design, NCCL/RCCL tuning, wide-EP) is the committed next document; §5.4–5.5 carry the interim guidance.
- All VRAM math is a planning estimate; the §2.1 calculator plus measured headroom on your stack is the source of truth.
