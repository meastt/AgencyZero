"""
Tool Registry — wraps existing scripts as callable tools for agent brains.
Runs scripts as subprocesses with correct SITE_PREFIX and PYTHONPATH.
"""

import json
import os
import subprocess
import sys

TOOL_ALIASES = {
    "orphanrescue": "orphan_rescue",
    "orphan-rescue": "orphan_rescue",
    "orphan_rescan": "orphan_rescue",
    "build_site_inventory": "build_inventory",
    "site_inventory": "build_inventory",
    "update_meta": "update_post_meta",
    "inject_links": "inject_internal_links",
    "fix_affiliates": "fix_affiliate_links",
}


# Tool definitions: name -> (script_path relative to ROOT_DIR, output_file relative to ROOT_DIR)
# Output paths with {slug} are expanded per-agent based on SITE_PREFIX
TOOL_DEFINITIONS = {
    # ── READ tools (intelligence gathering) ─────────────────────────────
    "gsc_audit": {
        "script": "agents/seo_manager/scripts/gsc_audit.py",
        "output": "agents/seo_manager/data/gsc_audit_{slug}.json",
        "description": "Pull GSC performance data — clicks, impressions, positions, declining pages.",
    },
    "seo_audit": {
        "script": "shared/scripts/universal_seo_audit.py",
        "output": "seo_kickstart_results.json",
        "description": "Full SEO audit — internal links, orphans, content quality, meta tags. EXPENSIVE: prefer build_inventory for routine checks.",
    },
    "keyword_research": {
        "script": "shared/scripts/universal_keyword_research.py",
        "output": "keyword_opportunities.json",
        "description": "Keyword research — find opportunities, Page 2 pushes, gaps vs competitors.",
    },
    "affiliate_audit": {
        "script": "shared/scripts/affiliate_audit.py",
        "output": "affiliate_audit_report.json",
        "description": "Audit affiliate links — find broken, missing, or underperforming links.",
    },
    "build_inventory": {
        "script": "shared/scripts/build_site_inventory.py",
        "output": "state/inventory_{slug}.json",
        "description": "Build or refresh site inventory — crawls all posts, counts links, word counts, meta descriptions. Incremental after first run. Use INSTEAD of seo_audit for routine checks.",
    },
    # ── WRITE tools (make actual changes) ───────────────────────────────
    "update_post_meta": {
        "script": "shared/scripts/update_post_meta.py",
        "output": None,
        "description": "Update post titles and meta descriptions on WordPress. Write instructions to state/pending_meta_update_{slug}.json BEFORE calling this tool. Format: {\"updates\": [{\"post_id\": 123, \"new_title\": \"...\", \"new_meta_description\": \"...\"}]}",
    },
    "inject_internal_links": {
        "script": "shared/scripts/inject_internal_links.py",
        "output": None,
        "description": "Inject internal links into WordPress posts. Write instructions to state/pending_link_inject_{slug}.json BEFORE calling. Format: {\"injections\": [{\"source_post_id\": 456, \"target_url\": \"...\", \"anchor_text\": \"...\", \"context_hint\": \"...\"}]}",
    },
    "fix_affiliate_links": {
        "script": "shared/scripts/fix_affiliate_links.py",
        "output": None,
        "description": "Fix broken or untagged affiliate links. Write instructions to state/pending_affiliate_fix_{slug}.json BEFORE calling. Format: {\"fixes\": [{\"post_id\": 123, \"broken_url\": \"...\", \"fixed_url\": \"...\", \"action\": \"retag\"}]}",
    },
    # ── LEGACY tools ────────────────────────────────────────────────────
    "orphan_rescue": {
        "script": "scripts/orphan_rescue.py",
        "output": "data/orphan_rescan.json",
        "description": "DEPRECATED: Use inject_internal_links instead. Legacy orphan rescue script.",
    },
    "generate_image": {
        "script": "shared/scripts/generate_featured_image.py",
        "output": None,
        "description": "Generate a featured image for a post using AI.",
    },
}


class ToolRegistry:
    """Wraps existing scripts as callable tools for agent brains."""

    def __init__(self, root_dir, site_prefix):
        """
        Args:
            root_dir: Project root directory.
            site_prefix: SITE_PREFIX env var value (e.g., "WP_GRIDDLEKING").
        """
        self.root_dir = root_dir
        self.site_prefix = site_prefix
        self.slug = site_prefix.lower().replace('wp_', '').replace('_', '')

    def list_tools(self):
        """Return available tool names and descriptions."""
        return {
            name: defn["description"]
            for name, defn in TOOL_DEFINITIONS.items()
        }

    def _resolve_output_path(self, output_template):
        """Replace {slug} in output path with agent-specific slug."""
        if not output_template:
            return None
        return output_template.replace("{slug}", self.slug)

    def run_tool(self, tool_name, **kwargs):
        """Run a tool by name and return results.

        Args:
            tool_name: Name from tool definitions.
            **kwargs: Extra args (e.g., title for generate_image).

        Returns:
            dict: {"success": bool, "output": str, "data": dict|None}
        """
        canonical_name = TOOL_ALIASES.get(tool_name, tool_name)
        defn = TOOL_DEFINITIONS.get(canonical_name)
        if not defn:
            return {
                "success": False,
                "output": f"Unknown tool: {tool_name}",
                "data": None,
            }

        script_path = os.path.join(self.root_dir, defn["script"])
        if not os.path.exists(script_path):
            return {
                "success": False,
                "output": f"Script not found: {defn['script']}",
                "data": None,
            }

        # Build environment
        env = os.environ.copy()
        env["SITE_PREFIX"] = self.site_prefix
        # Suppress direct Telegram alerts from scripts — the Commander chain
        # of command owns all outward messaging when tools run under an agent.
        env["SUPPRESS_TELEGRAM_ALERTS"] = "1"

        # Add shared/scripts to PYTHONPATH for telegram_utils etc.
        shared_scripts = os.path.join(self.root_dir, "shared", "scripts")
        existing_pypath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{shared_scripts}:{existing_pypath}" if existing_pypath else shared_scripts

        # Build command
        cmd = [sys.executable, script_path]
        # Pass extra kwargs as positional args (e.g., generate_image takes title + niche)
        for val in kwargs.values():
            if val is not None:
                cmd.append(str(val))

        # Determine working directory (script's parent)
        cwd = os.path.dirname(script_path)

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=cwd,
            )

            stdout = result.stdout[-3000:] if result.stdout else ""
            stderr = result.stderr[-1000:] if result.stderr else ""

            if result.returncode != 0:
                return {
                    "success": False,
                    "output": f"Script failed (exit {result.returncode}):\n{stderr}\n{stdout}",
                    "data": None,
                }

            # Try to load structured output
            data = None
            output_rel = self._resolve_output_path(defn.get("output"))
            if output_rel:
                output_path = os.path.join(self.root_dir, output_rel)
                if os.path.exists(output_path):
                    try:
                        with open(output_path, "r") as f:
                            data = json.load(f)
                    except (json.JSONDecodeError, OSError):
                        pass

            return {
                "success": True,
                "output": stdout,
                "data": data,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                    "output": f"Tool `{canonical_name}` timed out (5 min limit).",
                "data": None,
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Tool `{canonical_name}` error: {str(e)[:300]}",
                "data": None,
            }
