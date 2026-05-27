# TokenWatch

> htop for LLM spend. See where your tokens go — locally, with zero accounts.

Local-first LLM cost tracking and attribution. Wrap your OpenAI/Anthropic
client and every call is recorded to a local SQLite DB. `pip install` and go —
no infrastructure, no accounts, nothing leaves your machine.

## Install

```bash
pip install tokenwatch
```

## Quick Start

Wrap your client once; usage is recorded automatically:

```python
from tokenwatch import TokenWatch
import openai

tw = TokenWatch()                      # data stays on your machine
client = tw.wrap(openai.OpenAI())      # OpenAI or Anthropic

client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    metadata={"feature": "chat"},      # optional tags for attribution
)
```

Then inspect spend from the CLI:

```bash
$ tw report                 # spend over today / 7d / 30d
$ tw top --by model         # biggest spenders by model
$ tw top --by caller        # ...or by which code called the API
$ tw trend --days 7         # daily spend as an ASCII chart
```

Attribution is automatic: the caller is inferred from the call stack, and any
`metadata={...}` you pass is stored as tags.

## How it works

- **SDK** — duck-typed wrappers for OpenAI & Anthropic clients (the provider packages don't even need to be installed)
- **Storage** — local SQLite at `~/.tokenwatch/usage.db`
- **CLI** — `tw report`, `tw top`, `tw trend`
- **Pricing** — built-in per-model cost table; or pass `cost_usd` to `record()` yourself

## Status

**v0.1 — cost tracking & attribution are stable** (43 passing tests).

Anomaly detection (spending spikes / `tw check`) is on the roadmap, not yet
shipped. The tagline's "catch anomalies" half is the next milestone, not a
current feature — this README documents only what works today.

## License

MIT
