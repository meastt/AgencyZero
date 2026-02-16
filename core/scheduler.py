"""
Scheduler — runs agent ticks and Commander review cycles on intervals.
Uses threading.Timer for simple, reliable scheduling.
"""

import threading
import time
from datetime import datetime

# Seconds to wait before a quick follow-up tick after an agent completes a plan.
QUICK_FOLLOW_UP_SECONDS = 15


class AgentScheduler:
    """Timer-based scheduler for autonomous agent loops."""

    def __init__(self):
        self._agents = {}       # key -> {"brain": AgentBrain, "interval": seconds, "timer": Timer}
        self._review = None     # {"brain": CommanderBrain, "interval": seconds, "timer": Timer}
        self._report = None     # {"brain": CommanderBrain, "send_fn": callable, "interval": s, "timer": Timer}
        self._running = False
        self._lock = threading.Lock()
        self._agent_locks = {}  # per-agent locks to prevent concurrent tick() execution
        self._review_lock = threading.Lock()
        self._review_retrigger_pending = False

    def register_agent(self, agent_key, brain, interval_minutes=60):
        """Register an agent brain for periodic ticking."""
        self._agents[agent_key] = {
            "brain": brain,
            "interval": interval_minutes * 60,
            "timer": None,
        }
        self._agent_locks[agent_key] = threading.Lock()

    def register_review(self, commander_brain, interval_minutes=15):
        """Register Commander review cycle."""
        self._review = {
            "brain": commander_brain,
            "interval": interval_minutes * 60,
            "timer": None,
        }

    def register_report(self, commander_brain, send_fn, interval_hours=4):
        """Register periodic monitoring report."""
        self._report = {
            "brain": commander_brain,
            "send_fn": send_fn,
            "interval": interval_hours * 3600,
            "timer": None,
        }

    def start(self):
        """Start all scheduled loops."""
        self._running = True

        # Start agent timers (staggered to avoid thundering herd)
        for i, (key, entry) in enumerate(self._agents.items()):
            delay = 120 + (i * 30)  # Start after 2 min, staggered by 30s
            self._schedule_agent(key, delay)
            print(f"  Scheduled {key}: first tick in {delay}s, then every {entry['interval']//60}min")

        # Start review timer
        if self._review:
            self._schedule_review(60)  # First review after 1 min
            print(f"  Scheduled review: first in 60s, then every {self._review['interval']//60}min")

        # Start periodic report timer
        if self._report:
            self._schedule_report(self._report["interval"])
            print(f"  Scheduled report: every {self._report['interval']//3600}h")

    def stop(self):
        """Stop all timers."""
        self._running = False
        with self._lock:
            for entry in self._agents.values():
                if entry["timer"]:
                    entry["timer"].cancel()
                    entry["timer"] = None
            if self._review and self._review["timer"]:
                self._review["timer"].cancel()
                self._review["timer"] = None
            if self._report and self._report["timer"]:
                self._report["timer"].cancel()
                self._report["timer"] = None
        print("Scheduler stopped.")

    def trigger_now(self, agent_key):
        """Force an immediate agent tick (called by Commander brain)."""
        if agent_key not in self._agents:
            return
        # Run in a new thread to avoid blocking
        thread = threading.Thread(
            target=self._run_agent_tick,
            args=(agent_key,),
            daemon=True,
        )
        thread.start()

    def trigger_review_now(self):
        """Force an immediate Commander review cycle."""
        if not self._review:
            return
        thread = threading.Thread(
            target=self._run_review,
            kwargs={"source": "immediate"},
            daemon=True,
        )
        thread.start()

    def set_interval(self, agent_key, minutes):
        """Change an agent's tick interval."""
        if agent_key in self._agents:
            self._agents[agent_key]["interval"] = minutes * 60

    def _schedule_agent(self, key, delay):
        """Schedule the next agent tick."""
        if not self._running:
            return
        with self._lock:
            entry = self._agents.get(key)
            if not entry:
                return
            if entry["timer"]:
                entry["timer"].cancel()
            entry["timer"] = threading.Timer(delay, self._run_agent_tick, args=(key,))
            entry["timer"].daemon = True
            entry["timer"].start()

    def _schedule_review(self, delay):
        """Schedule the next Commander review cycle."""
        if not self._running or not self._review:
            return
        with self._lock:
            if self._review["timer"]:
                self._review["timer"].cancel()
            self._review["timer"] = threading.Timer(
                delay,
                self._run_review,
                kwargs={"source": "scheduled"},
            )
            self._review["timer"].daemon = True
            self._review["timer"].start()

    def _run_agent_tick(self, key):
        """Execute an agent tick and reschedule."""
        entry = self._agents.get(key)
        if not entry:
            return

        agent_lock = self._agent_locks.get(key)
        if not agent_lock:
            return

        # Prevent concurrent tick() calls for the same agent.
        if not agent_lock.acquire(blocking=False):
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] Agent {key} tick skipped — already running")
            return

        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] Agent tick: {key}")

        try:
            entry["brain"].tick()
        except Exception as e:
            print(f"[{ts}] Agent {key} tick error: {e}")
        finally:
            agent_lock.release()

        # Reschedule — use a short delay if the agent just finished a plan and
        # is ready for a new assessment cycle (last_assessment cleared to None).
        if self._running:
            delay = entry["interval"]
            try:
                agent_state = entry["brain"].state.get_agent(key)
                if (agent_state.get("status") == "idle"
                        and agent_state.get("last_assessment") is None):
                    delay = QUICK_FOLLOW_UP_SECONDS
                    print(f"[{key}] Plan just completed — quick follow-up in {delay}s")
            except Exception:
                pass
            self._schedule_agent(key, delay)

    def _run_review(self, source="scheduled"):
        """Execute Commander review cycle and reschedule."""
        if not self._review:
            return

        if not self._review_lock.acquire(blocking=False):
            ts = datetime.now().strftime("%H:%M:%S")
            # If an immediate review is requested while one is running, queue a fast follow-up.
            if source in ("immediate", "queued"):
                self._review_retrigger_pending = True
                print(f"[{ts}] Commander review queued ({source}) — already running")
            else:
                print(f"[{ts}] Commander review skipped ({source}) — already running")
                # Keep scheduled cadence alive even when this slot collides.
                if self._running:
                    self._schedule_review(self._review["interval"])
            return

        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] Commander review cycle ({source})")

        run_follow_up = False
        try:
            results = self._review["brain"].review_cycle()
            for r in results:
                print(f"  Review: {r['agent_key']} -> {r['decision']}")
        except Exception as e:
            print(f"[{ts}] Review cycle error: {e}")
        finally:
            # If an immediate/queued run was requested during this cycle, drain it next.
            run_follow_up = self._review_retrigger_pending
            self._review_retrigger_pending = False
            self._review_lock.release()

        # Drain queued immediate follow-ups so pending reviews don't wait for next interval.
        if self._running and run_follow_up:
            follow = threading.Thread(
                target=self._run_review,
                kwargs={"source": "queued"},
                daemon=True,
            )
            follow.start()

        # Scheduled runs should drive periodic cadence.
        if self._running and source == "scheduled":
            self._schedule_review(self._review["interval"])

    # ── Periodic Monitoring Report ──────────────────────────────────────

    def _schedule_report(self, delay):
        """Schedule the next periodic report."""
        if not self._running or not self._report:
            return
        with self._lock:
            if self._report["timer"]:
                self._report["timer"].cancel()
            self._report["timer"] = threading.Timer(delay, self._run_report)
            self._report["timer"].daemon = True
            self._report["timer"].start()

    def _run_report(self):
        """Generate and send the periodic monitoring report."""
        if not self._report:
            return

        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] Generating periodic report...")

        try:
            report_text = self._report["brain"].generate_periodic_report()
            self._report["send_fn"](report_text)
            print(f"[{ts}] Periodic report sent.")
        except Exception as e:
            print(f"[{ts}] Report error: {e}")

        # Reschedule
        if self._running:
            self._schedule_report(self._report["interval"])
