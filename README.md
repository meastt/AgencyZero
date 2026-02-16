
# AgencyZero: Autonomous SEO Infrastructure
### Production-Ready Multi-Agent System for WordPress
**Current Status:** Active Development | **License:** Commercial Source Code Available

---

## 🛑 Buying This Technology
This repository contains the core architecture for the AgencyZero autonomous fleet.
We are currently accepting offers for the full acquisition of this codebase and IP.

**[View Listing on Acquire.com](LINK_TO_YOUR_LISTING)** *(Add this link once your listing is live)*

---

[... Your existing documentation follows below ...]

# AgencyZero

Autonomous SEO agency powered by Claude. Three self-directed agents each manage a WordPress niche site, coordinated by a Commander bot via Telegram.

## Sites

| Agent | Site | Niche |
|-------|------|-------|
| Griddle King | griddleking.com | Outdoor cooking, griddles, BBQ |
| Photo Tips Guy | phototipsguy.com | Photography, astrophotography, telescopes |
| Tiger Tribe | tigertribe.net | Wild cats, predatory wildlife, conservation |

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    SCHEDULER                          │
│  Agent ticks every 15 min  |  Commander review 15 min │
└────────┬──────────┬──────────┬──────────┬────────────┘
         │          │          │          │
    ┌────▼────┐ ┌───▼───┐ ┌───▼───┐ ┌────▼─────────┐
    │ Griddle │ │ Photo │ │ Tiger │ │  Commander   │
    │  Brain  │ │ Brain │ │ Brain │ │    Brain     │
    └────┬────┘ └───┬───┘ └───┬───┘ └────┬─────────┘
         │          │          │          │
    ┌────▼──────────▼──────────▼──────────▼────────────┐
    │               TOOL REGISTRY                       │
    │  gsc_audit, seo_audit, keyword_research,          │
    │  affiliate_audit, orphan_rescue, generate_image   │
    └────────────────────┬─────────────────────────────┘
                         │
    ┌────────────────────▼─────────────────────────────┐
    │               STATE STORE                         │
    │  state/agent_griddle.json                         │
    │  state/agent_photo.json                           │
    │  state/agent_tiger.json                           │
    │  state/commander.json                             │
    └──────────────────────────────────────────────────┘
```

Each agent runs an autonomous loop: **assess** (audit + KPI refresh) -> **plan** (Claude creates action plan) -> **review** (Commander approves/rejects) -> **execute** (run tools + before/after KPI outcomes) -> **report** (Telegram summary + timeline state).

## Project Layout

```
core/                          # Autonomous brain system
  state_store.py               # Persistent JSON state (timeline, KPIs, outcomes; atomic writes)
  claude_client.py             # Shared Claude API client
  commander_brain.py           # Intelligent Commander + weekly portfolio allocation strategy
  agent_brain.py               # Autonomous agent loop (assess/plan/execute/report with KPI outcomes)
  tool_registry.py             # Wraps scripts as callable tools
  scheduler.py                 # Timer-based agent + review scheduling

commander_bot.py               # Telegram bot — entry point, safety-gated triggers + natural language

agents/
  agent_dispatch.py            # Agent registry, script runner, Telegram routing
  seo_manager/                 # Griddle King agent workspace
    scripts/gsc_audit.py       # Google Search Console performance audit
    scripts/tech_seo_fixer.py  # Technical SEO fixes
    seo_kickstart.py           # Full site kickstart analysis
    keyword_research.py        # Keyword opportunity finder
    STRATEGIC_PLAN.md          # Griddle King strategic roadmap
  photo_manager/               # Photo Tips Guy agent workspace
  cat_manager/                 # Tiger Tribe agent workspace

shared/scripts/                # Universal scripts (work with any site via SITE_PREFIX)
  universal_seo_audit.py       # SEO audit (internal links, orphans, content quality)
  universal_keyword_research.py # Keyword research
  affiliate_audit.py           # Affiliate link audit
  generate_featured_image.py   # AI-generated featured images
  telegram_utils.py            # Telegram alerting utility

scripts/                       # Standalone tools
  orphan_rescue.py             # Find and fix orphaned posts
  wp_link_injector.py          # Internal link injection

state/                         # Live agent state files (JSON)
data/                          # Generated audit outputs and logs
```

## Requirements

- Python 3.10+
- Credentials in `.env`:
  - `ANTHROPIC_API_KEY` — Claude API (powers all agent brains)
  - `GSC_JSON_KEY` — Google Search Console service account JSON
  - `WP_URL`, `WP_USERNAME`, `WP_APP_PASS` — WordPress API access per site
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — Commander bot
  - Per-site Telegram bot tokens (`WP_GRIDDLEKING_TELEGRAM_BOT_TOKEN`, etc.)
  - `BRAVE_SEARCH_API_KEY` — keyword research

## Quick Start

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your credentials (see above). **Never commit `.env`** — it contains secrets.

3. Start the Commander bot:

```bash
python3 commander_bot.py
```

This starts:
- Telegram polling for commands and natural language
- Commander Brain with conversation history and live state awareness
- 3 autonomous agent brains (tick every 15 min)
- Commander review cycle (every 15 min)
- Single-instance lock for poller safety (`state/commander_bot.lock`)

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/help` | Show commands without triggering execution |
| `/status` | Live fleet status from agent state files |
| `/mission` | Current mission overview |
| `/portfolio` | Executive allocation + KPI outcomes |
| `/start` | Safety-gated immediate full reassessment request |
| `/start confirm` | Confirm forced reassessment within 2 minutes |
| `/griddle [task]` | Griddle King operations |
| `/photo [task]` | Photo Tips Guy operations |
| `/tiger [task]` | Tiger Tribe operations |
| `/audit [site]` | Run SEO audit |
| `/keywords [site]` | Run keyword research |

Or just type naturally — the Commander Brain understands context and remembers your conversation.

## How Autonomy Works

1. **Scheduler** ticks each agent every 15 minutes
2. **Agent Brain** checks if its site assessment is stale (>1 hour)
3. If stale, runs GSC audit and/or SEO audit to get fresh data
4. **Claude** analyzes the data and creates a prioritized action plan
5. Plan is submitted to **Commander Brain** for review
6. Commander auto-reviews every 15 minutes (approve/reject with reasoning)
7. Approved plans trigger immediate execution (no idle approval lag)
8. Manual trigger intent (`/start confirm`, or natural-language trigger action) forces reassessment even when state is fresh
9. Each execution captures baseline KPIs, post-execution KPIs, and deltas
10. Results and agent updates are routed into Commander timeline/state (single chain of command by default)
11. Commander generates weekly portfolio allocation weights by ROI pressure
12. Errors/escalations flow through Commander to the user

Priority order: revenue leaks > declining pages > Page 2 pushes > orphan fixes > new content.

## Canonical KPI Schema

Each agent persists KPI snapshots in its state file and records before/after deltas for every executed plan:

- `organic_clicks_28d`
- `top20_keywords_count`
- `affiliate_ctr_pct`
- `revenue_per_session_usd`
- `monthly_revenue_usd`
- `orphan_pages_count` (supporting operational KPI)

Outcome records are written to `execution_history` with baseline, post-execution values, and confidence notes.

## Adaptive Reassessment Windows

URL-level impact windows are tracked in `recent_url_actions` with `review_not_before` timestamps.

- Agents propose reassessment context in plan JSON:
  - `target_urls`
  - `reassess_after_hours`
  - `content_type`
  - `competition_level`
  - `change_scope`
  - `critical_override`
- Runtime applies a hybrid model (agent proposal + system signals from tools/snapshot/content age) to determine final cooldown.
- Active cooldown URLs are injected into the next assessment prompt to avoid unnecessary rapid rework.
- `/portfolio` exposes latest cooldown rationale and the next reassessment timestamp per agent.

## Security

- **Never commit `.env`** — it contains API keys, WordPress credentials, and Telegram tokens. Use `.env.example` as a template.
- `state/` and `data/` are gitignored — they contain operational data and audit outputs.

## Safety Notes

- **Single poller only:** Telegram `getUpdates` allows one active poller per bot token. The bot now fails fast on 409 conflict.
- **Default message chain:** direct site-agent Telegram messages are disabled by default; internal updates flow to Commander timeline/state.
- **Debug override:** set `AGENT_DIRECT_TELEGRAM=true` to re-enable direct site-agent bot messages temporarily.
