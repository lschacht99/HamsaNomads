from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .content_analysis import analyze_transcript, save_content_analysis
from .paths import LOG_DIR, ROOT, find_ffmpeg
from .recipe_schema import save_recipe, validate_recipe
from .transcription import load_manual_transcript, save_transcript, segments_from_transcript_text, transcribe_with_whisper

VIDEO_W = 1080
VIDEO_H = 1920

STYLE_CONFIG = {
    "hamsa-clean": {"font": "Arial", "size": 66, "primary": "#111111", "accent": "#7B8A6A", "box": "#F6F2E7", "border": "#7B8A6A", "label": "HAMSA NOMADS", "margin_v": 270},
    "paris-tip": {"font": "Arial", "size": 64, "primary": "#111111", "accent": "#C8886A", "box": "#ECE7DB", "border": "#DCC7A1", "label": "PARIS TIP", "margin_v": 300},
    "game": {"font": "Georgia", "size": 66, "primary": "#111111", "accent": "#7B8A6A", "box": "#F6F2E7", "border": "#C8886A", "label": "QUEST UNLOCKED", "margin_v": 250},
    "video_game_dialogue": {"font": "Georgia", "size": 66, "primary": "#111111", "accent": "#7B8A6A", "box": "#F6F2E7", "border": "#C8886A", "label": "QUEST UNLOCKED", "margin_v": 250},
    "wrong-vs-right": {"font": "Arial", "size": 62, "primary": "#111111", "accent": "#C8886A", "box": "#ECE7DB", "border": "#C8886A", "label": "WRONG WORD", "margin_v": 285},
    "passport_stamp": {"font": "Arial", "size": 62, "primary": "#111111", "accent": "#C8886A", "box": "#ECE7DB", "border": "#C8886A", "label": "PASSPORT NOTE", "margin_v": 290},
    "retreat_luxury": {"font": "Georgia", "size": 60, "primary": "#111111", "accent": "#7B8A6A", "box": "#ECE7DB", "border": "#DCC7A1", "label": "RETREAT NOTE", "margin_v": 300},
}


def _ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "").replace("}", "").replace("\n", "\\N")


def _ass_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - math.floor(seconds)) * 100))
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _hex_to_ass(hex_color: str, alpha: str = "00") -> str:
    clean = hex_color.lstrip("#")
    red, green, blue = clean[0:2], clean[2:4], clean[4:6]
    return f"&H{alpha}{blue}{green}{red}"


def _override_color(hex_color: str) -> str:
    clean = hex_color.lstrip("#")
    red, green, blue = clean[0:2], clean[2:4], clean[4:6]
    return f"&H{blue}{green}{red}&"


def _caption_text(text: str, recipe: dict[str, Any]) -> str:
    escaped = _ass_escape(text)
    for item in recipe.get("caption_system", {}).get("keyword_highlights", []):
        word = item.get("word", "")
        color = item.get("color", "#7B8A6A")
        if word and word.lower() in escaped.lower():
            escaped = escaped.replace(word, f"{{\\c{_override_color(color)}\\b1}}{_ass_escape(word)}{{\\rCaption}}")
    return escaped


def write_ass(segments: list[dict[str, Any]], recipe: dict[str, Any], path: Path) -> Path:
    style_name = recipe.get("style", {}).get("name", "hamsa-clean")
    config = STYLE_CONFIG.get(style_name, STYLE_CONFIG["hamsa-clean"])
    primary = _hex_to_ass(config["primary"])
    accent = _hex_to_ass(config["accent"])
    box = _hex_to_ass(config["box"], "10")
    border = _hex_to_ass(config["border"])
    label = recipe.get("intro_card", {}).get("label") or config["label"]
    margin_v = int(config["margin_v"])
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {VIDEO_W}
PlayResY: {VIDEO_H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{config['font']},{config['size']},{primary},{accent},{border},{box},-1,0,0,0,100,100,0,0,3,5,1,2,96,96,{margin_v},1
Style: Label,Georgia,42,{primary},{accent},{border},{_hex_to_ass('#F6F2E7', '08')},-1,0,0,0,100,100,1,0,3,3,0,8,96,96,112,1
Style: Stamp,Arial,50,{accent},{primary},{_hex_to_ass('#DCC7A1')},{_hex_to_ass('#ECE7DB', '08')},-1,0,0,0,100,100,1,0,3,3,0,8,96,96,170,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    intro = recipe.get("intro_card", {})
    if intro.get("enabled", True):
        end = float(intro.get("duration_sec", 1.8))
        events.append(f"Dialogue: 2,{_ass_time(0)},{_ass_time(end)},Label,,0,0,0,,{_ass_escape(label)}\\N{_ass_escape(intro.get('headline', 'Jewish travel note'))}")
    for seg in segments:
        events.append(f"Dialogue: 3,{_ass_time(float(seg['start']))},{_ass_time(float(seg['end']))},Caption,,0,0,0,,{_caption_text(seg['text'], recipe)}")
    for overlay in recipe.get("overlays", []):
        if overlay.get("type") == "wrong_vs_right":
            start = float(overlay.get("start_sec", 2.0))
            end = start + float(overlay.get("duration_sec", 3.0))
            text = f"{{\\c{_override_color('#C8886A')}}}❌ {_ass_escape(overlay.get('wrong', 'Don’t ask: Cholov Yisroel'))}\\N{{\\c{_override_color('#7B8A6A')}}}✅ {_ass_escape(overlay.get('right', 'Ask: Chamour'))}"
            events.append(f"Dialogue: 5,{_ass_time(start)},{_ass_time(end)},Caption,,0,0,0,,{text}")
    for card in recipe.get("section_cards", []):
        start = float(card.get("start_sec", 0))
        end = start + float(card.get("duration_sec", 0.7))
        events.append(f"Dialogue: 4,{_ass_time(start)},{_ass_time(end)},Stamp,,0,0,0,,{_ass_escape(card.get('title', 'LOCAL TIP'))}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return path


def _resolve_logo_path(recipe: dict[str, Any], explicit_logo: str | Path | None = None) -> Path | None:
    logo_settings = recipe.get("logo", {})
    candidate = explicit_logo or logo_settings.get("path") or "assets/brand/hamsa-logo.png"
    if not logo_settings.get("enabled", True) and explicit_logo is None:
        return None
    path = Path(candidate)
    if not path.is_absolute():
        path = ROOT / path
    return path if path.exists() else None


def _detect_cut_plan(video_path: Path, output_dir: Path, recipe: dict[str, Any], log_notes: list[str]) -> dict[str, Any]:
    settings = recipe.get("auto_cut", {})
    plan = {"enabled": bool(settings.get("enabled", False)), "source": str(video_path), "segments": [], "notes": []}
    if not plan["enabled"]:
        output_dir.joinpath("cut_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        return plan
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        plan["notes"].append("auto-cut skipped: ffmpeg missing")
        output_dir.joinpath("cut_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        return plan
    threshold = settings.get("silence_threshold_db", -35)
    min_silence = settings.get("min_silence_duration_sec", 0.7)
    cmd = [ffmpeg, "-hide_banner", "-i", str(video_path), "-af", f"silencedetect=noise={threshold}dB:d={min_silence}", "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    stderr = proc.stderr or ""
    silences: list[dict[str, float]] = []
    current_start: float | None = None
    for line in stderr.splitlines():
        if "silence_start:" in line:
            try:
                current_start = float(line.rsplit("silence_start:", 1)[1].strip())
            except ValueError:
                pass
        if "silence_end:" in line and current_start is not None:
            try:
                end_part = line.split("silence_end:", 1)[1].split("|", 1)[0].strip()
                silences.append({"start": current_start, "end": float(end_part)})
            except ValueError:
                pass
            current_start = None
    plan["silences"] = silences
    if silences and silences[0]["start"] <= 0.2 and silences[0]["end"] >= 1.0:
        note = f"opening trimmed candidate: first dead air ends at {silences[0]['end']:.2f}s"
        plan["notes"].append(note)
        log_notes.append(note)
    plan["notes"].append("cut metadata saved; original media preserved; jump-cut render can be expanded from this plan")
    output_dir.joinpath("cut_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan




def _concat_file_line(path: Path) -> str:
    # FFmpeg concat demuxer accepts forward slashes on Windows and Unix.
    escaped = path.resolve().as_posix().replace("'", "'\\''")
    return f"file '{escaped}'"


def _append_ffmpeg_failure_log(label: str, cmd: list[str], proc: subprocess.CompletedProcess[str]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        f"timestamp: {datetime.now().isoformat()}",
        f"ffmpeg step: {label}",
        f"command: {cmd!r}",
        f"return code: {proc.returncode}",
        "stdout:",
        proc.stdout or "",
        "stderr:",
        proc.stderr or "",
    ]
    with (LOG_DIR / "bot_render.log").open("a", encoding="utf-8") as handle:
        handle.write("\n" + "\n".join(lines) + "\n")


def _run_ffmpeg_or_raise(label: str, cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        _append_ffmpeg_failure_log(label, cmd, proc)
        stderr = (proc.stderr or proc.stdout or "No FFmpeg stderr/stdout captured.").strip()
        useful = "\n".join(line for line in stderr.splitlines()[-20:] if line.strip())
        raise RuntimeError(f"FFmpeg failed during {label}:\n{useful}")


def _assembly_encode_args(ffmpeg: str, input_args: list[str], assembled: Path) -> list[str]:
    return [
        ffmpeg,
        "-y",
        *input_args,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase,crop={VIDEO_W}:{VIDEO_H}",
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
        "-ar",
        "44100",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
        str(assembled.resolve()),
    ]


def _assemble_timeline(ffmpeg: str, recipe: dict[str, Any], output_dir: Path, notes: list[str]) -> Path | None:
    clips = [entry for entry in recipe.get("timeline", []) if entry.get("type", "video_clip") == "video_clip" and entry.get("source")]
    if not clips:
        return None
    out = output_dir.resolve()
    segment_dir = out / "timeline_segments"
    segment_dir.mkdir(parents=True, exist_ok=True)
    segment_paths: list[Path] = []
    for index, clip in enumerate(clips, start=1):
        source = Path(clip["source"])
        if not source.is_absolute():
            source = ROOT / source
        source = source.resolve()
        start = float(clip.get("source_start_sec", 0.0))
        end = float(clip.get("source_end_sec", start))
        duration = max(0.1, end - start)
        segment = (segment_dir / f"segment_{index:03d}.mp4").resolve()
        cmd = [
            ffmpeg,
            "-y",
            "-ss",
            f"{start:.2f}",
            "-i",
            str(source),
            "-t",
            f"{duration:.2f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
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
            "-ar",
            "44100",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(segment),
        ]
        _run_ffmpeg_or_raise(f"timeline segment {index:03d}", cmd)
        segment_paths.append(segment)

    assembled = (out / "assembly_input.mp4").resolve()
    if len(segment_paths) == 1:
        cmd = _assembly_encode_args(ffmpeg, ["-i", str(segment_paths[0])], assembled)
        _run_ffmpeg_or_raise("single segment timeline assembly", cmd)
        notes.append("timeline assembly re-encoded 1 content-aware clip")
        return assembled

    concat_file = (out / "timeline_concat.txt").resolve()
    concat_file.write_text("\n".join(_concat_file_line(path) for path in segment_paths) + "\n", encoding="utf-8")
    cmd = _assembly_encode_args(ffmpeg, ["-f", "concat", "-safe", "0", "-i", str(concat_file)], assembled)
    _run_ffmpeg_or_raise("concat timeline assembly", cmd)
    notes.append(f"timeline assembly re-encoded {len(segment_paths)} content-aware clips")
    return assembled

def render_ffmpeg(video_path: str | Path, output_dir: str | Path, recipe: dict[str, Any], *, transcript_path: str | Path | None = None, thumbnail_at: str = "00:00:01", logo_path: str | Path | None = None) -> dict[str, Any]:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg missing. Run download_ffmpeg.bat or put ffmpeg.exe and ffprobe.exe inside tools\\ffmpeg\\bin\\.")
    video = Path(video_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    recipe = validate_recipe(recipe)
    recipe["renderer"] = "ffmpeg"
    recipe["input_video"]["src"] = str(video)
    if logo_path:
        recipe.setdefault("logo", {})["path"] = str(logo_path)
    notes: list[str] = []
    assembled = _assemble_timeline(ffmpeg, recipe, out, notes)
    if assembled:
        video = assembled
        recipe["input_video"]["src"] = str(video)
    else:
        _detect_cut_plan(video, out, recipe, notes)

    if transcript_path:
        transcript = load_manual_transcript(transcript_path)
    elif recipe.get("captions"):
        transcript = {"mode": "recipe", "segments": recipe.get("captions", []), "text": " ".join(segment.get("text", "") for segment in recipe.get("captions", []))}
    else:
        try:
            transcript = transcribe_with_whisper(video, model=recipe.get("transcription", {}).get("model", "base"), language=recipe.get("transcription", {}).get("language", "auto"))
        except RuntimeError:
            transcript = {"mode": "fallback", "segments": segments_from_transcript_text(recipe.get("intro_card", {}).get("headline", "Hamsa Nomads travel tip")), "text": ""}
            notes.append("automatic transcription unavailable; used branded fallback captions")
    save_transcript(transcript, out / "transcript.json")
    analysis = recipe.get("content_analysis") or analyze_transcript(transcript)
    save_content_analysis(analysis, out / "content_analysis.json")
    recipe["content_analysis"] = analysis
    recipe["captions"] = transcript.get("segments", [])
    ass = write_ass(transcript.get("segments", []), recipe, out / "captions.ass")
    save_recipe(recipe, out / "edit_recipe.json")

    base_vf = f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase,crop={VIDEO_W}:{VIDEO_H},subtitles={ass.as_posix()}"
    logo = _resolve_logo_path(recipe, logo_path)
    final = out / "final_video.mp4"
    if logo:
        filter_complex = f"[0:v]{base_vf}[base];[1:v]scale=200:-1[logo];[base][logo]overlay=(W-w)/2:72:format=auto[v]"
        cmd = [ffmpeg, "-y", "-i", str(video), "-i", str(logo), "-filter_complex", filter_complex, "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(final)]
        notes.append(f"logo overlay used: {logo}")
    else:
        cmd = [ffmpeg, "-y", "-i", str(video), "-vf", base_vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(final)]
        notes.append("logo overlay skipped: logo file missing or disabled")
    subprocess.run(cmd, check=True)
    thumb = out / "thumbnail.jpg"
    subprocess.run([ffmpeg, "-y", "-ss", thumbnail_at, "-i", str(video), "-frames:v", "1", "-vf", f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase,crop={VIDEO_W}:{VIDEO_H}", str(thumb)], check=True)
    return {"final_video": final, "thumbnail": thumb, "recipe": out / "edit_recipe.json", "transcript": out / "transcript.json", "content_analysis": out / "content_analysis.json", "notes": notes}
