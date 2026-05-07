# Hamsa Caption Engine

A simple Windows tool that turns one MP4 into a vertical `1080x1920` captioned video.

- Free and local.
- No paid APIs.
- Uses Python, FFmpeg, optional local `faster-whisper` captions, transcript mode, and optional Telegram Bot API access.
- Designed for weak Windows PCs with Intel graphics by defaulting to CPU-friendly settings.

## First-time setup

Double click:

```text
install_windows.bat
```

The installer creates `.venv`, updates pip, and installs the basic project first. Python 3.11 is recommended on Windows.

You also need FFmpeg. The easiest non-technical setup is to put `ffmpeg.exe` in the same folder as `run_hamsa.bat`.

If FFmpeg is missing, `install_windows.bat` prints instructions. If you use Winget, this command can install FFmpeg system-wide:

```powershell
winget install --id Gyan.FFmpeg -e
```


## Install modes

### Basic mode: no Whisper required

Basic mode is installed with:

```powershell
pip install -e .
```

This supports the CLI, recipes, ASS subtitle generation, FFmpeg rendering, transcript mode, Telegram bot code, and the optional Remotion project. It does **not** install `faster-whisper`, so it avoids the `ctranslate2` dependency conflict seen with older `faster-whisper` pins.

Use transcript mode in basic installs:

```powershell
.\.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --transcript input\transcript.txt
```

### AI transcription mode

AI transcription mode is optional and installs `faster-whisper>=1.1.1,<2`:

```powershell
pip install -e .[whisper]
```

If Whisper is not installed and you try automatic transcription, the tool will tell you to use `--transcript transcript.txt` or install with `pip install -e .[whisper]`.

### Python version

Python 3.11 is recommended. Python 3.11.14 is fine; the previous install problem was caused by dependency resolution around older `faster-whisper`/`ctranslate2` pins, not by Python 3.11.

## Everyday local use

### Step 1: put video in `input`

Put one `.mp4` file in this folder:

```text
input
```

Example:

```text
input\my-video.mp4
```

### Step 2: double click `run_hamsa.bat`

The batch file checks Python, checks FFmpeg, finds the first MP4 in `input`, and starts the caption workflow.

### Step 3: choose style

`run_hamsa.bat` asks you to choose:

```text
1 game
2 paris-tip
3 hamsa-clean
4 wrong-vs-right
5 video-game-dialogue
```

Then choose caption mode:

```text
1 Whisper mode      automatic local captions, slower
2 Transcript mode   use input\transcript.txt, faster
```

Basic mode works without Whisper and can render from `input\transcript.txt`. Whisper mode is fully local and free, but it needs the optional install: `pip install -e .[whisper]`. Transcript mode is best for weak PCs when you already typed the captions yourself.

### Step 4: get video from `output`

When the render finishes, the output folder opens automatically.

Files created:

```text
output\captioned_vertical.mp4
output\captions.ass
output\thumbnail.jpg
output\edit_plan.json
```

## Telegram bot use

The Telegram bot works in transcript mode first, so `faster-whisper` is still optional. It uses your local Windows PC, Python, and FFmpeg. No paid APIs are used.

### Create the bot in Telegram

1. Open Telegram and message `@BotFather`.
2. Send `/newbot`.
3. Follow BotFather's prompts.
4. Copy the bot token.

### Create `.env`

In the project root, create a file named `.env`:

```text
HAMSA_TELEGRAM_BOT_TOKEN=your_token_here
```

The `.env` file is ignored by git so your token is not committed.

### Run the bot on Windows

Double click:

```text
run_bot.bat
```

The batch file activates `.venv` if it exists, loads `.env`, and runs:

```bat
py -3.11 -m hamsa_caption_engine.telegram_bot
```

Keep that window open while using the bot.

### Use the bot step by step

1. Send `/start` or `/help`.
2. Send a video file or MP4 document. The bot saves it to `input\test.mp4`.
3. Send transcript text. The bot saves it to `transcript.txt`. You can also send `/render` to use an existing `transcript.txt`.
4. Choose a style with `/game`, `/paris`, or `/clean`.
5. The bot runs the same transcript-mode render command used by the one-click runner.
6. The bot sends back `output\final_video.mp4` and also sends `output\thumbnail.jpg` if it exists.

Use `/status` any time to check whether the bot sees the video, transcript, selected style, and final output. If rendering fails, the bot sends a simple error and saves full logs to `logs\bot_render.log`.

## Transcript mode

Create this file:

```text
input\transcript.txt
```

Put one caption per line:

```text
Welcome to the trip.
This is the easiest local render mode.
No paid APIs needed.
```

Then double click `run_hamsa.bat` and choose transcript mode.



## Prompt-driven editing

The tool is **not one fixed template** applied to every video. It now works as a small local recipe engine:

```text
user prompt + video + optional transcript
→ edit_recipe.json
→ FFmpeg render
→ branded Hamsa Nomads video
```

Use a prompt to let the tool draft a recipe locally with simple free rules:

```powershell
.\.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --prompt "Make this feel like a video game quest about ordering kosher croissants in Paris. Use wrong-vs-right captions and a funny Jewish travel tone."
```

The local recipe builder detects style hints and keywords like `Paris`, `game`, `wrong/right`, `luxury`, `retreat`, and `storytime`. It chooses a caption style, creates intro-card text, chooses a CTA, stores keyword highlights, and keeps the edit inside the Hamsa Nomads brand identity. No paid APIs are used.

If no brand is provided, `hamsa` is used by default. You can also force the brand and style explicitly:

```powershell
.\.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --style paris-tip --brand hamsa
```

To add a 1.5-second branded title card before the video, use:

```powershell
.\.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --style wrong-vs-right --intro-card "Stop saying this in France"
```

The intro card uses a cream/parchment background, imperfect route line, `JEWISH TRAVEL NOTE` label, big title text, and small Hamsa Nomads logo text before transitioning into the video. It is generated with FFmpeg, not Adobe, Premiere, After Effects, or paid tools.

To render from a manual recipe:

```powershell
.\.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --recipe examples\recipes\paris_game_quest.json
```

A recipe can control:

- `project_title`
- `video_goal`
- `style` and `tone`
- `intro_card`
- `captions`
- `overlays`
- `keyword_highlights`
- `zooms`
- `screenshots`
- `thumbnail`
- `cta`
- `output_settings`

Example recipes live in:

```text
examples\recipes
```

Current rendering uses the recipe for style choice, optional intro card, manual captions, overlay text, screenshot exports, thumbnail timing/name, CTA metadata, and output settings. Zoom fields are included in the schema so recipes can describe richer edits while remaining brand-consistent and Windows-friendly.


## Optional Remotion renderer

FFmpeg remains the default renderer and is still the best weak-PC fallback. Remotion is optional for more designed videos and future cloud rendering. Recipes can choose either renderer:

```json
"renderer": "ffmpeg"
```

or:

```json
"renderer": "remotion"
```

### Windows Remotion setup

1. Install Node.js LTS from <https://nodejs.org/>.
2. Open Command Prompt in this project folder.
3. Install the optional Remotion project dependencies:

```bat
cd remotion
npm install
cd ..
```

### Render with Remotion

Use a recipe that has `"renderer": "remotion"`, or override the renderer from the command line:

```powershell
.\.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --recipe recipes\paris_chamour_game.json
```

```powershell
.\.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --prompt "Make this a premium video game dialogue quest in Paris" --renderer remotion
```

The Remotion renderer reads `edit_recipe.json` and supports vertical `1080x1920` output, phone video, Hamsa Nomads colors/type, animated intro cards, video-game dialogue captions, wrong-vs-right overlays, passport-stamp overlays, route-line motifs, a CTA end card, and JSON-driven timing.

If Node/Remotion is not installed or the PC is too weak, use the default FFmpeg renderer:

```powershell
.\.venv\Scripts\python.exe -m hamsa_caption_engine --input input\test.mp4 --recipe examples\recipes\wrong_vs_right_chamour.json --renderer ffmpeg
```

No paid APIs are used in either renderer. Remotion mode is simply the more designed local renderer; FFmpeg mode remains the lightweight fallback. Python dependencies stay in `pyproject.toml` and `requirements.txt`; Remotion dependencies stay in `remotion/package.json` and are installed separately with `npm install`.

## Brand Identity

Every generated video uses the Hamsa Nomads brand system from:

```text
brand\hamsa_nomads_brand.json
```

The brand system defines the warm travel palette (`warm_cream`, `ivory_parchment`, `sand`, `clay`, `olive_sage`, and `ink_black`), typography choices with fallbacks, and the rules for the visual identity. Caption styles are designed to feel warm, human, documentary, natural, connected, and grounded for a Jewish travel network.

The ASS subtitle generator uses that system for all styles:

- `hamsa-clean` uses cream/parchment boxes, ink black text, and subtle olive/clay details.
- `paris-tip` adds a `PARIS TIP` passport-note label with sand/clay accents.
- `game` is a warm travel quest card with labels like `QUEST UNLOCKED` and `LOCAL TIP`, not neon arcade styling.
- `wrong-vs-right` colors wrong phrases in clay and correct phrases in olive/sage.
- `video-game-dialogue` uses a premium adventure dialogue box with a cream surface and clay/olive border feeling.

The visual signature is an imperfect route/path line with passport/map-inspired motifs. The system intentionally avoids corporate, glossy, neon, childish, or cheap CapCut-style effects. It remains plain FFmpeg + ASS subtitles, so it works locally on Windows without Adobe, Premiere, After Effects, or paid APIs.

## Caption styles

See the visual style guide here:

```text
styles\README.md
```

Available styles:

- `game`
- `paris-tip`
- `hamsa-clean`
- `wrong-vs-right`
- `video-game-dialogue`

## Weak PC tips

- Start with `hamsa-clean` and transcript mode on weak PCs, then install `.[whisper]` only if you want automatic transcription.
- Use transcript mode for quick tests.
- Keep test clips short.
- Close browsers and games before Whisper mode if you install the optional `.[whisper]` extra.
- Rendering uses CPU x264 settings instead of paid APIs or GPU-only encoders.
- The Telegram bot processes one video at a time to avoid overloading the PC.

## Advanced command-line use

After running `install_windows.bat`, you can also use:

```powershell
.\.venv\Scripts\python.exe -m hamsa_caption_engine --style hamsa-clean --model tiny.en
```

Or with transcript mode:

```powershell
.\.venv\Scripts\python.exe -m hamsa_caption_engine --style game --transcript input\transcript.txt
```

To choose a custom output MP4 name:

```powershell
.\.venv\Scripts\python.exe -m hamsa_caption_engine --style hamsa-clean --video-name final_video.mp4
```
