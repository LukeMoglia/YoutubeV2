---
name: pov-final-video
description: Assemble the active Hierarchy POV project into an MP4 with black level title cards, gentle Ken Burns zoom, burned-in captions, a separate SRT, and a consistently branded thumbnail. Use when asked for automated final video assembly.
---

# Assemble a POV video with FFmpeg

Read `POV niche/generate_final_pov.md` and follow it. The audio stage has already been run by `$pov-audio`; this workflow assembles the finished scene MP3s and approved images.

1. Verify the active script, every approved image, every scene MP3, and `ffmpeg`/`ffprobe`. If any assets are missing, list the scene numbers and stop.
2. Run `pov-automation/chatterbox-env/Scripts/python.exe pov-automation/generate_final_video.py` from the repository root. The script inserts a black card before each level, showing only its level label and name for at least two seconds and long enough to finish the full spoken heading. It splits the first scene's existing narration after the rank name, at the pause before the next sentence; the scene image begins with that next sentence. Burned-in scene captions omit the heading, while the separate SRT includes it timed to the card. Each scene gets a gentle centered Ken Burns zoom, then clips are joined in order. The same run creates `final_output/thumbnail.png` from the first approved scene and `thumbnail_text` using the channel's fixed layout and brand colors, plus `final_output/upload_metadata.txt` with the title, description, hashtags, and thumbnail text.
3. Keep the final video, SRT, thumbnail, and upload metadata. The script leaves approved images and scene audio untouched. It uses per-scene render markers to resume completed clips after interruption.
4. Monitor the full render and report progress. Verify the MP4, SRT block count, duration, audio/video sync, and thumbnail dimensions/readability before reporting completion.
5. Warn the user that re-importing and re-encoding the final MP4 in CapCut may cause timing drift. If they want further editing, they should use raw image/audio assets and add captions/effects in CapCut instead.
