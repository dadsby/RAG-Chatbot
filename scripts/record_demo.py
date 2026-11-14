"""Record the README demo: docs/demo.gif plus screenshots, straight from the running app.

1. Start the app in one terminal:   python -m uvicorn api.main:app --port 8000
2. Once (installs a browser for automation, ~150 MB):
       pip install playwright pillow
       python -m playwright install chromium
3. In a second terminal:             python scripts/record_demo.py

It opens the app in a hidden browser, types a question, waits for the real answer, clicks a
citation, opens the retrieved passages and switches to German, capturing frames along the way.
The waiting time for the answer is sped up in the GIF (the README says so).

Output: docs/demo.gif, docs/screenshot-light.png, docs/screenshot-dark-mobile.png
If you set APP_PASSWORD, pass it:    python scripts/record_demo.py --password yourpassword
"""

import argparse
import io
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
QUESTION = "How many times can I retake a failed exam?"   # English question, German source: shows cross-language
MOBILE_QUESTION = "Was kostet das Parkticket für Studierende?"
GIF_WIDTH = 960


class Recorder:
    def __init__(self, page):
        self.page = page
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []

    def snap(self, ms: int = 100):
        img = Image.open(io.BytesIO(self.page.screenshot())).convert("RGB")
        if self.frames and img.tobytes() == self.frames[-1].tobytes():
            self.durations[-1] += ms          # same picture as before: just show it longer
        else:
            self.frames.append(img)
            self.durations.append(ms)

    def hold(self, seconds: float, ms: int = 100):
        """Capture in real time for `seconds`."""
        end = time.time() + seconds
        while time.time() < end:
            self.snap(ms)

    def wait_for(self, selector: str, timeout: float = 180, every: float = 0.6, shown_ms: int = 90):
        """Wait for an element; frames are taken every `every` s but shown for `shown_ms` (= sped up)."""
        end = time.time() + timeout
        while time.time() < end:
            if self.page.locator(selector).count():
                return
            self.snap(shown_ms)
            time.sleep(every)
        raise TimeoutError(f"{selector} didn't appear within {timeout} s. Is the app (and Ollama) running?")

    def type(self, text: str, every: int = 3):
        for i, ch in enumerate(text, 1):
            self.page.keyboard.type(ch, delay=25)
            if i % every == 0:
                self.snap(70)

    def save_gif(self, path: Path):
        frames = []
        for img in self.frames:
            h = round(img.height * GIF_WIDTH / img.width)
            small = img.resize((GIF_WIDTH, h), Image.LANCZOS)
            frames.append(small.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=self.durations,
                       loop=0, optimize=True, disposal=1)


def answer_selector():
    return ".a-body, .refusal, .error"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--password", default=None)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    creds = {"username": "demo", "password": args.password} if args.password else None

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- desktop, light, English: the GIF
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, color_scheme="light",
                                  locale="en-US", http_credentials=creds)
        page = ctx.new_page()
        page.goto(args.url, wait_until="networkidle")
        page.evaluate("localStorage.setItem('lang','en'); localStorage.setItem('theme','light')")
        page.reload(wait_until="networkidle")
        page.wait_for_selector(".doc")                      # library loaded
        rec = Recorder(page)

        rec.hold(0.3); rec.durations[-1] = 1400             # opening view
        page.click("#question")
        rec.type(QUESTION)
        rec.snap(500)
        page.keyboard.press("Enter")
        rec.wait_for(answer_selector())
        rec.snap(2600)                                      # read the answer

        if page.locator(".cite").count():
            page.locator(".cite").first.click()
            rec.hold(0.35, ms=40)                           # panel slides in
            rec.snap(2600)
            page.screenshot(path=str(OUT / "screenshot-light.png"))
            page.click("#panel-close")
            rec.snap(300)

        page.locator(".sources-toggle").last.click()
        rec.hold(0.2, ms=40)
        rec.snap(2000)
        page.click('[data-lang="de"]')                      # same screen in German
        rec.hold(0.25, ms=40)
        rec.snap(2200)

        rec.save_gif(OUT / "demo.gif")
        size_mb = (OUT / "demo.gif").stat().st_size / 1e6
        print(f"docs/demo.gif: {len(rec.frames)} frames, {size_mb:.1f} MB")
        if not (OUT / "screenshot-light.png").exists():
            page.screenshot(path=str(OUT / "screenshot-light.png"))
        ctx.close()

        # ---------- phone, dark, German: one screenshot
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                                  has_touch=True, color_scheme="dark", locale="de-AT", http_credentials=creds)
        page = ctx.new_page()
        page.goto(args.url, wait_until="networkidle")
        page.evaluate("localStorage.setItem('lang','de'); localStorage.setItem('theme','dark')")
        page.reload(wait_until="networkidle")
        page.fill("#question", MOBILE_QUESTION)
        page.keyboard.press("Enter")
        page.wait_for_selector(answer_selector(), timeout=180_000)
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "screenshot-dark-mobile.png"))
        ctx.close()
        browser.close()

    print("Saved docs/screenshot-light.png and docs/screenshot-dark-mobile.png")


if __name__ == "__main__":
    main()
