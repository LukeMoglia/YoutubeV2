# Use the POV workflow with Codex

This repository includes Codex skills in `.agents/skills/` alongside the original Claude Code command files. Open the repository root in Codex so it can discover the skills. You do not need Claude Code.

## One-time setup

To walk through a fresh clone interactively, open the repository root in Codex
and run `$pov-setup`. It configures local channel settings and identifies
personal assets or optional tools still needed without installing heavy audio
models or calling content providers.

The clone already contains `pov-automation/`. Add the local files used by your
channel inside it:

```text
pov-automation/
├── .env                         # optional; only needed for Claude API use
├── channel_config.txt           # channel name and local settings
└── character/
    └── character_ref.png        # your protagonist reference for image generation
```

Generated productions are saved under the ignored `pov-automation/videos/`
folder. The script workflow creates it as needed; create it manually before
saving a draft job there if you are preparing one by hand.

For Codex script generation, no API key is required: Codex writes the structured JSON, then a local Python finalizer validates and saves it. Set `CHANNEL_NAME` in `channel_config.txt` (the default `the channel` is accepted). Keep the protagonist reference at `character/character_ref.png` for image generation. Local configuration, the character image, and generated video assets are ignored by Git.

You need Python 3.12+, Git, and internet access. Codex is the default script writer. Anthropic API generation remains optional; add `ANTHROPIC_API_KEY` to `.env` only if you choose Claude. Image generation uses Kie.ai. Audio uses Chatterbox Turbo locally; it can use an NVIDIA GPU when compatible and falls back to CPU. Install FFmpeg (which includes `ffprobe`) for MP3 conversion and subtitle timing; the optional automated MP4 workflow also uses `ffmpeg` itself.

## Invoke stages

In Codex, ask for the task or invoke the skill by name:

| Stage | Codex skill | What it does |
|---|---|---|
| Ideas | `$pov-ideas` | Proposes 20 topics without paid API calls |
| Script | `$pov-script` | Writes and validates structured script JSON with Codex by default; Claude API is optional |
| Images | `$pov-images` | Generates/retries scene images through Kie.ai |
| Audio | `$pov-audio` | Generates per-scene Chatterbox Turbo audio locally and the SRT |
| Optional final video | `$pov-final-video` | Assembles the MP4 with title cards, Ken Burns motion, and captions; outputs an SRT, branded thumbnail, and copy-ready upload metadata |

Example: `$pov-script Your Life as Every Rank in a Nuclear Submarine Crew`

Run stages in order: ideas, script, images, review and approve every image, then audio. Choose either manual CapCut assembly from raw images/audio or the optional FFmpeg output. The final-video workflow also creates `final_output/thumbnail.png` using the channel's configured red, white, and near-black house style, and `final_output/upload_metadata.txt` with the title, description, hashtags, and thumbnail text. Image generation and optional Claude API calls may consume provider credits or quota; local Chatterbox audio does not. Codex script generation uses your current Codex session.

The `.md` files in `POV niche/` remain the workflow source documents. Codex skills preserve their format and output paths while allowing Codex or the optional Anthropic API to write scripts. The local Chatterbox Python environment is stored in `pov-automation/chatterbox-env/` and ignored by Git.
