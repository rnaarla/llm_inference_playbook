# Mock Example

This directory is reserved for a future non-GPU mock deployment that demonstrates
resource wiring without requiring a GPU cluster.

Current scope:

- offline examples live in `examples/*.local.yaml`
- real deployments require user-provided infrastructure

Planned:

- fake OpenAI-compatible backend
- local admission/gateway demo
- kind/k3d values with no GPU resource requests
