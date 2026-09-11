#!/usr/bin/env python3
"""The SEARCH-ENABLED arm: the same 25 prompts, with web access switched ON.

The baseline (run.py) measures what a model BELIEVES — fixed at training time,
and the surface no amount of work in 2026 can move. This arm measures what a
model can FIND, which responds to work in weeks. They are different questions
and they get reported side by side, never merged.

The prompts are byte-identical to the baseline. Never edit them: a changed
instrument measures nothing.

EVERY ROW RECORDS WHETHER THE MODEL ACTUALLY SEARCHED. A provider that silently
ignores the tool would otherwise produce answers indistinguishable from the
baseline, and the arm would report "no change" when it had simply not run. The
flag comes from the provider's own response structure, not from the prose.
"""
import json, os, re, sys, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from prompts import PROMPTS

OUT = Path(__file__).parent / "search_answers.jsonl"
URL_RE = re.compile(r'https?://[^\s\)\]"<>]+')


def post(url, payload, headers, timeout=600):
    r = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                               headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _usage(d, provider):
    """Normalise each provider's usage block.

    Recorded because the first costing of this arm had to BRACKET Anthropic's
    input tokens rather than state them — the harness threw the numbers away.
    Search results are injected into context, so input tokens are the whole
    cost story; without this a re-run cannot be priced from evidence.
    """
    u = d.get("usage") or {}
    if provider == "gemini":
        u = d.get("usageMetadata") or {}
        return {"input": u.get("promptTokenCount"), "output": u.get("candidatesTokenCount"),
                "total": u.get("totalTokenCount")}
    return {"input": u.get("input_tokens"), "output": u.get("output_tokens"),
            "cached": u.get("cache_read_input_tokens") or (u.get("input_tokens_details") or {}).get("cached_tokens"),
            "server_tool": u.get("server_tool_use")}


def ask_claude(model, prompt):
    d = post("https://api.anthropic.com/v1/messages",
             {"model": model, "max_tokens": 16000,
              "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
              "messages": [{"role": "user", "content": prompt}]},
             {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"})
    blocks = d["content"]
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    n = sum(1 for b in blocks if b.get("type") == "server_tool_use")
    urls = []
    for b in blocks:
        if b.get("type") == "web_search_tool_result":
            for r in (b.get("content") or []):
                if isinstance(r, dict) and r.get("url"):
                    urls.append(r["url"])
    return text, n, urls, _usage(d, "anthropic")


def ask_gemini(model, prompt):
    k = os.environ["GEMINI_API_KEY"]
    d = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={k}",
             {"contents": [{"parts": [{"text": prompt}]}],
              "tools": [{"google_search": {}}],
              "generationConfig": {"maxOutputTokens": 16000}}, {})
    c = d["candidates"][0]
    text = "".join(p.get("text", "") for p in c.get("content", {}).get("parts", []))
    gm = c.get("groundingMetadata") or {}
    n = len(gm.get("webSearchQueries") or [])
    urls = [ch.get("web", {}).get("uri", "") for ch in (gm.get("groundingChunks") or [])]
    # Gemini returns vertexaisearch redirect URLs; the readable domain is in .title
    urls += [ch.get("web", {}).get("title", "") for ch in (gm.get("groundingChunks") or [])]
    return text, n, [u for u in urls if u], _usage(d, "gemini")


def ask_grok(model, prompt):
    # Live Search (search_parameters) was deprecated 410 — this is the Agent Tools route.
    d = post("https://api.x.ai/v1/responses",
             {"model": model, "input": prompt, "tools": [{"type": "web_search"}]},
             {"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"})
    out = d.get("output", [])
    text = "".join(c.get("text", "") for o in out if o.get("type") == "message"
                   for c in (o.get("content") or []) if c.get("type") in ("output_text", "text"))
    n = sum(1 for o in out if o.get("type") == "web_search_call")
    urls = URL_RE.findall(json.dumps(out))
    return text, n, urls, _usage(d, "xai")


def ask(model, prompt):
    if model.startswith("claude"):
        return ask_claude(model, prompt)
    if model.startswith("gemini"):
        return ask_gemini(model, prompt)
    if model.startswith("grok"):
        return ask_grok(model, prompt)
    raise ValueError(f"no search route for {model}")   # gpt-5.5: account out of credits


def main():
    models = sys.argv[1:] or ["claude-opus-5", "gemini-3.1-pro-preview",
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
                for attempt in range(3):
                    try:
                        text, n, urls, usage = ask(model, prompt); break
                    except Exception as e:
                        print(f"  {model:24} retry {attempt+1}: {str(e)[:60]}", flush=True)
                        time.sleep(20); text = None
                if text is None:
                    print(f"  {model:24} FAILED {intent}", flush=True); continue
                blob = (text + " " + " ".join(urls)).lower()
                fh.write(json.dumps({
                    "model": model, "intent": intent, "prompt": prompt, "answer": text,
                    "searched": n > 0, "n_searches": n,
                    "cited_urls": sorted(set(urls))[:40],
                    "usage": usage,
                    "greencalculus_in_text": "greencalculus" in text.lower(),
                    "greencalculus_in_sources": "greencalculus" in " ".join(urls).lower(),
                }) + "\n")
                fh.flush()
                gc = "GC!" if "greencalculus" in blob else "   "
                print(f"  {model:24} {intent:11} {len(text):>6}ch  {n:>2} searches {gc} "
                      f"({time.time()-t0:.0f}s)", flush=True)
    print(f"\ndone in {time.time()-t0:.0f}s -> {OUT.name}")


if __name__ == "__main__":
    main()
