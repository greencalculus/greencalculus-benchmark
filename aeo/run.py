#!/usr/bin/env python3
"""Ask every model every prompt. One JSON line per (model, prompt)."""
import json, os, sys, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from prompts import PROMPTS

OUT = Path(__file__).parent / "answers.jsonl"

def post(url, payload, headers, timeout=300):
    r = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                               headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def ask(model, prompt):
    if model.startswith("claude"):
        d = post("https://api.anthropic.com/v1/messages",
                 {"model": model, "max_tokens": 20000, "messages": [{"role": "user", "content": prompt}]},
                 {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"})
        return "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
    if model.startswith("gemini"):
        k = os.environ["GEMINI_API_KEY"]
        d = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={k}",
                 {"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"maxOutputTokens": 20000}}, {})
        c = d["candidates"][0]
        return "".join(p.get("text", "") for p in c.get("content", {}).get("parts", []))
    base, env = ("https://api.x.ai/v1", "XAI_API_KEY") if model.startswith("grok") \
                else ("https://api.openai.com/v1", "OPENAI_API_KEY")
    body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    body["max_completion_tokens" if "openai" in base else "max_tokens"] = 20000
    d = post(base + "/chat/completions", body, {"Authorization": f"Bearer {os.environ[env]}"})
    return d["choices"][0]["message"]["content"] or ""

def main():
    models = sys.argv[1:] or ["claude-opus-5", "gpt-5.5", "gemini-3.1-pro-preview",
                              "gemini-3.6-flash", "grok-4.6"]
    done = set()
    if OUT.exists():
        for l in OUT.open():
            if l.strip():
                r = json.loads(l); done.add((r["model"], r["prompt"]))
    t0 = time.time()
    with OUT.open("a") as fh:
        for model in models:
            for intent, prompt in PROMPTS:
                if (model, prompt) in done:
                    continue
                try:
                    text = ask(model, prompt)
                except Exception as e:
                    print(f"  {model:24} ERROR {str(e)[:70]}", flush=True); continue
                fh.write(json.dumps({"model": model, "intent": intent,
                                     "prompt": prompt, "answer": text}) + "\n")
                fh.flush()
                print(f"  {model:24} {intent:11} {len(text):>6} chars  ({time.time()-t0:.0f}s)", flush=True)
    print(f"\ndone in {time.time()-t0:.0f}s -> {OUT.name}")

if __name__ == "__main__":
    main()
