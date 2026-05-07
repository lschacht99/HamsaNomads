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
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .diagnostics import collect
from .paths import INPUT_DIR, LOG_DIR, MODIFIED_RECIPES_DIR, OUTPUT_DIR, RECIPES_DIR, ROOT, ensure_project_dirs, find_ffmpeg, load_dotenv
from .recipe_builder import apply_prompt_rules, recipe_from_prompt
from .recipe_schema import default_recipe, recipe_summary, save_recipe
from .remotion_renderer import remotion_installed

TOKEN_ENV_VAR = "HAMSA_TELEGRAM_BOT_TOKEN"
BOT_RENDER_LOG = LOG_DIR / "bot_render.log"
RENDER_LOCK = asyncio.Lock()


def startup_report() -> dict[str, str]:
    data = collect()
    for key, value in data.items():
        print(f"{key}: {value}")
    return data


def help_text() -> str:
    return """Send me an MP4 video. Then send a prompt or choose /game /paris /clean. Use /ffmpeg for fast mode or /remotion for premium mode.

Commands:
/start /help
/auto - automatic Whisper transcription
/transcript - manual transcript mode
/ffmpeg - fast weak-PC mode
/remotion - premium animated mode
/autocut_on /autocut_off
/transitions_on /transitions_off
/game /paris /clean
/recipe /render
/modify your prompt
/status"""


def _state(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    data = context.user_data
    data.setdefault("renderer", "ffmpeg")
    data.setdefault("transcription_mode", "auto")
    data.setdefault("style", "hamsa-clean")
    data.setdefault("autocut", True)
    data.setdefault("transitions", False)
    data.setdefault("brand", "hamsa_nomads")
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


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    lines = [
        f"latest video path: {state.get('latest_video', 'none')}",
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


def video_attachment(update: Update):
    message = update.effective_message
    if message.video:
        return message.video
    if message.document:
        name = message.document.file_name or ""
        mime = message.document.mime_type or ""
        if name.lower().endswith(".mp4") or mime.startswith("video/"):
            return message.document
    return None


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    attachment = video_attachment(update)
    if not attachment:
        await update.effective_message.reply_text("Please send a real MP4 video.")
        return
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    user_id = update.effective_user.id if update.effective_user else 0
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = INPUT_DIR / f"telegram_{user_id}_{stamp}.mp4"
    telegram_file = await attachment.get_file()
    await telegram_file.download_to_drive(custom_path=video_path)
    state["latest_video"] = str(video_path)
    state["recipe"] = default_recipe(input_video=str(video_path), renderer=state["renderer"], style=state["style"])
    state["recipe"]["auto_cut"]["enabled"] = bool(state["autocut"])
    await update.effective_message.reply_text("Video received. Send a prompt, or choose /game /paris /clean.\nCurrent renderer: FFmpeg. Use /remotion for premium animated mode.")


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
    recipe = recipe_from_prompt(text, input_video=state.get("latest_video", ""), renderer=state["renderer"], style=state["style"])
    recipe["auto_cut"]["enabled"] = bool(state["autocut"])
    state["renderer"] = recipe["renderer"]
    state["style"] = recipe["style"]["name"]
    state["recipe"] = recipe
    path = save_recipe(recipe, OUTPUT_DIR / "edit_recipe.json")
    state["recipe_path"] = str(path)
    await update.effective_message.reply_text(recipe_summary(recipe) + "\n\nSend /render to render, or /modify to change it.")


async def style_and_render(update: Update, context: ContextTypes.DEFAULT_TYPE, style: str) -> None:
    state = _state(context)
    state["style"] = style
    state["recipe"] = _current_recipe(state)
    await update.effective_message.reply_text(f"Style set to {style}. Rendering latest video...")
    await render_command(update, context)


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
    video_path = state.get("latest_video")
    if state["renderer"] == "remotion":
        return [sys.executable, "-m", "hamsa_caption_engine", "--input", video_path, "--output-dir", "output", "--recipe", str(recipe_path), "--renderer", "remotion"]
    cmd = [sys.executable, "-m", "hamsa_caption_engine", "--input", video_path, "--output-dir", "output", "--style", state["style"], "--thumbnail-at", "00:00:01", "--renderer", "ffmpeg"]
    if state.get("transcript_path"):
        cmd.extend(["--transcript", state["transcript_path"]])
    if state.get("autocut"):
        cmd.append("--auto-cut")
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
    with BOT_RENDER_LOG.open("a", encoding="utf-8") as handle:
        handle.write("\n" + "\n".join(lines) + "\n")


async def render_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    if not state.get("latest_video"):
        await update.effective_message.reply_text("I need a video first. Send an MP4 video.")
        return
    async with RENDER_LOCK:
        recipe = _current_recipe(state)
        recipe_path = save_recipe(recipe, OUTPUT_DIR / "edit_recipe.json")
        cmd = _render_command_for_state(state, recipe_path)
        await update.effective_message.reply_text("Rendering locally now. FFmpeg is default and Remotion is optional.")
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        _write_render_log(state, cmd, proc, recipe_path)
        if proc.returncode != 0:
            await update.effective_message.reply_text("Render failed. Full logs were saved to logs/bot_render.log.\n\nLast useful error:\n" + _last_useful_error((proc.stdout or "") + "\n" + (proc.stderr or "")))
            return
        final = OUTPUT_DIR / "final_video.mp4"
        thumb = OUTPUT_DIR / "thumbnail.jpg"
        out_recipe = OUTPUT_DIR / "edit_recipe.json"
        if final.exists():
            await update.effective_message.reply_video(video=final.open("rb"), caption="final_video.mp4")
        if thumb.exists():
            await update.effective_message.reply_photo(photo=thumb.open("rb"), caption="thumbnail.jpg")
        if out_recipe.exists():
            await update.effective_message.reply_document(document=out_recipe.open("rb"), filename="edit_recipe.json")
        await update.effective_message.reply_text("Rendered and sent final_video.mp4, thumbnail.jpg, and edit_recipe.json.\n" + recipe_summary(recipe))


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
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("auto", auto))
    app.add_handler(CommandHandler("transcript", transcript_mode))
    app.add_handler(CommandHandler("ffmpeg", set_ffmpeg))
    app.add_handler(CommandHandler("remotion", set_remotion))
    app.add_handler(CommandHandler("autocut_on", autocut_on))
    app.add_handler(CommandHandler("autocut_off", autocut_off))
    app.add_handler(CommandHandler("transitions_on", transitions_on))
    app.add_handler(CommandHandler("transitions_off", transitions_off))
    app.add_handler(CommandHandler("game", game))
    app.add_handler(CommandHandler("paris", paris))
    app.add_handler(CommandHandler("clean", clean))
    app.add_handler(CommandHandler("recipe", recipe_command))
    app.add_handler(CommandHandler("render", render_command))
    app.add_handler(CommandHandler("modify", modify))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
