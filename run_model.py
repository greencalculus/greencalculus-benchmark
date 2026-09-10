#!/usr/bin/env python3
"""Ask a model the benchmark questions through its own API. No tools, no lookups.

Straight HTTP, zero dependencies. Each provider gets a small adapter because the
four request shapes differ; everything after that is identical, so no model gets
a friendlier path than another.

  python3 run_model.py --model gpt-5.5 --batches 1     # smoke test
  python3 run_model.py --model gpt-5.5                 # full 467
"""
import argparse, json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
BATCH = 30

PROMPT = """You are being measured on unaided factual recall of greenhouse-gas emission factors. This is a benchmark.

Answer every question below from your own knowledge. You have no tools and must not guess at what a lookup would say — answer as you would if asked directly.

For each question: give your best numeric value WITH its unit, and name the publisher/document you believe it comes from if you have one. If you genuinely do not know, say so plainly rather than inventing a number — an honest "I don't know" is a valid and useful answer. But do not hedge into uselessness: if you have a real best estimate, give the number.

Answer in EXACTLY this format, one block per question, nothing else:

[<id>] <your answer in one or two sentences, including the number, unit, and source if you have one>

The ids are the bracketed strings. Return ONLY the answer blocks — no preamble, no summary, no commentary.

{questions}"""


def post(url, payload, headers, timeout=600):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def anthropic(model, prompt):
    d = post("https://api.anthropic.com/v1/messages",
             {"model": model, "max_tokens": 8000,
              "messages": [{"role": "user", "content": prompt}]},
             {"x-api-key": os.environ["ANTHROPIC_API_KEY"],
              "anthropic-version": "2023-06-01"})
    return "".join(b.get("text", "") for b in d.get("content", []))


def openai_compatible(model, prompt, base, key_env):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if base.startswith("https://api.openai.com"):
        body["max_completion_tokens"] = 12000
    else:
        body["max_tokens"] = 12000
    d = post(base + "/chat/completions", body,
             {"Authorization": f"Bearer {os.environ[key_env]}"})
    return d["choices"][0]["message"]["content"] or ""


def gemini(model, prompt):
    key = os.environ["GEMINI_API_KEY"]
    d = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
             {"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"maxOutputTokens": 12000}}, {})
    parts = d["candidates"][0]["content"].get("parts", [])
    return "".join(p.get("text", "") for p in parts)


ADAPTERS = {
    "claude": lambda m, p: anthropic(m, p),
    "gpt":    lambda m, p: openai_compatible(m, p, "https://api.openai.com/v1", "OPENAI_API_KEY"),
    "gemini": lambda m, p: gemini(m, p),
    "grok":   lambda m, p: openai_compatible(m, p, "https://api.x.ai/v1", "XAI_API_KEY"),
}


def adapter_for(model):
    for k, fn in ADAPTERS.items():
        if model.startswith(k):
            return fn
    sys.exit(f"no adapter for model '{model}'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--batches", type=int, default=0, help="0 = all")
    args = ap.parse_args()

    qs = json.load(open(ROOT / "questions.json"))["questions"]
    seen, uniq = set(), []
    for q in qs:
        if q["id"] not in seen:
            seen.add(q["id"]); uniq.append(q)

    call = adapter_for(args.model)
    out = ROOT / "results" / f"raw_{args.model.replace('/', '_')}"
    out.mkdir(parents=True, exist_ok=True)

    batches = [uniq[i:i + BATCH] for i in range(0, len(uniq), BATCH)]
    if args.batches:
        batches = batches[:args.batches]

    t0 = time.time()
    for n, batch in enumerate(batches, 1):
        f = out / f"b{n:02d}.txt"
        if f.exists():
            print(f"  b{n:02d} already done, skipping", flush=True)
            continue
        listing = "\n".join(f"{i}. [{q['id']}] {q['question']}"
                            for i, q in enumerate(batch, 1))
        text = None
        for attempt in range(5):
            try:
                text = call(args.model, PROMPT.format(questions=listing))
                break
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:300]
                if e.code in (429, 500, 502, 503, 529) and attempt < 4:
                    wait = 2 ** attempt * 5
                    print(f"  b{n:02d} HTTP {e.code}, retry in {wait}s", flush=True)
                    time.sleep(wait); continue
                print(f"  b{n:02d} FAILED HTTP {e.code}: {body}", flush=True)
                break
            except Exception as e:
                if attempt < 4:
                    time.sleep(2 ** attempt * 5); continue
                print(f"  b{n:02d} FAILED: {e}", flush=True)
                break
        if text is None:
            continue
        got = len(re.findall(r"^\s*(?:\d+[.)]\s*)?\[([^\]]+)\]", text, re.M))
        f.write_text(text, encoding="utf-8")
        print(f"  b{n:02d}  {got}/{len(batch)} answers  ({time.time()-t0:.0f}s)", flush=True)

    done = sorted(out.glob("b*.txt"))
    total = sum(len(re.findall(r"^\s*(?:\d+[.)]\s*)?\[([^\]]+)\]", p.read_text(), re.M)) for p in done)
    print(f"\n{args.model}: {len(done)} batches, {total} answers -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
