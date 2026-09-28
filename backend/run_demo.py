import os
import time

from playwright.sync_api import sync_playwright

VIDEO_DIR = "demo_recordings"
os.makedirs(VIDEO_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--start-maximized"])
    context = browser.new_context(
        record_video_dir=VIDEO_DIR,
        record_video_size={"width": 1920, "height": 1080},
        viewport={"width": 1920, "height": 1080},
    )
    page = context.new_page()

    page.goto("http://localhost:8000/docs")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    page.screenshot(path=f"{VIDEO_DIR}/01_swagger_ui_loaded.png", full_page=True)

    page.click("button:has-text('Authorize')")
    time.sleep(1)
    try:
        page.fill("input[placeholder='Username']", "admin@warestock.com")
        page.fill("input[placeholder='Password']", "Admin123!")
        page.click("button:has-text('Authorize')")
        time.sleep(2)
    except Exception:  # noqa: S110 — authorize dialog may already be open
        pass
    page.screenshot(path=f"{VIDEO_DIR}/02_authorized.png", full_page=True)

    page.goto("http://localhost:8000/docs")
    page.wait_for_load_state("networkidle")
    time.sleep(1)
    page.screenshot(path=f"{VIDEO_DIR}/03_swagger_home.png", full_page=True)

    sections = [
        ("Auth", "04_auth"),
        ("Users", "05_users"),
        ("Organisations", "06_organisations"),
        ("SKUs", "07_skus"),
        ("Locations", "08_locations"),
        ("Stock", "09_stock"),
        ("Alerts", "10_alerts"),
        ("Photo Count", "11_photo_count"),
        ("AI", "12_ai"),
        ("Platform", "13_platform"),
        ("RBAC", "14_rbac"),
    ]

    for section_name, screenshot_name in sections:
        try:
            page.click(f"text={section_name}")
            time.sleep(0.5)
            page.screenshot(path=f"{VIDEO_DIR}/{screenshot_name}.png", full_page=True)
        except Exception:  # noqa: S110 — section may not be present
            pass

    page.screenshot(path=f"{VIDEO_DIR}/15_end.png", full_page=True)

    time.sleep(1)
    context.close()
    browser.close()

print("Done!")
