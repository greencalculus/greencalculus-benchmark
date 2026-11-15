#!/usr/bin/env python3
"""Plot the committed search-arm panel without making model calls.

  python3 aeo/plot.py --output panel.svg
  python3 aeo/trend.py --csv | python3 aeo/plot.py --csv - --output panel.png

Only rendering requires matplotlib; CSV and timeline handling use the stdlib.
"""
import argparse
import csv
import io
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

if __package__:
    from . import trend
else:
    import trend


def read_panel(source):
    rows = []
    for row in csv.DictReader(source):
        comparable = row['comparable'].lower()
        if comparable not in ('true', 'false'):
            raise ValueError('comparable must be true or false')
        prompts = int(row['n_prompts'])
        if prompts <= 0:
            raise ValueError('n_prompts must be positive')
        reach = float(row['reach_pct'])
        if not 0 <= reach <= 100:
            raise ValueError('reach_pct must be between 0 and 100')
        rows.append(dict(run=date.fromisoformat(row['run']), brand=row['brand'],
                         reach=reach, floor=100 / prompts,
                         comparable=comparable == 'true'))
    return sorted(rows, key=lambda r: (r['run'], r['brand']))


def read_timeline(source):
    rows = csv.DictReader((line for line in source if not line.startswith('#')),
                          delimiter='\t')
    return sorted([dict(row, date=date.fromisoformat(row['date'])) for row in rows
                   if row['status'] == 'shipped'], key=lambda r: r['date'])


def segments(rows):
    """An incomparable run breaks the line on both sides."""
    result, current = [], []
    for row in sorted(rows, key=lambda r: r['run']):
        if row['comparable']:
            current.append(row)
        elif current:
            result.append(current)
            current = []
    if current:
        result.append(current)
    return result


def draw(rows, events):
    from matplotlib.figure import Figure
    from matplotlib.ticker import PercentFormatter

    if not rows:
        raise ValueError('panel has no rows')
    fig = Figure(figsize=(11, 6))
    ax = fig.subplots()
    by_brand = defaultdict(list)
    for row in rows:
        by_brand[row['brand']].append(row)
    palette = ['#6c7a89', '#a38671', '#8d879e', '#7c9a92', '#a89b68']
    brands = [b for b in [trend.US] + trend.CONTROLS if b in by_brand]
    for index, brand in enumerate(brands):
        color = '#16723a' if brand == trend.US else palette[(index - 1) % len(palette)]
        label = brand.lstrip('_')
        for part in segments(by_brand[brand]):
            ax.plot([r['run'] for r in part], [r['reach'] for r in part],
                    marker='o', color=color, linewidth=2.5 if brand == trend.US else 1,
                    label=label)
            label = '_nolegend_'
        bad = [r for r in by_brand[brand] if not r['comparable']]
        if bad:
            ax.scatter([r['run'] for r in bad], [r['reach'] for r in bad],
                       marker='x', color=color, label=label)
    for event in events:
        ax.axvline(event['date'], color='#aaaaaa', linestyle=':', linewidth=0.8)
    floors = sorted({r['floor'] for r in rows})
    floor_label = f'{floors[0]:g}' if len(floors) == 1 else f'{floors[0]:g}–{floors[-1]:g}'
    fig.text(0.02, 0.025,
             f'One-prompt noise floor: {floor_label} percentage points (100 / n_prompts).\n'
             '×: incomparable run; lines stop there. Dotted rules: shipped events only.',
             fontsize=9)
    ax.set(title='Search-arm panel', ylabel='Answers naming the brand', ylim=(0, 100))
    ax.yaxis.set_major_formatter(PercentFormatter())
    ax.grid(axis='y', alpha=0.2)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    return fig


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', help='panel CSV file, or - for stdin; default: trend.py output')
    parser.add_argument('--timeline', type=Path, default=trend.TIMELINE)
    parser.add_argument('--output', type=Path, default=Path('panel.svg'))
    args = parser.parse_args(argv)
    if args.csv == '-':
        rows = read_panel(sys.stdin)
    elif args.csv:
        with open(args.csv) as source:
            rows = read_panel(source)
    else:
        from contextlib import redirect_stdout

        output = io.StringIO()
        with redirect_stdout(output):
            trend.main(["--csv"])
        rows = read_panel(io.StringIO(output.getvalue()))
    with args.timeline.open() as source:
        events = read_timeline(source)
    try:
        fig = draw(rows, events)
    except ImportError:
        parser.exit(2, 'Rendering requires matplotlib: python3 -m pip install matplotlib\n')
    fig.savefig(args.output, dpi=160)
    print(args.output)


if __name__ == '__main__':
    main()
