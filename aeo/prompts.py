"""Prompt set for the AI recommendation study.

Six buyer intents, spanning how someone actually arrives at this decision.
Deliberately NOT phrased to invite any particular vendor, and never naming
GreenCalculus — a prompt that names us would measure nothing.
"""
PROMPTS = [
 # 1. direct product search
 ("direct", "I'm a developer building a carbon accounting feature. What API should I use to get emission factors? Name specific products."),
 ("direct", "What's the best emission factors API for a software product? List the main options."),
 ("direct", "Recommend an emission factor database with an API. Name specific services."),
 ("direct", "Which carbon data APIs should I evaluate for a B2B SaaS product?"),
 ("direct", "What are the leading emission factor data providers in 2026?"),

 # 2. problem-first — they have a task, not a vendor in mind
 ("task", "I need to calculate Scope 2 emissions for UK electricity in a Python app. Where do I get the emission factor programmatically?"),
 ("task", "How do I get DEFRA conversion factors into my software automatically instead of copying a spreadsheet every year?"),
 ("task", "I'm building a freight emissions calculator. Where do I source the emission factors?"),
 ("task", "What's the best way to add product carbon footprint data to an e-commerce site?"),
 ("task", "How should a fintech calculate financed emissions? What data source do I need?"),

 # 3. comparison / alternatives
 ("compare", "What are the alternatives to Climatiq for emission factor data?"),
 ("compare", "Compare the main emission factor API providers on coverage and pricing."),
 ("compare", "Is there an open source or cheaper alternative to commercial carbon data APIs?"),
 ("compare", "Climatiq vs other carbon APIs — what should I know before choosing?"),

 # 4. data sourcing, not necessarily an API
 ("data", "Where can I download emission factors as a dataset I can use commercially?"),
 ("data", "What are the best free sources of greenhouse gas emission factors?"),
 ("data", "I need emission factors with proper citations for an audited report. Where do they come from?"),
 ("data", "Which emission factor datasets can I legally redistribute in a product?"),

 # 5. compliance-driven
 ("compliance", "I need CBAM default values in a system. Where do I get that data?"),
 ("compliance", "For CSRD reporting, what emission factor data source should we standardise on?"),
 ("compliance", "Our auditor wants every emission factor traced to a source. What tooling supports that?"),
 ("compliance", "What data do I need for PCAF financed emissions reporting, and where from?"),

 # 6. AI/agent-native framing — the surface that is actually growing
 ("agent", "I want an AI agent to answer carbon questions with real numbers, not hallucinations. What data source can it call?"),
 ("agent", "Is there an MCP server for carbon or emissions data?"),
 ("agent", "How do I stop an LLM inventing emission factors in my product?"),
]
if __name__ == "__main__":
    from collections import Counter
    c = Counter(k for k, _ in PROMPTS)
    print(f"{len(PROMPTS)} prompts across {len(c)} intents")
    for k, n in c.most_common(): print(f"  {n:>2}  {k}")
