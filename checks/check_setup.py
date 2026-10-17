"""Check that the environment can run the pipeline. Prints what to fix; exits 1 on any failure."""
import os
import subprocess
import sys

import requests

from tools.common import ROOT, load_config, record_versions

AUTHOR_EMAIL = "tanishahandoo2002@gmail.com"


def main():
    errors, warnings = [], []

    data = os.environ.get("C2C_DATA")
    if not data:
        errors.append("C2C_DATA is not set: export C2C_DATA=/Volumes/<drive>/c2c_data")
    elif not (os.path.isdir(data) and os.access(data, os.W_OK)):
        errors.append(f"C2C_DATA={data} is not a writable folder (is the external drive mounted?)")

    email = subprocess.run(["git", "config", "user.email"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if email != AUTHOR_EMAIL:
        errors.append(f"git user.email is '{email}', expected {AUTHOR_EMAIL}: git config user.email {AUTHOR_EMAIL}")
    hook = ROOT / ".git" / "hooks" / "commit-msg"
    if not (hook.exists() and os.access(hook, os.X_OK)):
        errors.append("commit-msg hook missing or not executable in .git/hooks")

    raters = load_config("screening")["raters"]
    qwen = raters["qwen"]
    try:
        tags = requests.get(qwen["base_url"].replace("/v1", "/api/tags"), timeout=5).json()
        names = [m["name"] for m in tags.get("models", [])]
        if not any(n == qwen["model"] or n.startswith(qwen["model"] + ":") for n in names):
            errors.append(f"Ollama is running but lacks {qwen['model']}: ollama pull {qwen['model']}")
    except requests.RequestException:
        errors.append("Ollama is not running: start it with OLLAMA_MODELS=$C2C_DATA/ollama ollama serve")

    gemini = raters["gemini"]
    key = os.environ.get(gemini["api_key_env"])
    if not key:
        warnings.append(f"{gemini['api_key_env']} not set: Gemini screening will not run")
    else:
        from openai import OpenAI
        try:
            ids = {m.id.removeprefix("models/") for m in OpenAI(base_url=gemini["base_url"], api_key=key).models.list()}
            if gemini["model"] not in ids:
                errors.append(f"Gemini model {gemini['model']} not offered; pick one of the current models in config/screening.yaml")
        except Exception as e:  # network or auth failure
            errors.append(f"Gemini API not reachable: {e}")

    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("FAIL:", e)
    if errors:
        sys.exit(1)
    record_versions("setup")
    print("setup OK")


if __name__ == "__main__":
    main()
