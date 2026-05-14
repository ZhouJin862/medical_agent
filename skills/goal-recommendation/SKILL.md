---
name: goal-recommendation
description: 健康目标推荐。根据人群分类、异常指标、症状，从目标池中推荐 3-4 个最适合的健康目标。
tags: [目标推荐, 运动目标, 健康管理, goal, recommendation]
tools:
  - script: scripts/goal_recommender.py
    args: ["--input", "$input", "--mode", "skill"]
---

# 健康目标推荐

从输入的目标池中挑选 3-4 个最适合用户的目标，按优先级排序。

## 规则

1. 只能从 goal_pool 中选择，禁止自创
2. 重症/高危人群不推荐高强度目标（如力量训练）
3. 优先选择与用户健康问题直接相关的目标

## 输出格式

严格输出 JSON，不要任何额外文字：

```json
{"recommended_goals": [{"value": "xxx", "label": "xxx", "icon": "xxx", "reason": "推荐理由(≤15字)"}]}
```
