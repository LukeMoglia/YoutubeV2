---
name: pov-final-video
description: Generate missing POV voiceover and assemble a static hard-cut MP4 with FFmpeg. Use when the user explicitly asks for automated final video assembly.
---

# Assemble a POV video with FFmpeg

Run the optional final workflow from `pov-automation/` at the repository root. Read source documents from the repository root; when your working directory is `pov-automation/`, prefix their paths with `../`.

## Instructions

1. Read `POV niche/generate_final_pov.md` and follow its current implementation exactly. It includes audio generation, per-scene clips, stream-copy concatenation, sync checks, and a separate SRT.
2. Check that the active script and all approved images exist. Stop and list missing scene numbers if the assets are incomplete.
3. Check `ELEVEN_LABS_API_KEY` and `ELEVEN_LABS_VOICE_ID` in `pov-automation/.env` by presence only. Never display or log secret values. Confirm `ffmpeg` and `ffprobe` are installed before starting.
4. This workflow may make billable ElevenLabs calls for any missing audio. Tell the user whether audio is missing and that the workflow may use their account quota before starting; proceed when they have requested this workflow.
5. Monitor each long-running process to completion. Do not use `-shortest`, burn subtitles into the video, or delete source assets. If interrupted, inspect generated files and logs before resuming.
6. Verify the resulting MP4, separate SRT, and audio/video sync checks. Warn that re-importing the finished MP4 into CapCut can cause drift; for manual editing, use `$pov-audio` and assemble the raw assets instead.
