import asyncio
import json
import os

import httpx
from moviepy import ImageClip, concatenate_videoclips, vfx
from PIL import Image, ImageDraw, ImageFont

BASE = "http://localhost:8000"
FRAMES_DIR = "video_frames"
os.makedirs(FRAMES_DIR, exist_ok=True)

with open("openapi.json") as f:
    spec = json.load(f)

paths = spec.get("paths", {})

CATEGORY_COLORS = {
    "auth": "#e74c3c",
    "stock": "#3498db",
    "skus": "#2ecc71",
    "locations": "#9b59b6",
    "alerts": "#e67e22",
    "photo-count": "#1abc9c",
    "ai": "#34495e",
    "platform": "#c0392b",
    "rbac": "#8e44ad",
    "users": "#16a085",
    "organisation": "#27ae60",
    "superadmin": "#8b4513",
    "other": "#7f8c8d",
}


def get_category(tags: list[str]) -> str:
    t = tags[0].lower() if tags and tags[0] else "other"
    for key in CATEGORY_COLORS:
        if key in t:
            return key
    return "other"


async def explore_features() -> dict[str, list[dict[str, str]]]:
    async with httpx.AsyncClient():
        categories = {}
        for path, methods in sorted(paths.items()):
            for method, detail in sorted(methods.items()):
                if method == "get":
                    continue
                cat = get_category(detail.get("tags", ["general"]))
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(
                    {
                        "method": method.upper(),
                        "path": path,
                        "summary": detail.get("summary", ""),
                        "tag": detail.get("tags", ["general"])[0],
                    }
                )
        return categories


def create_slide(
    title: str,
    description: str,
    endpoints: list[dict[str, str]],
    category: str,
    frame_num: int,
) -> str:
    W, H = 1920, 1080
    color = CATEGORY_COLORS.get(category, "#7f8c8d")
    img = Image.new("RGB", (W, H), color)
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/Arial.ttf", 54)
        font_body = ImageFont.truetype("C:/Windows/Fonts/Arial.ttf", 30)
        font_small = ImageFont.truetype("C:/Windows/Fonts/Arial.ttf", 22)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_over = ImageDraw.Draw(overlay)
    draw_over.rectangle([0, 0, 12, H], fill=color)
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.text((80, 50), title.upper(), fill="white", font=font_title)

    y_pos = 130
    wrapped_lines = []
    words = description.split()
    line = ""
    for word in words:
        test = line + " " + word if line else word
        if draw.textlength(test, font=font_body) < 1700:
            line = test
        else:
            wrapped_lines.append(line)
            line = word
    if line:
        wrapped_lines.append(line)
    for wl in wrapped_lines[:3]:
        draw.text((80, y_pos), wl, fill="#ecf0f1", font=font_body)
        y_pos += 40

    y_start = 250
    for i, ep in enumerate(endpoints[:10]):
        method = ep["method"]
        path = ep["path"]
        summary = ep.get("summary", "")

        method_colors = {
            "GET": "#27ae60",
            "POST": "#3498db",
            "PUT": "#f39c12",
            "PATCH": "#9b59b6",
            "DELETE": "#e74c3c",
        }
        mc = method_colors.get(method, "#7f8c8d")

        x = 80 + (i % 2) * 880
        y = y_start + (i // 2) * 110

        method_img = Image.new("RGB", (150, 48), mc)
        method_draw = ImageDraw.Draw(method_img)
        method_draw.text((10, 10), method, fill="white", font=font_small)
        img.paste(method_img, (x, y))

        text_x = x + 165
        full_text = f"{path}  —  {summary}"
        lines = []
        current = ""
        for w in full_text.split():
            test = current + " " + w if current else w
            if draw.textlength(test, font=font_body) < 720:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        for li, line_text in enumerate(lines[:2]):
            draw.text((text_x, y + 5 + li * 30), line_text, fill="#ecf0f1", font=font_body)

    if len(endpoints) > 10:
        draw.text(
            (80, y_start + 6 * 110 + 10),
            f"... and {len(endpoints) - 10} more endpoints",
            fill="#bdc3c7",
            font=font_body,
        )

    footer_y = H - 50
    draw.text(
        (80, footer_y), f"WareStock AI v0.1.0  |  Feature: {title}", fill="#7f8c8d", font=font_small
    )
    draw.text((W - 280, footer_y), f"Slide {frame_num}", fill="#7f8c8d", font=font_small)

    filepath = os.path.join(FRAMES_DIR, f"slide_{frame_num:03d}.png")
    img.save(filepath)
    return filepath


async def main() -> None:
    categories = await explore_features()

    print(f"Found {len(categories)} feature categories")
    for cat, eps in sorted(categories.items()):
        print(f"  {cat}: {len(eps)} endpoints")

    frame_num = 0
    clips = []

    frame_num += 1
    fp = create_slide(
        "WareStock AI", "AI-Powered Inventory Management SaaS Platform", [], "other", frame_num
    )
    clips.append(ImageClip(fp).with_duration(3).with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)]))

    for cat, eps in sorted(categories.items()):
        frame_num += 1
        fp = create_slide(cat.capitalize(), f"{len(eps)} API endpoints", eps, cat, frame_num)
        clips.append(
            ImageClip(fp).with_duration(5).with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)])
        )
        print(f"Created slide {frame_num}: {cat}")

    frame_num += 1
    fp = create_slide(
        "Features Complete",
        "All API features explored via Swagger Documentation",
        [],
        "other",
        frame_num,
    )
    clips.append(ImageClip(fp).with_duration(3).with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)]))

    print(f"\nCompiling video with {len(clips)} clips...")
    video = concatenate_videoclips(clips, method="compose")
    video.write_videofile("WareStock_AI_Features_Walkthrough.mp4", fps=24, codec="libx264")
    print("Done: WareStock_AI_Features_Walkthrough.mp4")


asyncio.run(main())
