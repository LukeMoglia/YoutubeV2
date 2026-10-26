---
name: pov-audio
description: Generate per-scene local expressive Chatterbox voiceover and the combined SRT for an active Hierarchy POV video. Use when asked to generate POV narration or audio.
---

# Generate POV audio and subtitles

Run the audio workflow from `pov-automation/` at the repository root. Read source documents from the repository root; when your working directory is `pov-automation/`, prefix their paths with `../`.

## Instructions

1. Read `POV niche/generate_audio_pov.md` and follow its expressive Chatterbox setup, device selection, output naming, and subtitle instructions.
2. Verify the active script and every approved image exist before generation. If any image is missing, report the scene numbers and stop. Confirm `ffmpeg` and `ffprobe` are available for MP3 conversion and validation.
3. Use standard expressive Chatterbox locally with the approved 15-second male reference clip beginning at 60 seconds, `exaggeration=0.6`, `cfg_weight=0.3`, and gentle EQ. Keep natural generated speed; do not time-stretch. Prefer CUDA and fall back to CPU on unsupported CUDA or GPU out-of-memory.
4. This stage runs locally and does not consume TTS account credits. If Chatterbox is not installed, follow the documented isolated-environment setup and install only the required local runtime/model.
5. Run scenes sequentially to avoid competing for the GTX 1060's VRAM. Monitor the same shell session to completion; if interrupted, inspect existing MP3s before resuming because completed scenes are skipped. Set `CHATTERBOX_FORCE_REGENERATE=true` in `.env` to replace all existing scene MP3s from scene 1, then remove or reset the setting after the run.
6. Verify per-scene audio and `final_output/subtitles.srt`, generated from final MP3 durations. Report missing or failed scenes. This stage does not assemble an MP4.
