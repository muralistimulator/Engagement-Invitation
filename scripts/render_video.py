import asyncio
import os
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
RECORDINGS = OUTPUT / "recordings"
OUTPUT.mkdir(exist_ok=True)
RECORDINGS.mkdir(exist_ok=True)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

def serve():
    os.chdir(ROOT)
    ThreadingHTTPServer(("127.0.0.1", 8000), QuietHandler).serve_forever()

async def main():
    threading.Thread(target=serve, daemon=True).start()
    await asyncio.sleep(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            record_video_dir=str(RECORDINGS),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        await page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        await page.wait_for_timeout(3500)

        sections = await page.locator("section").count()
        for i in range(sections):
            await page.locator("section").nth(i).scroll_into_view_if_needed()
            await page.wait_for_timeout(3500)

        await page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        await page.wait_for_timeout(1500)
        video = page.video
        await page.close()
        video_path = await video.path()
        await context.close()
        await browser.close()

    target = OUTPUT / "engagement-invitation.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-an", str(target)
    ], check=True)
    print(f"Created {target}")

if __name__ == "__main__":
    asyncio.run(main())
