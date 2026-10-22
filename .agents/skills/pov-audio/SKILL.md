---
name: pov-audio
description: Generate per-scene ElevenLabs voiceover and the combined SRT for an active Hierarchy POV video. Use when asked to generate POV narration or audio.
---

# Generate POV audio and subtitles

Run the audio workflow from `pov-automation/` at the repository root. Read source documents from the repository root; when your working directory is `pov-automation/`, prefix their paths with `../`.

## Instructions

1. Read `POV niche/generate_audio_pov.md` and follow its current implementation, voice settings, timeout handling, and output naming.
2. Verify the active script and every approved image exist before making requests. If any image is missing, report the scene numbers and stop.
3. Check for `ELEVEN_LABS_API_KEY` and `ELEVEN_LABS_VOICE_ID` in `pov-automation/.env` by presence only. Never display or log their values.
4. This stage sends narration text to ElevenLabs and uses account quota or credits. Before starting a batch, tell the user the scene count and that it consumes ElevenLabs quota; proceed when the user has requested audio generation.
5. Run with the source's bounded concurrency. Monitor the same shell session to completion; if interrupted, inspect existing MP3s before retrying because completed scenes are skipped.
6. Verify per-scene audio and `final_output/subtitles.srt`. Report missing or failed scenes. This stage does not assemble an MP4.
