# API 契约 — AI 圆桌讨论

> 对应数据模型定义见 [backend/app/models.py](../backend/app/models.py)
> TypeScript 类型见 [frontend/src/types/api.ts](../frontend/src/types/api.ts)

---

## 基础信息

| 项目 | 值 |
|---|---|
| Base URL | `http://localhost:8000` |
| 协议 | HTTP / SSE (text/event-stream) |
| 数据格式 | JSON（请求 & 响应） |
| 数据库 | SQLite |

---

## 端点清单

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/discussions` | 创建讨论（AI 自动生成参与者） |
| GET | `/api/discussions` | 获取讨论列表 |
| GET | `/api/discussions/{id}` | 获取讨论详情 + 参与者 |
| GET | `/api/discussions/{id}/messages` | 获取历史消息（重连时拉取） |
| GET | `/api/discussions/{id}/events` | **SSE 事件流（核心接口）** |

---

## ① POST /api/discussions — 创建讨论

**请求体：**

```json
{
  "topic": "AGI 是否应该暂停研发",
  "expert_count": 4
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `topic` | string | ✅ | 讨论话题，长度 1~200 |
| `expert_count` | integer | ❌ | 专家人数，默认 4，范围 1~8 |

**响应 200：**

```json
{
  "discussion_id": 1,
  "participants": [
    {
      "id": 1,
      "role": "host",
      "name": "张明",
      "title": "AI 伦理与治理专家",
      "stance": "持中立立场，擅长引导各方观点碰撞，确保讨论深入且有序…",
      "color_code": "#4A90D9",
      "order": 0
    },
    {
      "id": 2,
      "role": "expert",
      "name": "李薇",
      "title": "资深机器学习研究员",
      "stance": "认为技术中立，关键在于应用场景和监管框架的完善…",
      "color_code": "#FF6B6B",
      "order": 1
    }
  ]
}
```

---

## ② GET /api/discussions — 讨论列表

**响应 200：**

```json
[
  {
    "id": 1,
    "topic": "AGI 是否应该暂停研发",
    "status": "in_progress",
    "participant_count": 5,
    "created_at": "2026-06-24T10:00:00Z"
  },
  {
    "id": 2,
    "topic": "低代码平台是否会取代传统开发",
    "status": "pending",
    "participant_count": 4,
    "created_at": "2026-06-24T11:00:00Z"
  }
]
```

---

## ③ GET /api/discussions/{id} — 讨论详情

**响应 200：**

```json
{
  "id": 1,
  "topic": "AGI 是否应该暂停研发",
  "expert_count": 4,
  "status": "in_progress",
  "created_at": "2026-06-24T10:00:00Z",
  "participants": [
    {
      "id": 1,
      "role": "host",
      "name": "张明",
      "title": "AI 伦理与治理专家",
      "stance": "持中立立场…",
      "color_code": "#4A90D9",
      "order": 0
    }
  ]
}
```

---

## ④ GET /api/discussions/{id}/messages — 历史消息

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `before_id` | integer | ❌ | 上次看到的最新消息 ID（用于分页） |
| `limit` | integer | ❌ | 返回条数，默认 50，最大 200 |

**响应 200（按 `id ASC` 排序，保证绝对时序）：**

```json
[
  {
    "id": 42,
    "participant_id": 3,
    "participant_name": "王磊",
    "role": "expert",
    "content": "我认为从技术发展规律来看，AGI 的出现是必然的…",
    "color_code": "#FF6B6B",
    "created_at": "2026-06-24T10:05:00Z"
  }
]
```

---

## ⑤ GET /api/discussions/{id}/events — SSE 事件流 ⭐

**连接信息：**

| 项 | 值 |
|---|---|
| URL | `GET /api/discussions/{id}/events` |
| Content-Type | `text/event-stream` |
| Cache-Control | `no-cache` |
| Connection | `keep-alive` |

### 事件 A: guest_status_change — 参与者状态变更

参与者（主持人/专家）的实时状态发生转变时推送。

```json
event: guest_status_change
data: {
  "participant_id": 2,
  "status": "speaking",
  "timestamp": "2026-06-24T10:05:00Z"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `participant_id` | integer | 参与者的 ID |
| `status` | string | `"thinking"` / `"speaking"` / `"idle"` |
| `timestamp` | string (ISO 8601) | 事件发生时间 |

### 事件 B: message_chunk — 文本流式输出

AI 发言的流式文本片段，每次推送一个 `chunk`。

```json
event: message_chunk
data: {
  "participant_id": 2,
  "chunk_index": 0,
  "content": "我认为从技",
  "is_final": false
}
```

```json
event: message_chunk
data: {
  "participant_id": 2,
  "chunk_index": 12,
  "content": "这是不可忽视的历史趋势。",
  "is_final": true,
  "message_id": 42
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `participant_id` | integer | 发言者的 ID |
| `chunk_index` | integer | 从 0 开始递增的序号 |
| `content` | string | 本次推送的文本片段 |
| `is_final` | boolean | 是否为最后一片段 |
| `message_id` | integer | 仅 `is_final=true` 时携带，消息写入 DB 后的 ID |

### 事件 C: consensus_update — 共识动态更新

讨论过程中，AI 实时总结共识与分歧变化时推送。

```json
event: consensus_update
data: {
  "agreements": [
    "AGI 发展需要建立全球监管框架",
    "研究透明度是安全发展的前提"
  ],
  "divergences": [
    "暂停研发 vs 渐进式推进的时间表分歧",
    "开源 vs 闭源的治理路径分歧"
  ],
  "updated_at": "2026-06-24T10:12:00Z"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `agreements` | string[] | 已达成的共识要点列表 |
| `divergences` | string[] | 仍存在的分歧要点列表 |
| `updated_at` | string (ISO 8601) | 共识更新时间 |

---

## SSE 事件流生命周期

```
Timeline →
────────────────────────────────────────────────────────────────────────

  [guest_status_change]  participant:1 → "speaking"    ← 主持人开始发言
       │
  [message_chunk]        chunk_0 → chunk_1 → ... → chunk_N (is_final)
       │
  [guest_status_change]  participant:1 → "thinking"    ← 主持人转思考
  [guest_status_change]  participant:2 → "speaking"    ← 专家 1 开始发言
       │
  [message_chunk]        chunk_0 → ... → chunk_M (is_final)
       │
  [consensus_update]     agreements: [...] / divergences: [...]
       │
  [guest_status_change]  participant:2 → "idle"
       │
  ─── 循环：下一位专家发言 / 主持人总结 / 共识更新 ───
       │
  [guest_status_change]  participant:1 → "speaking"    ← 主持人最终总结
  [consensus_update]     最终共识版本
  [Discussion]           status → "completed"
```

---

## 状态码表

| 状态码 | 说明 |
|---|---|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误（topic 为空 / expert_count 超范围） |
| 404 | 讨论不存在 |
| 409 | 讨论已结束（拒绝新操作） |
| 500 | 服务端错误 |

---

## 错误响应格式

```json
{
  "detail": "具体错误信息"
}
```