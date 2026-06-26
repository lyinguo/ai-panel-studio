import { useEffect, useRef, useCallback } from "react";
import useStudioStore from "../stores/studioStore";

const SSE_URL = "http://localhost:8000";

/**
 * useDiscussionStream(discussionId)
 *
 * 职责（单一）：
 * 1. 通过 discussionId 连接 SSE 事件流
 * 2. 断线自动重连（EventSource 内置 + 手动兜底）
 * 3. 解析 4 种 SSE 事件并写入 Zustand Store
 * 4. 组件卸载时断开
 *
 * 页面组件只负责拿 store 的数据渲染，不感知任何 SSE 逻辑。
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
    addMessage,
  } = useStudioStore();

  const connect = useCallback(() => {
    if (!discussionId || !mountedRef.current) return;

    // 清理旧连接
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    const es = new EventSource(`${SSE_URL}/api/discussions/${discussionId}/events`);
    esRef.current = es;

    // ── 4 种事件处理器 ──

    es.addEventListener("guest_status_change", (e) => {
      if (!mountedRef.current) return;
      try {
        const d = JSON.parse(e.data);
        updateGuestStatus(d.participant_id, d.status);
      } catch (_) {}
    });

    es.addEventListener("message_chunk", (e) => {
      if (!mountedRef.current) return;
      try {
        const d = JSON.parse(e.data);
        if (d.is_final) {
          finalizeTyping(d);
        } else {
          updateTypingContent(d);
        }
      } catch (_) {}
    });

    es.addEventListener("consensus_update", (e) => {
      if (!mountedRef.current) return;
      try {
        updateConsensus(JSON.parse(e.data));
      } catch (_) {}
    });

    es.addEventListener("discussion_status", (e) => {
      if (!mountedRef.current) return;
      try {
        const d = JSON.parse(e.data);
        if (d.status === "completed") setDiscussionStatus("completed");
        if (d.status === "in_progress") setDiscussionStatus("in_progress");
      } catch (_) {}
    });

    // ── 断线重连 ──
    es.onerror = () => {
      if (!mountedRef.current) return;
      es.close();
      esRef.current = null;
      // 3 秒后重试
      retryTimer.current = setTimeout(() => {
        if (mountedRef.current) connect();
      }, 3000);
    };
  }, [discussionId, updateGuestStatus, updateTypingContent, finalizeTyping, updateConsensus, setDiscussionStatus]);

  // 连接 / 断连
  useEffect(() => {
    mountedRef.current = true;
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
