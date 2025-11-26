import os
import ssl
import warnings
import torch
import soundfile as sf
import sys
from pathlib import Path
import huggingface_hub

# Prevent huggingface_hub from performing network downloads during this local run.
# Replace hf_hub_download with a local-first resolver that looks under common model dirs.
def _local_hf_hub_download(repo_id, filename, cache_dir=None, *args, **kwargs):
    search_paths = []
    try:
        if cache_dir:
            search_paths.append(Path(cache_dir))
    except Exception:
        pass
    # common local places we might have model files
    search_paths += [Path("./RVC/models_zh"), Path("./RVC/models"), Path.cwd()]

    for base in search_paths:
        try:
            p = base / filename
            if p.exists():
                return str(p)
            # recursive search
            for m in base.rglob(filename):
                return str(m)
        except Exception:
            continue
    raise FileNotFoundError(f"Local copy of {filename} not found under {search_paths}; network downloads disabled")

# Patch the hf_hub_download in the huggingface_hub module before any chatterbox imports
try:
    huggingface_hub.hf_hub_download = _local_hf_hub_download
except Exception:
    pass

# SECURITY: Disabling SSL certificate verification is unsafe and exposes you to
# MITM attacks. Use this only for temporary debugging in a trusted network.
# To enable the behavior below set the environment variable DISABLE_SSL_VERIFY=1
# before running the script (see PowerShell example in comments at bottom).
if os.environ.get("DISABLE_SSL_VERIFY") == "1":
    # For the stdlib HTTPS/urllib/urllib3
    os.environ.setdefault("PYTHONHTTPSVERIFY", "0")
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
    except Exception:
        pass
    # Suppress insecure-request warnings from urllib3/requests
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

# Prefer local `src` folder so we use the repository code (not an installed package)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import logging
logging.basicConfig(level=logging.INFO)
try:
    # diagnostic: confirm which tokenizer module file will be used
    import importlib
    tok_mod = importlib.import_module('chatterbox.models.tokenizers.tokenizer')
    logging.getLogger(__name__).info(f"tokenizer module path: {getattr(tok_mod, '__file__', 'unknown')}")
except Exception:
    logging.getLogger(__name__).exception("failed to import tokenizer module for diagnostic")

from chatterbox.mtl_tts import ChatterboxMultilingualTTS
import traceback
import time

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {DEVICE}")

def clone_and_synthesize(ref_wav_path: str, text: str, out_path: str):
    # 使用多语种模型以支持 language_id 参数（例如中文 'zh'）
    # 确保本地模型权重已下载到 ./models（或替换为你的目录）
    model = ChatterboxMultilingualTTS.from_local("./RVC/models_zh", device=DEVICE)
    # 调用 generate（会内部处理 reference wav）
    try:
        print(f"[DEBUG] Calling model.generate() at {time.strftime('%X')}")
        wav_tensor = model.generate(
            text,
            language_id="zh",
            audio_prompt_path=ref_wav_path,
            exaggeration=0.5,
            temperature=0.6,
            cfg_weight=0.5,
            min_p=0.05,
            top_p=0.9,
            repetition_penalty=1.4
        )
        print(f"[DEBUG] model.generate returned type={type(wav_tensor)}")
        if wav_tensor is None:
            print("[ERROR] model.generate returned None")
            return
        try:
            # If it's a tensor, show shape/dtype
            import torch as _torch
            if isinstance(wav_tensor, _torch.Tensor):
                print(f"[DEBUG] wav_tensor.shape={wav_tensor.shape}, dtype={wav_tensor.dtype}, device={wav_tensor.device}")
            else:
                print(f"[DEBUG] wav_tensor repr: {repr(wav_tensor)[:200]}")
        except Exception:
            print("[DEBUG] failed to introspect wav_tensor")

        # model.generate 返回形如 torch.Tensor([1, N])，采样率在 model.sr（通常 24000）
        try:
            wav = wav_tensor.squeeze(0).cpu().numpy()
        except Exception as e:
            print("[ERROR] Failed to convert wav_tensor to numpy:", e)
            traceback.print_exc()
            return

        try:
            print(f"[DEBUG] Writing output to {out_path} with samplerate={getattr(model, 'sr', 'unknown')}")
            sf.write(out_path, wav, samplerate=getattr(model, 'sr', 24000))
            print(f"Saved cloned audio to {out_path} (sr={getattr(model, 'sr', 'unknown')})")
        except Exception as e:
            print("[ERROR] Failed to write WAV:", e)
            traceback.print_exc()
    except Exception as e:
        print("[ERROR] Exception during generation:", e)
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Run RVC clone-and-synthesize")
    parser.add_argument("--ref", "-r", default="./RVC/input/audio/nahida.wav", help="Reference wav path")
    parser.add_argument("--out", "-o", default="./RVC/output/cloned_nahida.wav", help="Output wav path")
    parser.add_argument("--text-file", "-t", default="./RVC/input/text/nahida.txt", help="Path to txt file containing the target text (UTF-8). If omitted, a built-in text is used.")
    args = parser.parse_args()

    ref = args.ref
    out = args.out

    if args.text_file:
        p = Path(args.text_file)
        if not p.exists():
            raise SystemExit(f"Text file not found: {p}")
        text = p.read_text(encoding="utf-8")
    else:
        # 默认目标文本（如果没有提供 text-file）
        text = "使用默认目标文本"

    clone_and_synthesize(ref, text, out)