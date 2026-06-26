import React, { useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import GuestPanel from "../components/GuestPanel";
import Transcript from "../components/Transcript";
import ConsensusPanel from "../components/ConsensusPanel";
import useStudioStore from "../stores/studioStore";
import useDiscussion from "../hooks/useDiscussion";

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
    activeSpeakerId,
    resetDiscussion,
  } = useStudioStore();

  const { connectToDiscussion } = useDiscussion();

  // 从 URL 加载已有讨论
  useEffect(() => {
    if (!id || loaded.current) return;
    loaded.current = true;

    const load = async () => {
      try {
        const resp = await fetch(`${API}/api/discussions/${id}`);
        if (!resp.ok) { navigate("/"); return; }
        const data = await resp.json();
        connectToDiscussion(data);
      } catch (e) {
        console.error("加载讨论失败:", e);
        navigate("/");
      }
    };
    load();

    return () => resetDiscussion();
  }, [id]);

  return (
    <div className="studio">
      {/* 返回按钮 */}
      <button className="studio__back" onClick={() => navigate("/")}>
        ← 返回列表
      </button>

      <GuestPanel
        participants={participants}
        guestStatuses={guestStatuses}
        discussionStatus={discussionStatus}
        activeSpeakerId={activeSpeakerId}
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
            <button className="studio-btn studio-btn--ghost" onClick={() => navigate("/")}>
              返回列表
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Studio;
