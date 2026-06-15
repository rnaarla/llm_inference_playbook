# Compatibility Matrix

These are **target pins**, not fleet validation evidence. A profile is proven
only when `validated_on` / `validated_by` are set in `playbook/versions.lock`
after live validation.

| Component | Target | Status |
|---|---|---|
| Kubernetes | 1.29 | target pin |
| vLLM | 0.9.1 | target pin |
| CUDA | 12.4 | target pin |
| NVIDIA driver | 550.54.15 | target pin |
| NCCL | 2.21.5 | target pin |
| KServe | 0.14.0 | target pin |
| Gateway API Inference Extension | 0.1.0 | target pin |
| DCGM exporter | 3.3.8 | target pin |
| SGLang | 0.4.6 | secondary profile target |

See `playbook/versions.lock` for the canonical profile file.
