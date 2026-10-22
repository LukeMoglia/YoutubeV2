---
name: pov-script
description: Create a structured Hierarchy POV video script for a selected topic. Use when the user asks to write or generate a POV, ten-level, or rank-ladder script.
---

# Generate a Hierarchy POV script

The project data directory is `pov-automation/` at the repository root. Keep generated scripts and channel data there. Read source documents from the repository root; when your working directory is `pov-automation/`, prefix their paths with `../`.

## Instructions

1. Read `POV niche/generate_script_pov.md` for the canonical script format, JSON schema, validation, and file-writing behavior. Also read `POV niche/generate-script-pov-skill.md` for the creative style and quality checklist.
2. Use the user's selected topic. If none was provided, ask for one before generating.
3. The canonical workflow calls the Anthropic API using `ANTHROPIC_API_KEY` from `pov-automation/.env`. Check only whether the required key is present; never print it, include it in a command argument, or put it in generated logs. If unavailable, explain that the user can configure it locally in that file.
4. Run from `pov-automation/` so relative input and output paths match the source instructions. Use the complete Python implementation in `generate_script_pov.md`; adapt Claude Code specific file-creation wording to the available Codex tools. Keep temporary runner code outside tracked source files.
5. The call is billable. Before making it, state that the Anthropic API will be used and wait for the user to request script generation if they only asked about setup or this skill.
6. Verify the script completed its structural checks and created the expected `videos/current_video_folder.txt`, script JSON, and history entry. Report any failed checks; do not claim completion if the command failed.

Do not replace the script with a plain-text draft when the user needs the image/audio pipeline: downstream stages require the structured JSON and character bank.
