# SEO Playbook - Griddle King Domination Strategy

## Philosophy
Every action must move the needle on:
1. **Traffic** (sessions, users)
2. **Rankings** (position improvements)
3. **Authority** (backlinks, internal structure)
4. **Conversions** (if applicable)

Never optimize for the sake of optimizing. Every change must have a measurable hypothesis.

---

## Audit 1: CTR Overhaul

### Goal
Fix high-impression, low-CTR pages to capture more of the traffic we're already earning.

### Workflow
1. **Pull GSC data**: Last 28 days, query for pages (not queries)
2. **Filter**: 
   - Top 20 by impressions
   - CTR < 2%
   - Position < 20 (we're visible, just not clickable)
3. **Analyze each page**:
   - Current title/meta in WordPress
   - Top 3 competitors' titles for same keyword
   - User intent (informational, transactional, comparison?)
4. **Rewrite**:
   - **Title formula**: [Number/Year] + Power Word + Keyword + Benefit
     - Example: "7 Best Cast Iron Griddles (2026) – Tested by Chefs"
   - **Meta formula**: Hook + Value Prop + CTA
     - Example: "We tested 23 griddles over 6 months. Here's what actually works for home cooking. See the winner →"
5. **Update WordPress**:
   - Use `wp_update_post` for title
   - Use SEO plugin meta fields for description
6. **Track**: Note changes in `memory/ctr-experiments.md` with before/after data

### Success Metric
Average CTR increase of 1-3% within 14 days = 15-45% more traffic from same rankings.

---

## Audit 2: Authority Mapping

### Goal
Distribute link equity from high-authority posts to boost smaller/newer content.

### Workflow
1. **Identify power posts**:
   - Top 10 by organic sessions (GSC or WordPress analytics)
   - Bonus: Check domain authority (if using SEO plugin)
2. **Content inventory**:
   - Pull all posts from WordPress
   - Tag by topic/category
3. **Link matching**:
   - For each power post, identify 3-5 relevant smaller posts
   - **Relevance rules**:
     - Same niche (griddles, cooking surfaces, recipes)
     - Contextually natural (not forced)
     - Helpful to the reader (would they actually click?)
4. **Insertion strategy**:
   - Add links within first 3 paragraphs (highest engagement zone)
   - Use descriptive anchor text (not "click here")
   - Format: "If you're new to griddle cooking, start with our [beginner's guide to seasoning]."
5. **Update via WordPress API**:
   - Use `wp_alter_post` for surgical edits (search-replace)
   - Or pull full content → edit → `wp_update_post`
6. **Monitor**:
   - Track position changes for linked posts over 30 days
   - Note in `memory/link-experiments.md`

### Success Metric
5-10 position improvements in linked posts within 30 days.

---

## Audit 3: Stage 1 Push (Page 2 → Page 1)

### Goal
Move keywords from positions 11-15 to positions 1-10 (the "low-hanging fruit" of SEO).

### Workflow
1. **Pull GSC data**:
   - Last 90 days
   - Filter: avg position 11-15
   - Sort by impressions (search volume proxy)
2. **Select targets**:
   - Top 5 by impressions
   - Check actual search volume via Brave Search or keyword tool
   - Prioritize commercial intent keywords
3. **Content audit** (per keyword/page):
   - **Freshness**: When was it last updated? Add 2026 date to title/intro.
   - **Depth**: Word count vs. top 3 competitors? Aim for 20% longer.
   - **Media**: Images, videos, infographics? Add missing visual content.
   - **Internal links**: Who's linking to this page? Add 2-3 more.
   - **Backlinks**: Any? If not, note for outreach.
   - **SERP features**: Are competitors winning featured snippets? Add FAQ/list format.
4. **Refresh strategy**:
   - Add new section (e.g., "2026 Update: What's Changed")
   - Expand thin sections with unique insights
   - Add comparison table if competitors have one
   - Optimize for featured snippets (use H2 questions + concise answers)
5. **On-page SEO**:
   - Check keyword in title, H1, first paragraph
   - Add LSI keywords (related terms Google expects)
   - Improve internal linking (both to and from this page)
6. **Update WordPress** + **Note in GSC**:
   - Request re-indexing via Search Console API
7. **Track weekly**:
   - Log position changes in `memory/page2-push.md`

### Success Metric
3/5 keywords reach Page 1 within 60 days = 30-50% traffic increase for those terms.

---

## Audit 4: Competitor Content Gap

### Goal
Find topics competitors rank for that we're completely missing. Own those gaps.

### Workflow
1. **Identify competitors**:
   - Use Brave Search: `site:competitor.com griddles`
   - Top 3 by domain authority or traffic overlap
2. **Analyze their content**:
   - Scrape top 20 pages by traffic (use web_fetch)
   - Extract main keywords/topics
   - Group into pillars (e.g., "Griddle Recipes," "Buying Guides," "Maintenance")
3. **Gap analysis**:
   - Cross-reference with our content inventory
   - Find 3 pillar topics they dominate that we don't cover
4. **Prioritize**:
   - Search volume (use Brave Search for trending topics)
   - Commercial intent (can we monetize it?)
   - Authority required (can we realistically compete?)
5. **Content brief** (for #1 gap):
   - **Target keyword** + search volume
   - **Search intent** (what does the user want?)
   - **Outline**:
     - H1: Main keyword
     - H2s: Subtopics from top 3 competitors + unique angles
     - Required sections: Intro, main content, FAQ, conclusion
   - **Length**: Target word count (top 3 avg + 20%)
   - **Media**: Required images, videos, tables
   - **Internal links**: 5-7 relevant existing posts to link to
   - **Unique angle**: What will make ours better than competitors?

### Success Metric
Publish 1 gap-filling post per month = 10-15% traffic increase from new keywords.

---

## Audit 5: Orphan Search & Rescue

### Goal
No post should be invisible. Every piece of content needs link equity flowing to it.

### Workflow
1. **Pull all posts from WordPress**:
   - Use `wp_get_posts` with high limit
   - Extract post IDs, titles, slugs, dates
2. **Scan for internal links**:
   - For each post, check if any OTHER posts link to it
   - **Method**: 
     - Loop through all post content
     - Search for `href="[target-post-slug]"`
     - Count incoming links
3. **Identify orphans**:
   - Posts with 0 incoming internal links
   - Exclude: homepage, contact page, about (non-content pages)
4. **Match with link sources**:
   - For each orphan, find 2-3 topically relevant posts to link FROM
   - **Criteria**:
     - Similar topic/category
     - Higher traffic (pass authority)
     - Contextually natural fit
5. **Add links**:
   - Use `wp_alter_post` or full content update
   - Place links in body (not just "related posts" widgets)
   - Use descriptive anchor text
6. **Track rescued orphans**:
   - Note in `memory/orphan-rescue.md`
   - Monitor position/traffic changes over 30 days

### Success Metric
All orphans connected + 5-10% traffic increase to previously orphaned content within 60 days.

---

## Tools & Scripts Needed

### GSC API Wrapper
- Authenticate with service account JSON
- Pull page performance data (impressions, clicks, CTR, position)
- Pull query performance data
- Filter by date range, position, device

### WordPress API Wrapper
- Authenticate with app password or MCP
- CRUD operations on posts
- SEO metadata updates
- Internal link scanning

### Brave Search Integration
- Competitor research
- Keyword volume estimates
- SERP feature analysis

### Data Tracking
- `memory/ctr-experiments.md` - Before/after CTR data
- `memory/link-experiments.md` - Link additions + position changes
- `memory/page2-push.md` - Weekly position tracking for target keywords
- `memory/orphan-rescue.md` - Orphan inventory + rescue actions

---

## Red Flags to Watch For

1. **Keyword cannibalization**: Multiple posts targeting same keyword → consolidate or differentiate
2. **Thin content**: <500 words → expand or merge
3. **Outdated dates**: Old publish dates → refresh + add "2026 update"
4. **Broken links**: Internal 404s → fix immediately
5. **Slow pages**: >3s load time → optimize images, cache
6. **Mobile issues**: Not mobile-friendly → theme/design fix
7. **Duplicate meta**: Same title/description on multiple pages → unique per page

---

## Reporting Format (After Each Audit)

```
## Audit [N]: [Name]
**Status:** ✅ Complete
**Date:** YYYY-MM-DD
**Findings:**
- [Key metric 1]
- [Key metric 2]
**Actions Taken:**
- [Action 1] (e.g., "Updated 7 titles + meta descriptions")
- [Action 2] (e.g., "Added 15 internal links across 5 power posts")
**Expected Impact:**
- [Projection] (e.g., "15-20% CTR increase within 14 days")
**Tracking:**
- [Where data is logged] (e.g., "memory/ctr-experiments.md")
```

---

## Long-Term Strategy (Post-Kickstart)

### Monthly Cycles
1. **Week 1**: Fresh content (1-2 new posts from competitor gap research)
2. **Week 2**: Refresh cycle (update 3-5 old posts with new data/links)
3. **Week 3**: Link building (guest posts, outreach, citations)
4. **Week 4**: Technical SEO (fix issues, optimize speed, mobile)

### Quarterly Reviews
- Full site audit (crawl for errors)
- Backlink profile analysis
- Competitor benchmark (are they pulling ahead?)
- Content pruning (delete or noindex low-value pages)

### Annual Goals
- 100% YoY traffic growth
- Top 3 rankings for 20 main keywords
- 5,000+ monthly organic sessions
- Featured snippets for 10+ queries

---

## Anti-Patterns (What NOT to Do)

❌ **Keyword stuffing** - Kills readability, Google penalizes it
❌ **Buying backlinks** - High risk of manual penalty
❌ **Thin content farms** - 100 posts of 200 words each = waste
❌ **Ignoring user intent** - Ranking #1 for wrong intent = no conversions
❌ **Over-optimization** - 100% exact match anchors = red flag
❌ **Neglecting mobile** - 60%+ of traffic is mobile
❌ **Forgetting about humans** - Write for people, optimize for bots

---

**When in doubt: Quality > Quantity. Depth > Breadth. Value > Volume.**
