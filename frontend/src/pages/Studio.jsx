import React, { useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import GuestPanel from "../components/GuestPanel";
import Transcript from "../components/Transcript";
import ConsensusPanel from "../components/ConsensusPanel";
import useStudioStore from "../stores/studioStore";
import { useDiscussionStream } from "../hooks/useDiscussionStream";

const API = "http://localhost:8000";

function Studio() {
  const { id } = useParams();
  const navigate = useNavigate();
  const loaded = useRef(false);

  const {
    discussionId,
    participants,
    messages,
    typingMessage,
    consensus,
    guestStatuses,
    discussionStatus,
    setDiscussionId,
    setParticipants,
    setDiscussionStatus,
    loadMessages,
    updateConsensus,
    resetDiscussion,
  } = useStudioStore();

  // 加载讨论元数据 + 历史消息
  useEffect(() => {
    if (!id || loaded.current) return;
    loaded.current = true;

    (async () => {
      try {
        // 1. 获取讨论元数据
        const metaResp = await fetch(`${API}/api/discussions/${id}`);
        if (!metaResp.ok) { navigate("/"); return; }
        const meta = await metaResp.json();
        if (meta.status === "pending") { navigate(`/lobby/${id}`); return; }

        setDiscussionId(meta.id);
        setParticipants(meta.participants);
        setDiscussionStatus(meta.status === "completed" ? "completed" : "in_progress");

        // 2. 如果讨论已结束或已有消息，加载历史消息
        const msgResp = await fetch(`${API}/api/discussions/${id}/messages?limit=200`);
        if (msgResp.ok) {
          const msgs = await msgResp.json();
          if (msgs.length > 0) {
            loadMessages(msgs);
          }
        }

        // 3. 加载共识数据
        if (meta.consensus) {
          updateConsensus(meta.consensus);
        }
      } catch (e) {
        console.error("加载讨论失败:", e);
        navigate("/");
      }
    })();

    return () => {
      resetDiscussion();
      loaded.current = false;
    };
  }, [id]);

  // SSE 连接（实时事件）
  useDiscussionStream(discussionStatus === "in_progress" ? id : null);

  const isCompleted = discussionStatus === "completed";
  const showResults = isCompleted && messages.length > 0;

  return (
    <div className="studio">
      <button className="studio__back" onClick={() => navigate("/")}>← 返回列表</button>

      <GuestPanel
        participants={participants}
        guestStatuses={guestStatuses}
        discussionStatus={discussionStatus}
      />

      <div className="studio__stage">
        <Transcript
          messages={messages}
          typingMessage={typingMessage}
          discussionStatus={discussionStatus}
        />
      </div>

      <ConsensusPanel consensus={consensus} discussionStatus={discussionStatus} />

      <div className="studio__footer">
        {discussionStatus === "in_progress" && (
          <div className="studio__status-bar">
            <span className="studio__status-dot" />
            <span>AI 圆桌讨论进行中</span>
            <span className="studio__msg-count">{messages.length} 条发言</span>
          </div>
        )}
        {isCompleted && (
          <div className="studio__status-bar studio__status-bar--done">
            <span>✓ 讨论已结束</span>
            <span className="studio__msg-count">{messages.length} 条发言</span>
            <button className="studio-btn studio-btn--ghost" onClick={() => navigate("/")}>返回列表</button>
          </div>
        )}
        {!discussionStatus && (
          <div className="studio__status-bar">
            <span>加载中...</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default Studio;