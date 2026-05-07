# Hamsa Nomads Video Automation

A Windows-friendly Telegram video-editing bot for Hamsa Nomads. Send the bot a real MP4, give it a prompt, and it builds an `edit_recipe.json`, transcribes with optional local Whisper, renders with reliable FFmpeg by default or optional premium Remotion, then sends back `final_video.mp4`, `thumbnail.jpg`, and the recipe.

No Adobe, Premiere, After Effects, CapCut, CUDA, Nvidia GPU, paid APIs, or cloud rendering are required.

## WINDOWS SETUP

### Step 1
Double-click `install_windows.bat`.

### Step 2
When asked, choose:

- install Whisper: yes if you want automatic transcription
- setup FFmpeg: yes
- install Remotion: yes if you want premium animated mode
- add Telegram token: yes

### Step 3
Double-click `run_bot.bat`.

### Step 4
In Telegram:

- send `/start`
- send MP4
- send a prompt or choose `/game` `/paris` `/clean`
- use `/ffmpeg` or `/remotion`
- send `/render`
- receive final video

Example prompt:

```text
Make this like a premium video game quest about asking for chamour in France. Add wrong-vs-right captions and a passport stamp moment.
```

## Manual token setup

Create `.env` in the project root:

```env
HAMSA_TELEGRAM_BOT_TOKEN=your_token_here
```

Do not commit `.env`. Use `.env.example` as the safe template.

## Install commands

Basic install:

```bat
python -m pip install -e .
```

Optional Whisper install:

```bat
python -m pip install -e ".[whisper]"
```

The Windows scripts use `.venv\Scripts\python.exe` for runtime and bot commands.


## Logo and branded caption design

Add your Hamsa Nomads logo here:

```text
assets/brand/hamsa-logo.png
assets/brand/hamsa-logo-white.png
assets/brand/hamsa-logo-dark.png
```

Only `assets/brand/hamsa-logo.png` is required. If the logo is missing, Remotion renders the fallback text `Hamsa Nomads` instead of crashing, and FFmpeg simply skips the logo overlay.

To tune the visual system:

- Edit `brand/hamsa_nomads_brand.json` for colors, typography, and logo paths.
- Edit a recipe `caption_system` block for caption type, parchment box style, max words, and keyword highlights.
- Edit `remotion/src/components/CaptionDialogueBox.tsx` for premium animated caption design.
- Edit `src/hamsa_caption_engine/ffmpeg_renderer.py` for fast FFmpeg caption style.

Recommended workflow:

1. Add logo to `assets/brand/hamsa-logo.png`.
2. Run `/status` in Telegram and confirm the logo exists.
3. Use `/ffmpeg` for reliable weak-PC mode.
4. Use `/remotion` for premium animated mode.
5. If Remotion fails, open `logs/bot_render.log`; it includes full Node/Remotion stdout/stderr, paths, command, Node/npm versions, and logo status.


### Remotion Windows asset rule

Remotion must not receive raw `file:///C:/...` Windows paths inside React components. The Python Remotion renderer stages browser-safe runtime assets into:

```text
remotion/public/runtime/input.mp4
remotion/public/runtime/hamsa-logo.png
remotion/public/runtime/edit_recipe.json
```

React components load those staged assets with `staticFile()`, and video uses `OffthreadVideo`, so local Windows videos and logos do not hit `ERR_UNKNOWN_URL_SCHEME` or `MEDIA_ELEMENT_ERROR` from raw file URLs.

Caption/design source files:

- FFmpeg fast styles: `src/hamsa_caption_engine/ffmpeg_renderer.py`
- Remotion premium components: `remotion/src/components/`
- Prompt and recipe logic: `src/hamsa_caption_engine/recipe_builder.py`
- Brand colors/logo identity: `brand/hamsa_nomads_brand.json`

Example recipe caption design:

```json
"caption_system": {
  "type": "video_game_dialogue",
  "position": "lower_third",
  "max_words_per_caption": 6,
  "box_style": "parchment",
  "keyword_highlights": [
    {"word": "Cholov Yisroel", "style": "wrong", "color": "#C8886A"},
    {"word": "Chamour", "style": "correct", "color": "#7B8A6A"}
  ]
}
```

## Bot commands

- `/start` and `/help` explain the workflow.
- `/auto` enables automatic Whisper transcription.
- `/transcript` switches to manual transcript mode.
- `/ffmpeg` selects reliable weak-PC rendering.
- `/remotion` selects optional premium animated rendering.
- `/autocut_on` and `/autocut_off` control pause detection and cut-plan generation.
- `/transitions_on` and `/transitions_off` control transitions.
- `/game`, `/paris`, `/clean` set a style and render the latest video.
- `/recipe` shows the current recipe summary.
- `/render` renders the latest video.
- `/modify [prompt]` applies local rule-based prompt changes, saves a modified recipe, and renders again.
- `/status` shows paths, selected renderer/style, transcription mode, imports, FFmpeg, Node/npm, Python executable, and project root.

## Prompt-driven editing rules

The recipe builder is local and rule-based. No paid API is used.

- `video game`, `quest`, `RPG`, `level`, `mission` selects video-game dialogue styling.
- `Paris`, `France`, `chamour`, `croissant` selects Paris-tip styling.
- `wrong/right`, `mistake`, `don't say`, `instead` adds a wrong-vs-right overlay.
- `luxury`, `retreat`, `house`, `villa` selects retreat-luxury styling.
- `passport`, `travel note`, `stamp` adds passport stamp styling and a freeze-frame moment.
- `premium animation`, `animated`, `cinematic title`, `smooth`, `premium` selects Remotion transitions.
- `simple`, `fast`, `weak PC` selects FFmpeg with hard cuts only.
- `make it faster`, `cut the pauses`, `more dynamic`, `make it punchy`, `reel style` enables auto-cut, jump-cut planning, and punch-in zooms.

## Auto-cut and transitions

Auto-cut detects silent sections with FFmpeg and saves safe metadata to `output\cut_plan.json`. The original MP4 is never destroyed. Defaults:

- silence threshold: `-35 dB`
- remove silences longer than `0.7s`
- keep `0.25s` of breathing room

If auto-cut fails, rendering continues with the original video. FFmpeg mode stays simple and reliable. Remotion mode supports richer route-line, passport-stamp, parchment-card, quest-banner, soft-zoom, and text match-cut style transitions.

## CLI examples

Help:

```bat
.venv\Scripts\python.exe -m hamsa_caption_engine --help
```

FFmpeg transcript mode:

```bat
.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --output-dir output --style game --transcript transcript.txt --thumbnail-at 00:00:01 --renderer ffmpeg
```

FFmpeg automatic Whisper mode:

```bat
.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --output-dir output_auto --style game --thumbnail-at 00:00:01 --renderer ffmpeg
```

Prompt mode:

```bat
.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --output-dir output_prompt --prompt "Make this a premium video game quest about asking for chamour in Paris. Add wrong-vs-right captions." --renderer remotion
```

Remotion recipe mode:

```bat
.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --output-dir output_remotion --recipe recipes\paris_chamour_game.json --renderer remotion
```

## Troubleshooting

Problem: `No module named hamsa_caption_engine`

Fix: run `install_windows.bat`. Make sure `run_bot.bat` uses `.venv\Scripts\python.exe`.

Problem: `faster-whisper` missing

Fix:

```bat
.venv\Scripts\python.exe -m pip install -e ".[whisper]"
```

Problem: FFmpeg missing

Fix: run `download_ffmpeg.bat` or put `ffmpeg.exe` and `ffprobe.exe` inside `tools\ffmpeg\bin\`.

Problem: Remotion missing

Fix:

```bat
cd remotion
npm install
```

Problem: Bot token missing

Fix: create `.env` with:

```env
HAMSA_TELEGRAM_BOT_TOKEN=...
```

## Test commands

```bat
.venv\Scripts\python.exe -m compileall src
.venv\Scripts\python.exe -m hamsa_caption_engine --help
.venv\Scripts\python.exe -c "import hamsa_caption_engine; print('package import works')"
.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; print('faster-whisper works')"
```
