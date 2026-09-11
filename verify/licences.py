#!/usr/bin/env python3
"""The licence audit's figures, recomputed rather than trusted.

The audit behind /guides/emission-factor-licences/ is a point-in-time statement:
137 sources, each one's terms read once and the verdict recorded. Two things can
go wrong with a figure like that, and they are different problems.

  1. It cannot be checked at all. That was true until this file existed -- the
     numbers came from a live registry query nobody had written down.
  2. It goes stale silently. A licence gets re-reviewed, a publisher grants
     permission, and a published percentage quietly stops being true.

So the audit is snapshotted (`licence_snapshot.json`, with the date it describes)
and the snapshot is what the published guide is checked against. `--drift`
compares the snapshot to the live registry and reports what has moved since.

  python3 verify/licences.py            # figures from the committed snapshot
  python3 verify/licences.py --drift    # snapshot vs the live registry
"""
import argparse, collections, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, "licence_snapshot.json")

# The licence families as the published guide names them, most specific first --
# "CC BY-NC-SA" must be tested before "CC BY-NC", and that before "CC BY".
FAMILIES = [
    ("CC BY-NC-SA",                 r"CC[\s-]?BY[\s-]?NC[\s-]?SA"),
    ("CC BY-NC-ND",                 r"CC[\s-]?BY[\s-]?NC[\s-]?ND"),
    ("CC BY-NC",                    r"CC[\s-]?BY[\s-]?NC"),
    ("CC BY-SA",                    r"CC[\s-]?BY[\s-]?SA"),
    ("CC BY 4.0",                   r"CC[\s-]?BY(?![\s-]?(NC|SA|ND))"),
    ("Open Government Licence",     r"Open Government Licence|\bOGL\b"),
    ("Etalab Open Licence",         r"Etalab|Licence Ouverte"),
    ("US public domain",            r"U\.?S\.? Government (public domain|work)|US public domain|NIST Standard Reference Data"),
    ("EU Official Journal",         r"EU Official Journal"),
    ("Eurostat reuse policy",       r"Eurostat reuse policy"),
    ("Paid / subscription",         r"Paid licence|Paid \(|subscription"),
    ("All rights reserved",         r"all rights reserved|proprietary|reproduction without permission prohibited|(?<!IEA-PVPS )\(c\)|©"),
]


def family_of(licence):
    """The guide's own taxonomy. Anything that matches no named instrument is
    'Bespoke / no standard instrument' -- which is the 42% the guide reports."""
    if not licence:
        return "Bespoke / no standard instrument"
    for name, pattern in FAMILIES:
        if re.search(pattern, licence, re.I):
            return name
    return "Bespoke / no standard instrument"


def live():
    """Join the canonical sources registry to corpus row counts, on the server."""
    php = r'''
$reg = gc_mb_canonical_sources_registry();
$rows = gc_mb_raw_factors();
$raw = array(); $canon = array(); $seen = array();
foreach($rows as $r){ $r=(array)$r;
  $s = is_array($r["source"]) ? ($r["source"]["id"] ?? "?") : $r["source"];
  if(!isset($raw[$s])){ $raw[$s]=0; $canon[$s]=0; }
  $raw[$s]++;
  if(!isset($seen[$r["key"]])){ $seen[$r["key"]]=1; $canon[$s]++; }
}
$out = array();
foreach($raw as $sid=>$n){
  $e = isset($reg[$sid]) ? (array)$reg[$sid] : null;
  $out[] = array("id"=>$sid, "raw"=>$n, "canon"=>$canon[$sid],
    "redistributable"=> $e ? ($e["redistributable"] ? 1 : 0) : -1,
    "license"=> $e ? $e["license"] : null);
}
echo json_encode($out);
'''
    # Send the PHP as a file rather than an inline argument: a shell round-trip
    # eats every $ in a double-quoted string and the query silently returns junk.
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False) as fh:
        fh.write("<?php\n" + php)
        local = fh.name
    subprocess.run(["ssh", "greencalculus", "cat > /tmp/gc-licence-join.php"],
                   stdin=open(local), check=True)
    out = subprocess.run(
        ["ssh", "greencalculus",
         "cd /home/master/applications/sysuggskbt/public_html && "
         "wp eval-file /tmp/gc-licence-join.php"],
        capture_output=True, text=True, check=True).stdout
    os.unlink(local)
    return json.loads(out)


def load_snapshot():
    with open(SNAPSHOT) as fh:
        return json.load(fh)


def figures(sources):
    raw_rows = sum(s["raw"] for s in sources)
    may = [s for s in sources if s["redistributable"] == 1]
    may_not = [s for s in sources if s["redistributable"] == 0]
    may_rows = sum(s["raw"] for s in may)
    bespoke = [s for s in sources if family_of(s["license"]) == "Bespoke / no standard instrument"]

    figs = {
        "licence.sources": len(sources),
        "licence.rows": raw_rows,
        "licence.may_republish.sources": len(may),
        "licence.may_republish.rows": may_rows,
        "licence.may_republish.row_pct": round(may_rows / raw_rows * 100),
        "licence.may_not.sources": len(may_not),
        "licence.may_not.rows": sum(s["raw"] for s in may_not),
        "licence.no_standard_instrument.sources": len(bespoke),
        "licence.no_standard_instrument.pct": round(len(bespoke) / len(sources) * 100),
    }
    fam = collections.defaultdict(lambda: [0, 0, 0])
    for s in sources:
        f = fam[family_of(s["license"])]
        f[0] += 1
        f[1 if s["redistributable"] == 1 else 2] += 1
    for name, (total, yes, no) in fam.items():
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        figs[f"licence.family.{slug}.sources"] = total
        figs[f"licence.family.{slug}.may"] = yes
        figs[f"licence.family.{slug}.may_not"] = no
    for s in sources:
        figs[f"licence.source.{s['id']}.rows"] = s["raw"]
    return figs, fam


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drift", action="store_true")
    ap.add_argument("--write-snapshot", metavar="AS_OF",
                    help="capture the live registry as the snapshot, dated AS_OF (YYYY-MM-DD)")
    args = ap.parse_args()

    if args.write_snapshot:
        sources = live()
        with open(SNAPSHOT, "w") as fh:
            json.dump({"as_of": args.write_snapshot, "sources": sources}, fh, indent=1)
        print(f"snapshot written: {len(sources)} sources, as at {args.write_snapshot}")
        return 0

    snap = load_snapshot()
    figs, fam = figures(snap["sources"])
    print(f"licence audit as at {snap['as_of']}\n")
    for k, v in sorted(figs.items()):
        if k.startswith("licence.source."):
            continue
        print(f"  {k:52} {v}")
    print(f"\n  {'family':34}{'sources':>8}{'may':>6}{'may not':>9}")
    for name, (total, yes, no) in sorted(fam.items(), key=lambda kv: -kv[1][0]):
        print(f"  {name:34}{total:>8}{yes:>6}{no:>9}")

    if not args.drift:
        return 0

    now = live()
    print(f"\n--- drift: snapshot ({snap['as_of']}) vs the live registry ---")
    was = {s["id"]: s for s in snap["sources"]}
    changed = 0
    for s in now:
        old = was.get(s["id"])
        if old is None:
            print(f"  NEW      {s['id']} ({s['raw']} rows)")
            changed += 1
        elif old["redistributable"] != s["redistributable"]:
            direction = ("may not -> MAY REPUBLISH" if s["redistributable"] == 1
                         else "may -> MAY NOT REPUBLISH")
            print(f"  CHANGED  {s['id']} ({s['raw']} rows): {direction}")
            changed += 1
        elif old["raw"] != s["raw"]:
            print(f"  ROWS     {s['id']}: {old['raw']} -> {s['raw']}")
            changed += 1
    for sid in was:
        if sid not in {s["id"] for s in now}:
            print(f"  GONE     {sid}")
            changed += 1
    if not changed:
        print("  none -- the published audit still describes the live registry")
        return 0
    nf, _ = figures(now)
    print(f"\n  published : {figs['licence.may_republish.sources']} may / "
          f"{figs['licence.may_not.sources']} may not · "
          f"{figs['licence.may_republish.rows']} rows · "
          f"{figs['licence.may_republish.row_pct']}%")
    print(f"  live now  : {nf['licence.may_republish.sources']} may / "
          f"{nf['licence.may_not.sources']} may not · "
          f"{nf['licence.may_republish.rows']} rows · "
          f"{nf['licence.may_republish.row_pct']}%")
    print("\n  The guide states the snapshot. Drift is not a failure -- it is the")
    print("  signal to re-date the guide, or to record why the old date still stands.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
