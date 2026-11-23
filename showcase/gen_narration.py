import json, wave, numpy as np
from kokoro_onnx import Kokoro

MODEL = "/home/zoth/.local/share/zoth-tts/kokoro-v1.0.onnx"
VOICES = "/home/zoth/.local/share/zoth-tts/voices-v1.0.bin"
kokoro = Kokoro(MODEL, VOICES)
voices = kokoro.get_voices()
voice = "am_michael" if "am_michael" in voices else ("am_adam" if "am_adam" in voices else voices[0])
print("Using voice:", voice)

LINES = [
    ("s1", "One terminal is never enough. Meet the Zoth 21-Agent Swarm Multiplexer, taking your workflow from zero to hero with Ghostbyte leading the Pantheon."),
    ("s2", "Built on a local-first loopback daemon at port 8141, it puts Antigravity with 27 frontier models and Hermes Agent with Nous Portal and custom models front and center, alongside Codex, Claude Code, OpenCode, and Ollama."),
    ("s3", "Watch it live. Pick any harness and model per agent, type a directive, and the multiplexer spawns a real PTY terminal using Ducky-script automation: spawn, wait, inject prompt, hit enter, and stream the response live over Server-Sent Events."),
    ("s4", "Need the whole Pantheon moving at once? Hit Broadcast to Swarm to launch parallel PTY terminals across all 21 agents, or filter instantly by Cadre: Architects, Code, Security, Creative, and Swarm."),
    ("s5", "From parallel security audits and multi-model code consensus, to zero-egress local memory sync and one-click Markdown transcript exports, every tool is unlocked and built for Zoth Studio and ZothOS."),
    ("s6", "Twenty-one autonomous agents. One sovereign command deck. Launch Zoth Swarm Multiplexer today at nullai.tech.")
]

meta = {}
for key, text in LINES:
    samples, sr = kokoro.create(text, voice=voice, speed=1.06, lang="en-us")
    pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
    out_wav = f"/home/zoth/NullAITech/zoth-swarm-multiplexer/showcase/narration/{key}.wav"
    with wave.open(out_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    dur = len(samples) / sr
    meta[key] = {"file": out_wav, "duration": round(dur, 3), "sr": sr, "text": text}
    print(f"{key}: {dur:.2f}s")

with open("/home/zoth/NullAITech/zoth-swarm-multiplexer/showcase/narration/meta.json", "w") as f:
    json.dump(meta, f, indent=2)
