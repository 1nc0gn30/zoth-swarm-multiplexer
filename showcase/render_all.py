import functools, http.server, json, os, socketserver, subprocess, sys, threading, time
import numpy as np
import wave
from playwright.sync_api import sync_playwright

ROOT = "/home/zoth/NullAITech/zoth-swarm-multiplexer/showcase"
OUT = f"{ROOT}/out"
os.makedirs(OUT, exist_ok=True)

with open(f"{ROOT}/narration/meta.json") as f:
    NARR = json.load(f)

SCENES = [
    ("s1", round(NARR["s1"]["duration"] + 0.6, 2), False),
    ("s2", round(NARR["s2"]["duration"] + 0.6, 2), False),
    ("s3_ov", round(NARR["s3"]["duration"] + 0.6, 2), True),
    ("s4_ov", round(NARR["s4"]["duration"] + 0.6, 2), True),
    ("s5", round(NARR["s5"]["duration"] + 0.6, 2), False),
    ("s6", round(NARR["s6"]["duration"] + 0.8, 2), False),
]
FPS = 30

# Start static HTTP server for stage.html + ghostGeometry.js
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()

def render_scene_video(page, scene_id, dur, alpha):
    total_frames = int(round(dur * FPS))
    if alpha:
        out_path = f"{OUT}/{scene_id}.mov"
        cmd = [
            "ffmpeg", "-y", "-f", "image2pipe", "-vcodec", "png", "-r", str(FPS),
            "-i", "-", "-c:v", "png", "-pix_fmt", "rgba", out_path
        ]
    else:
        out_path = f"{OUT}/{scene_id}.mp4"
        cmd = [
            "ffmpeg", "-y", "-f", "image2pipe", "-vcodec", "png", "-r", str(FPS),
            "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "16",
            "-pix_fmt", "yuv420p", out_path
        ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(total_frames):
        t = i / FPS
        page.evaluate("([sid, t, d]) => window.renderScene(sid, t, d)", [scene_id, t, dur])
        png = page.screenshot(type="png", omit_background=alpha)
        proc.stdin.write(png)
    proc.stdin.close()
    proc.wait()
    print(f"Rendered {scene_id} ({total_frames} frames, {dur}s) -> {out_path}")

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/usr/bin/google-chrome",
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(f"http://127.0.0.1:{port}/stage.html", wait_until="networkidle")
    for sid, dur, alpha in SCENES:
        render_scene_video(page, sid, dur, alpha)
    browser.close()

# Composite s3 and s4 screen recordings with Ghostbyte 3D overlays
d3 = dict((s[0], s[1]) for s in SCENES)["s3_ov"]
d4 = dict((s[0], s[1]) for s in SCENES)["s4_ov"]

subprocess.run([
    "ffmpeg", "-y",
    "-stream_loop", "-1", "-i", f"{ROOT}/recordings/s3_demo.mp4",
    "-i", f"{OUT}/s3_ov.mov",
    "-filter_complex", f"[0:v]trim=duration={d3},setpts=PTS-STARTPTS[bg];[bg][1:v]overlay=0:0:shortest=1[out]",
    "-map", "[out]", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
    f"{OUT}/s3.mp4"
], check=True)

subprocess.run([
    "ffmpeg", "-y",
    "-stream_loop", "-1", "-i", f"{ROOT}/recordings/s4_demo.mp4",
    "-i", f"{OUT}/s4_ov.mov",
    "-filter_complex", f"[0:v]trim=duration={d4},setpts=PTS-STARTPTS[bg];[bg][1:v]overlay=0:0:shortest=1[out]",
    "-map", "[out]", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
    f"{OUT}/s4.mp4"
], check=True)

# Concat s1..s6 video
ORDER = ["s1", "s2", "s3", "s4", "s5", "s6"]
concat_list = f"{OUT}/concat.txt"
with open(concat_list, "w") as f:
    for sid in ORDER:
        f.write(f"file '{OUT}/{sid}.mp4'\n")

silent_video = f"{OUT}/video_silent.mp4"
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
    "-c", "copy", silent_video
], check=True)

# Build mixed audio: Kokoro narration + subtle procedural ambient synth bed + transition whooshes
SR = 24000
durs = {
    "s1": SCENES[0][1],
    "s2": SCENES[1][1],
    "s3": SCENES[2][1],
    "s4": SCENES[3][1],
    "s5": SCENES[4][1],
    "s6": SCENES[5][1],
}
total_dur = sum(durs[k] for k in ORDER)
total_samples = int(total_dur * SR)
t_arr = np.arange(total_samples, dtype=np.float32) / SR

# Warm cyberpunk ambient pad (D2, A2, F#3, C#4) at low ducked level
pad = (
    0.28 * np.sin(2 * np.pi * 73.42 * t_arr) +
    0.22 * np.sin(2 * np.pi * 110.00 * t_arr) +
    0.16 * np.sin(2 * np.pi * 185.00 * t_arr) +
    0.12 * np.sin(2 * np.pi * 277.18 * t_arr)
) * (0.65 + 0.35 * np.sin(2 * np.pi * 0.18 * t_arr))
# Fade in/out bed
fade_in = np.minimum(1.0, t_arr / 1.5)
fade_out = np.minimum(1.0, (total_dur - t_arr) / 2.0)
bed = pad * fade_in * fade_out * 0.09

narr_track = np.zeros(total_samples, dtype=np.float32)
cursor = 0.0
for sid in ORDER:
    start_s = int((cursor + 0.2) * SR)
    with wave.open(NARR[sid]["file"], "rb") as wf:
        raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    end_s = min(total_samples, start_s + len(raw))
    narr_track[start_s:end_s] += raw[:end_s - start_s]
    # Add subtle transition chime at each scene boundary
    if cursor > 0.5:
        cs = int(cursor * SR)
        clen = min(int(0.45 * SR), total_samples - cs)
        ct = np.arange(clen, dtype=np.float32) / SR
        chime = np.sin(2 * np.pi * 587.33 * ct) * np.exp(-ct * 8.0) * 0.12
        bed[cs:cs + clen] += chime
    cursor += durs[sid]

# Duck bed where narration is active
env = np.convolve(np.abs(narr_track), np.ones(int(0.15 * SR)) / (0.15 * SR), mode="same")
duck = np.clip(1.0 - env * 2.5, 0.35, 1.0)
mixed = np.clip(narr_track * 0.92 + bed * duck, -0.96, 0.96)
pcm = (mixed * 32767.0).astype(np.int16)

mix_wav = f"{OUT}/audio_mix.wav"
with wave.open(mix_wav, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(pcm.tobytes())

final_mp4 = f"{ROOT}/zoth_swarm_multiplexer_showcase.mp4"
subprocess.run([
    "ffmpeg", "-y", "-i", silent_video, "-i", mix_wav,
    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
    "-shortest", final_mp4
], check=True)
print("FINAL SHOWCASE READY:", final_mp4)
