from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path.cwd()
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920


@dataclass
class CaptionSegment:
    start: float
    end: float
    text: str


CAPTION_STYLES: dict[str, dict[str, str | int]] = {
    "game": {
        "font": "Arial Black",
        "fontsize": 86,
        "primary": "&H0000FFFF",  # yellow (ASS uses BBGGRR)
        "secondary": "&H0000A5FF",
        "outline": "&H00000000",
        "back": "&H80000000",
        "bold": -1,
        "italic": 0,
        "borderstyle": 1,
        "outline_width": 7,
        "shadow": 3,
        "alignment": 2,
        "margin_l": 72,
        "margin_r": 72,
        "margin_v": 245,
    },
    "paris-tip": {
        "font": "Georgia",
        "fontsize": 72,
        "primary": "&H00F7F0FF",
        "secondary": "&H00C7B4FF",
        "outline": "&H00604784",
        "back": "&H70000000",
        "bold": -1,
        "italic": 0,
        "borderstyle": 1,
        "outline_width": 4,
        "shadow": 2,
        "alignment": 2,
        "margin_l": 84,
        "margin_r": 84,
        "margin_v": 280,
    },
    "hamsa-clean": {
        "font": "Arial",
        "fontsize": 68,
        "primary": "&H00FFFFFF",
        "secondary": "&H00DADADA",
        "outline": "&H00202020",
        "back": "&H90000000",
        "bold": -1,
        "italic": 0,
        "borderstyle": 1,
        "outline_width": 3,
        "shadow": 1,
        "alignment": 2,
        "margin_l": 96,
        "margin_r": 96,
        "margin_v": 255,
    },
}


def run(cmd: Sequence[str]) -> None:
    print("$ " + " ".join(str(part) for part in cmd))
    subprocess.run(cmd, check=True)


def require_binary(name: str) -> str:
    exe = shutil.which(name)
    if not exe:
        raise SystemExit(
            f"Missing required executable: {name}. Install it and make sure it is on PATH."
        )
    return exe


def find_single_mp4(input_dir: Path) -> Path:
    videos = sorted(input_dir.glob("*.mp4"))
    if len(videos) != 1:
        raise SystemExit(
            f"Expected exactly one .mp4 in {input_dir}. Found {len(videos)}."
        )
    return videos[0]


def ass_timestamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - math.floor(seconds)) * 100))
    if centis == 100:
        secs += 1
        centis = 0
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def escape_ass(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
        .strip()
    )


def style_line(style_name: str) -> str:
    style = CAPTION_STYLES[style_name]
    values = [
        "Default",
        style["font"],
        style["fontsize"],
        style["primary"],
        style["secondary"],
        style["outline"],
        style["back"],
        style["bold"],
        style["italic"],
        0,
        0,
        100,
        100,
        0,
        0,
        style["borderstyle"],
        style["outline_width"],
        style["shadow"],
        style["alignment"],
        style["margin_l"],
        style["margin_r"],
        style["margin_v"],
        1,
    ]
    return "Style: " + ",".join(str(value) for value in values)


def write_ass(path: Path, segments: Iterable[CaptionSegment], style_name: str) -> None:
    events = []
    for segment in segments:
        if not segment.text.strip() or segment.end <= segment.start:
            continue
        text = escape_ass(segment.text)
        events.append(
            f"Dialogue: 0,{ass_timestamp(segment.start)},{ass_timestamp(segment.end)},Default,,0,0,0,,{text}"
        )

    content = "\n".join(
        [
            "[Script Info]",
            "Title: Hamsa Nomads Captions",
            "ScriptType: v4.00+",
            f"PlayResX: {VIDEO_WIDTH}",
            f"PlayResY: {VIDEO_HEIGHT}",
            "ScaledBorderAndShadow: yes",
            "WrapStyle: 0",
            "YCbCr Matrix: TV.709",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
            style_line(style_name),
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
            *events,
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def extract_audio(ffmpeg: str, source: Path, wav_path: Path) -> list[str]:
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(wav_path),
    ]
    run(cmd)
    return cmd


def transcribe(audio_path: Path, model_size: str, language: str | None) -> list[CaptionSegment]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit(
            "Python package faster-whisper is not installed. Run: pip install -r requirements.txt"
        ) from exc

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
        beam_size=1,
        word_timestamps=False,
    )
    return [
        CaptionSegment(start=float(item.start), end=float(item.end), text=item.text.strip())
        for item in segments
    ]


def transcript_segments(transcript_path: Path) -> list[CaptionSegment]:
    lines = [line.strip() for line in transcript_path.read_text(encoding="utf-8").splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        raise SystemExit(f"Transcript file is empty: {transcript_path}")

    segments: list[CaptionSegment] = []
    for index, line in enumerate(lines):
        start = index * 3.0
        segments.append(CaptionSegment(start=start, end=start + 2.8, text=line))
    return segments


def ffmpeg_subtitle_path(path: Path) -> str:
    # FFmpeg's subtitles filter accepts forward slashes on Windows. Escape characters
    # that are special inside filter values.
    value = path.resolve().as_posix()
    return value.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def render_video(ffmpeg: str, source: Path, ass_path: Path, output_path: Path) -> list[str]:
    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
        f"subtitles='{ffmpeg_subtitle_path(ass_path)}'"
    )
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run(cmd)
    return cmd


def create_thumbnail(ffmpeg: str, source: Path, thumbnail_path: Path, at: str) -> list[str]:
    vf = f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}"
    cmd = [
        ffmpeg,
        "-y",
        "-ss",
        at,
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        vf,
        "-q:v",
        "2",
        str(thumbnail_path),
    ]
    run(cmd)
    return cmd


def write_edit_plan(
    path: Path,
    *,
    source: Path,
    output_video: Path,
    ass_path: Path,
    thumbnail_path: Path,
    style: str,
    model: str,
    segments: list[CaptionSegment],
    commands: list[list[str]],
) -> None:
    plan = {
        "project": "hamsa-caption-engine",
        "source": str(source),
        "outputs": {
            "video": str(output_video),
            "subtitles": str(ass_path),
            "thumbnail": str(thumbnail_path),
        },
        "render": {
            "width": VIDEO_WIDTH,
            "height": VIDEO_HEIGHT,
            "format": "mp4",
            "video_codec": "libx264",
            "audio_codec": "aac",
            "hardware_note": "CPU-first settings for weak Windows PCs with Intel graphics; no paid APIs are used.",
        },
        "caption_style": style,
        "transcription": {
            "engine": "faster-whisper",
            "model": model,
            "device": "cpu",
            "compute_type": "int8",
        },
        "segments": [asdict(segment) for segment in segments],
        "commands": commands,
    }
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a vertical MP4 with styled local captions from one MP4 in /input."
    )
    parser.add_argument("--input", type=Path, help="MP4 to process. Defaults to the only MP4 in ./input.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Output folder. Default: ./output")
    parser.add_argument("--style", choices=sorted(CAPTION_STYLES), default="hamsa-clean")
    parser.add_argument("--model", default="tiny.en", help="faster-whisper model size. Use tiny.en/base.en on weak PCs.")
    parser.add_argument("--language", default="en", help="Spoken language code, or 'auto'. Default: en")
    parser.add_argument("--thumbnail-at", default="00:00:01", help="Timestamp for thumbnail.jpg. Default: 00:00:01")
    parser.add_argument("--transcript", type=Path, help="Optional UTF-8 text file; skips Whisper and creates timed captions from lines.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    ffmpeg = require_binary("ffmpeg")
    source = args.input or find_single_mp4(INPUT_DIR)
    if not source.exists():
        raise SystemExit(f"Input video does not exist: {source}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_video = args.output_dir / "captioned_vertical.mp4"
    ass_path = args.output_dir / "captions.ass"
    thumbnail_path = args.output_dir / "thumbnail.jpg"
    edit_plan_path = args.output_dir / "edit_plan.json"
    commands: list[list[str]] = []

    with tempfile.TemporaryDirectory(prefix="hamsa_caption_") as temp_dir:
        wav_path = Path(temp_dir) / "audio.wav"
        if args.transcript:
            segments = transcript_segments(args.transcript)
        else:
            commands.append(extract_audio(ffmpeg, source, wav_path))
            language = None if args.language.lower() == "auto" else args.language
            segments = transcribe(wav_path, args.model, language)

    if not segments:
        raise SystemExit("No caption segments were produced.")

    write_ass(ass_path, segments, args.style)
    commands.append(render_video(ffmpeg, source, ass_path, output_video))
    commands.append(create_thumbnail(ffmpeg, source, thumbnail_path, args.thumbnail_at))
    write_edit_plan(
        edit_plan_path,
        source=source,
        output_video=output_video,
        ass_path=ass_path,
        thumbnail_path=thumbnail_path,
        style=args.style,
        model=args.model,
        segments=segments,
        commands=commands,
    )

    print(f"Wrote {output_video}")
    print(f"Wrote {ass_path}")
    print(f"Wrote {thumbnail_path}")
    print(f"Wrote {edit_plan_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
