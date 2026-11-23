import functools, http.server, json, socketserver, subprocess, threading
from playwright.sync_api import sync_playwright

ROOT = "/home/zoth/NullAITech/zoth-swarm-multiplexer/showcase"
OUT = f"{ROOT}/out"
with open(f"{ROOT}/narration/meta.json") as f:
    NARR = json.load(f)

FPS = 30
TARGETS = [
    ("s3_ov", round(NARR["s3"]["duration"] + 0.6, 2), True),
    ("s4_ov", round(NARR["s4"]["duration"] + 0.6, 2), True),
    ("s5", round(NARR["s5"]["duration"] + 0.6, 2), False),
]

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(f"http://127.0.0.1:{port}/stage.html", wait_until="networkidle")
    for sid, dur, alpha in TARGETS:
        total_frames = int(round(dur * FPS))
        out_path = f"{OUT}/{sid}.mov" if alpha else f"{OUT}/{sid}.mp4"
        cmd = (
            ["ffmpeg", "-y", "-f", "image2pipe", "-vcodec", "png", "-r", str(FPS), "-i", "-", "-c:v", "png", "-pix_fmt", "rgba", out_path]
            if alpha else
            ["ffmpeg", "-y", "-f", "image2pipe", "-vcodec", "png", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", out_path]
        )
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for i in range(total_frames):
            page.evaluate("([sid, t, d]) => window.renderScene(sid, t, d)", [sid, i / FPS, dur])
            proc.stdin.write(page.screenshot(type="png", omit_background=alpha))
        proc.stdin.close()
        proc.wait()
        print("Re-rendered", sid)
    browser.close()

d3, d4 = TARGETS[0][1], TARGETS[1][1]
for idx, dur in [("s3", d3), ("s4", d4)]:
    subprocess.run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", f"{ROOT}/recordings/{idx}_demo.mp4",
        "-i", f"{OUT}/{idx}_ov.mov",
        "-filter_complex", f"[0:v]trim=duration={dur},setpts=PTS-STARTPTS[bg];[bg][1:v]overlay=0:0:shortest=1[out]",
        "-map", "[out]", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", f"{OUT}/{idx}.mp4"
    ], check=True)

subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/concat.txt", "-c", "copy", f"{OUT}/video_silent.mp4"], check=True)
final_mp4 = f"{ROOT}/zoth_swarm_multiplexer_showcase.mp4"
subprocess.run([
    "ffmpeg", "-y", "-i", f"{OUT}/video_silent.mp4", "-i", f"{OUT}/audio_mix.wav",
    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-shortest", final_mp4
], check=True)
subprocess.run([
    "ffmpeg", "-y", "-i", final_mp4,
    "-vf", "select='isnan(prev_selected_t)+gte(t-prev_selected_t,13.5)',scale=960:540,tile=3x2",
    "-frames:v", "1", f"{ROOT}/contact_sheet.jpg"
], check=True)
subprocess.run(["cp", final_mp4, "/home/zoth/.gemini/antigravity-cli/brain/d85e179e-2943-486d-966e-a80c77e646e8/zoth_swarm_multiplexer_showcase.mp4"], check=True)
print("RE-RENDER COMPLETE")
