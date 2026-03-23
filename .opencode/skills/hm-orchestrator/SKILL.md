---
name: hm-orchestrator
description: Пошаговый фасилитатор «Карты гипотез». Задает один вопрос за раз, ведет от цели к визуализации; сохраняет состояние, вызывает узкие HM‑модули, генерирует Mermaid (.mmd) как fallback.
---

# HM Orchestrator (OpenCode)

Что делает
- Ведет шаги: цель/метрики → субъекты → гипотезы → задачи → приоритизация → ревью → экспорт → визуализация.
- Один шаг — один ключевой вопрос; недостающее уточняет сам; сохраняет `.hm/session.json` и `.hm/map.json`.
- Визуализация: fallback — `hm/map.mmd` по скрипту `skills/hm-orchestrator/scripts/hm_map_to_mermaid.py`.

Как использовать
- Запусти оркестрацию и следуй вопросам; на каждом шаге доступны: [Далее] [Уточнить] [Исправить N] [Стоп].
- Можно перепрыгивать по этапам по новой вводной пользователя.

Интеграции
- Узкие модули: `hm-goal-metrics`, `hm-subject-motivation`, `hm-hypothesis-builder`, `hm-task-linker`, `hm-prioritization`, `hm-review-troubleshooter`, `hm-json-export`.
- Поздние стадии: MCP для Miro/Holst (опционально). Цвета — согласно стандарту.
