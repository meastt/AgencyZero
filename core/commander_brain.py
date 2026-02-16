"""
Intelligent Commander Brain — replaces the stateless intent classifier.
Maintains conversation context, reads live agent state, auto-reviews plans.
"""

import json
from datetime import datetime, timedelta

WEEKLY_STRATEGY_DAYS = 7

COMMANDER_SYSTEM = """You are Commander SEO, the autonomous agency director for AgencyZero.
You manage 3 autonomous agents that each run a WordPress niche site:

- Griddle King (griddleking.com) — outdoor cooking, griddles, BBQ
- Photo Tips Guy (phototipsguy.com) — photography, astrophotography, telescopes
- Tiger Tribe (tigertribe.net) — wild cats, predatory wildlife, conservation

CRITICAL OPERATING MODE:
You are FULLY AUTONOMOUS. The owner does NOT want to be asked for approval or input.
- NEVER ask the user to approve plans. YOU approve them.
- NEVER ask "what should I do?" or "your orders?" — YOU decide and act.
- NEVER present options for the user to choose from. Make the call yourself.
- Only message the user when they ask you something OR when there is a genuine problem
  that requires human intervention (missing credentials, broken integrations, budget decisions).
- When the user asks for status, give a concise data-driven report. No questions attached.

CORE OBJECTIVES (always optimize for both):
1) Get each site to at least $1,000/month revenue.
2) Maintain trustworthy state visibility for both manager-level and agent-level timelines.

RULES:
1. NEVER dump static files or canned status text. Always reference ACTUAL live data.
2. You have conversation history — reference prior messages naturally.
3. When the user says "execute", "go", "start" — trigger agent assessment cycles.
4. When asked about status, read the LIVE AGENT STATES provided, not static docs.
5. Keep replies concise, authoritative, and data-driven.
6. You can take actions by including an "actions" array in your response.
7. NEVER claim a task executed/completed unless explicitly present in LIVE AGENT STATES.
8. If data is unknown, say unknown. Do not infer step counts, timeline, or interval values.

Available actions:
- {"action": "trigger_agent", "agent": "griddle|photo|tiger|all"} — start agent assessment
- {"action": "approve_plan", "agent": "griddle|photo|tiger"} — approve pending plan
- {"action": "reject_plan", "agent": "griddle|photo|tiger", "reason": "..."} — reject with feedback
- {"action": "set_interval", "minutes": 30} — change agent tick interval
- {"action": "resolve_escalation", "agent": "griddle|photo|tiger", "resolution": "..."} — resolve an open escalation

Respond as JSON:
{
  "reply": "Your message to the user (plain text, Telegram-friendly)",
  "actions": []
}

If there are no actions to take, return an empty actions array.
Reply with JSON only."""


REVIEW_SYSTEM = """You are Commander SEO autonomously reviewing agent plans.
You are FULLY AUTONOMOUS. Approve plans quickly to keep agents moving.

Approve if:
- The plan uses available tools correctly
- The priority order is reasonable (revenue leaks > declining pages > Page 2 pushes > orphans > new content)
- The plan is actionable (not vague)

Only reject if:
- The plan would cause damage (deleting content, breaking links)
- The agent is using wrong site data (cross-contamination)
- The plan is completely nonsensical

Default to APPROVE. Speed matters more than perfection.

Respond as JSON:
{
  "decision": "approve" or "reject",
  "reasoning": "1-2 sentences explaining your decision",
  "feedback": "Specific feedback for the agent (if rejecting, what to change)"
}

Reply with JSON only."""


class CommanderBrain:
    """Intelligent Commander that replaces the dumb intent classifier."""

    def __init__(self, state_store, claude_client, agent_keys, trigger_fn=None, set_interval_fn=None):
        """
        Args:
            state_store: StateStore instance for persistent state.
            claude_client: ClaudeClient instance.
            agent_keys: List of agent keys (e.g., ["griddle", "photo", "tiger"]).
            trigger_fn: Callable(agent_key) to force an immediate agent tick.
            set_interval_fn: Callable(agent_key, minutes) to change tick interval.
        """
        self.state = state_store
        self.claude = claude_client
        self.agent_keys = agent_keys
        self.trigger_fn = trigger_fn
        self.set_interval_fn = set_interval_fn

    def handle_message(self, text):
        """Process a user message and return an intelligent response.

        Returns:
            str: Reply text for the user.
            list: Actions to execute.
        """
        # Save incoming message to conversation buffer
        self.state.add_conversation("user", text)

        factual_reply = self.get_factual_reply_if_applicable(text)
        if factual_reply is not None:
            self.state.add_conversation("commander", factual_reply)
            return factual_reply, []

        # Build context for Claude
        commander_state = self.state.get_commander()
        agent_states = self.state.get_all_agent_states(self.agent_keys)

        context = self._build_context(commander_state, agent_states)
        messages = self._build_messages(commander_state, text)

        try:
            result = self.claude.structured_chat(
                COMMANDER_SYSTEM,
                messages,
                max_tokens=800,
            )
        except Exception as e:
            reply = f"Brain error: {str(e)[:200]}. Try a slash command."
            self.state.add_conversation("commander", reply)
            return reply, []

        reply = result.get("reply", "Acknowledged.")
        actions = result.get("actions", [])

        # Save reply to conversation buffer
        self.state.add_conversation("commander", reply)

        # Execute actions
        executed = self._execute_actions(actions)

        return reply, executed

    def get_factual_reply_if_applicable(self, text):
        """Return deterministic report for factual/status queries, else None."""
        normalized = (text or "").lower()
        if any(k in normalized for k in ("/status", "fleet status", "live status")):
            return self.get_live_status()
        if any(k in normalized for k in ("/portfolio", "portfolio")):
            return self.get_portfolio_status()
        if any(
            k in normalized for k in (
                "/mission",
                "mission overview",
                "current mission",
                "current state",
                "what have we been doing",
                "what are we doing",
                "what happened",
            )
        ):
            return self.get_mission_overview()
        return None

    def review_cycle(self):
        """Autonomous plan review — runs on a timer.

        Returns:
            list[dict]: Review results with agent_key, decision, feedback.
        """
        commander_state = self.state.get_commander()
        reviews = commander_state.get("pending_reviews", [])
        results = []

        for review in reviews:
            agent_key = review.get("agent_key")
            plan = review.get("plan", {})

            # Get agent context
            agent_state = self.state.get_agent(agent_key)

            review_prompt = (
                f"Agent: {agent_key}\n"
                f"Site snapshot: {json.dumps(agent_state.get('site_snapshot', {}), default=str)}\n"
                f"Recent completed tasks: {json.dumps(agent_state.get('completed_tasks', [])[:5], default=str)}\n"
                f"Proposed plan:\n{json.dumps(plan, default=str)}"
            )

            try:
                from core.claude_client import MODEL_HAIKU
                decision = self.claude.structured_chat(
                    REVIEW_SYSTEM,
                    [{"role": "user", "content": review_prompt}],
                    max_tokens=400,
                    model=MODEL_HAIKU,
                )
            except Exception as e:
                # DO NOT auto-approve on error — escalate instead
                self.state.add_escalation(
                    agent_key,
                    f"Plan review failed (Claude error: {str(e)[:200]}). Manual approval needed."
                )
                results.append({
                    "agent_key": agent_key,
                    "decision": "escalated",
                    "feedback": f"Review error: {str(e)[:200]}",
                })
                continue  # Skip to next review

            if decision.get("decision") == "approve":
                self.state.approve_plan(agent_key, decision.get("feedback", ""))
                # Kick the agent immediately so approval leads to execution now.
                self._trigger(agent_key)
            else:
                self.state.reject_plan(agent_key, decision.get("feedback", ""))

            results.append({
                "agent_key": agent_key,
                "decision": decision.get("decision"),
                "feedback": decision.get("feedback", ""),
            })

        # Update review timestamp
        commander_state = self.state.get_commander()
        commander_state["last_review_cycle"] = datetime.now().isoformat()
        self.state.save_commander(commander_state)
        self._run_portfolio_strategy_if_due()

        return results

    def get_live_status(self):
        """Build a status report from actual agent state files."""
        agent_states = self.state.get_all_agent_states(self.agent_keys)
        agent_meta = {
            "griddle": ("Griddle King", "griddleking.com"),
            "photo": ("Photo Tips Guy", "phototipsguy.com"),
            "tiger": ("Tiger Tribe", "tigertribe.net"),
        }

        lines = ["*AGENCYZERO FLEET — LIVE STATUS*\n"]

        for key in self.agent_keys:
            st = agent_states.get(key, {})
            name, site = agent_meta.get(key, (key, ""))
            status = st.get("status", "unknown")
            task = st.get("current_task")
            snap = st.get("site_snapshot", {})
            last_tick = st.get("last_tick", "never")
            errors = st.get("error_log", [])
            completed = st.get("completed_tasks", [])
            plan = st.get("pending_plan")
            mission = st.get("mission", {})
            timeline = st.get("timeline", [])

            status_emoji = {
                "idle": "🟢",
                "assessing": "🔍",
                "planning": "📋",
                "awaiting_approval": "⏳",
                "executing": "⚡",
                "reporting": "📊",
                "error": "🔴",
            }.get(status, "⚪")

            line = f"{status_emoji} *{name}* ({site})\n"
            line += f"  Status: {status}"
            if task:
                line += f" — {task}"
            line += "\n"

            if snap:
                clicks = snap.get("total_clicks")
                if clicks is not None:
                    line += f"  Clicks: {clicks} | "
                orphans = snap.get("orphan_count")
                if orphans is not None:
                    line += f"Orphans: {orphans} | "
                declining = snap.get("declining_pages")
                if declining is not None:
                    line += f"Declining: {declining}"
                line += "\n"

            if plan and plan.get("status") == "pending_review":
                line += f"  Plan pending review (submitted {plan.get('submitted_at', '?')})\n"

            if completed:
                last = completed[0]
                line += f"  Last task: {last.get('summary', '?')[:60]} ({last.get('completed_at', '?')[:16]})\n"

            progress = mission.get("last_progress_note")
            if progress:
                line += f"  Mission progress: {progress[:70]}\n"

            if timeline:
                last_event = timeline[0]
                line += f"  Timeline: {last_event.get('type', '?')} @ {last_event.get('at', '?')[:16]}\n"

            if errors:
                line += f"  Last error: {errors[0].get('error', '?')[:60]}\n"

            line += f"  Last tick: {last_tick[:16] if last_tick != 'never' else 'never'}\n"
            lines.append(line)

        # Pending reviews
        cmd = self.state.get_commander()
        pending = cmd.get("pending_reviews", [])
        if pending:
            lines.append(f"\n*Pending Reviews:* {len(pending)}")
            for r in pending:
                lines.append(f"  - {r.get('agent_key')}: plan submitted {r.get('submitted_at', '?')[:16]}")

        escalations = [e for e in cmd.get("escalations", []) if not e.get("resolved")]
        if escalations:
            lines.append(f"\n*Open Escalations:* {len(escalations)}")
            for e in escalations:
                lines.append(f"  - {e.get('agent_key')}: {e.get('issue', '?')[:60]}")

        strategy = cmd.get("portfolio_strategy", {})
        allocations = strategy.get("allocations", [])
        if allocations:
            lines.append("\n*Portfolio Allocation (weekly):*")
            for item in allocations:
                lines.append(
                    f"  - {item.get('agent_key')}: {item.get('allocation_pct')}% "
                    f"(score={item.get('priority_score')}, reason={item.get('reason')[:45]})"
                )

        lines.append(f"\n_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
        return "\n".join(lines)

    def get_mission_overview(self):
        """Deterministic mission overview from state, no model interpretation."""
        agent_states = self.state.get_all_agent_states(self.agent_keys)
        labels = {
            "griddle": ("Griddle King", "griddleking.com"),
            "photo": ("Photo Tips Guy", "phototipsguy.com"),
            "tiger": ("Tiger Tribe", "tigertribe.net"),
        }
        lines = [f"*MISSION OVERVIEW — {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"]
        for key in self.agent_keys:
            st = agent_states.get(key, {})
            name, site = labels.get(key, (key, ""))
            snapshot = st.get("site_snapshot", {})
            status = st.get("status", "unknown")
            task = st.get("current_task") or "None"
            completed = st.get("completed_tasks", [])
            last_summary = completed[0].get("summary", "No completed tasks yet") if completed else "No completed tasks yet"
            plan = st.get("pending_plan")
            plan_state = plan.get("status") if plan else "none"

            lines.append(f"*{name}* ({site})")
            lines.append(f"  Status: {status}")
            lines.append(f"  Current task: {task}")
            if snapshot:
                clicks = snapshot.get("total_clicks")
                declines = snapshot.get("declining_pages")
                page2 = snapshot.get("page2_opportunities")
                lines.append(f"  Metrics: clicks={clicks}, declining={declines}, page2={page2}")
            else:
                lines.append("  Metrics: none")
            lines.append(f"  Pending plan: {plan_state}")
            lines.append(f"  Last completed: {last_summary[:80]}")
            lines.append("")

        cmd = self.state.get_commander()
        pending_reviews = len(cmd.get("pending_reviews", []))
        unresolved = len([e for e in cmd.get("escalations", []) if not e.get("resolved")])
        lines.append(f"*Commander Queue:* pending_reviews={pending_reviews}, open_escalations={unresolved}")
        return "\n".join(lines)

    def get_portfolio_status(self):
        """Build an executive portfolio report with allocation + KPI deltas."""
        cmd = self.state.get_commander()
        strategy = cmd.get("portfolio_strategy", {})
        allocations = strategy.get("allocations", [])

        # Ensure we always have an allocation plan available for this view.
        if not allocations:
            agent_states = self.state.get_all_agent_states(self.agent_keys)
            allocations = self._build_weekly_allocations(agent_states)
            strategy["last_generated_at"] = datetime.now().isoformat()
            strategy["cadence_days"] = int(strategy.get("cadence_days") or WEEKLY_STRATEGY_DAYS)
            strategy["allocations"] = allocations
            strategy["notes"] = "On-demand portfolio strategy generated via /portfolio."
            cmd["portfolio_strategy"] = strategy
            self.state.save_commander(cmd)

        alloc_by_agent = {a.get("agent_key"): a for a in allocations}
        agent_states = self.state.get_all_agent_states(self.agent_keys)
        labels = {
            "griddle": "Griddle King",
            "photo": "Photo Tips Guy",
            "tiger": "Tiger Tribe",
        }

        def _fmt_num(value, digits=1):
            if value is None:
                return "n/a"
            try:
                num = float(value)
            except (TypeError, ValueError):
                return "n/a"
            if digits == 0:
                return str(int(round(num)))
            return f"{num:.{digits}f}"

        lines = ["*AGENCYZERO PORTFOLIO — EXECUTIVE VIEW*\n"]
        lines.append(f"Strategy note: {strategy.get('notes', 'n/a')}")
        lines.append("")

        for agent_key in self.agent_keys:
            st = agent_states.get(agent_key, {})
            alloc = alloc_by_agent.get(agent_key, {})
            kpis = st.get("kpis", {})
            history = st.get("execution_history", [])
            latest = history[0] if history else {}
            deltas = latest.get("deltas", {})
            recent_urls = st.get("recent_url_actions", [])

            clicks_delta = deltas.get("organic_clicks_28d", {}).get("absolute")
            revenue_delta = deltas.get("monthly_revenue_usd", {}).get("absolute")
            orphan_delta = deltas.get("orphan_pages_count", {}).get("absolute")

            lines.append(
                f"*{labels.get(agent_key, agent_key)}* "
                f"— allocation {alloc.get('allocation_pct', 0)}% "
                f"(score {alloc.get('priority_score', 'n/a')})"
            )
            lines.append(
                f"  KPI: clicks={_fmt_num(kpis.get('organic_clicks_28d'), 0)}, "
                f"top20={_fmt_num(kpis.get('top20_keywords_count'), 0)}, "
                f"orphans={_fmt_num(kpis.get('orphan_pages_count'), 0)}, "
                f"rev/mo=${_fmt_num(kpis.get('monthly_revenue_usd'), 0)}"
            )
            if latest:
                lines.append(
                    f"  Last outcome: clicks Δ={_fmt_num(clicks_delta, 0)}, "
                    f"revenue Δ=${_fmt_num(revenue_delta, 0)}, "
                    f"orphans Δ={_fmt_num(orphan_delta, 0)}, "
                    f"confidence={latest.get('confidence', 'n/a')}"
                )
            else:
                lines.append("  Last outcome: n/a (no execution outcome yet)")

            if recent_urls:
                cooldown_item = recent_urls[0]
                action_txt = str(cooldown_item.get("action", "n/a"))
                if "| cooldown=" in action_txt:
                    _, cooldown_details = action_txt.split("| cooldown=", 1)
                    lines.append(f"  Cooldown logic: {cooldown_details[:120]}")
                else:
                    lines.append(f"  Cooldown logic: {action_txt[:120]}")
                lines.append(
                    f"  Next reassess not before: {str(cooldown_item.get('review_not_before', 'n/a'))[:16]}"
                )
            else:
                lines.append("  Cooldown logic: n/a (no URL-level actions recorded)")
            lines.append(f"  Why: {alloc.get('reason', 'n/a')}")
            lines.append("")

        generated = strategy.get("last_generated_at", "")
        generated_txt = generated[:16] if generated else "n/a"
        lines.append(f"_Portfolio generated {generated_txt}_")
        return "\n".join(lines)

    def _build_context(self, commander_state, agent_states):
        """Build context string with live agent data."""
        parts = []
        for key, st in agent_states.items():
            mission = st.get("mission", {})
            timeline = st.get("timeline", [])
            latest_event = timeline[0] if timeline else {}
            parts.append(
                f"Agent {key}: status={st.get('status')}, "
                f"task={st.get('current_task')}, "
                f"target=${mission.get('revenue_target_monthly_usd', 1000)}/mo, "
                f"progress={str(mission.get('last_progress_note', 'none'))[:80]}, "
                f"timeline={latest_event.get('type', 'none')}, "
                f"snapshot={json.dumps(st.get('site_snapshot', {}), default=str)[:200]}, "
                f"last_tick={st.get('last_tick', 'never')}"
            )
        return "\n".join(parts)

    def _build_messages(self, commander_state, current_text):
        """Build message list with conversation history for Claude."""
        messages = []

        # Add conversation history
        buffer = commander_state.get("conversation_buffer", [])
        for msg in buffer[-18:]:  # Leave room for current + context
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["text"]})

        # Fix: ensure messages alternate roles (Claude requirement)
        messages = self._fix_alternation(messages)

        # Build context-enriched current message
        agent_states = self.state.get_all_agent_states(self.agent_keys)
        context = self._build_context(
            commander_state, agent_states
        )

        pending = commander_state.get("pending_reviews", [])
        pending_text = ""
        if pending:
            pending_text = f"\nPending plans for review: {json.dumps(pending, default=str)[:500]}"
        strategy = commander_state.get("portfolio_strategy", {})
        strategy_text = ""
        if strategy.get("allocations"):
            strategy_text = (
                "\nPortfolio strategy: "
                f"{json.dumps(strategy.get('allocations', []), default=str)[:500]}"
            )

        enriched = (
            f"LIVE AGENT STATES:\n{context}\n"
            f"{pending_text}{strategy_text}\n\n"
            f"USER MESSAGE: {current_text}"
        )

        messages.append({"role": "user", "content": enriched})
        return messages

    @staticmethod
    def _fix_alternation(messages):
        """Ensure messages alternate user/assistant roles for the API."""
        if not messages:
            return messages
        fixed = [messages[0]]
        for msg in messages[1:]:
            if msg["role"] == fixed[-1]["role"]:
                # Merge same-role messages
                fixed[-1]["content"] += "\n" + msg["content"]
            else:
                fixed.append(msg)
        # Must start with user
        if fixed and fixed[0]["role"] != "user":
            fixed = fixed[1:]
        return fixed

    def _execute_actions(self, actions):
        """Execute actions returned by Claude."""
        executed = []
        for act in actions:
            action_type = act.get("action")

            if action_type == "trigger_agent":
                target = act.get("agent", "all")
                if target == "all":
                    for key in self.agent_keys:
                        self._trigger(key, force_reassess=True)
                    executed.append({"action": "trigger_agent", "agents": list(self.agent_keys)})
                    self.state.log_commander_timeline(
                        "trigger_agent",
                        "Triggered all agents immediately.",
                        {"agents": list(self.agent_keys)},
                    )
                elif target in self.agent_keys:
                    self._trigger(target, force_reassess=True)
                    executed.append({"action": "trigger_agent", "agents": [target]})
                    self.state.log_commander_timeline(
                        "trigger_agent",
                        f"Triggered {target} immediately.",
                        {"agent": target},
                    )

            elif action_type == "approve_plan":
                agent = act.get("agent")
                if agent in self.agent_keys:
                    self.state.approve_plan(agent, act.get("feedback", ""))
                    # Don't wait for the next interval tick.
                    self._trigger(agent)
                    executed.append({"action": "approve_plan", "agent": agent})

            elif action_type == "reject_plan":
                agent = act.get("agent")
                if agent in self.agent_keys:
                    self.state.reject_plan(agent, act.get("reason", ""))
                    executed.append({"action": "reject_plan", "agent": agent})

            elif action_type == "set_interval":
                try:
                    minutes = int(act.get("minutes", 0) or 0)
                except (TypeError, ValueError):
                    continue
                if minutes <= 0:
                    continue

                target = act.get("agent", "all")
                if target == "all":
                    for agent in self.agent_keys:
                        if self.set_interval_fn:
                            self.set_interval_fn(agent, minutes)
                    executed.append({"action": "set_interval", "agent": "all", "minutes": minutes})
                    self.state.log_commander_timeline(
                        "set_interval",
                        f"Set all agent intervals to {minutes} minutes.",
                        {"minutes": minutes},
                    )
                elif target in self.agent_keys:
                    if self.set_interval_fn:
                        self.set_interval_fn(target, minutes)
                    executed.append({"action": "set_interval", "agent": target, "minutes": minutes})
                    self.state.log_commander_timeline(
                        "set_interval",
                        f"Set {target} interval to {minutes} minutes.",
                        {"agent": target, "minutes": minutes},
                    )

            elif action_type == "resolve_escalation":
                agent = act.get("agent")
                resolution = act.get("resolution", "Resolved by Commander")
                if agent:
                    self.state.resolve_escalation(agent, resolution)
                    executed.append({"action": "resolve_escalation", "agent": agent})
                    self.state.log_commander_timeline(
                        "escalation_resolved",
                        f"Resolved escalation for {agent}: {resolution[:200]}",
                        {"agent_key": agent},
                    )

        return executed

    def _trigger(self, agent_key, force_reassess=False):
        """Trigger an immediate agent tick."""
        if force_reassess:
            self.state.request_reassess(agent_key, reason="commander trigger_agent")
        if self.trigger_fn:
            self.trigger_fn(agent_key)
        else:
            # Fallback: just set status so next tick will assess
            self.state.set_agent_status(agent_key, "idle")

    @staticmethod
    def _safe_num(value, default=0.0):
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _priority_score(self, agent_key, state):
        """Score a site for weekly effort allocation."""
        kpis = state.get("kpis", {})
        snapshot = state.get("site_snapshot", {})
        mission = state.get("mission", {})
        target = self._safe_num(mission.get("revenue_target_monthly_usd"), 1000.0)
        revenue = self._safe_num(kpis.get("monthly_revenue_usd"), 0.0)
        revenue_gap = max(target - revenue, 0.0)
        revenue_gap_ratio = min(revenue_gap / target, 1.0) if target > 0 else 0.0

        decline_count = self._safe_num(snapshot.get("declining_pages"), 0.0)
        orphan_count = self._safe_num(kpis.get("orphan_pages_count"), 0.0)
        click_delta_pct = self._safe_num(snapshot.get("clicks_change_pct"), 0.0)
        negative_trend = abs(min(click_delta_pct, 0.0))
        errors = len(state.get("error_log", []))

        # Weighted portfolio formula: higher is higher priority.
        score = (
            (revenue_gap_ratio * 45.0) +
            (min(decline_count, 20.0) * 2.0) +
            (min(orphan_count, 100.0) * 0.2) +
            (negative_trend * 0.8) +
            (errors * 3.0)
        )

        if score < 1.0:
            score = 1.0

        reason = (
            f"gap=${int(revenue_gap)}/mo, declines={int(decline_count)}, "
            f"orphans={int(orphan_count)}, trend={click_delta_pct:.1f}%"
        )
        return round(score, 2), reason

    def _build_weekly_allocations(self, agent_states):
        scored = []
        total = 0.0
        for agent_key in self.agent_keys:
            st = agent_states.get(agent_key, {})
            score, reason = self._priority_score(agent_key, st)
            scored.append({"agent_key": agent_key, "priority_score": score, "reason": reason})
            total += score

        allocations = []
        running_pct = 0
        for idx, item in enumerate(sorted(scored, key=lambda x: x["priority_score"], reverse=True)):
            if idx == len(scored) - 1:
                pct = max(0, 100 - running_pct)
            else:
                pct = int(round((item["priority_score"] / total) * 100)) if total else 0
                running_pct += pct
            allocations.append({
                "agent_key": item["agent_key"],
                "priority_score": item["priority_score"],
                "allocation_pct": pct,
                "reason": item["reason"],
            })
        return allocations

    def _run_portfolio_strategy_if_due(self):
        """Generate weekly portfolio strategy and effort allocation."""
        cmd = self.state.get_commander()
        strategy = cmd.get("portfolio_strategy", {})
        cadence_days = int(strategy.get("cadence_days") or WEEKLY_STRATEGY_DAYS)
        last_at = strategy.get("last_generated_at")

        due = True
        if last_at:
            try:
                due = datetime.now() - datetime.fromisoformat(last_at) >= timedelta(days=cadence_days)
            except (TypeError, ValueError):
                due = True

        if not due:
            return

        agent_states = self.state.get_all_agent_states(self.agent_keys)
        allocations = self._build_weekly_allocations(agent_states)
        top = allocations[0] if allocations else {}
        notes = (
            f"Top priority: {top.get('agent_key', 'n/a')} at {top.get('allocation_pct', 0)}% "
            f"based on revenue gap, declines, orphan load, and trend."
        )

        strategy["last_generated_at"] = datetime.now().isoformat()
        strategy["cadence_days"] = cadence_days
        strategy["allocations"] = allocations
        strategy["notes"] = notes
        cmd["portfolio_strategy"] = strategy
        self.state.save_commander(cmd)
        self.state.log_commander_timeline(
            "portfolio_strategy",
            "Generated weekly portfolio allocation strategy.",
            {"allocations": allocations},
        )

    # ── Periodic Monitoring Report ──────────────────────────────────────

    def generate_periodic_report(self):
        """Build a 4-hour summary report. Pure data aggregation, no Claude call.

        Returns:
            str: Formatted report ready to send via Telegram.
        """
        window = self.state.flush_activity_window()
        spend = self.claude.flush_spend() if self.claude else {}

        window_start = window.get("window_start", "unknown")
        if window_start and window_start != "unknown":
            window_start = window_start[:16]
        now_str = datetime.now().strftime("%H:%M")

        writes = window.get("writes", [])
        failures = window.get("failures", [])
        cycles = window.get("cycles", 0)

        # Tally writes per agent
        agent_labels = {
            "griddle": "Griddle King",
            "photo": "Photo Tips Guy",
            "tiger": "Tiger Tribe",
        }
        agent_write_counts = {}
        for w in writes:
            key = w.get("agent_key", "unknown")
            tool = w.get("tool", "unknown")
            label = agent_labels.get(key, key)
            agent_write_counts.setdefault(label, {})
            agent_write_counts[label][tool] = agent_write_counts[label].get(tool, 0) + 1

        # Format report
        lines = [f"AGENCYZERO 4H REPORT ({window_start} - {now_str})\n"]

        # Changes
        lines.append("CHANGES MADE:")
        if agent_write_counts:
            for agent_name, tools in agent_write_counts.items():
                parts = [f"{count} {tool.replace('_', ' ')}" for tool, count in tools.items()]
                lines.append(f"  {agent_name}: {', '.join(parts)}")
        else:
            lines.append("  None — no WordPress writes this window")

        # Failures
        if failures:
            lines.append("\nFAILURES:")
            seen = set()
            for f in failures[:10]:
                key = (f.get("agent_key", ""), f.get("tool", ""))
                if key not in seen:
                    seen.add(key)
                    label = agent_labels.get(f.get("agent_key", ""), f.get("agent_key", ""))
                    lines.append(f"  {label}: {f.get('tool', '?')} — {f.get('error', '?')[:80]}")

        # Cycles and cost
        cost_window = spend.get("estimated_cost_usd", 0.0)
        api_calls = spend.get("api_calls", 0)
        lines.append(f"\nCYCLES: {cycles} total")
        lines.append(f"API CALLS: {api_calls}")
        lines.append(f"TOKEN SPEND: ~${cost_window:.2f} this window")

        # New escalations
        cmd = self.state.get_commander()
        new_esc = [
            e for e in cmd.get("escalations", [])
            if not e.get("resolved") and e.get("at", "") > (window.get("window_start") or "")
        ]
        lines.append(f"ESCALATIONS: {len(new_esc)} new")

        # Stall detection
        if not writes and cycles > 5:
            lines.append(
                "\nWARNING: No WordPress writes in the last 4 hours.\n"
                "Agents are cycling but producing read-only plans.\n"
                "Check /status for details."
            )
        elif not writes and cycles == 0:
            lines.append("\nNOTE: No agent activity this window.")

        return "\n".join(lines)
