from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .ffmpeg_renderer import render_ffmpeg
from .paths import ensure_project_dirs
from .recipe_builder import recipe_from_prompt
from .recipe_schema import default_recipe, load_recipe, save_recipe
from .remotion_renderer import render_remotion


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hamsa Nomads Windows-friendly video caption engine")
    parser.add_argument("--input", required=True, help="Input MP4 video path")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--style", default="hamsa-clean", help="game, paris-tip, hamsa-clean, wrong-vs-right, passport-stamp")
    parser.add_argument("--transcript", help="Manual transcript text file; works without Whisper")
    parser.add_argument("--thumbnail-at", default="00:00:01", help="Thumbnail timestamp")
    parser.add_argument("--renderer", choices=["ffmpeg", "remotion"], default="ffmpeg", help="Reliable FFmpeg or optional premium Remotion")
    parser.add_argument("--recipe", help="Existing edit_recipe.json")
    parser.add_argument("--prompt", help="Local rule-based prompt to create/update edit_recipe.json")
    parser.add_argument("--auto-cut", action="store_true", help="Detect pauses and save output/cut_plan.json; keeps natural breathing room")
    return parser


def main(argv: list[str] | None = None) -> int:
    ensure_project_dirs()
    args = build_parser().parse_args(argv)
    video = Path(args.input)
    output_dir = Path(args.output_dir)
    if args.recipe:
        recipe = load_recipe(args.recipe)
        recipe["input_video"]["src"] = str(video)
        recipe["renderer"] = args.renderer
    elif args.prompt:
        recipe = recipe_from_prompt(args.prompt, input_video=str(video), renderer=args.renderer, style=args.style)
    else:
        recipe = default_recipe(input_video=str(video), renderer=args.renderer, style=args.style)
    if args.auto_cut:
        recipe["auto_cut"]["enabled"] = True
        recipe["input_video"]["remove_silence"] = True
    save_recipe(recipe, output_dir / "edit_recipe.json")
    if args.renderer == "remotion":
        result = render_remotion(video, output_dir, recipe)
    else:
        result = render_ffmpeg(video, output_dir, recipe, transcript_path=args.transcript, thumbnail_at=args.thumbnail_at)
    print("Render complete")
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
