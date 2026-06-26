import { useCallback, useEffect, useRef } from "react";
import useStudioStore from "../stores/studioStore";

const SSE_URL = "http://localhost:8000";
const API_URL = "http://localhost:8000";

export default function useDiscussion() {
  const esRef = useRef(null);

  const {
    discussionStatus,
    setDiscussionId,
    setDiscussionStatus,
    setParticipants,
    updateGuestStatus,
    updateTypingContent,
    finalizeTyping,
    updateConsensus,
  } = useStudioStore();

  /** 连接到已有的讨论（SSE） */
  const _connectSSE = useCallback((discussionId) => {
    if (esRef.current) esRef.current.close();

    const es = new EventSource(`${SSE_URL}/api/discussions/${discussionId}/events`);
    esRef.current = es;

    es.addEventListener("guest_status_change", (e) => {
      try {
        updateGuestStatus(JSON.parse(e.data).participant_id, JSON.parse(e.data).status);
      } catch (_) {}
    });

    es.addEventListener("message_chunk", (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.is_final) finalizeTyping(data);
        else updateTypingContent(data);
      } catch (_) {}
    });

    es.addEventListener("consensus_update", (e) => {
      try {
        updateConsensus(JSON.parse(e.data));
      } catch (_) {}
    });

    es.addEventListener("discussion_status", (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.status === "completed") setDiscussionStatus("completed");
        if (d.status === "in_progress") setDiscussionStatus("in_progress");
      } catch (_) {}
    });

    es.onerror = () => {};
  }, [updateGuestStatus, updateTypingContent, finalizeTyping, updateConsensus, setDiscussionStatus]);

  /** 创建新讨论 */
  const startDiscussion = useCallback(async (topic, expertCount = 4) => {
    if (discussionStatus === "starting" || discussionStatus === "in_progress") return;
    setDiscussionStatus("starting");

    try {
      const resp = await fetch(`${API_URL}/api/discussions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, expert_count: expertCount }),
      });
      if (!resp.ok) throw new Error(`创建失败: ${resp.status}`);
      const data = await resp.json();
      setDiscussionId(data.discussion_id);
      setParticipants(data.participants);
      setDiscussionStatus("in_progress");
      _connectSSE(data.discussion_id);
    } catch (err) {
      console.error("创建讨论失败:", err);
      setDiscussionStatus("idle");
    }
  }, [discussionStatus, setDiscussionId, setDiscussionStatus, setParticipants, _connectSSE]);

  /** 连接到已有讨论（从首页进入） */
  const connectToDiscussion = useCallback((data) => {
    setDiscussionId(data.id);
    setParticipants(data.participants);
    setDiscussionStatus(data.status === "completed" ? "completed" : "in_progress");
    _connectSSE(data.id);
  }, [setDiscussionId, setParticipants, setDiscussionStatus, _connectSSE]);

  useEffect(() => {
    return () => {
      if (esRef.current) { esRef.current.close(); esRef.current = null; }
    };
  }, []);

  return { startDiscussion, connectToDiscussion };
}