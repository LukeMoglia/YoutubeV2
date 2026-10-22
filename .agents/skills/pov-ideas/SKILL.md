---
name: pov-ideas
description: Generate topic ideas for the Hierarchy POV YouTube format. Use when the user asks for POV ideas, rank ladder topics, or "Your Life at Every Rank" titles.
---

# Generate Hierarchy POV ideas

Use this skill when working in the POV automation repository. The runnable project data belongs in `pov-automation/` at the repository root. Read source documents from the repository root; when your working directory is `pov-automation/`, prefix their paths with `../`.

## Instructions

1. Read `POV niche/generate_ideas_pov.md` for the canonical format and validation rules. If present, also read `pov-automation/channel_config.txt`, `pov-automation/videos/ideas_history.txt`, and `pov-automation/videos/worlds_covered.txt` before generating ideas. Missing history files mean there is no recorded history yet.
2. Generate 20 ideas, checking for near-duplicates against the history. Each idea must have a closed world, at least six ordered rungs, and an escalating personal cost.
3. Follow the source file's title, thumbnail, world-type, diversity, and output rules. Do not claim to have written history files; this stage only proposes ideas.
4. End by telling the user to invoke `$pov-script` with the chosen title. Do not refer to Claude Code slash commands.

This stage uses no paid API. Never read out or expose `.env` values.
