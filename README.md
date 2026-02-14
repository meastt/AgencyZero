# OpenClawSEO

AI-assisted SEO automation workspace for OpenClaw.

This repository is set up to run an SEO manager agent (currently focused on `griddleking.com`) that performs recurring audits, identifies growth opportunities, and reports issues through Telegram.

## What This Repo Does

- Runs an OpenClaw agent workspace from `agents/seo_manager`
- Pulls Google Search Console data for ranking/click analysis
- Audits WordPress content for decay, orphan pages, and refresh targets
- Produces JSON outputs for follow-up actions and tracking
- Sends failure alerts to Telegram when critical integrations break

## Project Layout

- `main.sh` - bootstrap script (`openclaw` install + gateway start)
- `agents/seo_manager/seo_kickstart.py` - end-to-end kickstart analysis (GSC + WP + linking)
- `agents/seo_manager/scripts/gsc_audit.py` - periodic GSC drop/opportunity audit
- `agents/seo_manager/scripts/content_audit.py` - WordPress content opportunity scan
- `scripts/gsc_bridge.py` - lightweight GSC query helper
- `data/` - generated audit outputs
- `docs/` - architecture and operator documentation

## Requirements

- macOS/Linux shell environment
- Python 3.10+ (recommended)
- Node.js + npm (for `npm start`)
- OpenClaw CLI (auto-installed by `main.sh` if missing)
- Access credentials for:
  - Google Search Console service account
  - WordPress API (username + app password)
  - Brave Search API (optional for extended keyword/competitor workflows)
  - Telegram bot (optional, for alerting)

## Environment Variables

Create a `.env` file in the repo root and set the variables your workflow needs:

- `GSC_JSON_KEY` (required): full JSON service account key as a string
- `GSC_SITE_URL` (optional): defaults to `https://griddleking.com/`
- `WP_URL` (required for WP audits)
- `WP_USERNAME` (required for WP audits)
- `WP_APP_PASS` (required for WP audits)
- `BRAVE_SEARCH_API_KEY` (used by kickstart/expansion workflows)
- `TELEGRAM_BOT_TOKEN` (optional, for alerts)
- `TELEGRAM_CHAT_ID` (optional, for alerts)

## Quick Start

1. Install dependencies:

```bash
npm install
```

2. Configure `.env` with the variables above.

3. Start OpenClaw + register the SEO agent:

```bash
npm start
```

This runs `main.sh`, which:
- installs `openclaw` if needed
- registers agent `seo_manager` with workspace `./agents/seo_manager`
- starts the OpenClaw gateway

## Common Operations

Run from the repository root.

### Full kickstart mission

```bash
python3 agents/seo_manager/seo_kickstart.py
```

Output: `seo_kickstart_results.json`

### GSC performance audit

```bash
python3 agents/seo_manager/scripts/gsc_audit.py
```

Output: `data/gsc_audit_latest.json`

### Content opportunity audit

```bash
python3 agents/seo_manager/scripts/content_audit.py
```

Input required: `data/wp_posts.json`  
Output: `data/content_opportunities.json`

## Monitoring & Health Checks

- `openclaw status` - verify gateway/agent health
- `openclaw logs --follow` - stream runtime logs
- Re-run `npm start` to poke/restart local workflow

## Notes

- This repo currently reflects a single-agent implementation (`seo_manager`) with docs that also describe a future multi-agent architecture.
- Keep credentials out of version control; never commit real API keys or secrets.