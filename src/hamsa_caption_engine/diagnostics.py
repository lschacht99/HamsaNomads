from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys

from .paths import REMOTION_DIR, ROOT, find_ffmpeg, find_ffprobe, load_dotenv


def yesno(value: object) -> str:
    return "yes" if value else "no"


def _version(executable: str | None) -> str:
    if not executable:
        return "no"
    try:
        proc = subprocess.run([executable, "--version"], capture_output=True, text=True)
    except OSError as exc:
        return f"error: {exc}"
    return (proc.stdout or proc.stderr or "unknown").strip().splitlines()[0]


def _node_warning(node_version: str) -> str:
    clean = node_version.lower().replace("v", "").strip()
    major = clean.split(".", 1)[0]
    if major.isdigit() and int(major) >= 24:
        return "Node 24 detected. If Remotion crashes, try Node LTS 22 or 20."
    return "none"


def collect() -> dict[str, str]:
    load_dotenv()
    node = shutil.which("node")
    npm = shutil.which("npm")
    node_version = _version(node)
    return {
        "Python version": sys.version.replace("\n", " "),
        "Python executable": sys.executable,
        "Project root": str(ROOT),
        "project package import": yesno(importlib.util.find_spec("hamsa_caption_engine")),
        "faster_whisper import": yesno(importlib.util.find_spec("faster_whisper")),
        "ffmpeg found": find_ffmpeg() or "no",
        "ffprobe found": find_ffprobe() or "no",
        "node found": node or "no",
        "node version": node_version,
        "node warning": _node_warning(node_version),
        "npm found": npm or "no",
        "npm version": _version(npm),
        "remotion folder exists": yesno(REMOTION_DIR.exists()),
        "assets/brand/hamsa-logo.png exists": yesno((ROOT / "assets" / "brand" / "hamsa-logo.png").exists()),
        ".env exists": yesno((ROOT / ".env").exists()),
        "token exists": yesno(os.environ.get("HAMSA_TELEGRAM_BOT_TOKEN")),
    }


def main() -> None:
    for key, value in collect().items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
