# Model Cache

The implementation uses signed OCI model artifacts rather than runtime pulls from
the public internet.

## Registry Layout

```text
<registry-host>/models/<model-name>:<signed-tag>
<registry-host>/adapters/<adapter-name>:<signed-tag>
```

## Push

```bash
MODEL_SOURCE=/models/llama-3.1-70b-fp8 \
MODEL_ARTIFACT=<registry-host>/models/llama-3.1-70b-fp8:v1 \
COSIGN_KEY=cosign.key \
bash push_model_artifact.sh
```

## Pull

The engine chart uses an init container to pull `model.artifact` into
`model.cachePath`. The governance scaffold verifies the artifact signature and
approved digest before the ORAS pull. Production overlays should use
digest-pinned refs from promotion metadata.
