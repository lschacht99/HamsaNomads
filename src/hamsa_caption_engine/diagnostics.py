from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

from .paths import REMOTION_DIR, ROOT, find_ffmpeg, find_ffprobe, load_dotenv


def yesno(value: object) -> str:
    return "yes" if value else "no"


def collect() -> dict[str, str]:
    load_dotenv()
    return {
        "Python version": sys.version.replace("\n", " "),
        "Python executable": sys.executable,
        "Project root": str(ROOT),
        "project package import": yesno(importlib.util.find_spec("hamsa_caption_engine")),
        "faster_whisper import": yesno(importlib.util.find_spec("faster_whisper")),
        "ffmpeg found": find_ffmpeg() or "no",
        "ffprobe found": find_ffprobe() or "no",
        "node found": shutil.which("node") or "no",
        "npm found": shutil.which("npm") or "no",
        "remotion folder exists": yesno(REMOTION_DIR.exists()),
        ".env exists": yesno((ROOT / ".env").exists()),
        "token exists": yesno(os.environ.get("HAMSA_TELEGRAM_BOT_TOKEN")),
    }


def main() -> None:
    for key, value in collect().items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
