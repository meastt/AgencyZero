#!/usr/bin/env python3
"""
Agency Status Reporter
Reads strategic plans from all agents and consolidates a fleet readiness report.
"""
import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
AGENTS = {
    "🦁 Griddle King": os.path.join(ROOT_DIR, "agents/seo_manager/STRATEGIC_PLAN.md"),
    "📸 Photo Tips": os.path.join(ROOT_DIR, "agents/photo_manager/STRATEGIC_PLAN.md"),
    "🐅 Tiger Tribe": os.path.join(ROOT_DIR, "agents/cat_manager/STRATEGIC_PLAN.md")
}

def extract_section(content, header):
    """Extracts content under a markdown header."""
    pattern = re.compile(f"## {header}(.*?)(##|$)", re.DOTALL)
    match = pattern.search(content)
    if match:
        # Return first 300 chars to keep it brief
        text = match.group(1).strip()
        lines = text.split('\n')
        essential = []
        for line in lines:
            if line.strip() and not line.startswith('#'):
                essential.append(line.strip())
                if len(essential) >= 3: break
        return "\n".join(essential)
    return "No Data"

def get_mission(content):
    match = re.search(r"\*\*Mission:\*\*(.*)", content)
    return match.group(1).strip() if match else "Unknown"

def main():
    print("\n🚀 AGENCYZERO AGENCY STATUS REPORT")
    print("==================================================")
    
    for name, path in AGENTS.items():
        print(f"\n{name}")
        if os.path.exists(path):
            with open(path, 'r') as f:
                content = f.read()
                
            mission = get_mission(content)
            priorities = extract_section(content, "🏆 STRATEGIC PRIORITIES \(Next 30 Days\)")
            
            print(f"   Mission: {mission}")
            print(f"   Priorities:\n   {priorities.replace(chr(10), chr(10)+'   ')}")
        else:
            print("   ⚠️  Strategic Plan Missing (Agent Inactive?)")

    print("\n==================================================")
    print("✅ FLEET READY FOR COMMAND")

if __name__ == "__main__":
    main()
