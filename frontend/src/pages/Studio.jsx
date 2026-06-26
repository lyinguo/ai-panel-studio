import React from "react";
import GuestPanel from "../components/GuestPanel";
import Transcript from "../components/Transcript";
import ConsensusPanel from "../components/ConsensusPanel";
import useStudioStore from "../stores/studioStore";
import useDiscussion from "../hooks/useDiscussion";

function Studio() {
  const {
    participants,
    messages,
    typingMessage,
    consensus,
    guestStatuses,
    discussionStatus,
    activeSpeakerId,
    topic,
    expertCount,
    setTopic,
    setExpertCount,
    resetDiscussion,
  } = useStudioStore();

  const { startDiscussion } = useDiscussion();

  return (
    <div className="studio">
      {/* 嘉宾席 */}
      <GuestPanel
        participants={participants}
        guestStatuses={guestStatuses}
        discussionStatus={discussionStatus}
        activeSpeakerId={activeSpeakerId}
      />

      {/* 主舞台 */}
      <div className="studio__stage">
        <Transcript
          messages={messages}
          typingMessage={typingMessage}
          discussionStatus={discussionStatus}
        />
      </div>

      {/* 浮动共识看板 */}
      <ConsensusPanel consensus={consensus} discussionStatus={discussionStatus} />

      {/* 底部控制栏 */}
      <div className="studio__footer">
        {discussionStatus === "idle" && (
          <div className="studio__input-bar">
            <input
              className="studio__input"
              type="text"
              placeholder="输入讨论话题，例如：AGI 是否应该暂停研发"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && topic.trim()) {
                  startDiscussion(topic.trim(), expertCount);
                }
              }}
            />
            <select
              className="studio__select"
              value={expertCount}
              onChange={(e) => setExpertCount(Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
                <option key={n} value={n}>{n} 位专家</option>
              ))}
            </select>
            <button
              className="studio-btn studio-btn--primary"
              onClick={() => startDiscussion(topic.trim(), expertCount)}
              disabled={!topic.trim()}
            >
              ▶ 开始讨论
            </button>
          </div>
        )}

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
            <button className="studio-btn studio-btn--ghost" onClick={resetDiscussion}>
              发起新讨论
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Studio;