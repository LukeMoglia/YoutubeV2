Run the local Python generator from PowerShell or a monitored shell session. Keep the process visible and report progress until it completes; do not launch it detached without checking its output.

# Generate Audio Files for Each POV Scene

Generate one local expressive Chatterbox voiceover audio file per scene, plus one subtitle file you can upload to YouTube. Stop there. The user assembles the final video manually in CapCut, or runs `/generate_final_pov` for an automated assembly.

**No FFmpeg video assembly here. No clip concatenation. No final MP4.** This command ends at audio + subtitles.

## Scale Warning — Read Before Running

A POV video is **~250 scenes**, not ~120. That means:

- **~250 local synthesis runs.** Chatterbox loads one model and processes scenes sequentially; elapsed time depends on GPU support, VRAM, CPU, and scene text length.
- **~3,300 words ≈ 18,000 characters.** Text stays on this computer; local generation does not consume service quota.
- **Resumability is not optional.** The script skips any scene that already has an MP3 on disk. If it dies at scene 180, re-running it costs nothing for scenes 1–179.

Scenes run one at a time so they do not compete for GPU memory. CPU fallback is slower but preserves progress and output naming.

## STEP 1 — Read Active Video Folder and Verify Images

Read `videos/current_video_folder.txt` to get the active video folder path.

Read `[video_folder]/current_script.json` and extract:
- `total_scenes` — the actual number of scenes (do NOT assume any fixed number)
- The full scene list with voiceover text for each scene

Check that `[video_folder]/images/approved/` contains an image for every scene number from 1 to `total_scenes`.
If any are missing → tell the user exactly which scene numbers are missing and stop. Do not proceed to audio generation if images are incomplete.

## STEP 2 — Install Chatterbox Once

Use an isolated Python 3.12 environment so the audio model does not change the rest of the project. The GTX 1060 is a Pascal GPU, so pin PyTorch 2.6.0 with CUDA 12.4; newer prebuilt CUDA wheels may omit Pascal support. The project setup guide documents Python 3.12+. Run these commands from the repository root in PowerShell:

```powershell
py -3.12 -m venv pov-automation/chatterbox-env
pov-automation/chatterbox-env/Scripts/python.exe -m pip install --upgrade pip
pov-automation/chatterbox-env/Scripts/python.exe -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
pov-automation/chatterbox-env/Scripts/python.exe -m pip install chatterbox-tts==0.1.7
```

This installs the local runtime. Chatterbox downloads its model weights on the first generation run. After that, generation is local and does not use an ElevenLabs account or quota. Check whether CUDA is available with:

```powershell
pov-automation/chatterbox-env/Scripts/python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU fallback')"
```

The workflow tries the GTX 1060 when CUDA works. A 1060 came in 3 GB and 6 GB variants; if Chatterbox cannot load on CUDA or inference hits a recognized VRAM/compatibility error, the generator switches to CPU. Other scene inference errors are recorded as failures and do not trigger CPU fallback. CPU generation can take substantially longer. Keep `CHATTERBOX_DEVICE=auto` or leave it unset in `pov-automation/.env`.

## STEP 3 — Generate Voiceover for Each Scene

Use standard expressive Chatterbox (not Turbo). The approved narrator is conditioned on a 15-second excerpt beginning 60 seconds into the configured male reference recording. Set `CHATTERBOX_REFERENCE_OFFSET_SECONDS=60` and `CHATTERBOX_REFERENCE_AUDIO` in `pov-automation/.env`. Use `exaggeration=0.6` and `cfg_weight=0.3` to reduce clipped, rushed syllables while keeping the approved natural pace. Apply gentle EQ during WAV-to-MP3 conversion: `bass=g=1.1:f=160:w=0.7,treble=g=-0.6:f=5500`. Do not time-stretch the finished audio. The workflow runs scenes sequentially to avoid VRAM contention, validates existing MP3s before skipping them, and converts each generated WAV to `audio/scene_NNN.mp3` with FFmpeg.

If changing voices after generation, set `CHATTERBOX_FORCE_REGENERATE=true` in `pov-automation/.env` to replace every existing scene MP3 starting at scene 1. Remove or set it to `false` after generation so future runs can resume by skipping complete MP3s. The script extracts the configured reference excerpt and prepares Chatterbox conditionals once for the scene batch. Keep the approved natural phrasing edits in the active JSON for scenes 126, 140, 184, and 188.

Before generating, verify every approved image exists. Then run from the repository root:

```powershell
pov-automation/chatterbox-env/Scripts/python.exe pov-automation/generate_audio_chatterbox.py
```

The script checks image completeness, FFmpeg, and ffprobe; selects CUDA when available; falls back to CPU only for CUDA setup/compatibility or VRAM errors; and writes atomic per-scene MP3s. Once all scenes are ready, it rebuilds `final_output/subtitles.srt` using actual final MP3 durations and current voiceover text. Its final summary separates new files, valid skipped files, scene failures, device, and any fallback or setup failure. If interrupted, rerun the same command; valid finished MP3s are skipped, while partial or invalid files are regenerated. Check all failed scene numbers in the final summary and rerun after resolving any reported issue.
## STEP 4 — Subtitle File (generated by the script)

Generate one `.srt` covering all scenes in sequence. This file is **not burned into any video**. It exists so the user can upload it to YouTube as a caption track, which improves accessibility and gives YouTube a clean transcript to index.

Use `ffprobe` to measure each MP3's real duration. FFmpeg converts Chatterbox WAV output to MP3 in STEP 3; `ffprobe` reads the finished file metadata without encoding.

**A note on MP3 durations.** The encoded MP3 files can be slightly longer than the "natural" read — MP3 frames are padded to a fixed size. A 4.30-second read comes back as a 4.336-second file. Across 250 scenes those fractions sum to several seconds. Always measure with `ffprobe`; never estimate duration from word count.

```python
import subprocess, json, os

def get_audio_duration(filepath):
    """Read duration from the container format, not the stream. Some MP3s
    report a missing or zero stream duration while the format-level duration
    is correct."""
    result = subprocess.run([
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        filepath
    ], capture_output=True, text=True)
    info = json.loads(result.stdout)
    return float(info['format']['duration'])

def seconds_to_srt_time(seconds):
    """Convert seconds to SRT timestamp.

    Round to whole milliseconds FIRST, then decompose. Rounding each field
    separately lets a value like 59.9999 render as "00:00:60,000" — an invalid
    SRT timestamp that YouTube rejects outright. Integer division after a single
    round makes every carry (ms -> s -> m -> h) happen correctly.
    """
    total_ms = int(round(seconds * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms  = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

srt_lines = []
current_time = 0.0

for scene in scenes:
    n = scene['scene_number']
    audio_file = f"{video_folder}/audio/scene_{n:03d}.mp3"
    duration = get_audio_duration(audio_file)

    start = seconds_to_srt_time(current_time)
    end = seconds_to_srt_time(current_time + duration)

    srt_lines.append(str(n))
    srt_lines.append(f"{start} --> {end}")
    srt_lines.append(scene['voiceover'])
    srt_lines.append("")

    current_time += duration

os.makedirs(f'{video_folder}/final_output', exist_ok=True)
srt_path = f'{video_folder}/final_output/subtitles.srt'
with open(srt_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(srt_lines))

print(f"[OK] SRT subtitle file: {srt_path}")
print(f"     Total audio duration: {current_time:.1f} seconds ({current_time/60:.1f} minutes)")

if current_time < 1380:   # 23 minutes
    print(f"[WARN] Audio is only {current_time/60:.1f} min — target is ~25 min.")
    print(f"       The script may have come back short. Check the word count.")
```

**Important note about SRT timing.** This SRT assumes scenes are placed back-to-back with zero gap. That is exactly what `/generate_final_pov` does, so the timings will match its output.

If you instead assemble in CapCut and add transitions, pauses, or extra clips, these timings will drift. In that case either regenerate the SRT after the edit is locked, or let CapCut auto-caption the exported video.

## STEP 5 — No Cleanup. Keep Everything.

This command deletes nothing. The user needs everything on disk:

- `images/approved/` — all approved scene images
- `audio/` — all per-scene MP3 files **(KEPT)**
- `final_output/subtitles.srt` — subtitle file for YouTube upload
- `current_script.json` — original script

The `images/pending/` folder may be deleted if the user explicitly confirms all images are approved. That is the only optional cleanup.

## STEP 6 — Report Results

Output to the user, with concrete paths:

```
Audio generation complete.

Video folder: [video_folder]/

Files ready:
- Images:    [video_folder]/images/approved/   (N PNG files: scene_001.png -> scene_NNN.png)
- Audio:     [video_folder]/audio/             (N MP3 files: scene_001.mp3 -> scene_NNN.mp3)
- Subtitles: [video_folder]/final_output/subtitles.srt

Stats:
- Total scenes: [total_scenes]
- Combined audio duration: [min:sec]
- Audio provider: Chatterbox expressive (local)

Next step — pick one:

  A) Automated assembly:  run /generate_final_pov
     Produces final_video.mp4 with no subtitles burned in, no zoom effects.
     Upload subtitles.srt to YouTube separately as a caption track.

  B) Manual edit in CapCut:
     1. New project, 1920x1080, 30fps
     2. Drag all PNGs from images/approved/ into the timeline (auto-sorts by filename)
     3. Drag all MP3s from audio/ into the audio track (also auto-sorts)
     4. Match each image's duration to its audio clip (scene_001.png = scene_001.mp3)
     5. Do NOT import subtitles.srt into CapCut — upload it to YouTube instead
     6. Add intro, B-roll, music as needed, then export

YouTube metadata (from current_script.json):
- Title:          [title]
- Description:    [description]
- Thumbnail Text: [thumbnail_text]
- Hashtags:       [hashtags]

Cost of this run:
- Audio generation: local; no TTS account quota
- ffmpeg/ffprobe: local tools

If any scenes failed: they are listed above. Re-run `$pov-audio` — it skips
scenes that already have a valid MP3 and retries only the missing ones. CPU fallback and CUDA setup errors are reported separately.
```

Do not generate a video file here. The pipeline stops at audio and subtitles.
