from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .director import analyze_project
from .ffmpeg_renderer import render_ffmpeg
from .paths import ensure_project_dirs
from .recipe_builder import recipe_from_prompt
from .recipe_schema import default_recipe, load_recipe, save_recipe
from .remotion_renderer import RemotionRenderError, render_remotion


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hamsa Nomads content-aware video editor")
    parser.add_argument("--input", help="Input video path (.mp4, .mov, .m4v)")
    parser.add_argument("--inputs", nargs="+", help="One or more input video paths for a multi-video project")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--style", default="hamsa-clean", help="game, paris-tip, hamsa-clean, wrong-vs-right, passport-stamp")
    parser.add_argument("--transcript", help="Manual transcript text file; works without Whisper")
    parser.add_argument("--thumbnail-at", default="00:00:01", help="Thumbnail timestamp")
    parser.add_argument("--renderer", choices=["ffmpeg", "remotion"], default="ffmpeg", help="Reliable FFmpeg or optional premium Remotion")
    parser.add_argument("--recipe", help="Existing edit_recipe.json")
    parser.add_argument("--prompt", default="", help="Local rule-based prompt/director note to create/update edit_recipe.json")
    parser.add_argument("--auto-cut", dest="auto_cut", action="store_true", default=True, help="Detect pauses and build output/cut_plan.json")
    parser.add_argument("--no-auto-cut", dest="auto_cut", action="store_false", help="Disable silence removal/cut planning")
    parser.add_argument("--visual-ai", choices=["none", "smolvlm2", "qwen2_5_vl"], default="none", help="Optional local visual model for keyframe analysis")
    parser.add_argument("--logo", help="Optional logo path for FFmpeg/recipe logo overlay, e.g. assets/brand/hamsa-logo.png")
    return parser


def _input_paths(args: argparse.Namespace) -> list[str]:
    paths = list(args.inputs or [])
    if args.input:
        paths.insert(0, args.input)
    return paths


def main(argv: list[str] | None = None) -> int:
    ensure_project_dirs()
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    inputs = _input_paths(args)
    if args.recipe:
        recipe = load_recipe(args.recipe)
        if inputs:
            recipe["input_video"]["src"] = str(Path(inputs[0]))
        recipe["renderer"] = args.renderer
    elif inputs:
        analysis = analyze_project(inputs, output_dir, prompt=args.prompt, renderer=args.renderer, auto_cut=args.auto_cut, visual_ai=args.visual_ai, style=args.style, progress=lambda message: print(message))
        recipe = analysis["recipe"]
    elif args.prompt:
        recipe = recipe_from_prompt(args.prompt, input_video="", renderer=args.renderer, style=args.style)
    else:
        print("Provide --input, --inputs, --recipe, or --prompt.", file=sys.stderr)
        return 2
    if args.logo:
        recipe.setdefault("logo", {})["path"] = args.logo
        recipe["logo"]["enabled"] = True
    save_recipe(recipe, output_dir / "edit_recipe.json")
    render_input = recipe.get("input_video", {}).get("src") or (inputs[0] if inputs else "")
    if not render_input:
        print("No render input is available after analysis.", file=sys.stderr)
        return 2
    if args.renderer == "remotion":
        try:
            result = render_remotion(render_input, output_dir, recipe)
        except RemotionRenderError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    else:
        result = render_ffmpeg(render_input, output_dir, recipe, transcript_path=args.transcript, thumbnail_at=args.thumbnail_at, logo_path=args.logo)
    print("Render complete")
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
