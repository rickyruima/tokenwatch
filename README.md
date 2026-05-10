# TokenWatch

> htop for LLM spend. See where your tokens go, catch anomalies locally.

Local-first LLM cost anomaly detection and attribution. Zero infrastructure, zero accounts, `pip install` and go.

## Quick Start

```python
from tokenwatch import TokenWatch
import openai

tw = TokenWatch()  # data stays on your machine
client = tw.wrap(openai.OpenAI())

response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    metadata={"customer_id": "cust_123", "feature": "chat"}
)
```

```bash
$ tw report
Today: $42.13 (↑12% vs yesterday)
  gpt-4-turbo   $28.40  (67%)
  claude-3-opus  $11.20  (27%)

$ tw check
🚨 Spike: feature=agent_chat cost $312 in last hour (baseline: $42)
```

## Architecture

- **SDK**: Python, wraps OpenAI/Anthropic clients
- **Storage**: Local SQLite (~/.tokenwatch/usage.db)
- **CLI**: `tw report`, `tw top`, `tw check`, `tw watch`, `tw query`
- **Anomaly detection**: Statistical (z-score, EWMA, percentile) — no ML, no cloud

## Status

Pre-development. See `PRD.md`.
