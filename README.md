# AI Panel Studio — 智能圆桌讨论系统

一个基于 **FastAPI + React + DeepSeek LLM** 的 AI 圆桌讨论平台。  
用户输入话题和专家人数，系统自动生成多位 AI 专家进行实时辩论，并通过 **SSE 流** 向前端推送直播级字幕。

---

## ✨ 核心特性

- **AI 自动组局** — 输入话题和人数，LLM 动态生成主持人 + 多领域专家
- **流式辩论直播** — SSE 推送三事件：状态变更 → 文本块 → 共识提炼
- **直播级字幕** — 纯文本无 Markdown，打字机效果实时滚动
- **动态共识看板** — 讨论过程中实时提炼共识与分歧
- **多讨论隔离** — 每个讨论拥有独立状态、事件流、数据，严格互不干扰

---

## 🏗 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+ · FastAPI · SQLAlchemy · SQLite · SSE-Starlette |
| 前端 | React 18 · Vite · Zustand · EventSource (SSE) |
| AI | DeepSeek API (OpenAI 兼容接口) |
| 测试 | Pytest + Pytest-asyncio · Playwright (E2E) |

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 创建 conda 虚拟环境
conda create -n ai-panel-studio python=3.11 -y

# 激活环境并安装依赖
conda activate ai-panel-studio
cd backend
pip install -r requirements.txt
```

### 2. 配置 API 密钥

复制 `.env.example` 为 `.env`，填入你的 DeepSeek API Key：

```bash
cp .env.example .env
# 编辑 .env 文件：
# DEEPSEEK_API_KEY=sk-your_key_here
```

> 没有 API Key？系统会自动使用**兜底数据**运行，可正常体验完整 UI 和交互流程。

### 3. 一键启动

双点击根目录的 **`start.bat`**：

```
start.bat
```

脚本会自动：
1. ✅ 激活 `ai-panel-studio` conda 环境
2. ✅ 启动后端 FastAPI（端口 8000）
3. ✅ 安装前端依赖（如果缺少）
4. ✅ 启动前端 Vite（端口 5173）
5. ✅ 自动打开浏览器

或者手动分步启动：

```bash
# 终端 1 — 后端
conda activate ai-panel-studio
cd backend
uvicorn app.main:app --reload --port 8000

# 终端 2 — 前端
cd frontend
npm install
npm run dev
```

打开浏览器访问 **http://localhost:5173** 即可。

---

## 🧪 运行测试

```bash
# 后端单元测试（TDD 绿灯）
conda activate ai-panel-studio
cd backend
pytest tests/ -v

# E2E 端到端测试（需先启动前后端服务）
cd e2e
npm install
npx playwright test
```

---

## 📁 项目结构

```
ai-panel-studio/
├── README.md                    ← 本文件
├── start.bat                    ← 一键启动脚本
├── .env.example                 ← API 配置模板
│
├── backend/                     ← FastAPI 后端
│   ├── app/
│   │   ├── main.py              ← 应用入口 + 路由注册
│   │   ├── models.py            ← SQLAlchemy 数据模型
│   │   ├── api/discussions.py   ← API 路由（REST + SSE）
│   │   ├── core/config.py       ← 环境配置
│   │   ├── db/                  ← 数据库连接
│   │   ├── schemas/api.py       ← Pydantic 请求/响应模型
│   │   └── services/
│   │       ├── llm_service.py   ← LLM 调用（含 think 标签拦截器）
│   │       ├── discussion_engine.py  ← 讨论调度引擎
│   │       └── event_bus.py     ← SSE 事件总线（讨论隔离）
│   └── tests/                   ← Pytest 单元测试
│
├── frontend/                    ← React + Vite 前端
│   └── src/
│       ├── hooks/useDiscussion.js   ← SSE 连接 Hook
│       ├── stores/studioStore.js    ← Zustand 全局状态
│       ├── components/              ← UI 组件
│       │   ├── GuestCard.jsx        ← 嘉宾卡片
│       │   ├── GuestPanel.jsx       ← 嘉宾席面板
│       │   ├── Transcript.jsx       ← 主舞台字幕
│       │   ├── MessageBubble.jsx    ← 消息气泡
│       │   └── ConsensusPanel.jsx   ← 共识面板
│       └── pages/Studio.jsx         ← 演播厅主页面
│
├── docs/
│   ├── API_Contract.md          ← API 契约文档
│   └── ER_Diagram.md            ← ER 图文档
│
├── e2e/                         ← Playwright E2E 测试
│   └── tests/discussion.spec.js
│
└── backend/README_ARCHITECTURE.md  ← 架构核心原则
```

---

## 📡 SSE 事件流

| 事件类型 | 用途 | 前端消费 |
|---|---|---|
| `guest_status_change` | 参与者状态变更 | 嘉宾卡状态指示器 |
| `message_chunk` | 流式文本输出 | 主舞台打字机字幕 |
| `consensus_update` | 共识动态提炼 | 侧边栏共识面板 |

---

## 🧠 架构原则

> **多个独立讨论并发，各自状态、事件流、数据严格互不干扰。**

详情见 [backend/README_ARCHITECTURE.md](backend/README_ARCHITECTURE.md)

---

## 📜 许可

MIT License
