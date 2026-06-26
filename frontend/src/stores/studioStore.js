import { create } from "zustand";

const useStudioStore = create((set, get) => ({
  // ── 核心状态 ──
  discussionId: null,
  participants: [],
  messages: [],
  typingMessage: null,
  consensus: { agreements: [], divergences: [] },
  guestStatuses: {},
  discussionStatus: "idle",
  topic: "",
  expertCount: 4,
  round: 0,

  // ── chunk 缓冲（用于平滑流式显示） ──
  _chunkTimer: null,
  _pendingContent: "",

  setDiscussionId: (id) => set({ discussionId: id }),
  setTopic: (topic) => set({ topic }),
  setExpertCount: (count) => set({ expertCount: count }),
  setRound: (round) => set({ round }),

  setParticipants: (participants) => {
    const statuses = {};
    participants.forEach((p) => { statuses[p.id] = "idle"; });
    set({ participants, guestStatuses: statuses, messages: [], typingMessage: null, _pendingContent: "" });
  },

  setDiscussionStatus: (status) => set({ discussionStatus: status }),

  updateGuestStatus: (participantId, status) =>
    set((state) => ({
      guestStatuses: { ...state.guestStatuses, [participantId]: status },
      activeSpeakerId: status === "speaking" ? participantId : state.activeSpeakerId,
    })),

  /** 带缓冲的 typing 内容更新 — chunk 级平滑 */
  updateTypingContent: (data) => {
    const state = get();
    const participant = state.participants.find((p) => p.id === data.participant_id);
    if (!participant) return;

    const chunk = data.content || "";
    const pending = state._pendingContent + chunk;

    // 有标点或累积超过 30 字 → 立即刷新
    if (/[。.!?！？\n]/.test(chunk) || pending.length > 30) {
      const existing = state.typingMessage;
      const newContent = (existing?.participant_id === data.participant_id ? existing.content : "") + pending;
      set({
        typingMessage: {
          participant_id: participant.id,
          participant_name: participant.name,
          role: participant.role,
          title: participant.title,
          color_code: participant.color_code,
          content: newContent,
        },
        _pendingContent: "",
      });
    } else {
      set({ _pendingContent: pending });
    }
  },

  /** 完成一条消息 */
  finalizeTyping: (data) =>
    set((state) => {
      const tm = state.typingMessage;
      if (!tm) return state;
      const fullContent = tm.content + state._pendingContent;
      const newMsg = {
        id: data.message_id || Date.now(),
        participant_id: tm.participant_id,
        participant_name: tm.participant_name,
        role: tm.role,
        title: tm.title,
        content: fullContent,
        color_code: tm.color_code,
        created_at: new Date().toISOString(),
      };
      return {
        messages: [...state.messages, newMsg],
        typingMessage: null,
        _pendingContent: "",
      };
    }),

  updateConsensus: (consensus) => set({ consensus: { ...consensus } }),

  addMessage: (msg) =>
    set((state) => ({
      messages: [...state.messages, { id: Date.now(), ...msg }],
    })),

  resetDiscussion: () =>
    set({
      discussionId: null,
      messages: [],
      typingMessage: null,
      consensus: { agreements: [], divergences: [] },
      guestStatuses: {},
      discussionStatus: "idle",
      round: 0,
      _pendingContent: "",
    }),
}));

export default useStudioStore;
