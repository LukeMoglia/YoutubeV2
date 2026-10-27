"""Validate a Codex-authored POV JSON script and add it to the video workspace."""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from collections import Counter
from datetime import date
from pathlib import Path

ALLOWED_STYLES = {"pov_scene", "world_scene", "object_scene", "cost_scene"}
FIXED_CORE = "completely bald with NO hair"
FRAME_RULE = "nothing cropped"
STYLE = "Clean 2D cartoon illustration, bold thick black outlines, flat color fills with soft cel shading, muted naturalistic palette (dusty blues, warm browns, sage greens, cream, charcoal — never neon, never oversaturated), soft ambient lighting with gentle directional light source, cinematic composition"
PROTAGONIST_CORE = "the protagonist (large rounded oval head with warm light-tan skin, completely bald with NO hair; a small rounded button nose, visible rounded ears, thick dark eyebrows, and a full expressive mouth; two small solid black oval eyes set wide apart, no visible whites; short thick neck; head roughly 35% of body height; average adult build)"
AGE_LAYERS = {
    1: "youthful smooth head, no lines, slightly rounder face, posture upright and slightly hunched with uncertainty",
    2: "youthful smooth head, no lines, slightly rounder face, posture upright and slightly hunched with uncertainty",
    3: "smooth head, faint eyebrow furrow, posture squared and confident",
    4: "smooth head, faint eyebrow furrow, posture squared and confident",
    5: "two faint horizontal forehead lines, slight shadow under the eyes, posture solid and settled",
    6: "two faint horizontal forehead lines, slight shadow under the eyes, posture solid and settled",
    7: "three visible forehead lines, deeper shadow under the eyes, faint vertical crease between the brows, shoulders beginning to round",
    8: "three visible forehead lines, deeper shadow under the eyes, faint vertical crease between the brows, shoulders beginning to round",
    9: "deep forehead lines, heavy under-eye shadow, pronounced brow crease, shoulders rounded, stance slightly stooped",
    10: "heavily lined head with deep creases across the forehead and around the eyes, sunken eye sockets, visibly stooped posture, slow careful stance",
}


def expand_compact_image_prompt(data: dict, scene: dict) -> None:
    """Turn Codex's concise scene direction into the full reusable image-prompt spine."""
    prompt = scene.get("image_prompt", "")
    if not isinstance(prompt, str) or STYLE in prompt:
        return
    style = scene.get("scene_style")
    detail = prompt.strip()
    shots = ("WIDE SHOT", "WIDE-MEDIUM SHOT", "MEDIUM SHOT", "OVER-THE-SHOULDER", "HIGH-ANGLE", "BIRD'S-EYE", "LOW-ANGLE")
    shot = shots[(scene.get("scene_number", 1) - 1) % len(shots)]
    lower_detail = detail.lower()
    if style == "cost_scene" or re.search(r"death|dead|loss|empty|absent|blood|grief|cough|leaves|missed", lower_detail):
        expression = "mouth turned down, inner eyebrows raised, eyes lowered and half-lidded"
    elif re.search(r"alarm|fear|darkness|breach|fall|threat|wound", lower_detail):
        expression = "mouth open in a small O, eyebrows raised and angled inward, eyes widened"
    elif re.search(r"smile|laugh|birdsong|sunlight|home|joy", lower_detail):
        expression = "mouth in a quiet closed-lip smile, eyebrows relaxed, eyes gently narrowed"
    elif re.search(r"order|command|inspect|hold|count|correct|carry|march", lower_detail):
        expression = "mouth pressed into a firm line, eyebrows angled inward, eyes steady"
    else:
        expression = "mouth a flat slack line, eyebrows heavy and level, eyes narrowed with exhaustion"
    if style == "pov_scene":
        costume = data["character_bank"].get("protagonist_costumes", {}).get(f"level_{scene['level']}")
        if not costume:
            raise ValueError(f"Missing explicit costume for level {scene['level']}; no topic fallback is safe")
        scene["image_prompt"] = (
            f"{STYLE}. {shot}. SETTING: {detail}. CHARACTER: {data['character_bank']['protagonist_fixed_core']}, "
            f"{script_age_layer(data['character_bank'], scene['level'])}, wearing {costume}. Action: {detail}. Expression: {expression}. "
            "full character fully inside frame with generous empty margin on all sides, head not touching the top edge, nothing cropped. "
            "Original character design — NOT Family Guy, Simpsons, South Park, or any animated TV show."
        )
    elif style == "cost_scene":
        costume = data["character_bank"].get("protagonist_costumes", {}).get(f"level_{scene['level']}")
        if not costume:
            raise ValueError(f"Missing explicit costume for level {scene['level']}; no topic fallback is safe")
        secondary = data["character_bank"].get("secondary_characters", {})
        with_part = ""
        match = re.search(r"\bWITH:\s*([^.;]+)", detail)
        if match:
            name = match.group(1).strip()
            appearance = next((v for k, v in secondary.items() if k.lower() == name.lower()), "")
            age_words = {
                "eight": 8, "eighteen": 18, "twenty": 20, "twenty-seven": 27,
                "twenty-nine": 29, "thirty-five": 35, "forty": 40,
                "forty-two": 42, "forty-eight": 48, "fifty": 50,
                "fifty-two": 52, "fifty-seven": 57, "sixty-two": 62,
            }
            voiceover = scene.get("voiceover", "")
            age_match = re.search(rf"\b{re.escape(name)},\s*([a-z-]+)", voiceover, re.I)
            if appearance and age_match and age_match.group(1).lower() in age_words:
                appearance = re.sub(
                    r"about \d+", f"about {age_words[age_match.group(1).lower()]}", appearance, count=1
                )
            with_part = f" WITH: {name}, {appearance}." if appearance else f" WITH: {name}."
        scene["image_prompt"] = (
            f"{STYLE}. TWO-SHOT ({shot}). SETTING: {detail}. PROTAGONIST: {data['character_bank']['protagonist_fixed_core']}, "
            f"{script_age_layer(data['character_bank'], scene['level'])}, wearing {costume}; expression: {expression}."
            f"{with_part} The secondary character's expression matches the moment, full face visible. Both characters fully inside frame with generous empty margin on all sides, head not touching the top edge, nothing cropped. "
            "Original character design — NOT Family Guy, Simpsons, South Park, or any animated TV show."
        )
    elif style == "world_scene":
        scene["image_prompt"] = (
            f"{STYLE}. {shot}. SETTING: {detail}. The protagonist does NOT appear. "
            "Any people have full normal faces, hair, noses, mouths, and ears. Everything fully inside frame with generous empty margin on all sides, nothing cropped. "
            "Original character design — NOT Family Guy, Simpsons, South Park, or any animated TV show."
        )
    elif style == "object_scene":
        scene["image_prompt"] = (
            f"{STYLE}. {shot}. SINGLE OBJECT: {detail}. NO PEOPLE in this frame. "
            "The object is centered and lit like evidence. Full object fully inside frame with generous empty margin on all sides, nothing cropped."
        )


def script_age_layer(bank: dict, level: int) -> str:
    layers = bank.get('protagonist_age_layers', {})
    group = f'level_{level}' if level >= 9 else f'level_{level if level % 2 else level-1}_{level+1 if level % 2 else level}'
    value = layers.get(str(level), layers.get(f'level_{level}', layers.get(group)))
    if not value:
        raise ValueError(f'Missing explicit age layer for level {level}')
    return value


def normalize_production_context(data: dict) -> dict:
    """Keep one explicit world's setting and exclusions with each production."""
    topic = str(data.get("topic", "")).strip()
    raw = data.get("production_context")
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("production_context must be an object")
    result = {
        "world": raw.get("world") or topic,
        "period": raw.get("period") or "Only the period explicitly named by this production's scenes; do not infer another era.",
        "setting": raw.get("setting") or topic,
        "required_visual_elements": raw.get("required_visual_elements") or [topic],
        "excluded_visual_elements": raw.get("excluded_visual_elements") or [
            "Any period, setting, character, costume, technology, architecture, symbol or prop not required by this production or current scene."
        ],
        "continuity": raw.get("continuity") or {},
    }
    for key in ("world", "period", "setting"):
        if not isinstance(result[key], str) or not result[key].strip():
            raise ValueError(f"production_context.{key} must be a non-empty string")
    for key in ("required_visual_elements", "excluded_visual_elements"):
        values = result[key]
        if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError(f"production_context.{key} must be a non-empty list of specific strings")
    if not isinstance(result["continuity"], dict):
        raise ValueError("production_context.continuity must be an object")
    data["production_context"] = result
    return result


def read_config(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Path to the model's JSON output")
    parser.add_argument("--topic", required=True, help="Selected video topic")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not read valid JSON from {args.input}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("ERROR: script JSON must be one object.", file=sys.stderr)
        return 1

    errors: list[str] = []
    scenes = data.get("scenes")
    if not isinstance(scenes, list):
        errors.append("scenes must be an array")
        scenes = []
    if data.get("topic") != args.topic:
        errors.append("topic field does not match --topic")
    bank = data.get("character_bank")
    if not isinstance(bank, dict):
        errors.append("character_bank must be an object")
    try:
        normalize_production_context(data)
    except ValueError as exc:
        errors.append(str(exc))

    numbers: list[int] = []
    levels: Counter[int] = Counter()
    styles: Counter[str] = Counter()
    words = 0
    level_positions: Counter[int] = Counter()
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            errors.append(f"scene {index} must be an object")
            continue
        number, level = scene.get("scene_number"), scene.get("level")
        if number is None:
            scene["scene_number"] = index
            number = index
        if scene.get("cta"):
            scene["scene_style"] = "pov_scene"
            scene["character"] = "main"
            scene.pop("cta", None)
        elif scene.get("scene_style") == "auto" and isinstance(level, int):
            level_positions[level] += 1
            position = level_positions[level]
            scene["scene_style"] = (
                "cost_scene" if position == 14 or (level in {4, 8} and position == 20) else
                "object_scene" if position in {15, 21} else
                "world_scene" if position in {4, 9, 19, 23} else
                "pov_scene"
            )
            scene["character"] = "none" if scene["scene_style"] == "object_scene" else (
                "supporting" if scene["scene_style"] == "world_scene" else "main"
            )
        if scene.get("scene_style") in ALLOWED_STYLES:
            scene.setdefault("character", {
                "pov_scene": "main",
                "cost_scene": "main",
                "world_scene": "supporting",
                "object_scene": "none",
            }[scene["scene_style"]])
        scene.setdefault("camera_effect", "static")
        scene.setdefault("duration_seconds", 6)
        if isinstance(level, int) and level in range(1, 11) and isinstance(bank, dict):
            try:
                expand_compact_image_prompt(data, scene)
            except (ValueError, KeyError) as exc:
                errors.append(f"scene {index}: {exc}")
        style, voiceover = scene.get("scene_style"), scene.get("voiceover")
        prompt = scene.get("image_prompt")
        if isinstance(number, int):
            numbers.append(number)
        else:
            errors.append(f"scene {index} has no integer scene_number")
        if isinstance(level, int) and level in range(1, 11):
            levels[level] += 1
        else:
            errors.append(f"scene {index} has invalid level")
        if style in ALLOWED_STYLES:
            styles[style] += 1
        else:
            errors.append(f"scene {index} has invalid scene_style")
        if isinstance(voiceover, str) and voiceover.strip():
            words += len(voiceover.split())
        else:
            errors.append(f"scene {index} has empty voiceover")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"scene {index} has empty image_prompt")
        elif scene.get("character") == "main" and FIXED_CORE not in prompt:
            errors.append(f"scene {index} is missing protagonist fixed core")
        ids = scene.get("secondary_character_ids")
        if ids is None:
            # Legacy scripts can be resumed; newly generated scripts should
            # explicitly list only the recurring characters visible in-frame.
            scene_text = f"{scene.get('voiceover', '')}\n{prompt or ''}"
            ids = [name for name in (bank.get("secondary_characters", {}) if isinstance(bank, dict) else {})
                   if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", scene_text, re.I)]
            scene["secondary_character_ids"] = ids
        if not isinstance(ids, list) or any(not isinstance(name, str) for name in ids):
            errors.append(f"scene {index} secondary_character_ids must be a list of character-bank names")
        elif isinstance(bank, dict) and any(name not in bank.get("secondary_characters", {}) for name in ids):
            errors.append(f"scene {index} references an unknown secondary-character ID")
        if isinstance(prompt, str) and FRAME_RULE not in prompt:
            errors.append(f"scene {index} is missing anti-crop phrase")

    if numbers != list(range(1, len(scenes) + 1)):
        errors.append("scene_number values must run consecutively from 1")
    if set(levels) != set(range(1, 11)):
        errors.append(f"all ten levels are required; found levels {sorted(levels)}")
    if len(scenes) < 235:
        errors.append(f"only {len(scenes)} scenes; minimum is 235")
    if words < 3100:
        errors.append(f"only {words} voiceover words; minimum is 3,100")
    if "The cycle continues." not in " ".join(
        scene.get("voiceover", "") for scene in scenes if isinstance(scene, dict)
    ):
        errors.append("the ring-closing line 'The cycle continues.' is missing")
    if isinstance(bank, dict):
        core = bank.get("protagonist_fixed_core", "")
        if not isinstance(core, str) or FIXED_CORE not in core:
            errors.append("character_bank.protagonist_fixed_core is missing the bald protagonist wording")

    if errors:
        print("Script validation failed:")
        for error in errors[:40]:
            print(f"- {error}")
        if len(errors) > 40:
            print(f"- ... and {len(errors) - 40} more issue(s)")
        return 1

    root = Path.cwd()
    video_root = root / "videos"
    config = read_config(root / "channel_config.txt")
    data["total_scenes"] = len(scenes)
    data.setdefault("channel_name", config.get("CHANNEL_NAME", "the channel"))
    slug = re.sub(r"[^a-z0-9\s-]", "", args.topic.lower())
    slug = re.sub(r"\s+", "-", slug.strip())[:40].strip("-") or "pov-video"
    # Date/topic alone collides on repeat or parallel runs and overwrites scripts.
    folder = video_root / f"{date.today().isoformat()}_{slug}_{uuid.uuid4().hex[:12]}"
    for subfolder in ("images/pending", "images/approved", "audio", "clips", "final_output"):
        (folder / subfolder).mkdir(parents=True, exist_ok=True)
    script_path = folder / "current_script.json"
    script_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    video_root.mkdir(parents=True, exist_ok=True)
    automation_root = Path(__file__).resolve().parents[1] / "pov-automation"
    sys.path.insert(0, str(automation_root))
    try:
        from style_pipeline import Production, active_style_root
        production = Production(folder, style=active_style_root())
        try:
            production.init()
        finally:
            production.close()
    except Exception as exc:
        print(f"ERROR: could not enroll this production in the locked style workflow: {exc}", file=sys.stderr)
        return 1
    pointer_temp = video_root / f".current_video_folder_{uuid.uuid4().hex}.tmp"
    pointer_temp.write_text(folder.as_posix(), encoding="utf-8")
    pointer_temp.replace(video_root / "current_video_folder.txt")
    history_line = f"{date.today().isoformat()} | {args.topic} | {data.get('thumbnail_text', '')}"
    history = video_root / "ideas_history.txt"
    existing = history.read_text(encoding="utf-8").splitlines() if history.exists() else []
    if history_line not in existing:
        with history.open("a", encoding="utf-8") as stream:
            stream.write(history_line + "\n")
    style_summary = ", ".join(f"{name}={count}" for name, count in sorted(styles.items()))
    print(f"Script saved: {script_path}")
    print("Style authority initialized; image generation must pass the review and batch-drift gates.")
    print(f"Scenes: {len(scenes)} | words: {words} | estimated length: {words / 130:.1f} min")
    print(f"Levels: 1-10 present | styles: {style_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
