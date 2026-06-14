# Playbook artifacts — executable validation layer

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
PATH="$(pwd)/.venv/bin:$PATH" make offline    # CPU-safe CI
PATH="$(pwd)/.venv/bin:$PATH" make gpu        # requires live vLLM
PATH="$(pwd)/.venv/bin:$PATH" make game-day   # staging hooks
```

See repo [README](../README.md) for full navigation.
