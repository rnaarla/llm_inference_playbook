# capacity.py — PLANNING HELPER. python capacity.py meta-llama/Llama-3.1-70B-Instruct \
#   --dtype bf16 --kv-dtype fp8 --ctx 16384 --concurrency 32 --headroom 0.20
# Prefer --local-path to inspect the artifact you will actually serve.
import argparse, json, os, urllib.request

BYTES = {"fp32": 4, "float32": 4, "bf16": 2, "bfloat16": 2, "fp16": 2, "float16": 2,
         "fp8": 1, "int8": 1, "int4": 0.5}

def fetch_json(url):
    return json.load(urllib.request.urlopen(url))

def checkpoint_info(model, cfg, local_path=None):
    """Checkpoint BYTES are the serving-fit truth; parameter count is inferred
    only when the checkpoint dtype is unambiguous. For quantized checkpoints
    (FP8/INT4/AWQ/GPTQ/mixed), torch_dtype does NOT describe physical bytes/param —
    report size and skip param inference rather than mislead."""
    try:
        if local_path:
            idx = json.load(open(os.path.join(local_path, "model.safetensors.index.json")))
        else:
            idx = fetch_json(f"https://huggingface.co/{model}/raw/main/model.safetensors.index.json")
        total_bytes = idx["metadata"]["total_size"]
        quant = cfg.get("quantization_config")
        dtype = str(cfg.get("torch_dtype", "")).replace("torch.", "")
        if quant is None and dtype in BYTES:
            return total_bytes, total_bytes / BYTES[dtype], "safetensors-index"
        return total_bytes, None, "safetensors-index (quantized/mixed — params not inferred)"
    except Exception:
        pass
    # heuristic — WRONG for MoE/tied-embeddings/non-standard FFN; flagged in output
    h, L, V = cfg["hidden_size"], cfg["num_hidden_layers"], cfg["vocab_size"]
    params = 12 * L * h**2 + 2 * h * V
    return None, params, "HEURISTIC (verify!)"

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("model"); p.add_argument("--local-path", default=None)
    p.add_argument("--dtype", default="bf16"); p.add_argument("--kv-dtype", default="bf16")
    p.add_argument("--ctx", type=int, default=8192)
    p.add_argument("--concurrency", type=int, default=16)
    p.add_argument("--headroom", type=float, default=0.20)
    a = p.parse_args()
    cfg = (json.load(open(os.path.join(a.local_path, "config.json"))) if a.local_path
           else fetch_json(f"https://huggingface.co/{a.model}/raw/main/config.json"))
    n_layers = cfg["num_hidden_layers"]; hidden = cfg["hidden_size"]
    n_heads  = cfg["num_attention_heads"]; n_kv = cfg.get("num_key_value_heads", n_heads)
    head_dim = cfg.get("head_dim", hidden // n_heads)
    params, source = None, ""
    ckpt_bytes, params, source = checkpoint_info(a.model, cfg, a.local_path)
    # Serving weight footprint: checkpoint bytes if serving the checkpoint as-is;
    # params × serving-dtype bytes if re-quantizing/casting (requires known params)
    if ckpt_bytes is not None:
        w_gib = ckpt_bytes / 2**30
        w_note = "checkpoint bytes (as-served)"
        if params is not None and a.dtype:
            w_gib = params * BYTES[a.dtype] / 2**30
            w_note = f"params x {a.dtype}"
    else:
        w_gib = params * BYTES[a.dtype] / 2**30
        w_note = f"params x {a.dtype} (heuristic params)"
    kv_tok = 2 * n_layers * n_kv * head_dim * BYTES[a.kv_dtype]
    kv_gib = a.concurrency * a.ctx * kv_tok / 2**30
    total  = (w_gib + kv_gib) * (1 + a.headroom)
    print(f"param source: {source}")
    if ckpt_bytes is not None:
        print(f"checkpoint size: {ckpt_bytes/2**30:.1f} GiB")
    print(f"weights≈{w_gib:.1f} GiB ({w_note})  kv/token={kv_tok/2**20:.2f} MiB  "
          f"KV@{a.concurrency}x{a.ctx}≈{kv_gib:.1f} GiB  TOTAL+headroom≈{total:.1f} GiB")
    print(f"fits: 1xH100-80? {total<80}  1xH200-141? {total<141}  2xH100? {total<160}")
    print("PLANNING ESTIMATE — confirm against measured engine memory on your profile (§0.1)")
