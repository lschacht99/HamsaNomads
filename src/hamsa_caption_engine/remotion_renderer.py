from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .paths import REMOTION_DIR, find_executable
from .recipe_schema import save_recipe, validate_recipe

REMOTION_MISSING = "Remotion is not installed. Run install_windows.bat and choose Remotion install, or run npm install inside remotion/."


def remotion_installed() -> bool:
    return REMOTION_DIR.exists() and (REMOTION_DIR / "node_modules").exists()


def render_remotion(video_path: str | Path, output_dir: str | Path, recipe: dict[str, Any]) -> dict[str, Path]:
    node = find_executable("node")
    npm = find_executable("npm")
    if not node or not npm or not REMOTION_DIR.exists() or not (REMOTION_DIR / "node_modules").exists():
        raise RuntimeError(REMOTION_MISSING)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    recipe = validate_recipe(recipe)
    recipe["renderer"] = "remotion"
    recipe["input_video"]["src"] = str(Path(video_path))
    recipe_path = save_recipe(recipe, out / "edit_recipe.json")
    final = out / "final_video.mp4"
    cmd = [node, str(REMOTION_DIR / "render.mjs"), "--input", str(video_path), "--recipe", str(recipe_path), "--output", str(final)]
    subprocess.run(cmd, cwd=str(REMOTION_DIR), check=True)
    thumbnail = out / "thumbnail.jpg"
    if not thumbnail.exists():
        # Remotion script renders still when supported; absence is not fatal.
        thumbnail.touch()
    return {"final_video": final, "thumbnail": thumbnail, "recipe": recipe_path}
