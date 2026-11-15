#!/usr/bin/env python3
"""Offline panel plotting checks; only rendering needs optional matplotlib."""
import csv
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aeo import plot, trend

HEADER = 'run,n_answers,brand,reach_pct,named,n_prompts,comparable\n'


def panel():
    return plot.read_panel(io.StringIO(HEADER +
        '2026-01-01,10,GreenCalculus,50,5,2,true\n'
        '2026-01-02,10,GreenCalculus,40,4,2,false\n'
        '2026-01-03,10,GreenCalculus,60,6,2,true\n'))


def run(day, models=('a',), searched=True):
    return {'date': day, 'rows': [dict(model=m, prompt='p', answer='GreenCalculus',
                                     searched=searched) for m in models]}


class PlotTests(unittest.TestCase):
    def test_csv_cli_has_comparison_metadata(self):
        result = subprocess.run([sys.executable, str(ROOT / 'aeo/trend.py'), '--csv'],
                                check=True, capture_output=True, text=True)
        rows = list(csv.DictReader(io.StringIO(result.stdout)))
        runs = {r['date']: r for r in trend.discover()}
        for row in rows:
            self.assertEqual(int(row['n_prompts']),
                             len({r['prompt'] for r in runs[row['run']]['rows']}))
            self.assertIn(row['comparable'], ('true', 'false'))

    def test_csv_guards_match_model_and_search_checks(self):
        runs = [run('2026-01-01'), run('2026-01-02', ('a', 'b')),
                run('2026-01-03', searched=False)]
        output = io.StringIO()
        with patch.object(trend, 'discover', return_value=runs), \
                patch('sys.stdout', output):
            trend.main(['--csv'])
        rows = list(csv.DictReader(io.StringIO(output.getvalue())))
        self.assertTrue(all(r['comparable'] == ('true' if r['run'] == '2026-01-01' else 'false')
                            for r in rows))

    def test_incomparable_run_breaks_both_connections(self):
        self.assertEqual([[r['run'].day for r in part] for part in plot.segments(panel())],
                         [[1], [3]])

    def test_only_comparable_runs_connect_in_date_order(self):
        rows = panel()
        for row in rows:
            row['comparable'] = True
        self.assertEqual(len(plot.segments(list(reversed(rows)))[0]), 3)

    def test_noise_floor_uses_prompt_count(self):
        self.assertEqual(panel()[0]['floor'], 50)

    def test_invalid_prompt_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'positive'):
            plot.read_panel(io.StringIO(HEADER + '2026-01-01,1,GreenCalculus,0,0,0,true\n'))

    def test_unknown_comparability_is_not_silently_plotted(self):
        with self.assertRaisesRegex(ValueError, 'comparable'):
            plot.read_panel(io.StringIO(HEADER + '2026-01-01,1,GreenCalculus,0,0,25,maybe\n'))

    def test_timeline_is_sorted_and_excludes_pending_and_planned(self):
        source = io.StringIO('# comment\ndate\tstatus\twhat\n'
                             '2026-01-03\tshipped\tC\n'
                             '2026-01-02\tpending\tB\n'
                             '2026-01-04\tplanned\tD\n'
                             '2026-01-01\tshipped\tA\n')
        self.assertEqual([r['what'] for r in plot.read_timeline(source)], ['A', 'C'])

    @unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'skip rendering: optional matplotlib unavailable')
    def test_rendered_lines_do_not_cross_an_incomparable_point(self):
        fig = plot.draw(panel(), [])
        self.assertEqual([len(line.get_xdata()) for line in fig.axes[0].lines], [1, 1])
        self.assertEqual(len(fig.axes[0].collections), 1)
        self.assertIn('50 percentage points', fig.texts[0].get_text())
        output = io.BytesIO()
        fig.savefig(output, format='svg')
        self.assertIn(b'<svg', output.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
