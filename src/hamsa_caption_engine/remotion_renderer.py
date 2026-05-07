from __future__ import annotations

import shutil
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

from .paths import LOG_DIR, REMOTION_DIR, ROOT, find_executable, find_ffmpeg
from .recipe_schema import save_recipe, validate_recipe

REMOTION_DEPS_MISSING = "Remotion dependencies are not installed. Run install_windows.bat and choose Remotion install, or run npm install inside the remotion folder."
REMOTION_MISSING = "Remotion is not installed. Run install_windows.bat and choose Remotion install, or run npm install inside remotion/."
BOT_RENDER_LOG = LOG_DIR / "bot_render.log"
RUNTIME_DIR = REMOTION_DIR / "public" / "runtime"
RUNTIME_VIDEO_STATIC = "runtime/input.mp4"
RUNTIME_LOGO_STATIC = "runtime/hamsa-logo.png"
RUNTIME_RECIPE_STATIC = "runtime/edit_recipe.json"
ERROR_KEYWORDS = (
    "Error:",
    "TypeError:",
    "ReferenceError:",
    "SyntaxError:",
    "Cannot find module",
    "ENOENT",
    "MEDIA_ELEMENT_ERROR",
    "ERR_UNKNOWN_URL_SCHEME",
    "failed",
    "renderMedia",
    "delayRender",
    "lineNumber",
    "chunk",
)


class RemotionRenderError(RuntimeError):
    """Raised when Remotion exits unsuccessfully, with useful Node output."""


def remotion_installed() -> bool:
    return REMOTION_DIR.exists() and (REMOTION_DIR / "node_modules").exists()


def _run_version(executable: str | None, flag: str = "--version") -> str:
    if not executable:
        return "missing"
    try:
        proc = subprocess.run([executable, flag], capture_output=True, text=True)
    except OSError as exc:
        return f"error: {exc}"
    return (proc.stdout or proc.stderr or "unknown").strip().splitlines()[0]


def node_version_warning(node_version: str) -> str:
    clean = node_version.lower().replace("v", "").strip()
    major_text = clean.split(".", 1)[0]
    if major_text.isdigit() and int(major_text) >= 24:
        return "Node 24 detected. If Remotion crashes, try Node LTS 22 or 20."
    return ""


def _extract_meaningful_error(*chunks: str) -> str:
    text = "\n".join(chunk for chunk in chunks if chunk)
    lines = [line.rstrip() for line in text.splitlines()]
    meaningful_indexes = [
        index for index, line in enumerate(lines)
        if any(keyword.lower() in line.lower() for keyword in ERROR_KEYWORDS)
    ]
    if meaningful_indexes:
        selected: list[str] = []
        for index in meaningful_indexes[:6]:
            start = max(0, index - 2)
            end = min(len(lines), index + 5)
            selected.extend(lines[start:end])
            selected.append("---")
        compact = [line for line in selected if line.strip()]
        return "\n".join(compact[-28:])
    compact = [line for line in lines if line.strip()]
    return "\n".join(compact[-14:]) or "No Remotion stdout/stderr was captured."


def _append_remotion_log(
    *,
    cmd: list[str],
    node_path: str | None,
    node_version: str,
    npm_path: str | None,
    npm_version: str,
    render_script: Path,
    original_input_path: Path,
    staged_video_path: Path,
    source_logo_path: Path,
    staged_logo_path: Path,
    runtime_recipe_path: Path,
    output_path: Path,
    ffmpeg_path: str | None,
    stage_proc: subprocess.CompletedProcess[str] | None = None,
    proc: subprocess.CompletedProcess[str] | None = None,
    error: str | None = None,
) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    warning = node_version_warning(node_version)
    lines = [
        "Remotion renderer log",
        f"node path: {node_path or 'missing'}",
        f"node version: {node_version}",
        f"node warning: {warning or 'none'}",
        f"npm path: {npm_path or 'missing'}",
        f"npm version: {npm_version}",
        f"ffmpeg path: {ffmpeg_path or 'missing'}",
        f"remotion folder: {REMOTION_DIR}",
        f"render.mjs path: {render_script}",
        f"original input path: {original_input_path}",
        f"staged video path: {staged_video_path}",
        f"staged logo path: {staged_logo_path}",
        f"runtime recipe path: {runtime_recipe_path}",
        f"final output path: {output_path}",
        f"exact command: {cmd!r}",
        f"cwd: {REMOTION_DIR}",
        f"assets/brand/hamsa-logo.png exists: {source_logo_path.exists()}",
        f"remotion/public/runtime/input.mp4 exists: {staged_video_path.exists()}",
    ]
    if error:
        lines.extend(["error:", error])
    if stage_proc:
        lines.extend([
            "staging ffmpeg stdout:",
            stage_proc.stdout or "",
            "staging ffmpeg stderr:",
            stage_proc.stderr or "",
            f"staging ffmpeg return code: {stage_proc.returncode}",
        ])
    if proc:
        lines.extend([
            "stdout:",
            proc.stdout or "",
            "stderr:",
            proc.stderr or "",
            f"return code: {proc.returncode}",
        ])
    with BOT_RENDER_LOG.open("a", encoding="utf-8") as handle:
        handle.write("\n" + "\n".join(lines) + "\n")


def _preflight(input_path: Path, node: str | None, ffmpeg: str | None, render_script: Path) -> str | None:
    if not node:
        return REMOTION_MISSING
    if not render_script.exists():
        return f"Remotion render script is missing: {render_script}"
    if not (REMOTION_DIR / "node_modules").exists():
        return REMOTION_DEPS_MISSING
    if not ffmpeg:
        return "FFmpeg is required to stage browser-safe Remotion media. Run download_ffmpeg.bat or put ffmpeg.exe inside tools\\ffmpeg\\bin\\."
    if not input_path.exists():
        return f"Input video does not exist: {input_path}"
    return None


def _stage_video(ffmpeg: str, input_path: Path, staged_video_path: Path) -> subprocess.CompletedProcess[str]:
    staged_video_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        "-ac",
        "2",
        str(staged_video_path),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def _stage_logo(source_logo_path: Path, staged_logo_path: Path) -> bool:
    staged_logo_path.parent.mkdir(parents=True, exist_ok=True)
    if staged_logo_path.exists():
        staged_logo_path.unlink()
    if not source_logo_path.exists():
        return False
    shutil.copy2(source_logo_path, staged_logo_path)
    return True


def _write_runtime_recipe(recipe: dict[str, Any], runtime_recipe_path: Path, logo_was_staged: bool) -> Path:
    runtime_recipe = validate_recipe(deepcopy(recipe))
    runtime_recipe.setdefault("input_video", {})["src"] = RUNTIME_VIDEO_STATIC
    runtime_recipe.setdefault("logo", {}).update({
        "enabled": bool(runtime_recipe.get("logo", {}).get("enabled", True)),
        "watermark": bool(runtime_recipe.get("logo", {}).get("watermark", False)),
        "position": runtime_recipe.get("logo", {}).get("position", "top_center"),
        "path": RUNTIME_LOGO_STATIC if logo_was_staged else "",
        "fallback_text": runtime_recipe.get("logo", {}).get("fallback_text", "Hamsa Nomads"),
    })
    runtime_recipe_path.parent.mkdir(parents=True, exist_ok=True)
    return save_recipe(runtime_recipe, runtime_recipe_path)


def render_remotion(video_path: str | Path, output_dir: str | Path, recipe: dict[str, Any]) -> dict[str, Path]:
    node = find_executable("node")
    npm = find_executable("npm")
    ffmpeg = find_ffmpeg()
    node_version = _run_version(node)
    npm_version = _run_version(npm)
    input_path = Path(video_path).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    recipe = validate_recipe(recipe)
    recipe["renderer"] = "remotion"
    output_recipe_path = save_recipe(recipe, (out / "edit_recipe.json").resolve()).resolve()
    output_path = (out / "final_video.mp4").resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_path = (out / "thumbnail.jpg").resolve()
    render_script = (REMOTION_DIR / "render.mjs").resolve()
    staged_video_path = (RUNTIME_DIR / "input.mp4").resolve()
    source_logo_path = (ROOT / "assets" / "brand" / "hamsa-logo.png").resolve()
    staged_logo_path = (RUNTIME_DIR / "hamsa-logo.png").resolve()
    runtime_recipe_path = (RUNTIME_DIR / "edit_recipe.json").resolve()

    cmd = [
        str(node) if node else "node",
        str(render_script),
        "--input",
        str(staged_video_path),
        "--recipe",
        str(runtime_recipe_path),
        "--output",
        str(output_path),
    ]

    preflight_error = _preflight(input_path, node, ffmpeg, render_script)
    if preflight_error:
        _append_remotion_log(cmd=cmd, node_path=node, node_version=node_version, npm_path=npm, npm_version=npm_version, render_script=render_script, original_input_path=input_path, staged_video_path=staged_video_path, source_logo_path=source_logo_path, staged_logo_path=staged_logo_path, runtime_recipe_path=runtime_recipe_path, output_path=output_path, ffmpeg_path=ffmpeg, error=preflight_error)
        raise RemotionRenderError(preflight_error)

    assert ffmpeg is not None
    stage_proc = _stage_video(ffmpeg, input_path, staged_video_path)
    if stage_proc.returncode != 0:
        _append_remotion_log(cmd=cmd, node_path=node, node_version=node_version, npm_path=npm, npm_version=npm_version, render_script=render_script, original_input_path=input_path, staged_video_path=staged_video_path, source_logo_path=source_logo_path, staged_logo_path=staged_logo_path, runtime_recipe_path=runtime_recipe_path, output_path=output_path, ffmpeg_path=ffmpeg, stage_proc=stage_proc, error="FFmpeg failed while staging Remotion browser-safe input.mp4")
        useful = _extract_meaningful_error(stage_proc.stdout or "", stage_proc.stderr or "")
        raise RemotionRenderError(f"Failed to stage browser-safe Remotion input.mp4:\n{useful}")

    logo_was_staged = _stage_logo(source_logo_path, staged_logo_path)
    runtime_recipe_path = _write_runtime_recipe(recipe, runtime_recipe_path, logo_was_staged).resolve()

    proc = subprocess.run(
        cmd,
        cwd=str(REMOTION_DIR),
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        _append_remotion_log(cmd=cmd, node_path=node, node_version=node_version, npm_path=npm, npm_version=npm_version, render_script=render_script, original_input_path=input_path, staged_video_path=staged_video_path, source_logo_path=source_logo_path, staged_logo_path=staged_logo_path, runtime_recipe_path=runtime_recipe_path, output_path=output_path, ffmpeg_path=ffmpeg, stage_proc=stage_proc, proc=proc)
        useful = _extract_meaningful_error(proc.stdout or "", proc.stderr or "")
        warning = node_version_warning(node_version)
        warning_text = f"\n\n{warning}" if warning else ""
        raise RemotionRenderError(f"Remotion render failed. Useful Node/Remotion error:\n{useful}{warning_text}")

    warning = node_version_warning(node_version)
    if warning:
        _append_remotion_log(cmd=cmd, node_path=node, node_version=node_version, npm_path=npm, npm_version=npm_version, render_script=render_script, original_input_path=input_path, staged_video_path=staged_video_path, source_logo_path=source_logo_path, staged_logo_path=staged_logo_path, runtime_recipe_path=runtime_recipe_path, output_path=output_path, ffmpeg_path=ffmpeg, stage_proc=stage_proc, proc=proc, error=warning)
    if not thumbnail_path.exists():
        # Remotion script renders still when supported; absence is not fatal.
        thumbnail_path.touch()
    return {"final_video": output_path, "thumbnail": thumbnail_path, "recipe": output_recipe_path}
