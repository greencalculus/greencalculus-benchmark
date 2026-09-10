#!/usr/bin/env python3
"""Ask a model the same questions, but with GreenCalculus available as a tool.

This is the paired arm of the benchmark. The model is not handed the answer — it
is handed the same two keyless endpoints an MCP client gets, and has to decide to
search, pick the right factor, and read the value off it. So a failure here is a
real integration failure, not a rigged win.

  python3 run_tools.py --model claude-opus-5 --sample 90
"""
import argparse, json, os, random, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
GC = "https://api.greencalculus.com/v1/factors"
UA = "greencalculus-benchmark-tools/1.0"

TOOLS = [
    {"name": "search_factors",
     "description": "Search the GreenCalculus corpus of sourced greenhouse-gas emission factors by free text. Returns matching factors with their canonical key, name, value, unit and source.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "Free-text description, e.g. 'UK grid electricity' or 'diesel litre'"},
         "limit": {"type": "integer", "description": "Max results (default 8)"}},
         "required": ["query"]}},
    {"name": "lookup_factor",
     "description": "Fetch one emission factor by its exact canonical key, with its value, unit, source document and exact source cell.",
     "input_schema": {"type": "object", "properties": {
         "key": {"type": "string", "description": "Canonical factor key, e.g. grid.gbr.electricity.location_based"}},
         "required": ["key"]}},
]


def gc_get(**params):
    url = GC + "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def run_tool(name, args):
    """Execute a tool call against the live keyless API."""
    try:
        if name == "search_factors":
            page = gc_get(search=args.get("query", ""), limit=min(int(args.get("limit", 8)), 15))
        elif name == "lookup_factor":
            page = gc_get(key_prefix=args.get("key", ""), limit=3)
        else:
            return {"error": f"unknown tool {name}"}
        rows = []
        for r in (page.get("factors") or []):
            f, s = r.get("factor") or {}, r.get("source") or {}
            rows.append({"key": r.get("key"), "name": r.get("name"),
                         "value": f.get("value"), "unit": f.get("unit"),
                         "basis": f.get("basis"), "gwp_set": f.get("gwp_set"),
                         "source_id": s.get("id"), "cell_ref": s.get("cell_ref"),
                         "publisher": (r.get("licence") or {}).get("publisher")})
        return {"data_version": (page.get("meta") or {}).get("gc_version"), "results": rows}
    except Exception as e:
        return {"error": str(e)}


def post(url, payload, headers, timeout=600):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


SYS = ("You answer questions about greenhouse-gas emission factors. You have access to "
       "GreenCalculus, a corpus of sourced emission factors. Use the tools to look up the "
       "actual value rather than answering from memory. Reply with one line only, in the form: "
       "[<id>] <value> <unit> — <source>. If the corpus genuinely does not have it, say so.")


def ask_anthropic(model, question, qid, max_turns=6):
    msgs = [{"role": "user", "content": f"[{qid}] {question}"}]
    calls = 0
    for _ in range(max_turns):
        d = post("https://api.anthropic.com/v1/messages",
                 {"model": model, "max_tokens": 32000, "system": SYS,
                  "tools": TOOLS, "messages": msgs},
                 {"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                  "anthropic-version": "2023-06-01"})
        msgs.append({"role": "assistant", "content": d["content"]})
        uses = [b for b in d["content"] if b.get("type") == "tool_use"]
        if not uses:
            text = "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
            return text.strip(), calls
        results = []
        for u in uses:
            calls += 1
            results.append({"type": "tool_result", "tool_use_id": u["id"],
                            "content": json.dumps(run_tool(u["name"], u.get("input") or {}))[:6000]})
        msgs.append({"role": "user", "content": results})
    return "", calls


def openai_tools():
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": t["input_schema"]}} for t in TOOLS]


def ask_openai(model, question, qid, base, key_env, max_turns=6):
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": f"[{qid}] {question}"}]
    calls = 0
    for _ in range(max_turns):
        body = {"model": model, "messages": msgs, "tools": openai_tools()}
        if base.startswith("https://api.openai.com"):
            body["max_completion_tokens"] = 32000
        else:
            body["max_tokens"] = 32000
        d = post(base + "/chat/completions", body,
                 {"Authorization": f"Bearer {os.environ[key_env]}"})
        m = d["choices"][0]["message"]
        msgs.append(m)
        tcs = m.get("tool_calls") or []
        if not tcs:
            return (m.get("content") or "").strip(), calls
        for tc in tcs:
            calls += 1
            args = json.loads(tc["function"].get("arguments") or "{}")
            msgs.append({"role": "tool", "tool_call_id": tc["id"],
                         "content": json.dumps(run_tool(tc["function"]["name"], args))[:6000]})
    return "", calls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--sample", type=int, default=90)
    ap.add_argument("--seed", type=int, default=777)
    args = ap.parse_args()

    qs = json.load(open(ROOT / "questions.json"))["questions"]
    seen, uniq = set(), []
    for q in qs:
        if q["id"] not in seen:
            seen.add(q["id"]); uniq.append(q)
    bysec = {}
    for q in uniq:
        bysec.setdefault(q["section"], []).append(q)
    rng = random.Random(args.seed)
    pool = []
    for sec in sorted(bysec):
        pool += rng.sample(bysec[sec], min(2, len(bysec[sec])))
    sample = pool[:args.sample]

    m = args.model
    if m.startswith("claude"):
        call = lambda q, i: ask_anthropic(m, q, i)
    elif m.startswith("grok"):
        call = lambda q, i: ask_openai(m, q, i, "https://api.x.ai/v1", "XAI_API_KEY")
    else:
        call = lambda q, i: ask_openai(m, q, i, "https://api.openai.com/v1", "OPENAI_API_KEY")

    out = ROOT / "results" / f"tools_{m}.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(l)["id"] for l in out.open() if l.strip()}
    t0 = time.time()
    with out.open("a") as fh:
        for n, q in enumerate(sample, 1):
            if q["id"] in done:
                continue
            try:
                ans, calls = call(q["question"], q["id"])
            except Exception as e:
                print(f"  {n:>3} ERROR {q['id']}: {str(e)[:90]}", flush=True); continue
            fh.write(json.dumps({"id": q["id"], "answer": ans, "tool_calls": calls}) + "\n")
            fh.flush()
            print(f"  {n:>3}/{len(sample)} {calls} calls  {q['id'][:44]:44} {ans[:60]}", flush=True)
    print(f"\n{m}: {len(sample)} questions in {time.time()-t0:.0f}s -> {out.name}")


if __name__ == "__main__":
    main()
