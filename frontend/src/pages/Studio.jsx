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
    participants,
    messages,
    typingMessage,
    consensus,
    guestStatuses,
    discussionStatus,
    setDiscussionId,
    setParticipants,
    setDiscussionStatus,
    resetDiscussion,
  } = useStudioStore();

  // 1. 加载讨论元数据
  useEffect(() => {
    if (!id || loaded.current) return;
    loaded.current = true;

    (async () => {
      try {
        const resp = await fetch(`${API}/api/discussions/${id}`);
        if (!resp.ok) { navigate("/"); return; }
        const data = await resp.json();
        if (data.status === "pending") { navigate(`/lobby/${id}`); return; }
        setDiscussionId(data.id);
        setParticipants(data.participants);
        setDiscussionStatus(data.status === "completed" ? "completed" : "in_progress");
      } catch (e) {
        navigate("/");
      }
    })();

    return () => resetDiscussion();
  }, [id]);

  // 2. SSE 连接（纯副作用，不返回值）
  useDiscussionStream(id);

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
        {discussionStatus === "completed" && (
          <div className="studio__status-bar studio__status-bar--done">
            <span>✓ 讨论已结束</span>
            <span className="studio__msg-count">{messages.length} 条发言</span>
            <button className="studio-btn studio-btn--ghost" onClick={() => navigate("/")}>返回列表</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Studio;