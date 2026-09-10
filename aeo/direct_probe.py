"""Ask each model directly about GreenCalculus. The recommendation study measures
whether we are RECOMMENDED; this measures whether we are KNOWN at all. The two
have different fixes, so they must be measured separately."""
import json, os, sys, time
from run import ask
from prompts import PROMPTS  # noqa: F401  (import keeps env loading identical)

PROBES = [
 ("known",   "What is GreenCalculus? Answer only from what you already know. If you do not know, say so plainly."),
 ("known",   "Does a company called GreenCalculus publish emission factor data? What can you tell me about them?"),
 ("compare", "How does GreenCalculus compare to Climatiq for emission factor data?"),
]
MODELS = ["claude-opus-5","gpt-5.5","gemini-3.1-pro-preview","gemini-3.6-flash","grok-4.6"]

if __name__ == "__main__":
    with open("direct_probe.jsonl","a") as fh:
        for m in MODELS:
            for kind, p in PROBES:
                for attempt in range(3):
                    try:
                        t = ask(m, p); break
                    except Exception as e:
                        print(f"  {m:24} retry {attempt+1}: {str(e)[:60]}", flush=True)
                        time.sleep(20); t = None
                if t is None:
                    print(f"  {m:24} FAILED"); continue
                fh.write(json.dumps({"model":m,"kind":kind,"prompt":p,"answer":t})+"\n"); fh.flush()
                print(f"  {m:24} {kind:8} {len(t):>6} chars", flush=True)
