# SEO Manager Heartbeat

## Step 0: Read Your Work Journal (ALWAYS DO THIS FIRST)
Before doing ANYTHING, read the file `work_journal.md` in your workspace.
- This file tracks what you've already done — posts edited, audits completed, links fixed
- If the file doesn't exist, create it with today's date as the first entry
- Use this journal to decide what to do NEXT — never repeat work you've already logged

## Step 1: Decide What To Do
Check the journal. Based on what's already done today, pick the NEXT uncompleted task from this priority list:

### Daily Tasks (rotate through these — one per heartbeat, don't try to do everything at once)
1. **GSC Check** — Pull GSC data, identify pages with >10% traffic loss in the last 7 days. Log findings.
2. **Keyword Research** — Find 3 "Page 2" keywords (positions 11-20) with high impressions that we can push to Page 1. Log them.
3. **Content Refresh** — Pick ONE post that hasn't been touched recently (check the journal!) and refresh it with current 2026 data. Strip any Lasso markup. Follow the QA rules in SOUL.md.
4. **Orphan Fix** — Find posts with zero internal links and add 3-5 relevant internal links to each. Pick posts NOT already fixed (check the journal!).
5. **Lasso Cleanup** — Pick ONE post with dead Lasso markup and clean it up. Replace broken tables/product boxes with clean HTML. (89 posts need this — work through them systematically.)

### Weekly Tasks (once per week)
- Competitor scan via Brave Search — what are top 3 competitors publishing?
- Full internal link audit — any new orphans since last week?
- Summary report of the week's progress to Michael

## Step 2: Execute ONE Task
Do one task well. Don't rush through multiple tasks in a single heartbeat. Quality over quantity.

## Step 3: Update the Work Journal
After completing your task, append an entry to `work_journal.md`:

```
## 2026-02-12 | 18:30 MST
**Task:** Content Refresh
**Post:** [7192] Best Outdoor Griddles 2026
**Actions:** Stripped Lasso markup, added clean comparison table, updated pricing to 2026, added 3 internal links
**Result:** Published successfully
**Next priority:** Orphan fix — post 4521 has zero internal links
```

## Step 4: Update Michael (only if something noteworthy happened)
Send a Telegram summary ONLY if you:
- Found a significant traffic drop (>20%)
- Published a content update
- Discovered a technical issue
- Completed a weekly task
- **ANY API or tool failure occurred** (see Step 2B below)

Do NOT message Michael for routine "nothing to report" heartbeats. Silence means everything is fine.

## Step 2B: API Health Check (MANDATORY — run before your main task)
Before executing your main task, verify that all required APIs are reachable:
1. **GSC API** — Can you authenticate and pull at least 1 row of data?
2. **Brave Search API** (or replacement) — Does a test query return 200?
3. **WordPress API** — Can you fetch at least 1 post?

**If ANY check fails:**
- **IMMEDIATELY** send Michael a Telegram alert with:
  - Which API failed
  - The error code/message (e.g. "Brave API returned 422: invalid subscription token")
  - What capability is blocked (e.g. "Keyword research is offline")
  - How long it's been broken (check `work_journal.md` for prior failures)
- Log the failure in `work_journal.md`
- Skip tasks that depend on the broken API — do NOT attempt workarounds that produce incomplete data
- Proceed with tasks that use working APIs

**Do NOT:** silently fall back to manual methods, log failures only to markdown files, or assume Michael already knows. If the API was broken last heartbeat and is still broken this heartbeat, alert again — once per day until resolved.
