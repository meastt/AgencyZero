"""
Autonomous Agent Brain — the core decision loop for each site agent.
Assess -> Plan -> Execute -> Report, with Commander review gates.
"""

import json
import re
import traceback
from datetime import datetime, timedelta

AGENT_SYSTEM_TEMPLATE = """You are {agent_name}, an autonomous SEO agent managing {site_url}.
Your niche: {niche}.

NON-NEGOTIABLE MISSION:
1) Grow this site's revenue to at least ${revenue_target}/month.
2) Keep clear operational state so Commander and the human timeline stay accurate.

AUTONOMY RULES:
- You do not wait for human permission to do normal SEO work.
- Commander is the only review gate when reviews are enabled.
- Always choose executable actions that CHANGE THE SITE to move revenue and rankings now.
- Do NOT rework the same URLs before their impact window expires unless there's a critical error.
- NEVER create plans that only run audit/research tools.  Every plan MUST include at least one WRITE tool.

CURRENT STATE:
{site_snapshot}

SITE INVENTORY SUMMARY:
{inventory_summary}

MISSION STATE:
{mission_state}

RECENT TASK HISTORY:
{task_history}

ACTIVE URL IMPACT WINDOWS (avoid touching until review_not_before):
{url_cooldowns}

STRATEGIC PLAN:
{strategic_plan}

AVAILABLE TOOLS:
{tools_list}

IMPORTANT TOOL USAGE:
- WRITE tools (update_post_meta, inject_internal_links, fix_affiliate_links) require you to
  write an instruction JSON file BEFORE calling the tool.  The tool description tells you the
  file path and format.  Include a "write_instructions" field in each step that needs one.
- Use build_inventory INSTEAD of seo_audit for routine data gathering.
- Only use gsc_audit, keyword_research, or affiliate_audit when you need FRESH external data.
- ONLY use tool names from the AVAILABLE TOOLS list.  Do NOT invent tool names.

PRIORITY ORDER (always follow this):
1. Revenue leaks (broken affiliate links, missing CTAs) — use fix_affiliate_links
2. Declining pages (traffic drops, position losses) — use update_post_meta to fix titles/descriptions
3. Page 2 pushes (positions 11-20, close to Page 1) — use update_post_meta for CTR improvement
4. Orphan fixes (posts with zero internal links) — use inject_internal_links
5. New content opportunities (keyword gaps) — use build_inventory + keyword_research

You are in ASSESSMENT mode. Analyze the current data and respond with JSON:
{{
  "assessment": "2-3 sentence analysis of current site health",
  "top_priority": "The single most important thing to fix right now",
  "plan": {{
    "name": "Short plan name",
    "target_urls": ["https://...", "..."],
    "reassess_after_hours": 24,
    "content_type": "refresh|new_content|internal_links|technical|monetization|mixed",
    "competition_level": "low|medium|high",
    "change_scope": "light|medium|heavy",
    "critical_override": false,
    "steps": [
      {{"tool": "tool_name", "reason": "why this step", "write_instructions": {{...}} }},
      ...
    ],
    "expected_impact": "What this should achieve"
  }}
}}

If no inventory exists yet, your FIRST step must be build_inventory.
Reply with JSON only."""


EXECUTION_SYSTEM = """You are {agent_name} executing a plan step.
You just ran the tool `{tool_name}` and got these results:

{tool_output}

Analyze the results and respond with JSON:
{{
  "summary": "1-2 sentence summary of what the tool found/did",
  "key_metrics": {{"metric_name": "value", ...}},
  "next_action": "continue" or "pause" or "escalate",
  "escalation_reason": "only if next_action is escalate"
}}

Reply with JSON only."""


# How long before assessment is considered stale
STALE_ASSESSMENT_HOURS = 1


class AgentBrain:
    """Autonomous agent loop — called by scheduler on each tick."""

    def __init__(self, agent_key, config, tools, state, claude, telegram_fn, review_now_fn=None):
        """
        Args:
            agent_key: e.g., "griddle"
            config: {"name", "site_url", "niche", "prefix"}
            tools: ToolRegistry instance
            state: StateStore instance
            claude: ClaudeClient instance
            telegram_fn: callable(message) to send Telegram alerts
            review_now_fn: optional callable() to trigger immediate Commander plan review
        """
        self.agent_key = agent_key
        self.config = config
        self.tools = tools
        self.state = state
        self.claude = claude
        self.telegram_fn = telegram_fn
        self.review_now_fn = review_now_fn

    def tick(self):
        """Main loop iteration — called by scheduler every interval.

        State machine:
            idle (stale assessment) -> assessing -> planning -> awaiting_approval
            idle (approved plan) -> executing -> reporting -> idle
            error -> idle (after timeout)
        """
        agent_state = self.state.get_agent(self.agent_key)
        status = agent_state.get("status", "idle")
        self.state.set_agent_status(self.agent_key, status)  # Update last_tick
        # Refresh after write to avoid acting on stale state.
        agent_state = self.state.get_agent(self.agent_key)
        status = agent_state.get("status", status)

        print(f"[{self.agent_key}] tick: status={status}")
        self.state.increment_cycle_count()

        try:
            if status == "executing":
                # Already executing, let it finish on next tick
                pass
            elif status == "awaiting_approval":
                self._check_approval(agent_state)
            elif status == "error":
                self._handle_error_recovery(agent_state)
            elif status == "idle":
                # Refresh again so approvals that arrived during this tick are seen.
                agent_state = self.state.get_agent(self.agent_key)
                # Check if we have an approved plan to execute
                plan = agent_state.get("pending_plan")
                if plan and plan.get("status") == "approved":
                    self._execute_plan(agent_state)
                else:
                    forced, reason = self.state.consume_reassess_request(self.agent_key)
                    if forced:
                        print(f"[{self.agent_key}] Forced reassessment: {reason}")
                        self._assess(self.state.get_agent(self.agent_key))
                    elif self._assessment_is_stale(agent_state):
                        self._assess(agent_state)
                # else: idle with fresh assessment, nothing to do
        except Exception as e:
            error_msg = f"{self.agent_key} tick error: {str(e)[:300]}"
            print(f"[{self.agent_key}] ERROR: {error_msg}")
            traceback.print_exc()
            self.state.log_agent_error(self.agent_key, error_msg)
            self._notify(f"Error during tick: {str(e)[:200]}")

    def _load_inventory(self):
        """Load site inventory if it exists and is fresh enough."""
        import os
        slug = self.config.get("prefix", "").lower().replace("wp_", "").replace("_", "")
        inv_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "state", f"inventory_{slug}.json"
        )
        if not os.path.exists(inv_path):
            return None
        try:
            with open(inv_path, "r") as f:
                inv = json.load(f)
            # Check freshness — stale if older than 6 hours
            last_updated = inv.get("meta", {}).get("last_updated")
            if last_updated:
                age = datetime.now() - datetime.fromisoformat(last_updated)
                if age > timedelta(hours=6):
                    return None  # Stale — will trigger build_inventory
            return inv
        except Exception:
            return None

    def _assess(self, agent_state):
        """Run assessment: audit site, analyze data, create plan."""
        print(f"[{self.agent_key}] Starting assessment...")
        self.state.set_agent_status(self.agent_key, "assessing", task="Site assessment")
        self.state.log_agent_timeline(
            self.agent_key,
            "assessment_started",
            "Started assessment cycle for fresh site diagnosis.",
        )
        self._notify("Starting site assessment...")

        # Check if we have a fresh inventory — skip expensive seo_audit if so
        inventory = self._load_inventory()
        if inventory:
            inv_summary = inventory.get("summary", {})
            print(f"[{self.agent_key}] Using existing inventory ({inv_summary.get('total_posts', 0)} posts)")
        else:
            print(f"[{self.agent_key}] No fresh inventory — will run build_inventory")

        # Run GSC audit to get fresh traffic data (lightweight, always worth it)
        gsc_result = self.tools.run_tool("gsc_audit")
        snapshot = {}

        if gsc_result["success"] and gsc_result.get("data"):
            data = gsc_result["data"]
            summary = data.get("summary", {})
            snapshot = {
                "total_clicks": summary.get("current_clicks"),
                "prev_clicks": summary.get("prev_clicks"),
                "clicks_change_pct": summary.get("change_pct"),
                "declining_pages": len(data.get("drops", [])),
                "page2_opportunities": len(data.get("page2_opportunities", [])),
                "top_page2": data.get("page2_opportunities", [])[:5],
            }
            self.state.update_site_snapshot(self.agent_key, snapshot)
            self.state.update_agent_kpis(
                self.agent_key,
                self._extract_kpis(gsc_data=data),
                source="gsc_audit",
            )
        elif not inventory:
            # No GSC data AND no inventory — run build_inventory as fallback
            inv_result = self.tools.run_tool("build_inventory")
            if inv_result["success"]:
                inventory = self._load_inventory()
                if inventory:
                    inv_summary = inventory.get("summary", {})
                    snapshot = {
                        "total_posts": inv_summary.get("total_posts"),
                        "orphan_count": inv_summary.get("orphan_count"),
                    }
                    self.state.update_site_snapshot(self.agent_key, snapshot)

        # Ask Claude to assess and plan
        agent_state = self.state.get_agent(self.agent_key)  # Refresh
        self.state.set_agent_status(self.agent_key, "planning", task="Creating action plan")

        system_prompt = self._build_assessment_prompt(agent_state)
        messages = [{"role": "user", "content": "Assess the current site state and create an action plan."}]

        try:
            result = self.claude.structured_chat(system_prompt, messages, max_tokens=800)
        except Exception as e:
            self.state.log_agent_error(self.agent_key, f"Assessment Claude error: {e}")
            self._notify(f"Assessment failed: {str(e)[:200]}")
            return

        # Submit plan for Commander review
        plan = result.get("plan", {})
        assessment = result.get("assessment", "No assessment")

        self.state.submit_plan(self.agent_key, {
            "assessment": assessment,
            "top_priority": result.get("top_priority", ""),
            "plan": plan,
        })
        if self.review_now_fn:
            # Don't wait for the next periodic review window.
            self.review_now_fn()
        self.state.log_agent_timeline(
            self.agent_key,
            "assessment_completed",
            f"Assessment complete. Priority: {result.get('top_priority', 'N/A')}",
            {"plan_name": plan.get("name", "?")},
        )

        agent_state = self.state.get_agent(self.agent_key)
        agent_state["last_assessment"] = datetime.now().isoformat()
        self.state.save_agent(self.agent_key, agent_state)

        self._notify(
            f"Assessment complete. Top priority: {result.get('top_priority', 'N/A')}\n"
            f"Plan '{plan.get('name', '?')}' submitted for Commander review."
        )
        print(f"[{self.agent_key}] Plan submitted: {plan.get('name', '?')}")

    def _execute_plan(self, agent_state):
        """Execute an approved plan step by step."""
        plan_data = agent_state.get("pending_plan", {})
        plan = plan_data.get("plan", {}).get("plan", {})
        steps = plan.get("steps", [])
        baseline_kpis = dict(agent_state.get("kpis", {}))
        failed_steps = 0
        tools_ran = set()
        target_urls = plan.get("target_urls", [])
        reassess_after_hours, cooldown_reason = self._determine_reassess_window_hours(plan, agent_state)

        if not steps:
            self.state.complete_task(self.agent_key, "Empty plan — no steps to execute")
            return

        # Validate all tool names before starting execution.
        available = set(self.tools.list_tools().keys())
        invalid = [s.get("tool") for s in steps if s.get("tool") not in available]
        if invalid:
            # Strip invalid steps rather than aborting the whole plan.
            steps = [s for s in steps if s.get("tool") in available]
            print(f"[{self.agent_key}] Stripped invalid tools from plan: {invalid}")
            if not steps:
                self.state.complete_task(
                    self.agent_key,
                    f"Plan had only invalid tools: {invalid}",
                )
                return

        self.state.set_agent_status(self.agent_key, "executing", task=plan.get("name", "Executing plan"))
        self.state.log_agent_timeline(
            self.agent_key,
            "execution_started",
            f"Executing approved plan: {plan.get('name', '?')}",
            {"steps": len(steps)},
        )
        self._notify(f"Executing plan: {plan.get('name', '?')} ({len(steps)} steps)")

        for i, step in enumerate(steps):
            tool_name = step.get("tool")
            reason = step.get("reason", "")

            print(f"[{self.agent_key}] Step {i+1}/{len(steps)}: {tool_name} — {reason}")
            self.state.set_agent_status(
                self.agent_key, "executing",
                task=f"{plan.get('name', '?')} (step {i+1}/{len(steps)}: {tool_name})"
            )

            # Write instruction files for write tools before invoking them.
            self._write_tool_instructions(tool_name, step)

            result = self.tools.run_tool(tool_name)
            tools_ran.add(tool_name)

            is_write_tool = tool_name in self.WRITE_TOOL_INSTRUCTION_MAP

            if not result["success"]:
                failed_steps += 1
                error_msg = f"Step {i+1} ({tool_name}) failed: {result['output'][:200]}"
                self.state.log_agent_error(self.agent_key, error_msg)
                self.state.log_agent_timeline(
                    self.agent_key,
                    "step_failed",
                    error_msg,
                    {"step": i + 1, "tool": tool_name},
                )
                self._notify(f"Plan step failed: {error_msg}")
                if is_write_tool:
                    self.state.log_write_failure(self.agent_key, tool_name, error_msg)
                # Continue with remaining steps rather than aborting
                continue

            # Track successful write tool executions for monitoring
            if is_write_tool:
                self.state.log_write_activity(self.agent_key, tool_name)

            # Analyze results
            try:
                analysis = self._analyze_step_result(tool_name, result)
                if analysis.get("next_action") == "escalate":
                    self.state.add_escalation(
                        self.agent_key,
                        analysis.get("escalation_reason", "Unknown issue")
                    )
                    self._notify(f"Escalation: {analysis.get('escalation_reason', '?')}")
                    break
                elif analysis.get("next_action") == "pause":
                    self._notify(f"Pausing after step {i+1}: {analysis.get('summary', '?')}")
                    break
            except Exception:
                pass  # Analysis is optional, don't fail the plan

        # Capture post-execution KPI snapshot — skip tools already run in plan.
        post_kpis = self._capture_post_execution_kpis(skip_tools=tools_ran)
        notes = f"{len(steps) - failed_steps}/{len(steps)} steps succeeded"
        confidence = "high" if failed_steps == 0 else "medium"
        self.state.record_execution_outcome(
            self.agent_key,
            plan.get("name", "Executing plan"),
            baseline_kpis=baseline_kpis,
            post_kpis=post_kpis,
            notes=notes,
            confidence=confidence,
        )
        self.state.record_url_actions(
            self.agent_key,
            urls=target_urls,
            action=(
                f"Plan execution: {plan.get('name', 'Unnamed plan')} | "
                f"cooldown={reassess_after_hours}h | {cooldown_reason}"
            ),
            review_after_hours=reassess_after_hours,
        )

        # Plan complete
        self._report_results(plan)

    def _report_results(self, plan):
        """Report plan execution results."""
        self.state.set_agent_status(self.agent_key, "reporting", task="Generating report")

        summary = f"Plan '{plan.get('name', '?')}' completed"
        # complete_task atomically clears pending_plan, last_assessment, and
        # sets status=idle — no separate write needed.
        self.state.complete_task(self.agent_key, summary)

        self._notify(f"Plan complete: {plan.get('name', '?')}\nExpected impact: {plan.get('expected_impact', 'N/A')}")
        print(f"[{self.agent_key}] Plan complete: {plan.get('name', '?')}")

    def _check_approval(self, agent_state):
        """Check if Commander has approved/rejected our plan."""
        # Always refresh state — approval/rejection may happen asynchronously.
        agent_state = self.state.get_agent(self.agent_key)
        plan = agent_state.get("pending_plan", {})
        status = plan.get("status", "pending_review")

        if status == "approved":
            print(f"[{self.agent_key}] Plan approved, executing now")
            self._execute_plan(agent_state)
        elif status == "rejected":
            feedback = plan.get("feedback", "No feedback")
            self._notify(f"Plan rejected: {feedback}")
            # Clear plan and go idle — will re-assess on next tick
            agent_state["pending_plan"] = None
            agent_state["status"] = "idle"
            agent_state["last_assessment"] = None  # Force re-assessment
            self.state.save_agent(self.agent_key, agent_state)
        # else: still pending, wait

    def _handle_error_recovery(self, agent_state):
        """Recover from error state after a cooldown."""
        errors = agent_state.get("error_log", [])
        if errors:
            last_error_time = errors[0].get("at", "")
            try:
                error_dt = datetime.fromisoformat(last_error_time)
                if datetime.now() - error_dt < timedelta(minutes=30):
                    return  # Still in cooldown
            except (ValueError, TypeError):
                pass

        # Cooldown expired, go back to idle
        self.state.set_agent_status(self.agent_key, "idle")
        print(f"[{self.agent_key}] Recovered from error, back to idle")

    def _assessment_is_stale(self, agent_state):
        """Check if the last assessment is old enough to warrant a new one."""
        last = agent_state.get("last_assessment")
        if not last:
            return True
        try:
            last_dt = datetime.fromisoformat(last)
            return datetime.now() - last_dt > timedelta(hours=STALE_ASSESSMENT_HOURS)
        except (ValueError, TypeError):
            return True

    def _build_assessment_prompt(self, agent_state):
        """Build the system prompt for assessment, filled with live data."""
        snapshot = agent_state.get("site_snapshot", {})
        completed = agent_state.get("completed_tasks", [])[:5]
        mission = agent_state.get("mission", {})
        revenue_target = mission.get("revenue_target_monthly_usd", 1000)
        cooldowns = self.state.get_active_url_cooldowns(self.agent_key)[:20]

        # Load inventory summary if available
        inventory = self._load_inventory()
        if inventory:
            inv_summary = inventory.get("summary", {})
            inventory_text = json.dumps(inv_summary, indent=2, default=str)
        else:
            inventory_text = "No inventory yet. First step should be build_inventory."

        # Try to load strategic plan
        strategic_plan = "No strategic plan loaded."
        try:
            import os
            plan_candidates = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "agents", "seo_manager", "STRATEGIC_PLAN.md"),
            ]
            for path in plan_candidates:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        strategic_plan = f.read(2000)
                    break
        except Exception:
            pass

        tools_list = "\n".join(
            f"- {name}: {desc}"
            for name, desc in self.tools.list_tools().items()
        )

        return AGENT_SYSTEM_TEMPLATE.format(
            agent_name=self.config["name"],
            site_url=self.config["site_url"],
            niche=self.config["niche"],
            revenue_target=revenue_target,
            site_snapshot=json.dumps(snapshot, indent=2, default=str),
            inventory_summary=inventory_text,
            mission_state=json.dumps(mission, indent=2, default=str),
            task_history=json.dumps(completed, indent=2, default=str),
            url_cooldowns=json.dumps(cooldowns, indent=2, default=str),
            strategic_plan=strategic_plan[:2000],
            tools_list=tools_list,
        )

    def _analyze_step_result(self, tool_name, result):
        """Ask Claude to analyze a tool execution result. Uses Haiku (cheap, fast)."""
        from core.claude_client import MODEL_HAIKU

        output_text = result.get("output", "")[:1500]
        if result.get("data"):
            output_text += f"\n\nStructured data keys: {list(result['data'].keys())[:20]}"

        system = EXECUTION_SYSTEM.format(
            agent_name=self.config["name"],
            tool_name=tool_name,
            tool_output=output_text,
        )

        return self.claude.structured_chat(
            system,
            [{"role": "user", "content": "Analyze these results."}],
            max_tokens=400,
            model=MODEL_HAIKU,
        )

    def _extract_kpis(self, gsc_data=None, seo_data=None):
        """Normalize tool outputs into canonical KPI fields."""
        kpis = {}
        if gsc_data:
            summary = gsc_data.get("summary", {})
            page2 = gsc_data.get("page2_opportunities", [])
            kpis["organic_clicks_28d"] = summary.get("current_clicks")
            # Proxy for keywords near page 1 where we can win quickly.
            kpis["top20_keywords_count"] = len(page2)

        if seo_data:
            kpis["orphan_pages_count"] = len(seo_data.get("orphaned_posts", []))
        return kpis

    def _capture_post_execution_kpis(self, skip_tools=None):
        """Refresh KPI snapshot after execution and return the merged KPI map.

        Args:
            skip_tools: set of tool names already run during plan execution.
                        Those tools are skipped here to avoid redundant API calls.
        """
        skip = skip_tools or set()
        kpi_updates = {}

        if "gsc_audit" not in skip:
            gsc_result = self.tools.run_tool("gsc_audit")
            if gsc_result["success"] and gsc_result.get("data"):
                data = gsc_result["data"]
                summary = data.get("summary", {})
                snapshot = {
                    "total_clicks": summary.get("current_clicks"),
                    "prev_clicks": summary.get("prev_clicks"),
                    "clicks_change_pct": summary.get("change_pct"),
                    "declining_pages": len(data.get("drops", [])),
                    "page2_opportunities": len(data.get("page2_opportunities", [])),
                    "top_page2": data.get("page2_opportunities", [])[:5],
                }
                self.state.update_site_snapshot(self.agent_key, snapshot)
                kpi_updates.update(self._extract_kpis(gsc_data=data))

        if "seo_audit" not in skip:
            seo_result = self.tools.run_tool("seo_audit")
            if seo_result["success"] and seo_result.get("data"):
                seo_data = seo_result["data"]
                kpi_updates.update(self._extract_kpis(seo_data=seo_data))

        if kpi_updates:
            self.state.update_agent_kpis(self.agent_key, kpi_updates, source="post_execution_refresh")

        refreshed = self.state.get_agent(self.agent_key)
        return dict(refreshed.get("kpis", {}))

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    @staticmethod
    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return False

    @staticmethod
    def _url_age_years(url):
        """Infer age bucket from year token in URL slug, if present."""
        if not isinstance(url, str):
            return None
        matches = re.findall(r"(20\d{2})", url)
        if not matches:
            return None
        try:
            newest = max(int(m) for m in matches)
            return max(0, datetime.now().year - newest)
        except ValueError:
            return None

    def _infer_competition_from_state(self, target_urls, agent_state):
        """Estimate competition from snapshot page2 data when not explicitly provided."""
        snap = agent_state.get("site_snapshot", {})
        page2 = snap.get("top_page2", []) or []
        if not target_urls or not page2:
            return "medium"

        positions = []
        impressions = []
        for row in page2:
            url = row.get("url")
            if url in target_urls:
                pos = self._safe_float(row.get("position"))
                imp = self._safe_float(row.get("impressions"))
                if pos is not None:
                    positions.append(pos)
                if imp is not None:
                    impressions.append(imp)

        if not positions and not impressions:
            return "medium"

        avg_pos = sum(positions) / len(positions) if positions else 14.0
        avg_imp = sum(impressions) / len(impressions) if impressions else 150.0

        # Heuristic: high impressions or deeper page-2 often need longer settle window.
        if avg_imp > 300 or avg_pos > 16:
            return "high"
        if avg_imp < 90 and avg_pos <= 13:
            return "low"
        return "medium"

    def _determine_reassess_window_hours(self, plan, agent_state):
        """Hybrid approach: blend agent proposal with system-derived timing signals."""
        steps = plan.get("steps", []) or []
        tools = {str(s.get("tool", "")).strip().lower() for s in steps}
        target_urls = plan.get("target_urls", []) or []
        requested = self._safe_float(plan.get("reassess_after_hours"))
        content_type = str(plan.get("content_type", "")).strip().lower()
        competition = str(plan.get("competition_level", "")).strip().lower()
        scope = str(plan.get("change_scope", "")).strip().lower()
        critical = self._safe_bool(plan.get("critical_override"))

        # System base by likely action class, then adapt with contextual multipliers.
        if "affiliate_audit" in tools or content_type == "monetization":
            base_hours = 120.0
            base_reason = "monetization changes need longer signal"
        elif "orphan_rescue" in tools or content_type in ("internal_links",):
            base_hours = 36.0
            base_reason = "internal link changes need crawl + ranking settle"
        elif content_type in ("new_content",):
            base_hours = 96.0
            base_reason = "new content needs index/settle window"
        elif content_type in ("technical",):
            base_hours = 24.0
            base_reason = "technical fixes can be validated sooner"
        else:
            base_hours = 48.0
            base_reason = "balanced default for mixed SEO updates"

        # Competition factor: explicit from agent if present, otherwise infer from state.
        if competition not in ("low", "medium", "high"):
            competition = self._infer_competition_from_state(target_urls, agent_state)
        comp_mult = {"low": 0.85, "medium": 1.0, "high": 1.3}.get(competition, 1.0)

        # Scope factor from explicit value or step volume.
        if scope not in ("light", "medium", "heavy"):
            if len(steps) >= 5:
                scope = "heavy"
            elif len(steps) >= 3:
                scope = "medium"
            else:
                scope = "light"
        scope_mult = {"light": 0.85, "medium": 1.0, "heavy": 1.25}.get(scope, 1.0)

        # Age factor inferred from URL year token when present.
        ages = [self._url_age_years(u) for u in target_urls]
        ages = [a for a in ages if a is not None]
        avg_age = (sum(ages) / len(ages)) if ages else None
        if avg_age is None:
            age_mult = 1.0
            age_note = "age unknown"
        elif avg_age < 1:
            age_mult = 1.15
            age_note = "fresh content"
        elif avg_age > 3:
            age_mult = 0.9
            age_note = "older stable content"
        else:
            age_mult = 1.0
            age_note = "mid-age content"

        system_hours = base_hours * comp_mult * scope_mult * age_mult
        if critical:
            system_hours = min(system_hours, 24.0)

        # Partnership model: blend system estimate with agent proposal when provided.
        if requested is not None:
            requested = self._clamp(requested, 12.0, 336.0)
            final_hours = (0.6 * system_hours) + (0.4 * requested)
            blend_note = f"blended with agent proposal {requested:.0f}h"
        else:
            final_hours = system_hours
            blend_note = "system-derived (no agent proposal)"

        final_hours = int(round(self._clamp(final_hours, 12.0, 336.0)))
        reason = (
            f"{base_reason}; competition={competition}; scope={scope}; "
            f"{age_note}; {blend_note}"
        )
        return final_hours, reason

    # ── Write tool instruction files ────────────────────────────────────

    WRITE_TOOL_INSTRUCTION_MAP = {
        "update_post_meta": "pending_meta_update_{slug}.json",
        "inject_internal_links": "pending_link_inject_{slug}.json",
        "fix_affiliate_links": "pending_affiliate_fix_{slug}.json",
    }

    def _write_tool_instructions(self, tool_name, step):
        """Write instruction JSON files that write tools expect before execution."""
        import os
        filename_template = self.WRITE_TOOL_INSTRUCTION_MAP.get(tool_name)
        if not filename_template:
            return  # Not a write tool — nothing to write

        instructions = step.get("write_instructions")
        if not instructions:
            return  # Agent didn't provide instructions for this step

        slug = self.config.get("prefix", "").lower().replace("wp_", "").replace("_", "")
        filename = filename_template.replace("{slug}", slug)
        state_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")
        os.makedirs(state_dir, exist_ok=True)
        path = os.path.join(state_dir, filename)

        try:
            with open(path, "w") as f:
                json.dump(instructions, f, indent=2, default=str)
            print(f"[{self.agent_key}] Wrote instructions for {tool_name}: {filename}")
        except Exception as e:
            print(f"[{self.agent_key}] Failed to write instructions for {tool_name}: {e}")

    def _notify(self, message):
        """Send a notification via the agent's Telegram bot."""
        full_msg = f"*{self.config['name']}*\n{message}"
        try:
            self.telegram_fn(full_msg)
        except Exception as e:
            print(f"[{self.agent_key}] Telegram notify failed: {e}")
