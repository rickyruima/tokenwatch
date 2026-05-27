# Promotional posts — tokenwatch

Repo: https://github.com/rickyruima/tokenwatch
Generated: 2026-05-27T05:05:38.709843+00:00

## twitter (314 chars)

I kept getting blindsided by my OpenAI/Anthropic bills, so I built tokenwatch.

Wrap your client once → every call's cost is tracked, attributed by model + caller, and flagged when spend spikes. All local SQLite, nothing leaves your machine.

pip install tokenwatch
https://github.com/rickyruima/tokenwatch
#LLMOps

## linkedin (1740 chars)

Ever opened your OpenAI or Anthropic dashboard at the end of the month and had no idea which feature, script, or experiment actually burned through your budget?

I hit this often enough that I built a small tool for it: tokenwatch.

The idea is simple. You wrap your LLM client once, and from then on every call's cost gets tracked, attributed, and watched — all on your own machine.

A few things I cared about while building it:

→ Local-first. Usage data lives in a local SQLite file at ~/.tokenwatch/usage.db. Nothing gets sent anywhere. No dashboard to log into, no third-party service holding your prompts.

→ Zero setup. No accounts, no API keys for the tool itself, no infrastructure to stand up. Just `pip install tokenwatch` and wrap your client. It works with both OpenAI and Anthropic clients — you don't even need the provider packages installed for it to track.

→ Automatic attribution. Costs are broken down by model, by caller, and by any custom metadata tags you attach. So when spend climbs, you can actually see where it came from instead of guessing.

→ Anomaly detection. It learns your baseline and flags spend spikes that go above it, so a runaway loop or an accidental switch to an expensive model doesn't quietly cost you a fortune.

The CLI is intentionally boring:
- `tw report` — what you've spent
- `tw top` — biggest cost drivers
- `tw trend` — spend over time
- `tw check` — flag anomalies

If you're building on these APIs and want visibility into your spend without shipping your usage data off to someone else's servers, it might save you some surprises.

It's open source and free. Feedback and issues welcome:
https://github.com/rickyruima/tokenwatch

#LLM #OpenAI #Anthropic #DeveloperTools #OpenSource

## reddit (2880 chars)
**Title:** tokenwatch: htop for LLM spend — local cost anomaly detection and attribution

```
TL;DR: I built tokenwatch, a local tool that tracks the cost of every OpenAI/Anthropic API call after you wrap your client once. Data stays in local SQLite (~/.tokenwatch/usage.db), nothing phones home, no account needed. `pip install tokenwatch`, then `tw report` / `tw top` / `tw trend` / `tw check`. https://github.com/rickyruima/tokenwatch

---

I kept getting surprised by my API bill. Not "oops, doubled it" surprised — more like the dashboard says $X and I have no idea which script, which model, or which dumb retry loop caused it. The provider dashboards tell you the total but not the *why*, and they're always a day behind.

I looked at the hosted observability platforms and they all wanted me to route my traffic through them or sign up for an account. For a side project where I just wanted to know "what is costing me money," that felt like a lot. I didn't want my prompts leaving my machine to answer a question my own logs could answer.

So I wrote tokenwatch. The idea is you wrap your existing client once and forget about it:

```python
import tokenwatch
from openai import OpenAI

client = tokenwatch.wrap(OpenAI())
```

After that, every call's token usage and cost gets logged to a SQLite file at `~/.tokenwatch/usage.db`. That's the whole setup. No server, no env vars pointing at a collector, no account.

What it does:

- **Tracks cost per call** and rolls it up by model and by caller, so you can actually see that one function is responsible for 80% of your spend.
- **Custom tags** — you can attach metadata (e.g. a feature name, a user id, an experiment) and slice spend by it later.
- **Anomaly check** — `tw check` compares recent spend against your baseline and flags spikes. I mostly use it in a pre-commit-ish way / cron to catch a runaway loop before the bill does.
- Works with **both OpenAI and Anthropic** clients. You don't even need both provider packages installed — it only touches the one you're using.

The CLI is small on purpose:

```
tw report   # summary of spend
tw top      # biggest spenders by model/caller/tag
tw trend    # spend over time
tw check    # flag spikes above baseline
```

Honest about the limits: it's local-first by design, so there's no team dashboard or shared view — if two machines make calls, you've got two databases. That's a deliberate tradeoff, not a roadmap apology; if you need centralized team analytics this isn't that. It tracks usage from the official SDKs, so calls you make with raw `requests` won't show up unless you wrap them.

I've been using it on my own stuff for a couple months and it's caught a couple of "why is this 10x normal" moments for me, which is the whole reason it exists.

Repo's here if you want to poke at it or tell me what's broken: https://github.com/rickyruima/tokenwatch

(I'm the author — happy to answer questions or take feature/criticism in the comments.)
```

## hackernews (2345 chars)
**Title:** Show HN: tokenwatch – htop for LLM spend — local cost anomaly detection and attribution

**Show HN: tokenwatch – Local-first cost tracking for OpenAI and Anthropic clients**

I build a few small apps on the OpenAI and Anthropic APIs, and I kept losing track of where my token spend was actually going. The provider dashboards tell you the total, but not which part of my code or which model is responsible, and they lag by a day or so. When something started burning money in a loop, I usually found out from the invoice.

tokenwatch wraps your existing client once and records every call locally:

    import tokenwatch
    from openai import OpenAI

    client = tokenwatch.wrap(OpenAI())

After that, each call's token counts and cost get written to a SQLite file at `~/.tokenwatch/usage.db`. Nothing is sent anywhere — the wrapper reads the usage numbers that the API already returns and stores them on your machine. You can tag calls with custom metadata (e.g. a feature name or user id) so spend is attributed by model, by caller, and by whatever tags you add.

There's a small CLI for looking at the data:

- `tw report` — totals over a period
- `tw top` — biggest spenders by model/caller/tag
- `tw trend` — spend over time
- `tw check` — flags days where spend is meaningfully above your recent baseline

A few decisions worth explaining:

- **Local SQLite, no service.** I didn't want to run infrastructure or send usage data to a third party just to know what my own code costs. `pip install tokenwatch` and you're done — no account, no API key beyond the one you already have.
- **No provider SDK dependency.** It wraps whatever client object you pass in by intercepting the response, so it doesn't import `openai` or `anthropic` itself. If you have both installed it tracks both; if you have neither it still installs fine.
- **Anomaly detection is deliberately dumb.** `tw check` compares recent spend against a rolling baseline and flags outliers. No model, no config — I just wanted a cron-able command that tells me when today looks wrong.

It's pricing-table-based for cost, so the numbers are estimates and can drift when providers change prices; the token counts are exact since they come from the API response. Pricing data is something I have to keep updated by hand right now.

Repo: https://github.com/rickyruima/tokenwatch

Happy to hear how others are tracking this, especially if there's prior art I missed.
