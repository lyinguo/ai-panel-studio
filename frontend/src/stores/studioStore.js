import { create } from "zustand";

const defaultStatuses = {};

const useStudioStore = create((set, get) => ({
  // ── 核心状态 ──
  discussionId: null,
  participants: [],
  messages: [],
  typingMessage: null, // { participant_id, participant_name, role, title, color_code, content }
  consensus: { agreements: [], divergences: [] },
  guestStatuses: {},
  discussionStatus: "idle", // idle | in_progress | completed
  topic: "",
  expertCount: 4,

  // ── SSE 驱动操作 ──

  setDiscussionId: (id) => set({ discussionId: id }),

  setTopic: (topic) => set({ topic }),

  setExpertCount: (count) => set({ expertCount: count }),

  setParticipants: (participants) => {
    const statuses = {};
    participants.forEach((p) => {
      statuses[p.id] = "idle";
    });
    set({ participants, guestStatuses: statuses, messages: [], typingMessage: null });
  },

  setDiscussionStatus: (status) => set({ discussionStatus: status }),

  /** 更新嘉宾实时状态 */
  updateGuestStatus: (participantId, status) =>
    set((state) => ({
      guestStatuses: { ...state.guestStatuses, [participantId]: status },
      activeSpeakerId: status === "speaking" ? participantId : state.activeSpeakerId,
    })),

  /** 追加 typing 消息内容 */
  updateTypingContent: (data) =>
    set((state) => {
      const participant = state.participants.find((p) => p.id === data.participant_id);
      if (!participant) return state;

      const existing = state.typingMessage;
      if (existing && existing.participant_id === data.participant_id) {
        return {
          typingMessage: {
            ...existing,
            content: existing.content + data.content,
          },
        };
      }
      return {
        typingMessage: {
          participant_id: participant.id,
          participant_name: participant.name,
          role: participant.role,
          title: participant.title,
          color_code: participant.color_code,
          content: data.content || "",
        },
      };
    }),

  /** 完成一条消息（is_final=true），移入 messages 数组 */
  finalizeTyping: (data) =>
    set((state) => {
      const tm = state.typingMessage;
      if (!tm) return state;

      const newMsg = {
        id: data.message_id || Date.now(),
        participant_id: tm.participant_id,
        participant_name: tm.participant_name,
        role: tm.role,
        title: tm.title,
        content: tm.content,
        color_code: tm.color_code,
        created_at: new Date().toISOString(),
      };

      return {
        messages: [...state.messages, newMsg],
        typingMessage: null,
      };
    }),

  /** 更新共识 */
  updateConsensus: (consensus) => set({ consensus: { ...consensus } }),

  /** 添加一条完整消息（模拟模式使用） */
  addMessage: (msg) =>
    set((state) => ({
      messages: [...state.messages, { id: Date.now(), ...msg }],
    })),

  /** 重置 */
  resetDiscussion: () =>
    set({
      discussionId: null,
      messages: [],
      typingMessage: null,
      consensus: { agreements: [], divergences: [] },
      guestStatuses: {},
      discussionStatus: "idle",
    }),
}));

export default useStudioStore;