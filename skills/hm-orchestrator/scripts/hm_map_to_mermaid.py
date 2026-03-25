#!/usr/bin/env python3
"""
Convert .hm/map.json (Hypothesis Map data) to Mermaid flowchart (.mmd).

Input:  ./.hm/map.json
Output: ./hm/map.mmd

Topology defaults follow the conventions from Byndyusoft/hypothesismapping:
- goal stays on the left
- subjects are to the right of the goal
- hypotheses are to the right of subjects
- tasks are to the right of hypotheses
- metrics can live on a dedicated band between goal and subjects
- blockers and notes live on a separate context lane

The renderer accepts an optional top-level `topology` block:
{
  "topology": {
    "mode": "extended_lr | classic_lr",
    "metrics": "separate_band | inline",
    "tasks": "auto | linked | board",
    "link_mode": "smart_tags | arrows",
    "note_lane": "bottom | inline",
    "blocker_lane": "bottom | inline"
  }
}
"""

import json
from collections import defaultdict
from pathlib import Path

GOAL_COLOR = "#cadf58"
SUBJECT_COLOR = "#ffc831"
NEG_SUBJECT_COLOR = "#ffb373"
HYP_COLOR = "#ffef73"
TASK_COLOR = "#a6cdff"
NOTE_COLOR = "#f1f1f1"
BLOCKER_COLOR = "#FFA391"
EDGE_COLOR = "#70736D"

PRIORITY_EDGE_COLORS = {
    "high": "#C0392B",
    "mid": "#D68910",
    "low": "#7F8C8D",
}
PRIORITY_RANK = {"low": 1, "mid": 2, "high": 3}

DEFAULT_TOPOLOGY = {
    "mode": "extended_lr",
    "metrics": "separate_band",
    "tasks": "auto",
    "link_mode": "smart_tags",
    "note_lane": "bottom",
    "blocker_lane": "bottom",
    "layout_engine": "elk",
}


def read_map(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(value))


def sanitize_label(value: str) -> str:
    """Keep Mermaid-safe labels while preserving Mermaid line breaks."""
    if value is None:
        return ""

    value = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    newline_token = "__MERMAID_NL__"
    value = value.replace("\\n", newline_token)

    replacements = {
        "[": " ",
        "]": " ",
        "{": " ",
        "}": " ",
        "\\": " ",
        "/": "-",
        "(": " ",
        ")": " ",
        "\u00ab": '"',
        "\u00bb": '"',
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2192": " to ",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)

    value = value.replace('"', "").replace("'", "")

    parts = []
    for chunk in value.split(newline_token):
        normalized = " ".join(chunk.split()).strip()
        if normalized:
            parts.append(normalized)

    return "\\n".join(parts)


def node(label: str, cls: str) -> str:
    return f"[{sanitize_label(label)}]:::{cls}"


def hidden_node(node_id: str) -> str:
    return f'{node_id}[" "]:::hidden'


def merge_topology(data: dict) -> dict:
    topology = DEFAULT_TOPOLOGY.copy()
    raw = data.get("topology") or {}
    for key in DEFAULT_TOPOLOGY:
        if isinstance(raw.get(key), str) and raw[key]:
            topology[key] = raw[key]

    if topology["tasks"] == "auto":
        has_board_lanes = any(task.get("status") or task.get("lane") for task in (data.get("tasks") or []))
        topology["resolved_tasks"] = "board" if has_board_lanes else "linked"
    else:
        topology["resolved_tasks"] = topology["tasks"]

    return topology


def add_edge(lines: list[str], edge_meta: list[dict], src: str, dst: str, priority: str | None = None, hidden: bool = False) -> None:
    lines.append(f"{src} --> {dst}")
    edge_meta.append(
        {
            "priority": priority if priority in PRIORITY_EDGE_COLORS else None,
            "hidden": hidden,
        }
    )


def max_priority(existing: str | None, candidate: str | None) -> str | None:
    if candidate not in PRIORITY_RANK:
        return existing
    if existing not in PRIORITY_RANK:
        return candidate
    return candidate if PRIORITY_RANK[candidate] >= PRIORITY_RANK[existing] else existing


def metric_label(prefix: str, metric: dict, target_key: str) -> str:
    target = metric.get(target_key)
    return f"{prefix}: {metric.get('name', 'metric')}\\ntarget: {target}"


def summarize_metric_impacts(hypothesis: dict) -> str:
    impacts = [impact.get("metric", "") for impact in (hypothesis.get("then_metrics_impact") or []) if impact.get("metric")]
    return ", ".join(impacts)


def task_lane(task: dict) -> str:
    return task.get("status") or task.get("lane") or "Без статуса"


def build_mermaid(data: dict) -> str:
    topology = merge_topology(data)

    frontmatter = [
        "---",
        "config:",
        f"  layout: {topology['layout_engine']}",
        "  look: classic",
        "  htmlLabels: false",
    ]
    if topology["layout_engine"] == "elk":
        frontmatter.extend(
            [
                "  elk:",
                "    mergeEdges: false",
                "    nodePlacementStrategy: LINEAR_SEGMENTS",
            ]
        )
    frontmatter.append("---")

    lines: list[str] = frontmatter + ["flowchart RL"]
    edge_meta: list[dict] = []
    node_ids: dict[str, str] = {}

    lines.append(f"classDef goal fill:{GOAL_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef subject fill:{SUBJECT_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef negsubject fill:{NEG_SUBJECT_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef hypothesis fill:{HYP_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef task fill:{TASK_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef note fill:{NOTE_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append(f"classDef blocker fill:{BLOCKER_COLOR},stroke:{EDGE_COLOR},color:#000;")
    lines.append("classDef hidden fill:transparent,stroke:transparent,color:transparent;")

    goal = data.get("goal") or {}
    goal_id = sanitize_id(goal.get("id") or "goal")
    goal_anchor = "_goal_band_anchor"
    lines.append('subgraph goal_band["Цель"]')
    lines.append("direction TB")
    lines.append(hidden_node(goal_anchor))
    lines.append(f'{goal_id}{node(f"Цель: {goal.get("name") or "Цель"}", "goal")}')
    lines.append("end")
    node_ids[goal.get("id") or goal_id] = goal_id

    metric_ids: list[str] = []
    metric_anchor = "_metric_band_anchor"
    metrics_in_separate_band = topology["metrics"] == "separate_band"
    if metrics_in_separate_band:
        lines.append('subgraph metric_band["Метрики"]')
        lines.append("direction TB")
        lines.append(hidden_node(metric_anchor))
    for idx, metric in enumerate(goal.get("metrics") or [], start=1):
        metric_key = metric.get("id") or f"m{idx}"
        metric_id = sanitize_id(metric_key)
        metric_ids.append(metric_id)
        node_ids[metric_key] = metric_id
        node_ids[metric.get("name", metric_key)] = metric_id
        line = f'{metric_id}{node(metric_label("Метрика", metric, "target"), "goal")}'
        if metrics_in_separate_band:
            lines.append(line)
        else:
            lines.insert(lines.index("end"), line)
        add_edge(lines, edge_meta, metric_id, goal_id)

    for idx, metric in enumerate(goal.get("balancing_metrics") or [], start=1):
        metric_key = metric.get("id") or f"bm{idx}"
        metric_id = sanitize_id(metric_key)
        metric_ids.append(metric_id)
        node_ids[metric_key] = metric_id
        node_ids[metric.get("name", metric_key)] = metric_id
        label = metric_label("Баланс", metric, "value") + f'\\nconstraint: {metric.get("constraint")}'
        line = f'{metric_id}{node(label, "goal")}'
        if metrics_in_separate_band:
            lines.append(line)
        else:
            lines.insert(lines.index("end"), line)
        add_edge(lines, edge_meta, metric_id, goal_id)
    if metrics_in_separate_band:
        lines.append("end")

    subject_anchor = "_subject_band_anchor"
    lines.append('subgraph subject_band["Субъекты"]')
    lines.append("direction TB")
    lines.append(hidden_node(subject_anchor))
    subject_ids: list[str] = []
    for idx, subject in enumerate(data.get("subjects") or [], start=1):
        subject_key = subject.get("id") or f"s{idx}"
        subject_id = sanitize_id(subject_key)
        subject_ids.append(subject_id)
        node_ids[subject_key] = subject_id
        cls = "negsubject" if subject.get("negative") else "subject"
        lines.append(f'{subject_id}{node(f"Субъект: {subject.get("name") or f"Субъект {idx}"}", cls)}')
    lines.append("end")

    hypothesis_anchor = "_hypothesis_band_anchor"
    lines.append('subgraph hypothesis_band["Гипотезы"]')
    lines.append("direction TB")
    lines.append(hidden_node(hypothesis_anchor))
    hypothesis_ids: dict[str, str] = {}
    for idx, hypothesis in enumerate(data.get("hypotheses") or [], start=1):
        hypothesis_key = hypothesis.get("id") or f"h{idx}"
        hypothesis_id = sanitize_id(hypothesis_key)
        hypothesis_ids[hypothesis_key] = hypothesis_id
        node_ids[hypothesis_key] = hypothesis_id
        label = (
            f"Гипотеза {hypothesis_key}\\n"
            f"Приоритет: {hypothesis.get('priority', 'n/a')}\\n"
            f"Если {hypothesis.get('if', '')}\\n"
            f"то {hypothesis.get('then', '')}\\n"
            f"потому что {hypothesis.get('because', '')}"
        )
        metric_summary = summarize_metric_impacts(hypothesis)
        if metric_summary:
            label += f"\\nтогда влияет на: {metric_summary}"
        lines.append(f'{hypothesis_id}{node(label, "hypothesis")}')
    lines.append("end")

    task_anchor = "_task_band_anchor"
    task_nodes: dict[str, str] = {}
    tasks = data.get("tasks") or []
    resolved_tasks_mode = topology["resolved_tasks"]
    lines.append('subgraph task_band["Задачи"]')
    lines.append("direction TB")
    lines.append(hidden_node(task_anchor))
    if resolved_tasks_mode == "board":
        tasks_by_lane: dict[str, list[dict]] = defaultdict(list)
        for task in tasks:
            tasks_by_lane[task_lane(task)].append(task)
        for lane_name in sorted(tasks_by_lane):
            lane_id = f"_lane_{sanitize_id(lane_name)}"
            lines.append(f'subgraph {lane_id}["{sanitize_label(lane_name)}"]')
            lines.append("direction TB")
            for idx, task in enumerate(tasks_by_lane[lane_name], start=1):
                task_key = task.get("id") or f"t_{sanitize_id(lane_name)}_{idx}"
                task_id = sanitize_id(task_key)
                task_nodes[task_key] = task_id
                node_ids[task_key] = task_id
                label = f'Задача: {task.get("title") or task_key}\\nТип: {task.get("type", "task")}'
                lines.append(f'{task_id}{node(label, "task")}')
            lines.append("end")
    else:
        for idx, task in enumerate(tasks, start=1):
            task_key = task.get("id") or f"t{idx}"
            task_id = sanitize_id(task_key)
            task_nodes[task_key] = task_id
            node_ids[task_key] = task_id
            label = f'Задача: {task.get("title") or f"Задача {idx}"}\\nТип: {task.get("type", "task")}'
            lines.append(f'{task_id}{node(label, "task")}')
    lines.append("end")

    context_anchor = "_context_band_anchor"
    if topology["note_lane"] == "bottom" or topology["blocker_lane"] == "bottom":
        lines.append('subgraph context_band["Контекст"]')
        lines.append("direction TB")
        lines.append(hidden_node(context_anchor))
        for idx, blocker in enumerate(data.get("blockers") or [], start=1):
            blocker_key = blocker.get("id") or f"b{idx}"
            blocker_id = sanitize_id(blocker_key)
            node_ids[blocker_key] = blocker_id
            label = f'Блокер: {blocker.get("reason", "")}\\nДействие: {blocker.get("actions", "")}'
            lines.append(f'{blocker_id}{node(label, "blocker")}')
        for idx, note_text in enumerate(data.get("notes") or [], start=1):
            note_key = f"note{idx}"
            note_id = sanitize_id(note_key)
            node_ids[note_key] = note_id
            lines.append(f'{note_id}{node(f"Заметка: {note_text}", "note")}')
        lines.append("end")

    # Hidden anchors force the band ordering for RL layout:
    # goal <- metrics <- subjects <- hypotheses <- tasks
    if metrics_in_separate_band:
        add_edge(lines, edge_meta, task_anchor, hypothesis_anchor, hidden=True)
        add_edge(lines, edge_meta, hypothesis_anchor, subject_anchor, hidden=True)
        add_edge(lines, edge_meta, subject_anchor, metric_anchor, hidden=True)
        add_edge(lines, edge_meta, metric_anchor, goal_anchor, hidden=True)
        for metric_id in metric_ids:
            add_edge(lines, edge_meta, metric_anchor, metric_id, hidden=True)
    else:
        add_edge(lines, edge_meta, task_anchor, hypothesis_anchor, hidden=True)
        add_edge(lines, edge_meta, hypothesis_anchor, subject_anchor, hidden=True)
        add_edge(lines, edge_meta, subject_anchor, goal_anchor, hidden=True)
    for subject_id in subject_ids:
        add_edge(lines, edge_meta, subject_anchor, subject_id, hidden=True)
    for hypothesis_id in hypothesis_ids.values():
        add_edge(lines, edge_meta, hypothesis_anchor, hypothesis_id, hidden=True)
    for task_id in task_nodes.values():
        add_edge(lines, edge_meta, task_anchor, task_id, hidden=True)
    if context_anchor in "".join(lines):
        add_edge(lines, edge_meta, context_anchor, goal_anchor, hidden=True)

    # Core visible semantic edges.
    subject_to_goal_priority: dict[str, str | None] = {}
    for hypothesis in data.get("hypotheses") or []:
        subject_ref = hypothesis.get("subject_ref")
        if subject_ref:
            subject_to_goal_priority[subject_ref] = max_priority(subject_to_goal_priority.get(subject_ref), hypothesis.get("priority"))

    for subject_ref, priority in subject_to_goal_priority.items():
        if subject_ref in node_ids:
            add_edge(lines, edge_meta, node_ids[subject_ref], goal_id, priority)

    for hypothesis in data.get("hypotheses") or []:
        hypothesis_id = hypothesis_ids.get(hypothesis.get("id"))
        if not hypothesis_id:
            continue
        subject_ref = hypothesis.get("subject_ref")
        if subject_ref and subject_ref in node_ids:
            add_edge(lines, edge_meta, hypothesis_id, node_ids[subject_ref], hypothesis.get("priority"))

        if topology["link_mode"] == "arrows":
            for impact in hypothesis.get("then_metrics_impact") or []:
                metric_ref = impact.get("metric")
                if metric_ref in node_ids:
                    add_edge(lines, edge_meta, hypothesis_id, node_ids[metric_ref], hypothesis.get("priority"))

    for task in tasks:
        task_id = task_nodes.get(task.get("id"))
        hypothesis_id = hypothesis_ids.get(task.get("linked_hypothesis"))
        if not task_id or not hypothesis_id:
            continue
        add_edge(lines, edge_meta, task_id, hypothesis_id, task.get("priority"), hidden=resolved_tasks_mode == "board")

    for idx, blocker in enumerate(data.get("blockers") or [], start=1):
        blocker_key = blocker.get("id") or f"b{idx}"
        blocker_id = node_ids.get(blocker_key)
        if blocker_id:
            add_edge(lines, edge_meta, blocker_id, goal_id)
    for idx, _note in enumerate(data.get("notes") or [], start=1):
        note_key = f"note{idx}"
        note_id = node_ids.get(note_key)
        if note_id:
            add_edge(lines, edge_meta, note_id, goal_id)

    for index, meta in enumerate(edge_meta):
        if meta["hidden"]:
            lines.append(f"linkStyle {index} stroke:transparent,stroke-width:0px,color:transparent,fill:none;")
            continue
        if meta["priority"]:
            color = PRIORITY_EDGE_COLORS[meta["priority"]]
            lines.append(f"linkStyle {index} stroke:{color},stroke-width:2px;")

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
