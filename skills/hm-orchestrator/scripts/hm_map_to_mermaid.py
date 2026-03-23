#!/usr/bin/env python3
"""
Convert .hm/map.json (Hypothesis Map data) to Mermaid flowchart (.mmd).
Minimal, redistributable helper for visualization fallback.

Input:  ./.hm/map.json
Output: ./hm/map.mmd (creates directory if missing)

Note: Keeps styles aligned with the Hypothesis Map color scheme.
"""
import json
import os
from pathlib import Path

GOAL_COLOR = "#cadf58"
SUBJECT_COLOR = "#ffc831"
NEG_SUBJECT_COLOR = "#ffb373"
HYP_COLOR = "#ffef73"
TASK_COLOR = "#a6cdff"
NOTE_COLOR = "#f1f1f1"
BLOCKER_COLOR = "#FFA391"
EDGE_COLOR = "#70736D"

def read_map(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def sanitize_id(s: str) -> str:
    # Keep simple ASCII ids for Mermaid nodes
    return ''.join(ch if ch.isalnum() or ch in "_-" else '_' for ch in s)

def node(label: str, cls: str) -> str:
    return f"[{label}]:::{cls}"

def build_mermaid(data: dict) -> str:
    lines = ["flowchart TB"]
    # class defs
    lines.append(f"classDef goal fill:{GOAL_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef subject fill:{SUBJECT_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef negsubject fill:{NEG_SUBJECT_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef hypothesis fill:{HYP_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef task fill:{TASK_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef note fill:{NOTE_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef blocker fill:{BLOCKER_COLOR},stroke:{EDGE_COLOR},color:#000;")

    goal = data.get("goal") or {}
    goal_id = sanitize_id(goal.get("id") or "goal")
    goal_name = goal.get("name") or goal.get("description") or "Цель"
    lines.append(f"{goal_id}{node(f'Цель: {goal_name}', 'goal')}")

    # subjects
    subj_index = {}
    for idx, s in enumerate(data.get("subjects") or []):
        sid = sanitize_id(s.get("id") or f"s{idx+1}")
        sname = s.get("name") or f"Субъект {idx+1}"
        cls = "negsubject" if s.get("negative") else "subject"
        lines.append(f"{sid}{node(f'Субъект: {sname}', cls)}")
        subj_index[s.get("id") or sid] = sid

    # hypotheses
    hyp_index = {}
    for idx, h in enumerate(data.get("hypotheses") or []):
        hid = sanitize_id(h.get("id") or f"h{idx+1}")
        linkage = h.get("linkage") or "via_subject"
        if_text = h.get("if") or ""
        then_text = h.get("then") or ""
        because = h.get("because") or ""
        label = f"Если {if_text}\\nто {then_text}\\nпотому что {because}"
        lines.append(f"{hid}{node(label, 'hypothesis')}")
        hyp_index[h.get("id") or hid] = hid

    # tasks
    for idx, t in enumerate(data.get("tasks") or []):
        tid = sanitize_id(t.get("id") or f"t{idx+1}")
        title = t.get("title") or f"Задача {idx+1}"
        lines.append(f"{tid}{node(f'Задача: {title}', 'task')}")

    # links: subject -> hypothesis -> task -> goal
    for h in (data.get("hypotheses") or []):
        hid = hyp_index.get(h.get("id") or sanitize_id(h.get("id") or ""))
        if not hid:
            continue
        sref = h.get("subject_ref")
        if sref:
            sid = subj_index.get(sref) or sanitize_id(sref)
            lines.append(f"{sid} --> {hid}")
        # tasks linked to hypothesis
        for t in (data.get("tasks") or []):
            if t.get("linked_hypothesis") == (h.get("id") or h.get("id")):
                tid = sanitize_id(t.get("id") or "")
                if tid:
                    lines.append(f"{hid} --> {tid}")
        # always draw hypothesis -> goal
        lines.append(f"{hid} --> {goal_id}")

    return "\n".join(lines) + "\n"

def main():
    root = Path.cwd()
    map_path = root / ".hm" / "map.json"
    out_dir = root / "hm"
    ensure_dir(out_dir)
    out_path = out_dir / "map.mmd"

    if not map_path.exists():
        raise SystemExit(".hm/map.json not found. Run orchestrator steps to produce map.json first.")

    data = read_map(map_path)
    content = build_mermaid(data)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
