# Hamsa Caption Engine

A Windows-friendly local video caption engine for turning one MP4 in `input/` into a captioned vertical `1080x1920` MP4 in `output/`.

The tool uses **Python + FFmpeg + faster-whisper** locally. It does **not** use paid APIs, cloud transcription, or GPU-only features. Defaults are chosen for a weak Windows PC with Intel graphics: CPU transcription, `int8` inference, and an FFmpeg `veryfast` x264 render.

## What it creates

For one source MP4, the command writes:

- `output/captioned_vertical.mp4` — vertical 1080x1920 MP4 with burned-in captions.
- `output/captions.ass` — styled ASS subtitles.
- `output/thumbnail.jpg` — vertical thumbnail frame.
- `output/edit_plan.json` — reproducible edit metadata, commands, style, and caption segments.

## Caption styles

Choose one of these styles with `--style`:

- `game` — large yellow gaming-style captions with a heavy outline.
- `paris-tip` — soft pink editorial captions for travel/tip clips.
- `hamsa-clean` — clean white captions with a subtle outline.

## Exact Windows setup

These steps work in PowerShell on Windows 10 or Windows 11.

### 1. Install Python

1. Download Python 3.10 or newer from <https://www.python.org/downloads/windows/>.
2. Run the installer.
3. Check **Add python.exe to PATH**.
4. Click **Install Now**.
5. Open a new PowerShell window and verify:

```powershell
python --version
pip --version
```

### 2. Install FFmpeg

Recommended simple install with Winget:

```powershell
winget install --id Gyan.FFmpeg -e
```

Close and reopen PowerShell, then verify:

```powershell
ffmpeg -version
```

If `ffmpeg` is not found, reboot or add the FFmpeg `bin` folder to your Windows `Path` environment variable.

### 3. Prepare the project

From the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

If PowerShell blocks activation, run this once for your user account and try activation again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Add your input video

Put exactly one `.mp4` file in the `input` folder:

```text
input\your-video.mp4
```

The default command expects exactly one MP4 in `input/`.

### 5. Run the caption engine

Weak-PC recommended command:

```powershell
hamsa-caption --style hamsa-clean --model tiny.en
```

Other style examples:

```powershell
hamsa-caption --style game --model tiny.en
hamsa-caption --style paris-tip --model tiny.en
```

For better English accuracy on a PC that can wait longer:

```powershell
hamsa-caption --style hamsa-clean --model base.en
```

For non-English or automatic language detection:

```powershell
hamsa-caption --style hamsa-clean --model tiny --language auto
```

## Faster test without transcription

If you already have caption text and want to test rendering without downloading a Whisper model, create a UTF-8 text file where each non-empty line is one caption:

```powershell
@"
Welcome to the trip.
This is the first local caption render.
No paid APIs needed.
"@ | Set-Content .\sample-transcript.txt -Encoding UTF8

hamsa-caption --style game --transcript .\sample-transcript.txt
```

Transcript mode assigns each line a simple 3-second timing block. Full mode uses local Whisper transcription for real timestamps.

## Performance tips for weak Intel-graphics PCs

- Start with `--model tiny.en` for English clips.
- Use `--model tiny --language auto` only when language detection is needed.
- Close browsers and games before running transcription.
- Keep clips short while testing.
- The render uses CPU x264 instead of GPU-specific encoders so it works across more Windows machines.
- If the PC is very slow, use transcript mode while designing styles, then run Whisper only for final videos.

## CLI reference

```text
hamsa-caption [--input PATH] [--output-dir PATH] [--style STYLE]
              [--model MODEL] [--language LANG] [--thumbnail-at HH:MM:SS]
              [--transcript PATH]
```

Important options:

- `--input PATH` — process a specific MP4 instead of auto-detecting one file in `input/`.
- `--output-dir PATH` — choose an output folder; default is `output/`.
- `--style {game,paris-tip,hamsa-clean}` — caption look.
- `--model MODEL` — faster-whisper model; `tiny.en` is the weak-PC default recommendation.
- `--language LANG` — language code like `en`, or `auto` for detection.
- `--thumbnail-at HH:MM:SS` — frame timestamp for `thumbnail.jpg`.
- `--transcript PATH` — skip Whisper and create captions from text lines.

## Output details

The vertical conversion uses FFmpeg filters equivalent to:

```text
scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920
```

Captions are burned in from the generated ASS file so the final MP4 works on phones and social platforms without sidecar subtitle support.
