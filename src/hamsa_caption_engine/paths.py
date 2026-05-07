from __future__ import annotations

import os
import shutil
from pathlib import Path


def project_root() -> Path:
    """Return the repository root, independent of the current working directory."""
    return Path(__file__).resolve().parents[2]


ROOT = project_root()
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
LOG_DIR = ROOT / "logs"
RECIPES_DIR = ROOT / "recipes"
MODIFIED_RECIPES_DIR = RECIPES_DIR / "modified"
BRAND_DIR = ROOT / "brand"
ASSETS_DIR = ROOT / "assets"
BRAND_ASSETS_DIR = ASSETS_DIR / "brand"
REMOTION_DIR = ROOT / "remotion"
TOOLS_FFMPEG_DIR = ROOT / "tools" / "ffmpeg"
TOOLS_FFMPEG_BIN = TOOLS_FFMPEG_DIR / "bin"


def ensure_project_dirs() -> None:
    for path in (INPUT_DIR, OUTPUT_DIR, LOG_DIR, RECIPES_DIR, MODIFIED_RECIPES_DIR, TOOLS_FFMPEG_DIR, BRAND_ASSETS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def _with_windows_suffix(path: Path, exe_name: str) -> Path:
    if path.name.lower() == exe_name.lower():
        return path
    return path / exe_name


def find_executable(name: str) -> str | None:
    """Find FFmpeg tools in local tools/bin, project root, then PATH."""
    candidates = [
        _with_windows_suffix(TOOLS_FFMPEG_BIN, f"{name}.exe"),
        ROOT / f"{name}.exe",
        TOOLS_FFMPEG_BIN / name,
        ROOT / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which(f"{name}.exe") or shutil.which(name)


def find_ffmpeg() -> str | None:
    return find_executable("ffmpeg")


def find_ffprobe() -> str | None:
    return find_executable("ffprobe")


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
