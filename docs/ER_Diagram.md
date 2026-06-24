# ER 图 — AI 圆桌讨论

> 底层原则：**多个独立讨论并发，各自状态、事件流、数据严格互不干扰。**
> 所有核心表以 `discussion_id` 作为隔离外键，查询必须强制携带讨论归属过滤。

---

## 实体关系总览

```
┌─────────────────────────────────────────────────────────┐
│                     discussions                          │
├─────────────────────────────────────────────────────────┤
│  id            (PK)       Integer                        │
│  topic                    String(200)    ← 用户输入      │
│  expert_count             Integer        ← 用户输入      │
│  status                   String(20)     pending/...     │
│  created_at               DateTime                       │
└──────────┬────────────────────────────────────┬──────────┘
           │ 1                                  │ 1
           │                                    │
           ▼                                    ▼
┌──────────────────┐         ┌──────────────────────────────┐
│   participants    │         │         consensus            │
├──────────────────┤         ├──────────────────────────────┤
│  id          (PK)│         │  id              (PK)        │
│  discussion_id   │◄────┐   │  discussion_id   (FK,UNIQUE) │◄─ 1:1
│  role             │    │   │  agreements       Text(JSON)  │
│  name             │    │   │  divergences      Text(JSON)  │
│  title            │    │   │  updated_at       DateTime    │
│  stance           │    │   └──────────────────────────────┘
│  color_code       │    │
│  order            │    │
│  created_at       │    │
└──────────┬────────┘    │
           │ 1           │
           │             │
           ▼             │
┌──────────────────┐     │
│    messages       │     │
├──────────────────┤     │
│  id          (PK)│     │
│  discussion_id   │─────┘
│  participant_id  │
│  content          │
│  created_at       │
└──────────────────┘

FK = Foreign Key | UNIQUE = Unique Constraint | 1:1 = one-to-one
```

---

## 表定义

### discussions

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | `Integer` | PK, Auto Increment | 全局唯一讨论 ID |
| topic | `String(200)` | NOT NULL | 用户输入的讨论话题 |
| expert_count | `Integer` | NOT NULL, DEFAULT 4 | 用户指定的专家人数 |
| status | `String(20)` | NOT NULL, DEFAULT 'pending' | `pending` / `in_progress` / `completed` |
| created_at | `DateTime` | NOT NULL | 创建时间（UTC） |

### participants

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | `Integer` | PK, Auto Increment | |
| discussion_id | `Integer` | FK → discussions.id, NOT NULL, INDEX | 隔离外键 |
| role | `String(10)` | NOT NULL | `host`（主持人）或 `expert`（专家） |
| name | `String(50)` | NOT NULL | AI 生成的姓名 |
| title | `String(100)` | NOT NULL | AI 生成的职业/Title |
| stance | `Text` | NOT NULL | AI 生成的核心立场描述 |
| color_code | `String(7)` | NOT NULL | UI 专属颜色标识 |
| order | `Integer` | NOT NULL, DEFAULT 0 | 显示排序（主持人 = 0） |
| created_at | `DateTime` | NOT NULL | |

### messages

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | `Integer` | PK, Auto Increment | 全局唯一 |
| discussion_id | `Integer` | FK → discussions.id, NOT NULL, INDEX | 隔离外键 |
| participant_id | `Integer` | FK → participants.id, NOT NULL, INDEX | 发言人 |
| content | `Text` | NOT NULL | 发言完整内容 |
| created_at | `DateTime` | NOT NULL | |

> **查询规范**：所有消息查询必须 `ORDER BY id ASC`，确保绝对时序。

### consensus

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | `Integer` | PK, Auto Increment | |
| discussion_id | `Integer` | FK → discussions.id, **UNIQUE**, NOT NULL, INDEX | 1:1 数据库级硬约束 |
| agreements | `Text` | NOT NULL, DEFAULT '[]' | 共识要点列表（JSON Array） |
| divergences | `Text` | NOT NULL, DEFAULT '[]' | 分歧要点列表（JSON Array） |
| updated_at | `DateTime` | NOT NULL | |

---

## 表关系总结

| 左表 | 关系 | 右表 | 约束 |
|---|---|---|---|
| `discussions` | **1 : N** | `participants` | `discussion_id` FK |
| `discussions` | **1 : N** | `messages` | `discussion_id` FK |
| `discussions` | **1 : 1** | `consensus` | `discussion_id` FK + **UNIQUE** |

---

## 隔离原则

```
-- ✅ 正确：所有查询强制按讨论过滤
SELECT * FROM messages
WHERE discussion_id = ?          -- 必须！
ORDER BY id ASC;

-- ❌ 错误：未带 discussion_id 过滤
SELECT * FROM messages;          -- 泄漏其他讨论数据
```
