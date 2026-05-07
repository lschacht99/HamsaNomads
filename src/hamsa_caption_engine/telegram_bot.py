from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

ROOT = Path.cwd()
INPUT_VIDEO = ROOT / "input" / "test.mp4"
TRANSCRIPT_FILE = ROOT / "transcript.txt"
OUTPUT_DIR = ROOT / "output"
FINAL_VIDEO = OUTPUT_DIR / "final_video.mp4"
CAPTIONED_VIDEO = OUTPUT_DIR / "captioned_vertical.mp4"
THUMBNAIL = OUTPUT_DIR / "thumbnail.jpg"
LOG_DIR = ROOT / "logs"
BOT_RENDER_LOG = LOG_DIR / "bot_render.log"
TOKEN_ENV_VAR = "TELEGRAM_BOT_TOKEN"
STYLE_COMMANDS = {
    "game": "game",
    "paris": "paris-tip",
    "clean": "hamsa-clean",
}
RENDER_LOCK = asyncio.Lock()


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def help_text() -> str:
    return "\n".join(
        [
            "Send me an MP4/video and I will render a Hamsa-caption video locally.",
            "",
            "Steps:",
            "1. Send a video file or MP4 document.",
            "2. Send transcript text, or send /render to use transcript.txt.",
            "3. Choose /game, /paris, or /clean.",
            "",
            "Commands: /start /help /game /paris /clean /status /render",
            "No paid APIs are used.",
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.setdefault("style", "hamsa-clean")
    await update.effective_message.reply_text(help_text())


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    style = context.user_data.get("style", "hamsa-clean")
    lines = [
        f"Video: {'yes' if INPUT_VIDEO.exists() else 'missing'} ({INPUT_VIDEO})",
        f"Transcript: {'yes' if TRANSCRIPT_FILE.exists() else 'missing'} ({TRANSCRIPT_FILE})",
        f"Style: {style}",
        f"Final video: {'yes' if FINAL_VIDEO.exists() else 'not rendered yet'}",
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
    attachment = video_attachment(update)
    if not attachment:
        await update.effective_message.reply_text("Please send a video file or MP4 document.")
        return

    INPUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)
    telegram_file = await attachment.get_file()
    await telegram_file.download_to_drive(custom_path=INPUT_VIDEO)
    context.user_data["video_received"] = True
    await update.effective_message.reply_text(
        "Video received. Now send me the transcript text, or send /render to use transcript.txt."
    )


async def handle_transcript_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not INPUT_VIDEO.exists() and not context.user_data.get("video_received"):
        await update.effective_message.reply_text("Send me input video first, then send transcript text.")
        return

    text = update.effective_message.text.strip()
    if not text:
        await update.effective_message.reply_text("Transcript text was empty. Please send transcript text again.")
        return

    TRANSCRIPT_FILE.write_text(text + "\n", encoding="utf-8")
    context.user_data["transcript_ready"] = True
    await update.effective_message.reply_text("Choose style: /game, /paris, or /clean.")


async def render_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not INPUT_VIDEO.exists():
        await update.effective_message.reply_text("I need a video first. Send a video file or MP4 document.")
        return
    if not TRANSCRIPT_FILE.exists():
        await update.effective_message.reply_text("I could not find transcript.txt. Send transcript text first.")
        return
    context.user_data["transcript_ready"] = True
    await update.effective_message.reply_text("Choose style: /game, /paris, or /clean.")


async def set_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command = update.effective_message.text.split()[0].lstrip("/").lower().split("@", 1)[0]
    style = STYLE_COMMANDS[command]
    context.user_data["style"] = style

    if not INPUT_VIDEO.exists():
        await update.effective_message.reply_text(f"Style set to {style}. Now send me a video file or MP4 document.")
        return
    if not TRANSCRIPT_FILE.exists():
        await update.effective_message.reply_text(f"Style set to {style}. Now send transcript text, or send /render to use transcript.txt.")
        return

    await render_current_job(update, style)


async def run_render(style: str) -> tuple[int, str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for stale_output in (FINAL_VIDEO, CAPTIONED_VIDEO, THUMBNAIL):
        if stale_output.exists():
            stale_output.unlink()
    cmd = [
        "py",
        "-3.11",
        "-m",
        "hamsa_caption_engine",
        "--input",
        r"input\test.mp4",
        "--output-dir",
        "output",
        "--style",
        style,
        "--transcript",
        "transcript.txt",
        "--thumbnail-at",
        "00:00:01",
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=ROOT,
    )
    stdout, _stderr = await process.communicate()
    log_text = stdout.decode(errors="replace")
    BOT_RENDER_LOG.write_text("$ " + " ".join(cmd) + "\n" + log_text, encoding="utf-8")
    return process.returncode or 0, log_text


def ensure_final_video_name() -> None:
    if FINAL_VIDEO.exists():
        return
    if CAPTIONED_VIDEO.exists():
        shutil.copy2(CAPTIONED_VIDEO, FINAL_VIDEO)


async def send_document(update: Update, path: Path, filename: str, caption: str) -> None:
    with path.open("rb") as file_obj:
        await update.effective_message.reply_document(
            document=file_obj,
            filename=filename,
            caption=caption,
        )


async def render_current_job(update: Update, style: str) -> None:
    await update.effective_message.reply_text(f"Rendering with {style}. This can take a few minutes on a weak PC.")
    async with RENDER_LOCK:
        return_code, _log_text = await run_render(style)

    if return_code != 0:
        await update.effective_message.reply_text(
            f"Render failed. Full logs were saved to {BOT_RENDER_LOG}."
        )
        return

    ensure_final_video_name()
    if not FINAL_VIDEO.exists():
        await update.effective_message.reply_text(
            f"Render finished, but I could not find {FINAL_VIDEO}. Full logs were saved to {BOT_RENDER_LOG}."
        )
        return

    await send_document(update, FINAL_VIDEO, "final_video.mp4", "Final Hamsa-caption video")
    if THUMBNAIL.exists():
        await send_document(update, THUMBNAIL, "thumbnail.jpg", "Thumbnail")
    await update.effective_message.reply_text("Done. Send another video any time.")


def build_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("render", render_command))
    for command in STYLE_COMMANDS:
        application.add_handler(CommandHandler(command, set_style))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transcript_text))
    return application


def main() -> int:
    load_dotenv()
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise SystemExit(
            "Missing TELEGRAM_BOT_TOKEN. Create .env with TELEGRAM_BOT_TOKEN=your_token_here."
        )

    print("Starting Hamsa Telegram bot. Press Ctrl+C to stop.")
    build_application(token).run_polling(allowed_updates=Update.ALL_TYPES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
