from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .cli import CAPTION_STYLES, INPUT_DIR, OUTPUT_DIR

TOKEN_ENV_VAR = "HAMSA_TELEGRAM_BOT_TOKEN"
DEFAULT_STYLE = "hamsa-clean"
COMMAND_STYLES = {
    "game": "game",
    "paris": "paris-tip",
    "clean": "hamsa-clean",
    "wrongright": "wrong-vs-right",
    "dialogue": "video-game-dialogue",
}
RENDER_LOCK = asyncio.Lock()


def selected_style(context: ContextTypes.DEFAULT_TYPE) -> str:
    style = context.user_data.get("style", DEFAULT_STYLE)
    if style not in CAPTION_STYLES:
        return DEFAULT_STYLE
    return style


def safe_job_name(update: Update) -> str:
    chat_id = update.effective_chat.id if update.effective_chat else "chat"
    message_id = update.effective_message.message_id if update.effective_message else "message"
    return f"telegram_{chat_id}_{message_id}"


def help_text() -> str:
    return "\n".join(
        [
            "Send me an MP4/video and I will caption it locally.",
            "",
            "Choose a style first:",
            "/game - bold gaming captions",
            "/paris - Paris tip style",
            "/clean - clean Hamsa style",
            "/wrongright - wrong vs right captions",
            "/dialogue - video game dialogue box",
            "",
            "No paid APIs are used. Rendering runs on this PC.",
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["style"] = selected_style(context)
    await update.effective_message.reply_text(help_text())


async def set_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command = update.effective_message.text.split()[0].lstrip("/").lower().split("@", 1)[0]
    style = COMMAND_STYLES[command]
    context.user_data["style"] = style
    await update.effective_message.reply_text(
        f"Style set to {style}. Now send me one MP4/video."
    )


def video_attachment(update: Update):
    message = update.effective_message
    if message.video:
        return message.video
    if message.document and message.document.mime_type:
        if message.document.mime_type.startswith("video/"):
            return message.document
    return None


async def run_caption_engine(source_video: Path, output_dir: Path, style: str) -> tuple[int, str]:
    cmd = [
        sys.executable,
        "-m",
        "hamsa_caption_engine",
        "--input",
        str(source_video),
        "--output-dir",
        str(output_dir),
        "--style",
        style,
        "--model",
        "tiny.en",
        "--video-name",
        "final_video.mp4",
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _stderr = await process.communicate()
    return process.returncode or 0, stdout.decode(errors="replace")


async def send_output_file(
    update: Update, path: Path, *, filename: str, caption: str | None = None
) -> None:
    with path.open("rb") as file_obj:
        await update.effective_message.reply_document(
            document=file_obj,
            filename=filename,
            caption=caption,
        )


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    attachment = video_attachment(update)
    if not attachment:
        await update.effective_message.reply_text(
            "Please send an MP4/video file, or choose a style with /clean first."
        )
        return

    style = selected_style(context)
    job_name = safe_job_name(update)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_video = INPUT_DIR / f"{job_name}.mp4"
    output_dir = OUTPUT_DIR / job_name
    output_dir.mkdir(parents=True, exist_ok=True)

    await update.effective_message.reply_text(
        f"Downloading your video and rendering with style: {style}. This can take a while on a weak PC."
    )
    telegram_file = await attachment.get_file()
    await telegram_file.download_to_drive(custom_path=source_video)

    async with RENDER_LOCK:
        return_code, log_text = await run_caption_engine(source_video, output_dir, style)

    if return_code != 0:
        short_log = log_text[-3500:] if log_text else "No log output."
        await update.effective_message.reply_text(
            "Render failed. Check Python, FFmpeg, and faster-whisper setup.\n\n"
            f"Last log lines:\n{short_log}"
        )
        return

    final_video = output_dir / "final_video.mp4"
    thumbnail = output_dir / "thumbnail.jpg"
    edit_plan = output_dir / "edit_plan.json"
    missing = [path.name for path in [final_video, thumbnail, edit_plan] if not path.exists()]
    if missing:
        await update.effective_message.reply_text(
            "Render finished, but these files were missing: " + ", ".join(missing)
        )
        return

    await send_output_file(update, final_video, filename="final_video.mp4", caption="Final captioned video")
    await send_output_file(update, thumbnail, filename="thumbnail.jpg", caption="Thumbnail")
    await send_output_file(update, edit_plan, filename="edit_plan.json", caption="Edit plan")
    await update.effective_message.reply_text("Done. Send another video any time.")


def build_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler(["start", "help"], start))
    for command in COMMAND_STYLES:
        application.add_handler(CommandHandler(command, set_style))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))
    return application


def main() -> int:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise SystemExit(
            f"Missing {TOKEN_ENV_VAR}. Set it to your Telegram bot token before starting the bot."
        )

    print("Starting Hamsa Telegram bot. Press Ctrl+C to stop.")
    build_application(token).run_polling(allowed_updates=Update.ALL_TYPES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
