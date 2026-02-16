"""
Persistent JSON state management for agents and Commander.
Atomic writes via tempfile + rename to prevent corruption on crash.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta

TIMELINE_LIMIT = 200
EXECUTION_HISTORY_LIMIT = 100


def _now():
    return datetime.now().isoformat()


def _merge_missing(existing, defaults):
    """Recursively fill missing keys from defaults. Returns True if changed."""
    changed = False
    for key, value in defaults.items():
        if key not in existing:
            existing[key] = value
            changed = True
        elif isinstance(existing.get(key), dict) and isinstance(value, dict):
            if _merge_missing(existing[key], value):
                changed = True
    return changed


def _default_agent_state(agent_key):
    """Seed state for a new agent."""
    return {
        "agent_key": agent_key,
        "status": "idle",
        "current_task": None,
        "pending_plan": None,
        "completed_tasks": [],
        "site_snapshot": {},
        "error_log": [],
        "last_assessment": None,
        "last_tick": None,
        "force_reassess": False,
        "force_reassess_reason": None,
        "mission": {
            "objective": "Grow this niche site to $1k/month revenue while improving SEO health.",
            "revenue_target_monthly_usd": 1000,
            "focus": "Revenue leaks, rankings growth, and content quality execution.",
            "last_progress_note": None,
            "last_progress_at": None,
        },
        "kpis": {
            "organic_clicks_28d": None,
            "top20_keywords_count": None,
            "affiliate_ctr_pct": None,
            "revenue_per_session_usd": None,
            "monthly_revenue_usd": None,
            "orphan_pages_count": None,
            "last_updated": None,
            "source": None,
        },
        "execution_history": [],
        "recent_url_actions": [],
        "timeline": [],
    }


def _default_commander_state():
    """Seed state for Commander."""
    return {
        "conversation_buffer": [],
        "agent_states_cache": {},
        "pending_reviews": [],
        "escalations": [],
        "last_review_cycle": None,
        "mission": {
            "objective": "Direct autonomous SEO operations to get each site to $1k/month.",
            "revenue_target_per_site_monthly_usd": 1000,
            "operating_mode": "autonomous",
            "human_update_policy": "Only escalate blockers/major updates.",
        },
        "portfolio_strategy": {
            "last_generated_at": None,
            "cadence_days": 7,
            "allocations": [],
            "notes": "",
        },
        "activity_window": {
            "window_start": None,
            "writes": [],
            "failures": [],
            "cycles": 0,
        },
        "timeline": [],
    }


class StateStore:
    """Manages persistent JSON state files for agents and Commander."""

    def __init__(self, state_dir):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

    def _path(self, name):
        return os.path.join(self.state_dir, f"{name}.json")

    def _read(self, name):
        path = self._path(name)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

    def _write(self, name, data):
        """Atomic write: write to tempfile then rename."""
        path = self._path(name)
        fd, tmp = tempfile.mkstemp(dir=self.state_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # ── Agent State ──────────────────────────────────────────────────────

    def get_agent(self, agent_key):
        """Load agent state, creating default if missing."""
        data = self._read(f"agent_{agent_key}")
        if data is None:
            data = _default_agent_state(agent_key)
            self._write(f"agent_{agent_key}", data)
        else:
            changed = _merge_missing(data, _default_agent_state(agent_key))
            if changed:
                self._write(f"agent_{agent_key}", data)
        return data

    def save_agent(self, agent_key, state):
        """Persist agent state."""
        state["last_updated"] = _now()
        self._write(f"agent_{agent_key}", state)

    def _timeline_event(self, event_type, message, metadata=None):
        event = {
            "at": _now(),
            "type": event_type,
            "message": str(message)[:1000],
        }
        if metadata:
            event["metadata"] = metadata
        return event

    @staticmethod
    def _append_timeline(state, event, limit=TIMELINE_LIMIT):
        timeline = state.get("timeline", [])
        timeline.insert(0, event)
        state["timeline"] = timeline[:limit]

    def log_agent_timeline(self, agent_key, event_type, message, metadata=None):
        """Append an event to an agent timeline."""
        state = self.get_agent(agent_key)
        event = self._timeline_event(event_type, message, metadata)
        self._append_timeline(state, event)
        self.save_agent(agent_key, state)

    @staticmethod
    def _coerce_number(value):
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _calc_delta(before, after):
        if before is None or after is None:
            return {"absolute": None, "pct": None}
        absolute = after - before
        pct = None
        if before != 0:
            pct = (absolute / abs(before)) * 100.0
        return {"absolute": absolute, "pct": pct}

    def log_commander_timeline(self, event_type, message, metadata=None):
        """Append an event to the commander's timeline."""
        state = self.get_commander()
        event = self._timeline_event(event_type, message, metadata)
        self._append_timeline(state, event)
        self.save_commander(state)

    def set_agent_status(self, agent_key, status, task=None):
        """Update agent status and optional current task."""
        state = self.get_agent(agent_key)
        prev_status = state.get("status")
        prev_task = state.get("current_task")
        state["status"] = status
        if task is not None:
            state["current_task"] = task
        elif status == "idle":
            # Idle should never carry stale execution task text.
            state["current_task"] = None
        state["last_tick"] = _now()
        if prev_status != status or (task is not None and prev_task != task):
            self._append_timeline(
                state,
                self._timeline_event(
                    "status_change",
                    f"Status changed {prev_status} -> {status}",
                    {"task": state.get("current_task")},
                ),
            )
        self.save_agent(agent_key, state)

    def request_reassess(self, agent_key, reason="manual trigger"):
        """Request a forced reassessment on the next idle tick."""
        state = self.get_agent(agent_key)
        state["force_reassess"] = True
        state["force_reassess_reason"] = (reason or "manual trigger")[:200]
        self._append_timeline(
            state,
            self._timeline_event(
                "reassess_requested",
                f"Forced reassessment requested: {state['force_reassess_reason']}",
            ),
        )
        self.save_agent(agent_key, state)

    def consume_reassess_request(self, agent_key):
        """Atomically consume pending reassess request; returns (bool, reason)."""
        state = self.get_agent(agent_key)
        if not state.get("force_reassess"):
            return False, None
        reason = state.get("force_reassess_reason", "manual trigger")
        state["force_reassess"] = False
        state["force_reassess_reason"] = None
        self.save_agent(agent_key, state)
        return True, reason

    def submit_plan(self, agent_key, plan):
        """Agent submits a plan for Commander review."""
        state = self.get_agent(agent_key)
        state["pending_plan"] = {
            "submitted_at": _now(),
            "plan": plan,
            "status": "pending_review",
        }
        state["status"] = "awaiting_approval"
        plan_name = plan.get("plan", {}).get("name", "Unnamed plan")
        self._append_timeline(
            state,
            self._timeline_event(
                "plan_submitted",
                f"Submitted plan for review: {plan_name}",
                {"plan_name": plan_name},
            ),
        )
        self.save_agent(agent_key, state)

        # Also add to commander's pending reviews
        cmd = self.get_commander()
        cmd["pending_reviews"].append({
            "agent_key": agent_key,
            "submitted_at": _now(),
            "plan": plan,
        })
        self._append_timeline(
            cmd,
            self._timeline_event(
                "plan_pending_review",
                f"{agent_key} submitted a plan for review",
                {"agent_key": agent_key, "plan_name": plan_name},
            ),
        )
        self.save_commander(cmd)

    def approve_plan(self, agent_key, feedback=""):
        """Commander approves an agent's plan."""
        state = self.get_agent(agent_key)
        if state.get("pending_plan"):
            plan_name = state["pending_plan"].get("plan", {}).get("plan", {}).get("name", "Unnamed plan")
            state["pending_plan"]["status"] = "approved"
            state["pending_plan"]["feedback"] = feedback
            state["pending_plan"]["approved_at"] = _now()
            state["status"] = "idle"  # Ready to execute on next tick
            self._append_timeline(
                state,
                self._timeline_event(
                    "plan_approved",
                    f"Plan approved: {plan_name}",
                    {"feedback": feedback[:300]},
                ),
            )
        self.save_agent(agent_key, state)
        self.log_commander_timeline(
            "plan_approved",
            f"Approved plan for {agent_key}",
            {"agent_key": agent_key, "feedback": feedback[:300]},
        )
        self._remove_pending_review(agent_key)

    def reject_plan(self, agent_key, feedback=""):
        """Commander rejects an agent's plan. Clears pending_plan and last_assessment
        so the agent re-assesses on next tick (with Commander feedback in timeline)."""
        state = self.get_agent(agent_key)
        if state.get("pending_plan"):
            plan_name = state["pending_plan"].get("plan", {}).get("plan", {}).get("name", "Unnamed plan")
            state["pending_plan"]["status"] = "rejected"
            state["pending_plan"]["feedback"] = feedback
            state["pending_plan"]["rejected_at"] = _now()
            self._append_timeline(
                state,
                self._timeline_event(
                    "plan_rejected",
                    f"Plan rejected: {plan_name}",
                    {"feedback": feedback[:300]},
                ),
            )
            # Clear so agent re-assesses on next tick instead of waiting for stale window
            state["pending_plan"] = None
            state["last_assessment"] = None
            state["status"] = "idle"
        self.save_agent(agent_key, state)
        self.log_commander_timeline(
            "plan_rejected",
            f"Rejected plan for {agent_key}",
            {"agent_key": agent_key, "feedback": feedback[:300]},
        )
        self._remove_pending_review(agent_key)

    def complete_task(self, agent_key, task_summary):
        """Record a completed task, trim to last 50.

        Also clears pending_plan atomically to prevent a race where another
        tick sees status=idle with an approved pending_plan still set.
        """
        state = self.get_agent(agent_key)
        state["completed_tasks"].insert(0, {
            "completed_at": _now(),
            "summary": task_summary,
        })
        state["completed_tasks"] = state["completed_tasks"][:50]
        state["current_task"] = None
        state["status"] = "idle"
        state["pending_plan"] = None
        state["last_assessment"] = None  # Allow immediate re-assessment next tick
        state.setdefault("mission", {})
        state["mission"]["last_progress_note"] = task_summary[:500]
        state["mission"]["last_progress_at"] = _now()
        self._append_timeline(
            state,
            self._timeline_event("task_completed", task_summary[:500]),
        )
        self.save_agent(agent_key, state)
        self.log_commander_timeline(
            "agent_task_completed",
            f"{agent_key} completed task",
            {"agent_key": agent_key, "summary": task_summary[:300]},
        )

    def log_agent_error(self, agent_key, error_msg):
        """Log an agent error, keep last 20."""
        state = self.get_agent(agent_key)
        state["error_log"].insert(0, {
            "at": _now(),
            "error": str(error_msg)[:500],
        })
        state["error_log"] = state["error_log"][:20]
        state["status"] = "error"
        self._append_timeline(
            state,
            self._timeline_event("error", str(error_msg)[:500]),
        )
        self.save_agent(agent_key, state)
        self.log_commander_timeline(
            "agent_error",
            f"{agent_key} entered error state",
            {"agent_key": agent_key, "error": str(error_msg)[:300]},
        )

    def update_site_snapshot(self, agent_key, snapshot_data):
        """Update the agent's cached site metrics."""
        state = self.get_agent(agent_key)
        state["site_snapshot"] = snapshot_data
        state["site_snapshot"]["updated_at"] = _now()
        self.save_agent(agent_key, state)

    def update_agent_kpis(self, agent_key, kpis, source=None):
        """Merge canonical KPI values for an agent."""
        state = self.get_agent(agent_key)
        existing = state.get("kpis", {})
        merged = dict(existing)
        for key, value in (kpis or {}).items():
            if value is not None:
                merged[key] = value

        merged["last_updated"] = _now()
        merged["source"] = source or merged.get("source")
        state["kpis"] = merged

        self._append_timeline(
            state,
            self._timeline_event(
                "kpi_update",
                "Updated canonical KPI snapshot.",
                {
                    "source": merged.get("source"),
                    "organic_clicks_28d": merged.get("organic_clicks_28d"),
                    "top20_keywords_count": merged.get("top20_keywords_count"),
                    "orphan_pages_count": merged.get("orphan_pages_count"),
                },
            ),
        )
        self.save_agent(agent_key, state)

    def record_execution_outcome(
        self,
        agent_key,
        plan_name,
        baseline_kpis,
        post_kpis,
        notes="",
        confidence="medium",
    ):
        """Persist before/after KPI outcome for one execution cycle."""
        state = self.get_agent(agent_key)
        before = baseline_kpis or {}
        after = post_kpis or {}

        deltas = {}
        for key in (
            "organic_clicks_28d",
            "top20_keywords_count",
            "affiliate_ctr_pct",
            "revenue_per_session_usd",
            "monthly_revenue_usd",
            "orphan_pages_count",
        ):
            b = self._coerce_number(before.get(key))
            a = self._coerce_number(after.get(key))
            deltas[key] = self._calc_delta(b, a)

        outcome = {
            "at": _now(),
            "plan_name": plan_name or "Unnamed plan",
            "baseline_kpis": before,
            "post_kpis": after,
            "deltas": deltas,
            "notes": (notes or "")[:500],
            "confidence": confidence,
        }

        history = state.get("execution_history", [])
        history.insert(0, outcome)
        state["execution_history"] = history[:EXECUTION_HISTORY_LIMIT]
        self._append_timeline(
            state,
            self._timeline_event(
                "execution_outcome",
                f"Captured KPI outcome for plan '{outcome['plan_name']}'.",
                {
                    "confidence": confidence,
                    "organic_clicks_delta": deltas["organic_clicks_28d"]["absolute"],
                    "revenue_delta": deltas["monthly_revenue_usd"]["absolute"],
                },
            ),
        )
        self.save_agent(agent_key, state)

        self.log_commander_timeline(
            "execution_outcome",
            f"{agent_key} recorded outcome for '{outcome['plan_name']}'",
            {"agent_key": agent_key, "confidence": confidence},
        )

    def get_active_url_cooldowns(self, agent_key):
        """Return URL actions still within impact window."""
        state = self.get_agent(agent_key)
        now = datetime.now()
        actions = []
        for item in state.get("recent_url_actions", []):
            review_at = item.get("review_not_before")
            if not review_at:
                continue
            try:
                if datetime.fromisoformat(review_at) > now:
                    actions.append(item)
            except (TypeError, ValueError):
                continue
        return actions

    def record_url_actions(self, agent_key, urls, action, review_after_hours=24):
        """Track URL-level impact windows to prevent premature rework."""
        clean_urls = []
        for url in urls or []:
            if not url:
                continue
            if isinstance(url, str):
                clean_urls.append(url.strip())
        if not clean_urls:
            return

        state = self.get_agent(agent_key)
        now = datetime.now()
        try:
            hours = float(review_after_hours)
        except (TypeError, ValueError):
            hours = 24.0
        if hours < 1:
            hours = 1.0

        review_at = (now + timedelta(hours=hours)).isoformat()
        entries = state.get("recent_url_actions", [])
        for url in clean_urls:
            entries.insert(0, {
                "url": url,
                "action": (action or "")[:200],
                "acted_at": now.isoformat(),
                "review_not_before": review_at,
            })
        state["recent_url_actions"] = entries[:200]
        self.save_agent(agent_key, state)

        self.log_agent_timeline(
            agent_key,
            "url_cooldown",
            f"Recorded {len(clean_urls)} URL impact window(s).",
            {"review_not_before": review_at},
        )

    # ── Commander State ──────────────────────────────────────────────────

    def get_commander(self):
        """Load commander state, creating default if missing."""
        data = self._read("commander")
        if data is None:
            data = _default_commander_state()
            self._write("commander", data)
        else:
            changed = _merge_missing(data, _default_commander_state())
            if changed:
                self._write("commander", data)
        return data

    def save_commander(self, state):
        """Persist commander state."""
        state["last_updated"] = _now()
        self._write("commander", state)

    def add_conversation(self, role, text):
        """Add a message to Commander's conversation buffer (last 20)."""
        cmd = self.get_commander()
        cmd["conversation_buffer"].append({
            "role": role,
            "text": text[:2000],
            "at": _now(),
        })
        cmd["conversation_buffer"] = cmd["conversation_buffer"][-20:]
        self.save_commander(cmd)

    def add_escalation(self, agent_key, issue):
        """Record an escalation from agent to Commander.

        Deduplicates: if an unresolved escalation with the same agent and
        similar text (first 80 chars) already exists, skip the duplicate.
        """
        cmd = self.get_commander()
        issue_prefix = (issue or "")[:80].lower()
        for existing in cmd.get("escalations", []):
            if (existing.get("agent_key") == agent_key
                    and not existing.get("resolved")
                    and (existing.get("issue") or "")[:80].lower() == issue_prefix):
                return  # Duplicate — don't spam
        cmd["escalations"].append({
            "agent_key": agent_key,
            "issue": issue,
            "at": _now(),
            "resolved": False,
        })
        self.save_commander(cmd)

    def resolve_escalation(self, agent_key, resolution=""):
        """Mark unresolved escalations for an agent as resolved."""
        cmd = self.get_commander()
        changed = False
        for esc in cmd.get("escalations", []):
            if esc.get("agent_key") == agent_key and not esc.get("resolved"):
                esc["resolved"] = True
                esc["resolved_at"] = _now()
                esc["resolution"] = (resolution or "Resolved")[:500]
                changed = True
        if changed:
            self.save_commander(cmd)

    # ── Activity Tracking (for periodic reports) ──────────────────────

    def log_write_activity(self, agent_key, tool_name, post_count=1):
        """Record a successful WordPress write for the current reporting window."""
        cmd = self.get_commander()
        window = cmd.setdefault("activity_window", {})
        if not window.get("window_start"):
            window["window_start"] = _now()
        window.setdefault("writes", []).append({
            "agent_key": agent_key,
            "tool": tool_name,
            "posts": post_count,
            "at": _now(),
        })
        self.save_commander(cmd)

    def log_write_failure(self, agent_key, tool_name, error):
        """Record a failed WordPress write for the current reporting window."""
        cmd = self.get_commander()
        window = cmd.setdefault("activity_window", {})
        if not window.get("window_start"):
            window["window_start"] = _now()
        window.setdefault("failures", []).append({
            "agent_key": agent_key,
            "tool": tool_name,
            "error": str(error)[:200],
            "at": _now(),
        })
        self.save_commander(cmd)

    def increment_cycle_count(self):
        """Bump the cycle counter for the current reporting window."""
        cmd = self.get_commander()
        window = cmd.setdefault("activity_window", {})
        if not window.get("window_start"):
            window["window_start"] = _now()
        window["cycles"] = window.get("cycles", 0) + 1
        self.save_commander(cmd)

    def flush_activity_window(self):
        """Reset the activity window and return the flushed data."""
        cmd = self.get_commander()
        flushed = dict(cmd.get("activity_window", {}))
        cmd["activity_window"] = {
            "window_start": _now(),
            "writes": [],
            "failures": [],
            "cycles": 0,
        }
        self.save_commander(cmd)
        return flushed

    def get_all_agent_states(self, agent_keys):
        """Load states for all agents, returns dict keyed by agent_key."""
        return {k: self.get_agent(k) for k in agent_keys}

    def _remove_pending_review(self, agent_key):
        """Remove a plan review from Commander's queue."""
        cmd = self.get_commander()
        cmd["pending_reviews"] = [
            r for r in cmd["pending_reviews"]
            if r.get("agent_key") != agent_key
        ]
        self.save_commander(cmd)
