# Generate the Final POV Video (Ken Burns + Burned-In Captions)

Use this optional final stage after scene images and audio are ready. It creates a ready-to-upload MP4 with a plain black level card before each level, held for at least two seconds and long enough for the narrator to finish the full level heading. It adds gentle Ken Burns zoom on every scene and burns in narration as styled captions. Each card shows only the level label and level name while the narrator says both the level and rank name. The first scene then begins with the next sentence; the heading is not repeated in the scene caption. The separate YouTube SRT includes both parts at their matching times. It also creates a thumbnail in the channel's fixed house style and a copy-ready YouTube metadata text file every time the final video workflow runs.

## Requirements

- Every scene has an image in `images/approved/` and an MP3 in `audio/`.
- The dedicated `pov-automation/chatterbox-env` exists (audio generation is done by `$pov-audio` first).
- `ffmpeg` and `ffprobe` are available on PATH.

## Run

From the repository root, run:

```powershell
$env:PATH = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin;$env:PATH"
pov-automation/chatterbox-env/Scripts/python.exe pov-automation/generate_final_video.py
```

The script reads the active folder from `pov-automation/videos/current_video_folder.txt`, validates every required image and MP3, then renders each scene as a 1920×1080, 30 fps clip. Before each level's first scene, it inserts a black title card with two centered lines: `LEVEL [NUMBER]` and the rank/name. Each card lasts at least two seconds and extends as needed to fit the full spoken heading. The workflow splits the first scene's existing narration after the level and rank name, at the pause before the next sentence; that opening plays over the card, and the scene clip starts with the next sentence. Each still receives a slow centered zoom. Scene captions show the remaining narration in bold white text with a black outline near the bottom. The SRT keeps the heading timed to the card and the rest timed to its scene.

The clips are concatenated in scene order. `-shortest` is not used, so the audio is not cut to the video frame grid. Per-scene render markers let the script resume finished clips after an interruption. It does not delete or modify approved images or source audio.

## Thumbnail house style

Every final video run creates `final_output/thumbnail.png` (1280×720) using `thumbnail_text` from `current_script.json`, the first approved scene image, and brand colors from `pov-automation/channel_config.txt`. The layout stays consistent across videos: full-bleed scene art with a 1.2× upper-left crop that keeps the protagonist prominent on the right; a dark left-side gradient; a red channel-name badge in the upper-left; and large uppercase Impact text on the left, white with the final line in the configured accent color and a dark outline. The image generator uses the approved scene as its visual, so the thumbnail stays in the video's established illustration style. The exact text is typeset locally for legibility; it does not rely on generated lettering.

## Outputs

- `final_output/final_video.mp4` — Ken Burns motion and captions burned into the picture.
- `final_output/subtitles.srt` — separate YouTube caption file, timed against the rendered clips.
- `final_output/thumbnail.png` — 1280×720 thumbnail in the consistent channel house style.
- `final_output/upload_metadata.txt` — copy-ready title, description, hashtags, and thumbnail text.
- `clips/scene_NNN.mp4` — intermediate clips, retained so an interrupted run can resume.

Check the reported scene count, duration, and audio/video sync before uploading. The final MP4 is already rendered; re-importing and re-encoding it in CapCut can cause timing drift. If you want to add an intro, music, or B-roll in CapCut, assemble from the raw approved images and audio instead.
