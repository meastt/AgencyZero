# SCALING BLUEPRINT: Multi-Domain & Revenue Automation

## Phase 1: Portfolio Expansion (Multi-Domain)
**Goal:** Replicate the SEO Manager's success across other niche sites (Photography, Predatory Cats) without code duplication.

### Architecture
```markdown
OpenClawSEO/
├── agents/
│   ├── seo_manager/          # Griddle King (Active)
│   ├── photo_manager/        # Photography Blog (New)
│   └── cat_manager/          # Predatory Cat Blog (New)
├── shared/                   # Shared Resources
│   ├── scripts/              # Universal SEO scripts (GSC, WP, Ahrefs)
│   └── OPERATIONAL_PLAYBOOK.md  # Standard Operating Procedures
└── .env                      # Siloed credentials
```

### Implementation Steps
1.  **Shared Library Refactor**: Move generic scripts (`seo_kickstart.py`, `keyword_research.py`) to `shared/scripts/` and parameterize them to accept site-specific configs.
2.  **Agent Provisioning**:
    - Create `agents/photo_manager` and `agents/cat_manager`.
    - Create unique `SOUL.md` files for each niche (e.g., "The Visual Storyteller" vs "The Apex Predator").
    - Create site-specific `STRATEGIC_PLAN.md`.
3.  **Config Update**:
    - Add new credentials to `.env` (e.g., `PHOTO_WP_URL`, `CAT_GSC_JSON_KEY`).
    - Register new agents in `openclaw.json`.

---

## Phase 2: Inbox Intelligence (Email Triage)
**Goal:** Turn email from a distraction into a deal-flow pipeline.

### Architecture
- **Input**: IMAP connection to your email (or niche-specific inboxes).
- **Processing**: Agent scans unsanctioned emails every 60 mins.
- **Output**: Telegram alerts for opportunities; Drafts for routine replies.

### Logic Flow
1.  **Filter**: Ignore newsletters, spam, receipts.
2.  **Classify**:
    - `💰 OPPORTUNITY`: Sponsorships, guest posts, affiliate offers.
    - `❓ INQUIRY`: Reader questions, bug reports.
    - `🗑️ NOISE`: Everything else.
3.  **Action**:
    - **Opportunity**: Forward to Telegram with summary + drafted reply.
    - **Inquiry**: Draft helpful reply based on blog content (RAG).
    - **Noise**: Archive/Read.

---

## Phase 3: Affiliate Revenue Engine (Active)
**Goal:** Maximize revenue per session through deeper integration.

### Active Capabilities (Griddle King)
- **Context**: Agent knows Amazon, Impact, and AvantLink IDs.
- **Directives**: `SOUL.md` prioritizes commercial content and link fixes.

### Next Steps (Automation)
1.  **Link Auditor Script**: Scan all posts for untagged Amazon links and auto-inject `?tag=YOUR_AFFILIATE_TAG`.
2.  **Stock Checker**: Periodic check of top 20 affiliate products; if OOS, swap with alternative or alert user.
3.  **Revenue Dashboard**: Pull Amazon/Impact reports to correlate *specific posts* with *revenue*, feeding back into the content strategy.

---

## Execution Roadmap
- [ ] **Step 1**: Refactor scripts to `shared/` to prepare for multi-site.
- [ ] **Step 2**: Pilot `photo_manager` agent creation.
- [ ] **Step 3**: Build `email_triage.py` script for Gmail/IMAP.
