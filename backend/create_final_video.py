import os

from moviepy import ImageClip, concatenate_videoclips, vfx
from PIL import Image, ImageDraw, ImageFont

FRAMES_DIR = "video_frames"
os.makedirs(FRAMES_DIR, exist_ok=True)

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


def create_text_slide(title: str, description: str, category: str, frame_num: int) -> str:
    W, H = 1920, 1080
    color = CATEGORY_COLORS.get(category, "#7f8c8d")
    img = Image.new("RGB", (W, H), color)
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/Arial.ttf", 58)
        font_body = ImageFont.truetype("C:/Windows/Fonts/Arial.ttf", 32)
        font_small = ImageFont.truetype("C:/Windows/Fonts/Arial.ttf", 24)
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

    y_pos = 140
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
        y_pos += 42

    footer_y = H - 50
    draw.text(
        (80, footer_y), f"WareStock AI v0.1.0  |  Feature: {title}", fill="#7f8c8d", font=font_small
    )
    draw.text((W - 280, footer_y), f"Slide {frame_num}", fill="#7f8c8d", font=font_small)

    filepath = os.path.join(FRAMES_DIR, f"slide_{frame_num:03d}.png")
    img.save(filepath)
    return filepath


def main() -> None:
    clips = []
    frame_num = 0

    frame_num += 1
    fp = create_text_slide(
        "WareStock AI",
        "AI-Powered Inventory Management SaaS Platform - End User Demo",
        "other",
        frame_num,
    )
    clips.append(ImageClip(fp).with_duration(4).with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)]))

    features = [
        (
            "Auth",
            "Register, Login, Logout, Refresh Tokens, Get Current User - JWT Authentication with RS256/HS256",
            "auth",
        ),
        (
            "Users",
            "User Management - Invite, Assign to Warehouse, Deactivate/Reactivate, Role-Based Access",
            "users",
        ),
        (
            "Organisations",
            "Multi-Tenant Organisation Management - Create, Update, Warehouses, Subscription",
            "organisation",
        ),
        (
            "Platform",
            "Superadmin - System Admins, Helpdesk, Impersonation, Audit Logs, Support Flags",
            "superadmin",
        ),
        (
            "RBAC",
            "Role-Based Access Control - Permissions, Roles, Temporal Permission Grants",
            "rbac",
        ),
        ("SKUs", "SKU Management - Create, Read, Update, Delete, Barcode Lookup", "skus"),
        ("Locations", "Warehouse Location Management - Create, Read, Update, Delete", "locations"),
        ("Stock", "Stock Tracking - Levels, Movements, Scan In/Out/Count/Image, Summary", "stock"),
        (
            "Alerts",
            "Reorder Alert System - List, Summary, Detail, Acknowledge, Background Monitoring",
            "alerts",
        ),
        (
            "Photo Count",
            "AI Photo Counting - Upload, Analysis, Discrepancy Detection, Item Extraction",
            "photo-count",
        ),
        ("AI/RAG", "AI RAG Pipeline - Semantic Search, Build Index, Natural Language Query", "ai"),
    ]

    for feature_name, description, category in features:
        frame_num += 1
        fp = create_text_slide(feature_name, description, category, frame_num)
        clips.append(
            ImageClip(fp).with_duration(5).with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)])
        )
        print(f"Created: {feature_name}")

    frame_num += 1
    fp = create_text_slide(
        "Features Complete",
        "All API features explored via Swagger Documentation - Full End-to-End Demo",
        "other",
        frame_num,
    )
    clips.append(ImageClip(fp).with_duration(4).with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)]))

    print(f"\nCompiling final video with {len(clips)} clips...")
    video = concatenate_videoclips(clips, method="compose")
    video.write_videofile("WareStock_AI_EndUser_Demo.mp4", fps=24, codec="libx264")
    print("Done: WareStock_AI_EndUser_Demo.mp4")


main()
