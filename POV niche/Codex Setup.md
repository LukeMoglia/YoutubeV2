# Use the POV workflow with Codex

This repository includes Codex skills in `.agents/skills/` alongside the original Claude Code command files. Open the repository root in Codex so it can discover the skills. You do not need Claude Code.

## One-time setup

Create `pov-automation/` in the repository root with:

```text
pov-automation/
├── .env
├── channel_config.txt
├── character/
│   └── character_ref.png
└── videos/
```

Use the example values and instructions in [Hierarchy_POV_Claude_Code_Automation_System_v38.md](Hierarchy_POV_Claude_Code_Automation_System_v38.md) for `channel_config.txt`, the protagonist reference, and API setup. Put API keys only in `pov-automation/.env`; do not paste them into Codex chat. Local configuration, the character image, and generated video assets are ignored by Git.

You need Python 3.12+, Git, and internet access. Codex replaces Claude Code as the workflow operator, while script generation still uses the Anthropic API specified by v38. Image generation uses Kie.ai; audio generation uses ElevenLabs. Install FFmpeg (which includes `ffprobe`) for subtitle timing; the optional automated MP4 workflow also uses `ffmpeg` itself.

## Invoke stages

In Codex, ask for the task or invoke the skill by name:

| Stage | Codex skill | What it does |
|---|---|---|
| Ideas | `$pov-ideas` | Proposes 20 topics without paid API calls |
| Script | `$pov-script` | Writes and validates the structured script JSON using the Anthropic API |
| Images | `$pov-images` | Generates/retries scene images through Kie.ai |
| Audio | `$pov-audio` | Generates per-scene ElevenLabs audio and the SRT |
| Optional MP4 | `$pov-final-video` | Generates missing audio and assembles a static MP4 with FFmpeg |

Example: `$pov-script Your Life as Every Rank in a Nuclear Submarine Crew`

Run stages in order: ideas, script, images, review and approve every image, then audio. Choose either manual CapCut assembly from raw images/audio or the optional FFmpeg output. The API stages consume provider credits or quota; the skills call this out before starting paid batches.

The `.md` files in `POV niche/` remain the workflow source documents. Codex skills translate their Claude-specific command and execution directions to Codex while preserving the existing API scripts and output paths.
