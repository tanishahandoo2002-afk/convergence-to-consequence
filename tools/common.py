"""Config loading, data paths and version recording shared by every stage."""
import datetime
import os
import platform
import re
from importlib import metadata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
_ENV = re.compile(r"\$\{(\w+)\}")


def _expand(value):
    if isinstance(value, str):
        def sub(m):
            if m.group(1) not in os.environ:
                raise KeyError(f"environment variable {m.group(1)} is not set")
            return os.environ[m.group(1)]
        return _ENV.sub(sub, value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def load_config(name, config_dir=ROOT / "config"):
    """Read config/<name>.yaml, expanding ${VAR} from the environment."""
    return _expand(yaml.safe_load((Path(config_dir) / f"{name}.yaml").read_text()))


def data_dir(*parts):
    """$C2C_DATA/<parts>, created if missing. Large and non-shareable data live here."""
    if not os.environ.get("C2C_DATA"):
        raise RuntimeError("C2C_DATA is not set; point it at the data folder on the external drive")
    path = Path(os.environ["C2C_DATA"]).joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def record_versions(stage, path=ROOT / "results" / "versions.txt"):
    """Append the date, stage and key package versions to results/versions.txt."""
    pkgs = ["nimare", "nilearn", "nibabel", "pandas", "openai"]
    versions = " ".join(f"{p}={metadata.version(p)}" for p in pkgs)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(f"{datetime.date.today()} {stage} python={platform.python_version()} {versions}\n")
