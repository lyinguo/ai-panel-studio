// ============================================================
// AI Panel Studio — TypeScript 类型定义（与后端 API 契约同步）
// 数据模型对应 SQLAlchemy 实体定义
// ============================================================

// ---------- 枚举常量 ----------

/** 讨论状态 */
export type DiscussionStatus = "pending" | "in_progress" | "completed";

/** 参与者角色 */
export type ParticipantRole = "host" | "expert";

/** 参与者实时状态（仅 SSE 事件中使用） */
export type GuestStatus = "thinking" | "speaking" | "idle";

// ---------- 核心实体 ----------

/** 讨论组 */
export interface Discussion {
  id: number;
  topic: string;
  expert_count: number;
  status: DiscussionStatus;
  created_at: string; // ISO 8601
}

/** 讨论列表项（列表页用） */
export interface DiscussionListItem {
  id: number;
  topic: string;
  status: DiscussionStatus;
  participant_count: number;
  created_at: string;
}

/** 参与者（AI 生成） */
export interface Participant {
  id: number;
  role: ParticipantRole;
  name: string;
  title: string;
  stance: string;
  color_code: string;
  order: number;
}

/** 消息记录 */
export interface Message {
  id: number;
  participant_id: number;
  participant_name: string;
  role: ParticipantRole;
  content: string;
  color_code: string;
  created_at: string;
}

/** 动态共识 */
export interface Consensus {
  agreements: string[];
  divergences: string[];
  updated_at: string;
}

// ---------- API 请求 / 响应 ----------

/** POST /api/discussions 请求体 */
export interface CreateDiscussionRequest {
  topic: string;
  expert_count: number; // 1~8，默认 4
}

/** POST /api/discussions 响应 */
export interface CreateDiscussionResponse {
  discussion_id: number;
  participants: Participant[];
}

/** GET /api/discussions/{id} 响应 */
export interface DiscussionDetailResponse extends Discussion {
  participants: Participant[];
}

/** GET /api/discussions/{id}/messages 查询参数 */
export interface MessagesQueryParams {
  before_id?: number;
  limit?: number; // 默认 50
}

// ---------- SSE 事件类型 ----------

/** SSE 事件: 参与者状态变更 */
export interface GuestStatusChangeEvent {
  event: "guest_status_change";
  data: {
    participant_id: number;
    status: GuestStatus;
    timestamp: string;
  };
}

/** SSE 事件: 文本流式输出 */
export interface MessageChunkEvent {
  event: "message_chunk";
  data: {
    participant_id: number;
    chunk_index: number;
    content: string;
    is_final: boolean;
    message_id?: number; // is_final=true 时携带
  };
}

/** SSE 事件: 共识动态更新 */
export interface ConsensusUpdateEvent {
  event: "consensus_update";
  data: {
    agreements: string[];
    divergences: string[];
    updated_at: string;
  };
}

/** SSE 联合事件类型 */
export type SSEEvent =
  | GuestStatusChangeEvent
  | MessageChunkEvent
  | ConsensusUpdateEvent;
