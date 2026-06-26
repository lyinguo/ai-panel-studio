import { create } from "zustand";

const useStudioStore = create((set, get) => ({
  // ── 数据状态 ──
  discussionId: null,
  participants: [],
  messages: [],
  typingMessage: null,   // 正在流式生成中的消息
  consensus: { agreements: [], divergences: [] },
  guestStatuses: {},     // { participantId: "idle"|"thinking"|"speaking" }
  discussionStatus: "idle",
  topic: "",
  expertCount: 4,

  // ── chunk 缓冲（打字机平滑化） ──
  _pendingContent: "",

  // ── API ──

  setDiscussionId: (id) => set({ discussionId: id }),
  setTopic: (topic) => set({ topic }),
  setExpertCount: (count) => set({ expertCount: count }),

  setParticipants: (participants) => {
    const statuses = {};
    participants.forEach((p) => { statuses[p.id] = "idle"; });
    set({ participants, guestStatuses: statuses, messages: [], typingMessage: null, _pendingContent: "" });
  },

  setDiscussionStatus: (status) => set({ discussionStatus: status }),

  /** 更新嘉宾状态（thinking / speaking / idle） */
  updateGuestStatus: (participantId, status) =>
    set((state) => ({
      guestStatuses: { ...state.guestStatuses, [participantId]: status },
    })),

  /** 带缓冲的 typing 更新 — 遇标点或 30 字才刷新，不逐字蹦 */
  updateTypingContent: (data) => {
    const state = get();
    const p = state.participants.find((p) => p.id === data.participant_id);
    if (!p) return;

    const chunk = data.content || "";
    const pending = state._pendingContent + chunk;

    if (/[。.!?！？\n]/.test(chunk) || pending.length > 30) {
      const tm = state.typingMessage;
      const merged = (tm?.participant_id === data.participant_id ? tm.content : "") + pending;
      set({
        typingMessage: {
          participant_id: p.id,
          participant_name: p.name,
          role: p.role,
          title: p.title,
          color_code: p.color_code,
          content: merged,
        },
        _pendingContent: "",
      });
    } else {
      set({ _pendingContent: pending });
    }
  },

  /** 完成一条消息（is_final=true） */
  finalizeTyping: (data) =>
    set((state) => {
      const tm = state.typingMessage;
      if (!tm) return state;
      const full = tm.content + state._pendingContent;
      return {
        messages: [...state.messages, {
          id: data.message_id || Date.now(),
          participant_id: tm.participant_id,
          participant_name: tm.participant_name,
          role: tm.role,
          title: tm.title,
          content: full,
          color_code: tm.color_code,
          created_at: new Date().toISOString(),
        }],
        typingMessage: null,
        _pendingContent: "",
      };
    }),

  updateConsensus: (consensus) => set({ consensus: { ...consensus } }),

  resetDiscussion: () =>
    set({
      discussionId: null,
      messages: [],
      typingMessage: null,
      consensus: { agreements: [], divergences: [] },
      guestStatuses: {},
      discussionStatus: "idle",
      _pendingContent: "",
    }),
}));

export default useStudioStore;