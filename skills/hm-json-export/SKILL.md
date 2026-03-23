---
name: hm-json-export
description: Экспортируй «Карту гипотез» в структурированный JSON/YAML (Strategy as Code): цели, метрики, субъекты, гипотезы, задачи, блокеры, заметки, связи и приоритеты.
---

# HM JSON Export

Назначение
- Стандартизованный экспорт данных карты для автоматизации, версионирования и интеграций.

Схема (минимум)
```
{
  "goal": {"id": "g1", "name": "...", "metrics": [...], "balancing_metrics": [...]},
  "subjects": [{"id": "s1", "name": "...", "pains_desires": [...], "negative": false}],
  "hypotheses": [{
    "id": "h1",
    "linkage": "via_subject|direct",
    "if": "...", "then": "...", "because": "...",
    "then_metrics_impact": [{"metric": "...", "direction": "up|down|hold", "expected_delta": "..."}],
    "goal_ref": "g1", "subject_ref": "s1|null", "priority": "high|mid|low|null"
  }],
  "tasks": [{"id": "t1", "title": "...", "linked_hypothesis": "h1", "type": "discovery|delivery|infra", "priority": "high|mid|low"}],
  "blockers": [{"id": "b1", "reason": "...", "actions": "...", "owner": "...", "deadline": "..."}],
  "notes": ["..."],
  "links": [{"from": "..", "to": "..", "priority": "none|low|mid|high"}]
}
```

Выход
- JSON или YAML; валидировать базовую целостность ссылок (существование goal_ref/subject_ref/linked_hypothesis).
