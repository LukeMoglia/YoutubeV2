"""Create a branded, repeatable YouTube thumbnail for the active POV video."""
from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

WIDTH = 1280
HEIGHT = 720
FONT_PATH = Path("C:/Windows/Fonts/impact.ttf")
FALLBACK_FONT_PATH = Path("C:/Windows/Fonts/ariblk.ttf")


def read_channel_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.is_file():
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def color(value: str, default: str) -> tuple[int, int, int]:
    candidate = value.strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{6}", candidate):
        return tuple(int(candidate[i:i + 2], 16) for i in (0, 2, 4))
    fallback = default.lstrip("#")
    return tuple(int(fallback[i:i + 2], 16) for i in (0, 2, 4))


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.upper().split()
    if not words:
        raise ValueError("The active script has empty thumbnail_text.")
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if line and font.getlength(candidate) > max_width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def make_thumbnail(folder: Path, channel_config_path: Path) -> Path:
    """Compose the channel's fixed thumbnail layout from scene 1 and script text."""
    script_path = folder / "current_script.json"
    image_path = folder / "images" / "approved" / "scene_001.png"
    if not script_path.is_file() or not image_path.is_file():
        raise FileNotFoundError(f"Thumbnail needs {script_path} and {image_path}.")
    script = json.loads(script_path.read_text(encoding="utf-8"))
    headline = re.sub(r"\s+", " ", str(script.get("thumbnail_text", ""))).strip()
    if not headline:
        raise ValueError("The active script must define thumbnail_text before video assembly.")

    settings = read_channel_config(channel_config_path)
    white = color(settings.get("BRAND_COLOR_PRIMARY", "#FFFFFF"), "#FFFFFF")
    dark = color(settings.get("BRAND_COLOR_SECONDARY", "#1A1A1A"), "#1A1A1A")
    accent = color(settings.get("BRAND_COLOR_ACCENT", "#E63946"), "#E63946")
    channel_name = settings.get("CHANNEL_NAME", "Bald Life POV").strip().upper()

    source = Image.open(image_path).convert("RGB")
    # Use a fixed 1.2x zoom anchored at the upper left: the protagonist grows
    # and moves right, leaving a predictable left column for headline text.
    zoom_w = int(WIDTH * 1.2)
    zoom_h = int(HEIGHT * 1.2)
    zoomed = ImageOps.fit(
        source, (zoom_w, zoom_h), method=Image.Resampling.LANCZOS,
        centering=(0.0, 0.0),
    )
    image = zoomed.crop((0, 0, WIDTH, HEIGHT)).convert("RGBA")

    # A fixed left-side dark gradient protects text contrast while leaving the
    # scene's protagonist and period details prominent on the right.
    shade = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = shade.load()
    for x in range(WIDTH):
        strength = max(0.0, min(0.74, 0.74 * (1.0 - x / 760)))
        alpha = int(255 * strength)
        for y in range(HEIGHT):
            pixels[x, y] = (*dark, alpha)
    image = Image.alpha_composite(image, shade)
    draw = ImageDraw.Draw(image)

    try:
        badge_font = ImageFont.truetype(str(FONT_PATH), 30)
        font_file = FONT_PATH if FONT_PATH.exists() else FALLBACK_FONT_PATH
        headline_font = ImageFont.truetype(str(font_file), 116)
    except OSError:
        badge_font = headline_font = ImageFont.load_default()

    margin_x = 58
    badge_text = channel_name or "BALD LIFE POV"
    badge_width = min(520, int(draw.textlength(badge_text, font=badge_font)) + 48)
    draw.rounded_rectangle((margin_x, 50, margin_x + badge_width, 102), radius=10, fill=accent)
    draw.text((margin_x + 24, 57), badge_text, fill=white, font=badge_font)

    max_text_width = 575
    while headline_font.size > 66:
        lines = wrap_text(headline, headline_font, max_text_width)
        bbox_heights = [draw.textbbox((0, 0), line, font=headline_font, stroke_width=5)[3]
                        - draw.textbbox((0, 0), line, font=headline_font, stroke_width=5)[1]
                        for line in lines]
        if len(lines) <= 3 and sum(bbox_heights) + 18 * (len(lines) - 1) <= 435:
            break
        headline_font = ImageFont.truetype(str(font_file), headline_font.size - 4)
    lines = wrap_text(headline, headline_font, max_text_width)
    line_heights = [draw.textbbox((0, 0), line, font=headline_font, stroke_width=5)[3]
                    - draw.textbbox((0, 0), line, font=headline_font, stroke_width=5)[1]
                    for line in lines]
    gap = 12
    total_height = sum(line_heights) + gap * (len(lines) - 1)
    y = max(155, min(HEIGHT - total_height - 50, (HEIGHT - total_height) // 2 + 26))
    for index, (line, line_height) in enumerate(zip(lines, line_heights)):
        line_color = accent if index == len(lines) - 1 else white
        draw.text(
            (margin_x, y), line, fill=line_color, font=headline_font,
            stroke_width=5, stroke_fill=dark,
        )
        y += line_height + gap

    output_dir = folder / "final_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "thumbnail.png"
    image.convert("RGB").save(output_path, format="PNG", optimize=True)
    return output_path


def write_upload_metadata(folder: Path) -> Path:
    """Write a copy-ready text file of the active video's YouTube metadata."""
    script_path = folder / "current_script.json"
    if not script_path.is_file():
        raise FileNotFoundError(f"Upload metadata needs {script_path}.")
    script = json.loads(script_path.read_text(encoding="utf-8"))
    title = str(script.get("title", "")).strip()
    description = str(script.get("description", "")).strip()
    thumbnail_text = str(script.get("thumbnail_text", "")).strip()
    hashtags = script.get("hashtags", [])
    if not title or not description:
        raise ValueError("The active script must define both title and description.")
    if isinstance(hashtags, str):
        hashtags = hashtags.split()
    hashtags = [str(tag).strip() for tag in hashtags if str(tag).strip()]

    sections = [
        "YOUTUBE UPLOAD METADATA",
        "",
        "TITLE",
        title,
        "",
        "DESCRIPTION",
        description,
        "",
        "HASHTAGS (already included in the description above)",
        " ".join(hashtags),
        "",
        "THUMBNAIL TEXT",
        thumbnail_text,
    ]
    output_dir = folder / "final_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "upload_metadata.txt"
    output_path.write_text("\n".join(sections) + "\n", encoding="utf-8", newline="\n")
    return output_path


def main() -> int:
    root = Path(__file__).resolve().parent
    pointer = root / "videos" / "current_video_folder.txt"
    if not pointer.is_file():
        raise FileNotFoundError(f"Active video pointer is missing: {pointer}")
    folder = Path(pointer.read_text(encoding="utf-8-sig").strip())
    if not folder.is_absolute():
        folder = root / folder
    output_path = make_thumbnail(folder.resolve(), root / "channel_config.txt")
    print(f"Thumbnail: {output_path}")
    print(f"Size: {WIDTH}x{HEIGHT}")
    metadata_path = write_upload_metadata(folder.resolve())
    print(f"Upload metadata: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
