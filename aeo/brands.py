"""Brand detection. Aliases matter — a model writing 'Green Calculus' or
'Climatiq.io' must count. Ordered longest-first so 'Carbon Interface' is not
swallowed by a bare 'carbon' match; every pattern is word-boundaried."""
BRANDS = {
 "GreenCalculus":     [r"greencalculus", r"green calculus"],
 "Climatiq":          [r"climatiq"],
 "Carbon Interface":  [r"carbon interface", r"carboninterface"],
 "Electricity Maps":  [r"electricity maps?", r"electricitymaps?", r"tomorrow\.io grid"],
 "ecoinvent":         [r"ecoinvent"],
 "EXIOBASE":          [r"exiobase"],
 "Watershed":         [r"watershed"],
 "Persefoni":         [r"persefoni"],
 "Sweep":             [r"\bsweep\b"],
 "Plan A":            [r"plan a\b(?! bit| little| few)"],
 "Normative":         [r"\bnormative\b"],
 "Emitwise":          [r"emitwise"],
 "Sphera":            [r"sphera"],
 "CO2.js":            [r"co2\.js", r"co2js", r"green web foundation"],
 "Cloverly":          [r"cloverly"],
 "Patch":             [r"\bpatch\b(?! notes| file)"],
 "Climate TRACE":     [r"climate trace"],
 "SimaPro":           [r"simapro"],
 "GaBi":              [r"\bgabi\b"],
 "OpenLCA":           [r"openlca", r"open lca"],
 "Cozero":            [r"cozero"],
 "Greenly":           [r"greenly"],
 "Sinai":             [r"sinai technologies"],
 "CarbonChain":       [r"carbonchain", r"carbon chain"],
 "Altruistiq":        [r"altruistiq"],
 # public datasets, not vendors — tracked separately
 "_DEFRA":            [r"\bdefra\b", r"\bdesnz\b", r"\bbeis\b"],
 "_EPA":              [r"\bepa\b", r"egrid"],
 "_IPCC":             [r"\bipcc\b"],
 "_Ember":            [r"\bember\b"],
 "_ADEME":            [r"\bademe\b", r"base carbone", r"agribalyse"],
 "_EEIO/USEEIO":      [r"useeio", r"\beeio\b"],
}
VENDORS = [b for b in BRANDS if not b.startswith("_")]
DATASETS = [b for b in BRANDS if b.startswith("_")]
