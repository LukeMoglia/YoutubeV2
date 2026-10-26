---
name: pov-script
description: Create a structured Hierarchy POV video script for a selected topic. Use when the user asks to write or generate a POV, ten-level, or rank-ladder script.
---

# Generate a Hierarchy POV script

The project data directory is `pov-automation/` at the repository root. Keep generated scripts and channel data there. Read source documents from the repository root; when your working directory is `pov-automation/`, prefix their paths with `../`.

## Instructions

For production isolation, save each draft as `videos/script_jobs/<unique-job-uuid>/script.json`, never a shared `codex_script_output.json` during concurrent work. Use the explicit production folder printed by the finalizer for downstream workers; the current-folder pointer is only an interactive convenience. Rendering is governed by `pov-automation/style/v1/STYLE_BIBLE.md`, not by shot-specific artistic modifiers. Preserve the local character bank and supply explicit per-level age layers and costumes.

1. Read `POV niche/generate_script_pov.md` for the canonical script format, JSON schema, validation, and file-writing behavior. Also read `POV niche/generate-script-pov-skill.md` for the creative style and quality checklist.
2. Use the user's selected topic. If none was provided, ask for one before generating.
3. Default to **Codex mode**: write the complete JSON directly with the current Codex model, following the creative prompt and schema in `POV niche/generate_script_pov.md`. No Anthropic API key or external model call is needed. Save raw JSON under `pov-automation/videos/`.
4. Run the shared finalizer from `pov-automation/`: `python "../POV niche/finalize_pov_script.py" --input <raw-json-path> --topic "<selected topic>"`. It validates the JSON and creates the standard video folder, current-folder pointer, script JSON, and history entry. Fix validation errors and rerun before reporting success.
5. If the user explicitly chooses Claude, use the Anthropic API implementation in `generate_script_pov.md`. Check only whether `ANTHROPIC_API_KEY` is present; never print it, include it in a command argument, or put it in logs. The Claude API call is billable.

Do not replace the script with a plain-text draft when the user needs the image/audio pipeline: downstream stages require the structured JSON and character bank.
