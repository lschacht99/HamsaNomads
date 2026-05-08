from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from telegram import Update
from telegram.error import TelegramError, TimedOut
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

from .content_analysis import analysis_summary, analyze_transcript, save_content_analysis
from .diagnostics import collect
from .director import analyze_project
from .paths import INPUT_DIR, LOG_DIR, MODIFIED_RECIPES_DIR, OUTPUT_DIR, RECIPES_DIR, ROOT, ensure_project_dirs, find_ffmpeg, load_dotenv
from .recipe_builder import apply_prompt_rules, recipe_from_prompt, recipe_from_transcript
from .recipe_schema import default_recipe, recipe_summary, save_recipe
from .remotion_renderer import remotion_installed

from .transcription import save_transcript, segments_from_transcript_text, transcribe_with_whisper

TOKEN_ENV_VAR = "HAMSA_TELEGRAM_BOT_TOKEN"
BOT_RENDER_LOG = LOG_DIR / "bot_render.log"
RENDER_LOCK = asyncio.Lock()
TELEGRAM_READ_TIMEOUT = 300
TELEGRAM_WRITE_TIMEOUT = 300
TELEGRAM_CONNECT_TIMEOUT = 30
TELEGRAM_POOL_TIMEOUT = 30


def startup_report() -> dict[str, str]:
    data = collect()
    for key, value in data.items():
        print(f"{key}: {value}")
    return data


def _format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= 1024
    return f"{size} B"


def _path_size(path: Path) -> int | None:
    return path.stat().st_size if path.exists() else None


def _append_bot_log(lines: list[str]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with BOT_RENDER_LOG.open("a", encoding="utf-8") as handle:
        handle.write("\n" + "\n".join(lines) + "\n")


def _log_upload_event(event: str, **details: Any) -> None:
    lines = [f"timestamp: {datetime.now().isoformat()}", f"upload event: {event}"]
    lines.extend(f"{key}: {value}" for key, value in details.items())
    _append_bot_log(lines)


def help_text() -> str:
    return """Send one or more videos. I analyze transcript, scenes, keyframes, visuals, and your prompt before building a content-aware edit recipe. Remotion is renderer only; FFmpeg remains available.

Commands:
/start /help
/new_project /clear - start over
/add_video - send videos any time
/videos - list current session clips
/auto - automatic Whisper transcription
/transcript - manual transcript mode
/ffmpeg - fast weak-PC mode
/remotion - premium animated mode
/autocut_on /autocut_off
/visual_none /visual_smol /visual_qwen
/transitions_on /transitions_off
/game /paris /clean
/analyze - transcribe/analyze latest video
/recipe /render /rerender
/modify your prompt
/local_output - show latest local output files
/status /cancel"""


def _state(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    data = context.user_data
    data.setdefault("renderer", "ffmpeg")
    data.setdefault("transcription_mode", "auto")
    data.setdefault("style", "hamsa-clean")
    data.setdefault("autocut", True)
    data.setdefault("transitions", False)
    data.setdefault("brand", "hamsa_nomads")
    data.setdefault("videos", [])
    data.setdefault("visual_ai", "none")
    data.setdefault("prompt", "")
    return data


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _state(context)
    await update.effective_message.reply_text(help_text())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(help_text())


async def auto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _state(context)["transcription_mode"] = "auto"
    await update.effective_message.reply_text("Automatic Whisper transcription enabled.")


async def transcript_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _state(context)["transcription_mode"] = "manual"
    await update.effective_message.reply_text("Manual transcript mode enabled. Send transcript text next.")


async def set_ffmpeg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    state["renderer"] = "ffmpeg"
    state["transitions"] = False
    await update.effective_message.reply_text("Renderer set to FFmpeg fast mode.")


async def set_remotion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    state["renderer"] = "remotion"
    state["transitions"] = True
    await update.effective_message.reply_text("Renderer set to Remotion premium mode. Run install_windows.bat and choose Remotion install if needed.")


async def autocut_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _state(context)["autocut"] = True
    await update.effective_message.reply_text("Auto-cut enabled: long pauses >0.7s are planned for compression to 0.25s.")


async def autocut_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _state(context)["autocut"] = False
    await update.effective_message.reply_text("Auto-cut disabled.")


async def transitions_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _state(context)["transitions"] = True
    await update.effective_message.reply_text("Transitions enabled. Remotion uses premium transitions; FFmpeg keeps them simple.")


async def transitions_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _state(context)["transitions"] = False
    await update.effective_message.reply_text("Transitions disabled.")


def _session_dir(user_id: int) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return INPUT_DIR / f"session_{user_id}_{stamp}"


async def new_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    state["videos"] = []
    state.pop("latest_video", None)
    state.pop("recipe", None)
    state.pop("recipe_path", None)
    state.pop("analysis", None)
    user_id = update.effective_user.id if update.effective_user else 0
    session_dir = _session_dir(user_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    state["session_dir"] = str(session_dir)
    await update.effective_message.reply_text("New Hamsa Nomads project started. Send one or more videos, then /analyze.")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await new_project(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("Current operation cancelled. Send /new_project to start over or /videos to inspect current clips.")


async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("Send one or more MP4/MOV/M4V files. I will save them into the current session.")


async def videos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    current = state.get("videos", [])
    if not current:
        await update.effective_message.reply_text("No videos in this session yet. Send a video, or use /new_project first.")
        return
    lines = ["Current session videos:"]
    for index, path in enumerate(current, start=1):
        video = Path(path)
        size = _format_bytes(_path_size(video) or 0) if video.exists() else "missing"
        lines.append(f"{index}. {video.name} ({size})")
    await update.effective_message.reply_text("\n".join(lines))


async def visual_none(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _state(context)["visual_ai"] = "none"
    await update.effective_message.reply_text("Visual AI disabled. Analysis will use transcript, scene metadata, filenames, prompt, and keyframe metadata.")


async def visual_smol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _state(context)["visual_ai"] = "smolvlm2"
    await update.effective_message.reply_text("SmolVLM2 selected. If it is not installed, I will continue with transcript-only/fallback visual analysis.")


async def visual_qwen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _state(context)["visual_ai"] = "qwen2_5_vl"
    await update.effective_message.reply_text("Qwen2.5-VL selected. If it is not installed, I will continue with transcript-only/fallback visual analysis.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    lines = [
        f"latest video path: {state.get('latest_video', 'none')}",
        f"session videos: {len(state.get('videos', []))}",
        f"visual AI mode: {state.get('visual_ai', 'none')}",
        f"selected renderer: {state['renderer']}",
        f"selected style: {state['style']}",
        f"transcription mode: {state['transcription_mode']}",
        f"auto-cut: {state['autocut']}",
        f"transitions: {state['transitions']}",
        f"hamsa_caption_engine imports: {bool(importlib.util.find_spec('hamsa_caption_engine'))}",
        f"faster_whisper imports: {bool(importlib.util.find_spec('faster_whisper'))}",
        f"ffmpeg found: {find_ffmpeg() or 'missing'}",
        f"node found: {shutil.which('node') or 'missing'}",
        f"node warning: {collect().get('node warning', 'none')}",
        f"npm found: {shutil.which('npm') or 'missing'}",
        f"Remotion project exists: {(ROOT / 'remotion').exists()}",
        f"logo exists: {(ROOT / 'assets' / 'brand' / 'hamsa-logo.png').exists()}",
        f"Python executable: {sys.executable}",
        f"project root: {ROOT}",
    ]
    await update.effective_message.reply_text("\n".join(lines))


async def local_output(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wanted = [
        OUTPUT_DIR / "final_video.mp4",
        OUTPUT_DIR / "final_video_telegram.mp4",
        OUTPUT_DIR / "edit_recipe.json",
        OUTPUT_DIR / "content_analysis.json",
        OUTPUT_DIR / "edit_decision_list.json",
        OUTPUT_DIR / "thumbnail.jpg",
    ]
    latest = OUTPUT_DIR / "final_video.mp4"
    lines = [f"Latest output is saved at: {latest.relative_to(ROOT)}", "Generated files:"]
    for path in wanted:
        if path.exists():
            lines.append(f"- {path.relative_to(ROOT)} ({_format_bytes(_path_size(path) or 0)})")
        else:
            lines.append(f"- {path.relative_to(ROOT)} (not created yet)")
    await update.effective_message.reply_text("\n".join(lines))


def video_attachment(update: Update):
    message = update.effective_message
    if message.video:
        return message.video
    if message.document:
        name = message.document.file_name or ""
        mime = message.document.mime_type or ""
        if name.lower().endswith((".mp4", ".mov", ".m4v")) or mime.startswith("video/"):
            return message.document
    return None



def _fallback_transcript(video_path: Path) -> dict[str, Any]:
    text = "Hamsa Nomads travel note"
    return {"mode": "fallback", "segments": segments_from_transcript_text(text), "text": text, "source_video": str(video_path)}


def _analyze_video_sync(video_path: Path, state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        transcript = transcribe_with_whisper(video_path)
    except RuntimeError as exc:
        transcript = _fallback_transcript(video_path)
        transcript["warning"] = str(exc)
    transcript_path = save_transcript(transcript, OUTPUT_DIR / "transcript.json")
    recipe, analysis = recipe_from_transcript(transcript, input_video=str(video_path), renderer=state.get("renderer"))
    recipe["auto_cut"]["enabled"] = bool(state.get("autocut", True))
    analysis_path = save_content_analysis(analysis, OUTPUT_DIR / "content_analysis.json")
    recipe_path = save_recipe(recipe, OUTPUT_DIR / "edit_recipe.json")
    _write_analysis_log(transcript, analysis, recipe_path, recipe.get("renderer", "ffmpeg"))
    state["transcript_path"] = str(transcript_path)
    state["content_analysis_path"] = str(analysis_path)
    state["recipe_path"] = str(recipe_path)
    state["analysis"] = analysis
    state["recipe"] = recipe
    state["style"] = recipe["style"]["name"]
    state["renderer"] = recipe.get("renderer", state.get("renderer", "ffmpeg"))
    return transcript, analysis, recipe


def _write_analysis_log(transcript: dict[str, Any], analysis: dict[str, Any], recipe_path: Path, renderer: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        f"timestamp: {datetime.now().isoformat()}",
        f"analysis transcript length: {analysis.get('transcript_length', len(transcript.get('text', '')))}",
        f"analysis caption segments: {analysis.get('caption_segment_count', len(transcript.get('segments', [])))}",
        f"detected hook: {analysis.get('hook', '')}",
        f"detected keywords: {analysis.get('caption_keywords', [])}",
        f"chosen style: {analysis.get('recommended_style', '')}",
        f"chosen overlays: {[overlay.get('type') for overlay in analysis.get('recommended_overlays', [])]}",
        f"recipe path: {recipe_path}",
        f"renderer: {renderer}",
    ]
    with BOT_RENDER_LOG.open("a", encoding="utf-8") as handle:
        handle.write("\n" + "\n".join(lines) + "\n")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    attachment = video_attachment(update)
    if not attachment:
        await update.effective_message.reply_text("Please send a real MP4, MOV, or M4V video.")
        return
    await update.effective_message.reply_text("Video received. Saving file…")
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    user_id = update.effective_user.id if update.effective_user else 0
    if not state.get("session_dir"):
        session_dir = _session_dir(user_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        state["session_dir"] = str(session_dir)
    session_dir = Path(state["session_dir"])
    session_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = getattr(attachment, "file_name", None) or f"telegram_{user_id}_{stamp}.mp4"
    suffix = Path(original_name).suffix.lower() or ".mp4"
    video_path = session_dir / f"video_{len(state.get('videos', [])) + 1:03d}_{stamp}{suffix}"
    telegram_file = await attachment.get_file()
    await telegram_file.download_to_drive(custom_path=video_path)
    state.setdefault("videos", []).append(str(video_path))
    state["latest_video"] = str(video_path)
    state.pop("recipe", None)
    await update.effective_message.reply_text(f"File saved. Send more videos, or send /analyze. Session now has {len(state['videos'])} video(s).")


def _current_recipe(state: dict[str, Any]) -> dict[str, Any]:
    video = state.get("latest_video", "")
    recipe = state.get("recipe") or default_recipe(input_video=video, renderer=state["renderer"], style=state["style"])
    recipe["renderer"] = state["renderer"]
    recipe["style"]["name"] = state["style"]
    recipe["auto_cut"]["enabled"] = bool(state["autocut"])
    if state["transitions"] and not recipe.get("transitions"):
        recipe["transitions"] = [{"type": "route_line_wipe" if state["renderer"] == "remotion" else "quick_fade", "start_sec": 1.5, "duration_sec": 0.35}]
    return recipe


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    text = (update.effective_message.text or "").strip()
    if not text:
        return
    if state["transcription_mode"] == "manual":
        transcript_path = OUTPUT_DIR / "transcript.txt"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(text + "\n", encoding="utf-8")
        state["transcript_path"] = str(transcript_path)
        state["transcription_mode"] = "manual_ready"
        await update.effective_message.reply_text("Transcript saved. Send /render to render, or send a prompt to update style first.")
        return
    state["prompt"] = text
    base = _current_recipe(state) if state.get("recipe") else recipe_from_prompt(text, input_video=state.get("latest_video", ""), renderer=state["renderer"], style=state["style"])
    recipe = apply_prompt_rules(base, text, requested_renderer=state.get("renderer"))
    recipe["auto_cut"]["enabled"] = bool(state["autocut"])
    state["renderer"] = recipe["renderer"]
    state["style"] = recipe["style"]["name"]
    state["recipe"] = recipe
    path = save_recipe(recipe, OUTPUT_DIR / "edit_recipe.json")
    state["recipe_path"] = str(path)
    await update.effective_message.reply_text(recipe_summary(recipe) + "\n\nSend /render to render, or /modify to change it.")


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    video_paths = state.get("videos") or ([state["latest_video"]] if state.get("latest_video") else [])
    if not video_paths:
        await update.effective_message.reply_text("I need a video first. Send one or more MP4/MOV/M4V videos.")
        return

    def progress(message: str) -> None:
        _append_bot_log([f"timestamp: {datetime.now().isoformat()}", f"analysis progress: {message}"])

    for message in ["Normalizing video", "Transcribing", "Detecting scenes", "Extracting keyframes", "Running visual analysis", "Building edit plan"]:
        await update.effective_message.reply_text(message + "…")
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                analyze_project,
                video_paths,
                OUTPUT_DIR,
                prompt=state.get("prompt", ""),
                renderer=state.get("renderer", "ffmpeg"),
                auto_cut=bool(state.get("autocut", True)),
                visual_ai=state.get("visual_ai", "none"),
                style=state.get("style", "hamsa-clean"),
                progress=progress,
            ),
            timeout=600,
        )
    except TimeoutError:
        await update.effective_message.reply_text("Analysis timed out after 10 minutes. Try fewer/shorter clips or /visual_none.")
        return
    state["analysis"] = result["content_analysis"]
    state["recipe"] = result["recipe"]
    state["recipe_path"] = str(result["recipe_path"])
    state["renderer"] = result["recipe"].get("renderer", state.get("renderer", "ffmpeg"))
    state["style"] = result["recipe"].get("style", {}).get("name", state.get("style", "hamsa-clean"))
    await update.effective_message.reply_text("Recipe ready.")
    analysis = result["content_analysis"]
    overlays = analysis.get("recommended_overlays", [])
    summary = "\n".join([
        "Analysis complete:",
        f"- Topic: {analysis.get('main_topic', 'Unknown')}",
        f"- Hook: {analysis.get('strongest_hook') or analysis.get('hook', '')}",
        f"- Style: {analysis.get('recommended_style', 'hamsa-clean')}",
        f"- Clips selected: {analysis.get('selected_clip_count', 0)}",
        f"- Overlays: {', '.join(o.get('type', 'overlay') for o in overlays) if overlays else 'none'}",
        f"- CTA: {analysis.get('recommended_cta', '')}",
        *(f"- Warning: {warning}" for warning in analysis.get("warnings", [])),
        "",
        "Send /recipe to inspect, /modify to change, or /render to render.",
    ])
    await update.effective_message.reply_text(summary)


async def style_and_render(update: Update, context: ContextTypes.DEFAULT_TYPE, style: str) -> None:
    state = _state(context)
    state["style"] = style
    state["recipe"] = _current_recipe(state)
    await update.effective_message.reply_text(f"Style set to {style}. Send /analyze to rebuild the content-aware recipe, or /render if a recipe already exists.")


async def game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await style_and_render(update, context, "game")


async def paris(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await style_and_render(update, context, "paris-tip")


async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await style_and_render(update, context, "hamsa-clean")


async def recipe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    recipe = _current_recipe(_state(context))
    await update.effective_message.reply_text(recipe_summary(recipe))


def _render_command_for_state(state: dict[str, Any], recipe_path: Path) -> list[str]:
    recipe = state.get("recipe") or {}
    video_path = recipe.get("input_video", {}).get("src") or state.get("latest_video")
    timeout_flag = "--auto-cut" if state.get("autocut") else "--no-auto-cut"
    cmd = [sys.executable, "-m", "hamsa_caption_engine", "--input", video_path, "--output-dir", "output", "--recipe", str(recipe_path), "--renderer", state["renderer"], timeout_flag]
    if state.get("transcript_path"):
        cmd.extend(["--transcript", state["transcript_path"]])
    return cmd


def _last_useful_error(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[-10:]) or "No stderr/stdout captured."


def _write_render_log(state: dict[str, Any], cmd: list[str], proc: subprocess.CompletedProcess[str] | None, recipe_path: Path) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        f"timestamp: {datetime.now().isoformat()}",
        f"Python executable: {sys.executable}",
        f"Python version: {sys.version.replace(chr(10), ' ')}",
        f"current working directory: {Path.cwd()}",
        f"project root: {ROOT}",
        f"video path: {state.get('latest_video')}",
        f"renderer: {state.get('renderer')}",
        f"style: {state.get('style')}",
        f"transcription mode: {state.get('transcription_mode')}",
        f"recipe path: {recipe_path}",
        f"exact subprocess command as a list: {cmd!r}",
        f"ffmpeg found/missing: {find_ffmpeg() or 'missing'}",
        f"faster_whisper import yes/no: {bool(importlib.util.find_spec('faster_whisper'))}",
        f"node found/missing: {shutil.which('node') or 'missing'}",
        f"npm found/missing: {shutil.which('npm') or 'missing'}",
        f"remotion installed yes/no: {remotion_installed()}",
    ]
    if proc:
        lines.extend(["stdout:", proc.stdout or "", "stderr:", proc.stderr or "", f"return code: {proc.returncode}"])
    _append_bot_log(lines)


def _make_telegram_video_copy(final: Path) -> Path:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg missing, so the Telegram-friendly upload copy could not be created.")
    telegram_copy = final.with_name("final_video_telegram.mp4")
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(final),
        "-vf",
        "scale=720:-2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-movflags",
        "+faststart",
        str(telegram_copy),
    ]
    _log_upload_event("prepare_telegram_copy_started", source=final, destination=telegram_copy, command=cmd)
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        _log_upload_event(
            "prepare_telegram_copy_failed",
            source=final,
            destination=telegram_copy,
            return_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )
        raise RuntimeError("Telegram-friendly video compression failed. See logs/bot_render.log.")
    _log_upload_event(
        "prepare_telegram_copy_success",
        source=final,
        source_size=_format_bytes(_path_size(final) or 0),
        destination=telegram_copy,
        destination_size=_format_bytes(_path_size(telegram_copy) or 0),
    )
    return telegram_copy


async def _reply_with_timeouts(send_method, **kwargs: Any) -> Any:
    return await send_method(
        **kwargs,
        read_timeout=TELEGRAM_READ_TIMEOUT,
        write_timeout=TELEGRAM_WRITE_TIMEOUT,
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        pool_timeout=TELEGRAM_POOL_TIMEOUT,
    )


async def _send_video_with_document_fallback(update: Update, final: Path, upload_file: Path) -> bool:
    message = update.effective_message
    upload_size = _path_size(upload_file) or 0
    _log_upload_event("upload_started", upload_file=upload_file, upload_file_size=_format_bytes(upload_size), upload_type="video")
    try:
        with upload_file.open("rb") as handle:
            await _reply_with_timeouts(message.reply_video, video=handle, caption=upload_file.name)
        _log_upload_event("upload_success", upload_file=upload_file, upload_file_size=_format_bytes(upload_size), upload_type="video")
        return True
    except TimedOut as exc:
        _log_upload_event("upload_failure", upload_file=upload_file, upload_file_size=_format_bytes(upload_size), upload_type="video", error=repr(exc))
        await message.reply_text(f"Render complete, but Telegram upload timed out. The file was saved locally at: {final.relative_to(ROOT)}")
    except TelegramError as exc:
        _log_upload_event("upload_failure", upload_file=upload_file, upload_file_size=_format_bytes(upload_size), upload_type="video", error=repr(exc))
        await message.reply_text(f"Render complete, but Telegram video upload failed. The file was saved locally at: {final.relative_to(ROOT)}")

    _log_upload_event("fallback_attempt_started", upload_file=upload_file, upload_file_size=_format_bytes(upload_size), upload_type="document")
    try:
        with upload_file.open("rb") as handle:
            await _reply_with_timeouts(message.reply_document, document=handle, filename=upload_file.name, caption=upload_file.name)
        _log_upload_event("fallback_attempt_success", upload_file=upload_file, upload_file_size=_format_bytes(upload_size), upload_type="document")
        return True
    except TelegramError as exc:
        _log_upload_event("fallback_attempt_failure", upload_file=upload_file, upload_file_size=_format_bytes(upload_size), upload_type="document", error=repr(exc))
        await message.reply_text(f"Telegram upload failed, but the video exists locally at {final.relative_to(ROOT)}.")
        return False


async def _send_render_artifacts(update: Update, thumb: Path, out_recipe: Path) -> None:
    message = update.effective_message
    if thumb.exists():
        try:
            with thumb.open("rb") as handle:
                await _reply_with_timeouts(message.reply_photo, photo=handle, caption="thumbnail.jpg")
            _log_upload_event("artifact_upload_success", artifact=thumb, artifact_size=_format_bytes(_path_size(thumb) or 0))
        except TelegramError as exc:
            _log_upload_event("artifact_upload_failure", artifact=thumb, artifact_size=_format_bytes(_path_size(thumb) or 0), error=repr(exc))
    if out_recipe.exists():
        try:
            with out_recipe.open("rb") as handle:
                await _reply_with_timeouts(message.reply_document, document=handle, filename="edit_recipe.json")
            _log_upload_event("artifact_upload_success", artifact=out_recipe, artifact_size=_format_bytes(_path_size(out_recipe) or 0))
        except TelegramError as exc:
            _log_upload_event("artifact_upload_failure", artifact=out_recipe, artifact_size=_format_bytes(_path_size(out_recipe) or 0), error=repr(exc))


async def render_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    if not state.get("latest_video"):
        await update.effective_message.reply_text("I need a video first. Send an MP4 video.")
        return
    async with RENDER_LOCK:
        recipe = _current_recipe(state)
        recipe_path = save_recipe(recipe, OUTPUT_DIR / "edit_recipe.json")
        cmd = _render_command_for_state(state, recipe_path)
        await update.effective_message.reply_text("Rendering…")
        render_timeout = 900 if state.get("renderer") == "remotion" else 600
        try:
            proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=render_timeout)
        except subprocess.TimeoutExpired as exc:
            _write_render_log(state, cmd, None, recipe_path)
            await update.effective_message.reply_text(f"Render timed out after {render_timeout // 60} minutes. This is a render timeout, not an upload failure.")
            return
        _write_render_log(state, cmd, proc, recipe_path)
        if proc.returncode != 0:
            await update.effective_message.reply_text("Render failed. Full logs were saved to logs/bot_render.log.\n\nLast useful error:\n" + _last_useful_error((proc.stdout or "") + "\n" + (proc.stderr or "")))
            return
        final = OUTPUT_DIR / "final_video.mp4"
        thumb = OUTPUT_DIR / "thumbnail.jpg"
        out_recipe = OUTPUT_DIR / "edit_recipe.json"
        if not final.exists():
            await update.effective_message.reply_text("Render finished, but output/final_video.mp4 was not found. Full logs were saved to logs/bot_render.log.")
            return
        final_size = _path_size(final) or 0
        _log_upload_event("render_complete", final_video=final, final_video_size=_format_bytes(final_size))
        await update.effective_message.reply_text("Render complete.")
        await update.effective_message.reply_text("Compressing Telegram copy…")
        await update.effective_message.reply_text("Preparing Telegram-friendly video...")
        try:
            telegram_copy = await asyncio.to_thread(_make_telegram_video_copy, final)
        except RuntimeError as exc:
            await update.effective_message.reply_text(f"Render complete, but Telegram-friendly compression failed. The file was saved locally at: {final.relative_to(ROOT)}\n{exc}")
            _log_upload_event("upload_skipped", reason=repr(exc), final_video=final, final_video_size=_format_bytes(final_size))
            await _send_render_artifacts(update, thumb, out_recipe)
            return
        telegram_size = _path_size(telegram_copy) or 0
        _log_upload_event(
            "upload_file_selected",
            final_video=final,
            final_video_size=_format_bytes(final_size),
            telegram_video=telegram_copy,
            telegram_video_size=_format_bytes(telegram_size),
            uploading=telegram_copy,
        )
        await update.effective_message.reply_text("Uploading video to Telegram...")
        video_sent = await _send_video_with_document_fallback(update, final, telegram_copy)
        await _send_render_artifacts(update, thumb, out_recipe)
        if video_sent:
            await update.effective_message.reply_text("Rendered and sent final_video_telegram.mp4, thumbnail.jpg, and edit_recipe.json. Original saved locally as output/final_video.mp4.\n" + recipe_summary(recipe))
        else:
            await update.effective_message.reply_text("thumbnail.jpg and edit_recipe.json were sent if available. Original video remains saved locally as output/final_video.mp4.\n" + recipe_summary(recipe))


async def rerender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await render_command(update, context)


async def modify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    prompt = " ".join(context.args) if context.args else ""
    if not prompt:
        await update.effective_message.reply_text("Use /modify followed by your change prompt.")
        return
    current = _current_recipe(state)
    MODIFIED_RECIPES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_recipe(current, MODIFIED_RECIPES_DIR / f"backup_{stamp}.json")
    modified = apply_prompt_rules(current, prompt)
    state["renderer"] = modified["renderer"]
    state["style"] = modified["style"]["name"]
    state["recipe"] = modified
    modified_path = save_recipe(modified, MODIFIED_RECIPES_DIR / f"edit_recipe_modified_{stamp}.json")
    state["recipe_path"] = str(modified_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "change_summary.txt").write_text(f"Modified recipe with prompt: {prompt}\n{recipe_summary(modified)}\n", encoding="utf-8")
    await update.effective_message.reply_text("Recipe modified and saved. Rendering again...\n" + recipe_summary(modified))
    await render_command(update, context)


def main() -> None:
    ensure_project_dirs()
    load_dotenv()
    data = startup_report()
    if data.get("project package import") == "no":
        raise SystemExit("Project package is not installed. Run install_windows.bat first.")
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise SystemExit("Missing HAMSA_TELEGRAM_BOT_TOKEN. Add it to .env.")
    request = HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=TELEGRAM_READ_TIMEOUT,
        write_timeout=TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=TELEGRAM_POOL_TIMEOUT,
    )
    app = ApplicationBuilder().token(token).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new_project", new_project))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("add_video", add_video))
    app.add_handler(CommandHandler("videos", videos))
    app.add_handler(CommandHandler("auto", auto))
    app.add_handler(CommandHandler("transcript", transcript_mode))
    app.add_handler(CommandHandler("ffmpeg", set_ffmpeg))
    app.add_handler(CommandHandler("remotion", set_remotion))
    app.add_handler(CommandHandler("autocut_on", autocut_on))
    app.add_handler(CommandHandler("autocut_off", autocut_off))
    app.add_handler(CommandHandler("visual_none", visual_none))
    app.add_handler(CommandHandler("visual_smol", visual_smol))
    app.add_handler(CommandHandler("visual_qwen", visual_qwen))
    app.add_handler(CommandHandler("transitions_on", transitions_on))
    app.add_handler(CommandHandler("transitions_off", transitions_off))
    app.add_handler(CommandHandler("game", game))
    app.add_handler(CommandHandler("paris", paris))
    app.add_handler(CommandHandler("clean", clean))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("recipe", recipe_command))
    app.add_handler(CommandHandler("render", render_command))
    app.add_handler(CommandHandler("rerender", rerender))
    app.add_handler(CommandHandler("modify", modify))
    app.add_handler(CommandHandler("local_output", local_output))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO | filters.Document.ALL, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
