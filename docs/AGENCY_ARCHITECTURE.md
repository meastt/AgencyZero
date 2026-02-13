# OpenClaw SEO Agency Architecture

## Overview

A 7-site SEO agency managed by an AI agent hierarchy. One Agency Head (Opus 4.6 with extended thinking) coordinates 7 specialized Worker Agents (Sonnet), each owning a single domain. Workers execute autonomously and report up. The Head tracks portfolio-wide metrics, identifies cross-site opportunities, and adjusts strategy from a leadership position.

---

## Portfolio

### Tier A: Content Blogs (WordPress)
Organic traffic sites monetized through content volume and authority. These are niche blogs targeting search traffic.

| Domain | Niche | Platform | Deploy Method | Agent Type |
|--------|-------|----------|---------------|------------|
| griddleking.com | Griddles, grills, smokers, flat tops | WordPress | WP REST API | Content Blog Agent |
| phototipsguy.com | Photography tips & gear | WordPress | WP REST API | Content Blog Agent |
| tigertribe.net | Predatory cats & animals (tigers, mountain lions, bears — educational/informational) | WordPress | WP REST API | Content Blog Agent |

### Tier B: App Marketing Sites (Next.js / Vercel)
Product sites that funnel organic traffic to iOS App Store and Google Play downloads. SEO goal is download conversions, not just traffic.

| Domain | Product | Platform | Deploy Method | Agent Type |
|--------|---------|----------|---------------|------------|
| ebikepsi.com | E-bike tire PSI calculator | Next.js (content in `content/blog/` markdown + `app/` routes, PSEO pages) | `git push main` -> Vercel | App Marketing Agent |
| protocol21blackjack.com | Blackjack simulator | Next.js monorepo (`web/src/` for site content) | `git push main` -> Vercel | App Marketing Agent |
| cranksmith.com | Bike parts compatibility tool | Next.js + Capacitor (`src/` for content) | `git push main` -> Vercel | App Marketing Agent |
| inkpreview.app | Tattoo preview tool | Next.js (`app/` directory) | `git push main` -> Vercel | App Marketing Agent |

---

## Agent Hierarchy

```
                    +---------------------------+
                    |      AGENCY HEAD          |
                    |   Model: Opus 4.6 (thinking) |
                    |   Role: Portfolio Strategist  |
                    +---------------------------+
                               |
            +------------------+------------------+
            |                                     |
    +-------+-------+                    +--------+-------+
    | TIER A: Blogs |                    | TIER B: Apps   |
    +---------------+                    +----------------+
    |               |                    |                |
    v               v                    v                v
+-----------+ +-----------+       +-----------+   +-----------+
|GriddleKing| |PhotoTips  |       | eBikePSI  |   |Protocol21 |
|  (Sonnet) | | (Sonnet)  |       | (Sonnet)  |   | (Sonnet)  |
+-----------+ +-----------+       +-----------+   +-----------+
                |                       |               |
          +-----------+           +-----------+   +-----------+
          |TigerTribe |           |CrankSmith |   |InkPreview |
          | (Sonnet)  |           | (Sonnet)  |   | (Sonnet)  |
          +-----------+           +-----------+   +-----------+
```

---

## Agent Roles

### Agency Head (1 agent)

**Model:** Opus 4.6 with extended thinking
**Channel:** Dedicated Telegram thread or channel for Mike
**Schedule:** Runs on-demand + weekly strategy cycle

**Responsibilities:**
- Receive structured reports from all 7 workers
- Portfolio-level metric tracking (total organic sessions, total impressions, download funnels)
- Cross-site strategy: identify keyword cannibalization between sites, link building opportunities across the portfolio
- Resource allocation: decide which sites get priority based on ROI potential
- Pattern recognition: "This content format is winning on 3 sites, roll it out everywhere"
- Escalation handler: workers flag blockers, Head decides resolution
- Weekly portfolio brief to Mike via Telegram

**Does NOT do:**
- Edit content directly
- Make API calls to WordPress or git pushes
- Execute audits — that's the workers' job

**Commands (Telegram):**
- `/portfolio` — Full dashboard: traffic, rankings, downloads across all 7 sites
- `/strategy` — Current strategic priorities and reasoning
- `/allocate` — Where resources are being focused and why
- `/site [domain]` — Deep dive on one site's performance
- `/escalations` — Open issues that need Mike's input

---

### Content Blog Agent (3 agents: Griddle King, PhotoTipsGuy, TigerTribe)

**Model:** Sonnet
**Capabilities:** WordPress REST API (create/edit/update posts, metadata, categories, internal links)
**Data Sources:** GSC API, Brave Search, WordPress API

**Responsibilities:**
- Daily GSC monitoring: traffic drops, impression spikes, CTR anomalies
- Content lifecycle: identify decaying posts, refresh with current data
- Internal linking: ensure no orphaned posts, maintain link equity flow
- Competitor research: find content gaps via Brave Search
- Keyword tracking: monitor Page 2 keywords ripe for promotion
- Technical SEO: fix 404s, broken metadata, missing alt tags, schema markup
- New content drafting: write and publish posts when gaps are identified

**Daily Heartbeat:**
1. Pull GSC data, flag anomalies
2. Check for orphaned/decaying content
3. Execute one content action (refresh, new post, link fix)
4. Submit structured report to Agency Head

**Report Format (to Head):**
```json
{
  "agent": "griddleking",
  "date": "2026-02-12",
  "metrics": {
    "total_clicks_7d": 1250,
    "total_impressions_7d": 45000,
    "avg_ctr": 2.8,
    "avg_position": 18.4
  },
  "actions_taken": [
    {"type": "content_refresh", "post": "best-flat-top-grills-2026", "reason": "CTR dropped 40% MoM"},
    {"type": "internal_link", "from": "griddle-accessories", "to": "best-flat-top-grills-2026"}
  ],
  "opportunities": [
    {"keyword": "blackstone griddle seasoning", "impressions": 800, "position": 12.3, "action": "needs dedicated post"}
  ],
  "blockers": []
}
```

---

### App Marketing Agent (4 agents: eBikePSI, Protocol21, CrankSmith, InkPreview)

**Model:** Sonnet
**Capabilities:** Git operations (clone, branch, edit files, commit, push to main via Vercel auto-deploy)
**Data Sources:** GSC API, Brave Search, repo file system

**Responsibilities:**
- SEO-optimized landing pages: ensure app store funnel pages rank for target keywords
- Blog/content strategy: write supporting content that targets informational queries and funnels to downloads
- Programmatic SEO (PSEO): generate location/variation pages at scale where applicable (ebikepsi already does this)
- App Store Optimization (ASO) alignment: ensure website keywords match App Store/Play Store listing keywords
- Technical SEO: meta tags, Open Graph, structured data, sitemap, robots.txt
- Conversion tracking: monitor which organic pages drive the most download clicks

**Key Difference from Blog Agents:**
These agents optimize for a **funnel**, not just traffic. Every content decision should answer: "Does this page move someone closer to downloading the app?"

**Content Workflow:**
1. `git pull origin main` to sync latest
2. Create/edit files in the repo (markdown in `content/`, components in `app/` or `src/`)
3. `git commit` with descriptive message
4. `git push origin main` — Vercel auto-deploys (agent interacts with GitHub only, not Vercel)
5. Verify deployment via GitHub Deployments API (`gh api repos/{owner}/{repo}/deployments`) — Vercel posts deployment status back to GitHub automatically. No Vercel token needed.
6. If deployment fails: read error from GitHub deployment status, fix the issue, re-push
7. Submit structured report to Agency Head

**Deployment Verification (detail):**
```bash
# After push, poll GitHub for Vercel deployment status
COMMIT_SHA=$(git rev-parse HEAD)
DEPLOY_ID=$(gh api "repos/{owner}/{repo}/deployments?sha=$COMMIT_SHA" --jq '.[0].id')
STATUS=$(gh api "repos/{owner}/{repo}/deployments/$DEPLOY_ID/statuses" --jq '.[0].state')
# "success" = live, "failure" = build failed, "pending" = still building
```

**Optional enhancement:** Add a `/api/health` endpoint to each Next.js site:
```javascript
// app/api/health/route.js
export function GET() {
  return Response.json({
    status: 'ok',
    commit: process.env.VERCEL_GIT_COMMIT_SHA || 'unknown'
  });
}
```
This lets the agent confirm the exact commit is live by hitting `https://{domain}/api/health`.

**Report Format (to Head):**
```json
{
  "agent": "ebikepsi",
  "date": "2026-02-12",
  "metrics": {
    "total_clicks_7d": 320,
    "total_impressions_7d": 12000,
    "avg_ctr": 2.7,
    "top_landing_page": "/best-ebike-tire-pressure",
    "estimated_download_clicks": 45
  },
  "actions_taken": [
    {"type": "pseo_pages", "count": 6, "template": "tire-size-guides"},
    {"type": "meta_fix", "page": "/calculator", "change": "added schema markup"}
  ],
  "opportunities": [
    {"keyword": "ebike tire pressure chart", "impressions": 2000, "position": 8.5, "action": "create dedicated landing page"}
  ],
  "deployment": {"status": "success", "commit": "a1b2c3d", "url": "https://ebikepsi.com"},
  "blockers": []
}
```

---

## Communication Architecture

### Worker -> Head (Structured Reports)
Workers submit JSON reports after each work cycle. The Head consumes these to build portfolio-wide awareness.

**Mechanism:** Two viable approaches (use both):

1. **OpenClaw agent-to-agent messaging (confirmed supported):**
   OpenClaw has native inter-agent messaging, disabled by default. Enable via config:
   ```json
   "tools": {
     "agentToAgent": {
       "enabled": true,
       "allow": ["agency_head", "seo_griddleking", "seo_phototipsguy", "seo_tigertribe",
                  "seo_ebikepsi", "seo_protocol21", "seo_cranksmith", "seo_inkpreview"]
     }
   }
   ```
   Communication is text-based natural language messages. Workers send structured report text to the Head. No RPC/pub-sub — just message passing.

2. **Shared filesystem (backup/audit trail):**
   Each worker also writes to `reports/{domain}/{date}.json` for persistence and Head ingestion. This serves as the audit trail and allows the Head to re-read historical data without re-querying workers.

### Head -> Worker (Strategic Directives)
The Head can issue directives to individual workers when strategy shifts.

**Example directives:**
- "griddleking: Pause new content. Focus 100% on refreshing top 20 posts this week."
- "ebikepsi: Protocol21 is ranking for 'cycling apps' — create a comparison page to capture spillover."
- "all: Google algorithm update detected. Run full technical audit on all sites immediately."

### Head -> Mike (Telegram)
Weekly portfolio brief + on-demand queries via commands. The Head is Mike's single point of contact — he shouldn't need to talk to individual workers.

---

## Environment & Credentials

### Per-Agent Environment Variables

**Important constraint:** OpenClaw does NOT support per-agent env blocks natively. The `env` block in `openclaw.json` is global — all agents share it. Each agent gets isolated sessions, workspaces, and auth profiles, but NOT isolated env vars.

**Workaround: Namespaced env vars + per-agent workspace `.env` files**

Use site-specific variable names in the global env block so agents can read only their own:

**Global env block (shared keys):**
```
ANTHROPIC_API_KEY={key}
BRAVE_SEARCH_API_KEY={key}
BRAVE_API_KEY={key}
GSC_JSON_KEY={shared service account JSON}
```

**WordPress agents — namespaced per site:**
```
WP_URL_GRIDDLEKING=https://griddleking.com/
WP_USERNAME_GRIDDLEKING=meastt09@gmail.com
WP_APP_PASS_GRIDDLEKING={app-password}

WP_URL_PHOTOTIPSGUY=https://phototipsguy.com/
WP_USERNAME_PHOTOTIPSGUY={user}
WP_APP_PASS_PHOTOTIPSGUY={app-password}

WP_URL_TIGERTRIBE=https://tigertribe.net/
WP_USERNAME_TIGERTRIBE={user}
WP_APP_PASS_TIGERTRIBE={app-password}
```

**Vercel agents — namespaced per site:**
```
SITE_URL_EBIKEPSI=https://ebikepsi.com/
REPO_PATH_EBIKEPSI=/path/to/ebikepsi-repo

SITE_URL_PROTOCOL21=https://protocol21blackjack.com/
REPO_PATH_PROTOCOL21=/path/to/protocol21-repo

SITE_URL_CRANKSMITH=https://cranksmith.com/
REPO_PATH_CRANKSMITH=/path/to/cranksmith-repo

SITE_URL_INKPREVIEW=https://inkpreview.app/
REPO_PATH_INKPREVIEW=/path/to/inkpreview-repo
```

Each agent's SOUL.md tells it which namespaced variables to use (e.g., "Your credentials are in WP_URL_GRIDDLEKING, WP_USERNAME_GRIDDLEKING, WP_APP_PASS_GRIDDLEKING").

**Alternative (Docker isolation):** Run each agent in its own Docker container with a dedicated `.env` file. This is the officially documented multi-agent isolation pattern but adds operational complexity.

### GSC Service Account
The existing service account (`openclaw-seo@gen-lang-client-0455698266.iam.gserviceaccount.com`) already has access to 3 properties. Add the remaining 4:
- [ ] ebikepsi.com
- [ ] protocol21blackjack.com
- [ ] cranksmith.com
- [ ] inkpreview.app

---

## OpenClaw Configuration

### Agent Registration

Each agent gets its own entry in `openclaw.json`:

```json
{
  "agents": {
    "list": [
      {"id": "agency_head", "name": "agency_head", "workspace": "/path/to/agency-head/"},
      {"id": "seo_griddleking", "name": "seo_griddleking", "workspace": "/path/to/agents/griddleking/"},
      {"id": "seo_phototipsguy", "name": "seo_phototipsguy", "workspace": "/path/to/agents/phototipsguy/"},
      {"id": "seo_tigertribe", "name": "seo_tigertribe", "workspace": "/path/to/agents/tigertribe/"},
      {"id": "seo_ebikepsi", "name": "seo_ebikepsi", "workspace": "/path/to/agents/ebikepsi/"},
      {"id": "seo_protocol21", "name": "seo_protocol21", "workspace": "/path/to/agents/protocol21/"},
      {"id": "seo_cranksmith", "name": "seo_cranksmith", "workspace": "/path/to/agents/cranksmith/"},
      {"id": "seo_inkpreview", "name": "seo_inkpreview", "workspace": "/path/to/agents/inkpreview/"}
    ]
  }
}
```

### Model Assignment
```json
{
  "agents": {
    "defaults": {
      "model": {"primary": "anthropic/claude-sonnet-4-5-20250929"}
    },
    "list": [
      {"id": "agency_head", "model": {"primary": "anthropic/claude-opus-4-6"}}
    ]
  }
}
```

### Telegram Bindings
The Head agent owns the Telegram channel. Workers do not have direct Telegram access — they report through the Head.

```json
{
  "bindings": [
    {"agentId": "agency_head", "match": {"channel": "telegram"}}
  ]
}
```

---

## Directory Structure

```
OpenClawSEO/
  agents/
    agency_head/
      SOUL.md              # Portfolio strategist persona
      HEARTBEAT.md         # Weekly strategy cycle
      USER.md              # Mike's context
    griddleking/
      SOUL.md              # Content blog agent persona
      HEARTBEAT.md         # Daily SEO tasks
    phototipsguy/
      SOUL.md
      HEARTBEAT.md
    tigertribe/
      SOUL.md
      HEARTBEAT.md
    ebikepsi/
      SOUL.md              # App marketing agent persona
      HEARTBEAT.md
    protocol21/
      SOUL.md
      HEARTBEAT.md
    cranksmith/
      SOUL.md
      HEARTBEAT.md
    inkpreview/
      SOUL.md
      HEARTBEAT.md
  reports/                  # Shared report directory
    griddleking/
    phototipsguy/
    tigertribe/
    ebikepsi/
    protocol21/
    cranksmith/
    inkpreview/
  scripts/
    gsc_bridge.py           # Shared GSC data fetcher
  docs/
    AGENCY_ARCHITECTURE.md  # This document
```

---

## Cost Management

Running 8 agents (1 Opus + 7 Sonnet) requires cost awareness.

**Strategies:**
- **Head runs on-demand + weekly**, not continuously. Opus thinking tokens are expensive — use them for strategy, not routine checks.
- **Workers run daily heartbeats** on Sonnet, which is significantly cheaper.
- **Workers compress data before reporting.** The Head should never process raw GSC dumps — only structured summaries.
- **Stagger worker schedules.** Don't run all 7 simultaneously. Spread across the day to flatten API usage.
- **Tiered activity:** Not all sites need daily attention. Low-traffic sites can run 2-3x/week while high-priority sites run daily.

**Rough cost estimate:**
- 7 Sonnet workers x daily heartbeat: ~$2-5/day depending on action complexity
- 1 Opus head x weekly strategy + on-demand: ~$3-8/week
- Total: ~$20-45/week at moderate activity levels
- Monitor and adjust based on actual token usage

---

## Rollout Plan

### Phase 1: Stabilize the Foundation (Current)
- [x] Single agent (Griddle King) fully operational
- [ ] Verify GSC + Brave + WordPress all working reliably for 1 week
- [ ] Document any edge cases or failures

### Phase 2: Template the Agent Pattern
- [ ] Extract reusable SOUL.md / HEARTBEAT.md templates for both agent types
- [ ] Create a "Content Blog Agent" template from the working Griddle King config
- [ ] Create an "App Marketing Agent" template (new — needs git workflow instead of WP API)
- [ ] Build the shared report format and reporting directory

### Phase 3: Expand to All 7 Workers
- [ ] Add GSC access for the 4 remaining sites
- [ ] Generate WP App Passwords for phototipsguy.com and tigertribe.net
- [ ] Clone repos for the 4 Vercel sites to the local machine (or configure git access)
- [ ] Register all 7 agents in openclaw.json with isolated workspaces and credentials
- [ ] Deploy each worker one at a time, verify it runs a full cycle successfully

### Phase 4: Deploy the Agency Head
- [ ] Write the Head's SOUL.md with portfolio strategy persona
- [ ] Configure Opus 4.6 model assignment
- [ ] Set up report ingestion (Head reads from `reports/` directory)
- [ ] Wire Telegram to the Head (replace current single-agent binding)
- [ ] Define the Head -> Worker directive format
- [ ] Test: Head receives reports from all 7 workers and generates a portfolio brief

### Phase 5: Run and Tune
- [ ] Run full agency for 2 weeks
- [ ] Monitor cost, identify wasteful patterns
- [ ] Tune heartbeat frequency per site based on traffic volume
- [ ] Calibrate Head's strategy cycle (weekly? bi-weekly?)
- [ ] Add alerting: Head notifies Mike of critical issues (traffic crashes, deployment failures, etc.)

---

## Resolved Questions

1. **Inter-agent messaging:** YES — OpenClaw supports it natively via `tools.agentToAgent` config. Disabled by default, must enable + allowlist agent IDs. Communication is text-based (natural language), not structured RPC. Use alongside filesystem reports for persistence.

2. **Git authentication for Vercel agents:** Agents interact with GitHub only (not Vercel directly). They `git push origin main` and Vercel auto-deploys. Use SSH keys already on the machine or a GitHub token. Deployment verification uses the GitHub API (`gh` CLI) to read deployment statuses that Vercel posts back — no Vercel token required.

3. **Concurrent agent limits:** No hard limit. OpenClaw docs say "dozens (even hundreds) are fine." 8 agents is well within range. Practical limit is RAM (~512MB per agent) and API token cost. Community reports of 5+ agents on 16GB RAM with no issues. The `maxConcurrent` setting controls parallelism within a single agent, not total agent count.

4. **TigerTribe niche:** Predatory cats and animals — tigers, mountain lions, bears, etc. Educational/informational content targeting queries like "how much does a bengal tiger weigh?" and "where are mountain lions native?"

5. **Vercel build verification:** YES — agents must verify deployment and handle failures autonomously. Use GitHub Deployments API to check status, retry on failure. Optionally add `/api/health` endpoints to each site for commit-level confirmation.

## Phase 5 Tuning Notes (Not Blockers)

These are optimization decisions to make once the agency is running and producing data:

1. **Per-agent env isolation at scale:** The namespaced env var approach (`WP_URL_GRIDDLEKING`, etc.) works fine for 7 sites. If it gets unwieldy, migrate to Docker-based isolation where each agent container gets its own `.env` file. Decision point: when adding site #8+.

2. **Heartbeat scheduling:** Start with fixed daily heartbeats for all workers. After 2 weeks of data, shift low-traffic sites (inkpreview, cranksmith) to 2-3x/week and keep high-traffic sites (griddleking, ebikepsi) daily. The Head agent can eventually manage this dynamically based on ROI signals.

3. **Cost monitoring:** Add a `cost_tokens` field to each worker's daily report. The Head agent sums these in its weekly brief to Mike. If weekly cost exceeds a threshold (e.g., $50), Head alerts immediately. Anthropic's API usage dashboard is the source of truth for actual spend.
