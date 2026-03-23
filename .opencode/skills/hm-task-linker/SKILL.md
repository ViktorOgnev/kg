---
name: hm-task-linker
description: Генерируй и привязывай задачи к веткам гипотез. Не допускай «висящих» задач; предлагай группировки/портфель.
---

# HM Task Linker (OpenCode)

Что делать
- Превращать гипотезы в проверочные/реализационные задачи с жёсткой привязкой к ветке.
- Давать тип (discovery|delivery|infra), предварительный приоритет и критерии результата.

Форматы
- Текст и/или JSON: tasks[{title, linked_hypothesis, goal_ref, subject_ref, type, priority}].
