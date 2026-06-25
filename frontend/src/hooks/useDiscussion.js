import { useCallback, useEffect, useRef } from "react";
import useStudioStore from "../stores/studioStore";

const SSE_URL = "http://localhost:8000";
const API_URL = "http://localhost:8000";

/**
 * useDiscussion — SSE 事件流连接与管理 Hook
 *
 * 职责：
 * 1. POST /api/discussions 创建讨论
 * 2. EventSource 连接 SSE /api/discussions/{id}/events
 * 3. 将三种事件分派到 Zustand Store
 * 4. 自动重连 & 清理
 */
export default function useDiscussion() {
  const esRef = useRef(null);
  const discussionIdRef = useRef(null);

  const {
    setDiscussionId,
    setDiscussionStatus,
    setParticipants,
    updateGuestStatus,
    updateTypingContent,
    finalizeTyping,
    updateConsensus,
    addMessage,
  } = useStudioStore();

  /** 创建讨论并连接 SSE */
  const startDiscussion = useCallback(
    async (topic, expertCount = 4) => {
      // 1. POST 创建讨论
      let discussionId;
      try {
        const resp = await fetch(`${API_URL}/api/discussions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic, expert_count: expertCount }),
        });
        if (!resp.ok) throw new Error(`创建失败: ${resp.status}`);
        const data = await resp.json();
        discussionId = data.discussion_id;
        discussionIdRef.current = discussionId;
        setDiscussionId(discussionId);
        setParticipants(data.participants);
        setDiscussionStatus("in_progress");
      } catch (err) {
        console.error("创建讨论失败:", err);
        setDiscussionStatus("idle");
        return;
      }

      // 2. 连接 SSE
      if (esRef.current) {
        esRef.current.close();
      }

      const es = new EventSource(`${SSE_URL}/api/discussions/${discussionId}/events`);
      esRef.current = es;

      es.addEventListener("guest_status_change", (e) => {
        try {
          const data = JSON.parse(e.data);
          updateGuestStatus(data.participant_id, data.status);
        } catch (err) {
          console.error("guest_status_change 解析失败:", err);
        }
      });

      es.addEventListener("message_chunk", (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.is_final) {
            finalizeTyping(data);
          } else {
            updateTypingContent(data);
          }
        } catch (err) {
          console.error("message_chunk 解析失败:", err);
        }
      });

      es.addEventListener("consensus_update", (e) => {
        try {
          const data = JSON.parse(e.data);
          updateConsensus(data);
        } catch (err) {
          console.error("consensus_update 解析失败:", err);
        }
      });

      es.addEventListener("discussion_status", (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.status === "completed") {
            setDiscussionStatus("completed");
          }
        } catch (err) {
          console.error("discussion_status 解析失败:", err);
        }
      });

      es.onerror = () => {
        console.warn("SSE 连接错误，尝试重连...");
      };
    },
    [
      setDiscussionId,
      setDiscussionStatus,
      setParticipants,
      updateGuestStatus,
      updateTypingContent,
      finalizeTyping,
      updateConsensus,
    ]
  );

  /** 断开 SSE 连接 */
  const stopDiscussion = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    discussionIdRef.current = null;
  }, []);

  // 卸载时清理
  useEffect(() => {
    return () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, []);

  return { startDiscussion, stopDiscussion };
}