import { create } from "zustand";
import { PARTICIPANTS, MOCK_EVENTS } from "../data/mock";

const initialStatuses = {};
PARTICIPANTS.forEach((p) => {
  initialStatuses[p.id] = "idle";
});

const useStudioStore = create((set, get) => ({
  // ── 状态 ──
  participants: PARTICIPANTS,
  messages: [],
  consensus: { agreements: [], divergences: [] },
  guestStatuses: initialStatuses,
  discussionStatus: "idle", // idle | in_progress | completed
  round: 0,
  activeSpeakerId: null,

  // ── 操作 ──

  /** 添加一条消息 */
  addMessage: (msg) =>
    set((state) => ({
      messages: [...state.messages, { id: Date.now(), ...msg }],
    })),

  /** 更新参与者状态 */
  updateGuestStatus: (participantId, status) =>
    set((state) => ({
      guestStatuses: { ...state.guestStatuses, [participantId]: status },
      activeSpeakerId:
        status === "speaking" ? participantId : state.activeSpeakerId,
    })),

  /** 更新共识 */
  updateConsensus: (consensus) =>
    set({ consensus: { ...consensus } }),

  /** 设置讨论状态 */
  setDiscussionStatus: (status) => set({ discussionStatus: status }),

  /** 设置当前轮次 */
  setRound: (round) => set({ round }),

  /** 启动模拟讨论（播放 Mock 事件序列） */
  startDiscussion: () => {
    const state = get();
    if (state.discussionStatus === "in_progress") return;

    set({ discussionStatus: "in_progress", messages: [], consensus: { agreements: [], divergences: [] } });

    let totalDelay = 0;
    let msgAccum = "";

    MOCK_EVENTS.forEach((evt) => {
      totalDelay += evt.delay;

      setTimeout(() => {
        const store = get();

        if (evt.type === "guest_status_change") {
          store.updateGuestStatus(
            evt.data.participant_id,
            evt.data.status
          );
        } else if (evt.type === "message_chunk" && evt.data.is_final) {
          const participant = store.participants.find(
            (p) => p.id === evt.data.participant_id
          );
          if (participant) {
            store.addMessage({
              participant_id: evt.data.participant_id,
              participant_name: participant.name,
              role: participant.role,
              title: participant.title,
              content: evt.data.content,
              color_code: participant.color_code,
              created_at: evt.data.timestamp || new Date().toISOString(),
            });
          }
        } else if (evt.type === "consensus_update") {
          store.updateConsensus(evt.data);
        }
      }, totalDelay);
    });

    // 最后标记讨论结束
    const finalDelay = totalDelay + 1500;
    setTimeout(() => {
      set({ discussionStatus: "completed" });
    }, finalDelay);
  },

  /** 重置讨论 */
  resetDiscussion: () =>
    set({
      messages: [],
      consensus: { agreements: [], divergences: [] },
      guestStatuses: initialStatuses,
      discussionStatus: "idle",
      round: 0,
      activeSpeakerId: null,
    }),
}));

export default useStudioStore;