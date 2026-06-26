import { useEffect, useRef, useCallback } from "react";
import useStudioStore from "../stores/studioStore";

const SSE_URL = "http://localhost:8000";

/**
 * useDiscussionStream(discussionId)
 *
 * 连接 SSE 事件流并自动更新 Zustand Store。
 * 传入 null 则跳过连接（用于已结束讨论的历史回放模式）。
 */
export default function useDiscussionStream(discussionId) {
  const esRef = useRef(null);
  const retryTimer = useRef(null);
  const mountedRef = useRef(true);

  const {
    setDiscussionStatus,
    updateGuestStatus,
    updateTypingContent,
    finalizeTyping,
    updateConsensus,
  } = useStudioStore();

  const connect = useCallback(() => {
    if (!discussionId || !mountedRef.current) return;

    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    const es = new EventSource(`${SSE_URL}/api/discussions/${discussionId}/events`);
    esRef.current = es;

    es.addEventListener("guest_status_change", (e) => {
      if (!mountedRef.current) return;
      try { updateGuestStatus(JSON.parse(e.data).participant_id, JSON.parse(e.data).status); }
      catch (_) {}
    });

    es.addEventListener("message_chunk", (e) => {
      if (!mountedRef.current) return;
      try {
        const d = JSON.parse(e.data);
        if (d.is_final) finalizeTyping(d);
        else updateTypingContent(d);
      } catch (_) {}
    });

    es.addEventListener("consensus_update", (e) => {
      if (!mountedRef.current) return;
      try { updateConsensus(JSON.parse(e.data)); }
      catch (_) {}
    });

    es.addEventListener("discussion_status", (e) => {
      if (!mountedRef.current) return;
      try {
        const d = JSON.parse(e.data);
        if (d.status === "completed") setDiscussionStatus("completed");
        if (d.status === "in_progress") setDiscussionStatus("in_progress");
      } catch (_) {}
    });

    // 终场总结（暂未在前端展示，预留事件解析）
    es.addEventListener("discussion_summary", (e) => {
      if (!mountedRef.current) return;
      try { const d = JSON.parse(e.data); console.log("Summary:", d.summary); }
      catch (_) {}
    });

    es.onerror = () => {
      if (!mountedRef.current) return;
      es.close();
      esRef.current = null;
      retryTimer.current = setTimeout(() => {
        if (mountedRef.current) connect();
      }, 3000);
    };
  }, [discussionId, updateGuestStatus, updateTypingContent, finalizeTyping, updateConsensus, setDiscussionStatus]);

  useEffect(() => {
    mountedRef.current = true;

    // 只在 discussionId 有效时连接（null = 历史回放模式，不需要 SSE）
    if (discussionId) connect();

    return () => {
      mountedRef.current = false;
      if (retryTimer.current) clearTimeout(retryTimer.current);
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [discussionId, connect]);
}

export { useDiscussionStream };