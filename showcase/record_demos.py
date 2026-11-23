import os, subprocess, time
from playwright.sync_api import sync_playwright

REC_DIR = "/home/zoth/NullAITech/zoth-swarm-multiplexer/showcase/recordings"
os.makedirs(REC_DIR, exist_ok=True)

daemon = subprocess.Popen(
    ["python3", "swarm_daemon.py", "--port", "8149"],
    cwd="/home/zoth/NullAITech/zoth-swarm-multiplexer",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(1.5)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        # --- DEMO 1: Harness selection + Single Agent PTY Ducky Spawn ---
        ctx1 = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=REC_DIR,
            record_video_size={"width": 1920, "height": 1080},
        )
        page1 = ctx1.new_page()
        page1.goto("http://127.0.0.1:8149/", wait_until="networkidle")
        page1.wait_for_timeout(1200)

        # Select Antigravity (agy) model on AZOTH
        page1.select_option("#model-select-AZOTH", index=1)
        page1.wait_for_timeout(900)

        # Switch NEXUS harness to hermes-agent and pick a Nous Portal model
        page1.select_option("#card-NEXUS select:first-of-type", "hermes-agent")
        page1.wait_for_timeout(1000)
        page1.select_option("#model-select-NEXUS", index=0)
        page1.wait_for_timeout(900)

        # Type directive in NEXUS and click RUN
        inp = page1.locator("#input-NEXUS")
        inp.click()
        inp.type("Reply with DUCKY_PTY_LIVE_OK", delay=45)
        page1.wait_for_timeout(600)
        page1.locator("#card-NEXUS button:has-text('RUN')").click()
        page1.wait_for_timeout(8500)

        v1 = page1.video.path()
        ctx1.close()

        # --- DEMO 2: Global Swarm Broadcast + Cadre Filtering ---
        ctx2 = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=REC_DIR,
            record_video_size={"width": 1920, "height": 1080},
        )
        page2 = ctx2.new_page()
        page2.goto("http://127.0.0.1:8149/", wait_until="networkidle")
        page2.wait_for_timeout(1000)

        b_inp = page2.locator("#global-broadcast-input")
        b_inp.click()
        b_inp.type("verify zero-egress && status", delay=40)
        page2.wait_for_timeout(600)
        page2.locator("button:has-text('Broadcast to Swarm')").click()
        page2.wait_for_timeout(4500)

        # Filter cadres smoothly
        for label in ["Architects", "Security", "Code", "All Agents"]:
            btn = page2.locator(f"button.cadre-btn:has-text('{label}')")
            if btn.count() > 0:
                btn.first.click()
                page2.wait_for_timeout(1800)

        v2 = page2.video.path()
        ctx2.close()
        browser.close()

    # Convert to clean 1920x1080 30fps mp4
    for src, dst in [(v1, f"{REC_DIR}/s3_demo.mp4"), (v2, f"{REC_DIR}/s4_demo.mp4")]:
        subprocess.run([
            "ffmpeg", "-y", "-i", src,
            "-vf", "fps=30,scale=1920:1080",
            "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
            dst
        ], check=True)
        print("Saved", dst)
finally:
    daemon.terminate()
    daemon.wait(timeout=5)
