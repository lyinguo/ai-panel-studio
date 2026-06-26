import React from "react";
import GuestCard from "./GuestCard";

function GuestPanel({
  participants,
  guestStatuses,
  discussionStatus,
  activeSpeakerId,
  topic,
  expertCount,
  onTopicChange,
  onExpertCountChange,
  onStart,
  onReset,
}) {
  return (
    <div className="guest-panel">
      <div className="guest-panel__inner">
        {/* 左：标题 */}
        <div className="guest-panel__brand">
          <span className="guest-panel__logo">🎙</span>
          <span className="guest-panel__title">圆桌演播厅</span>
          {discussionStatus === "in_progress" && (
            <span className="guest-panel__live">● 直播中</span>
          )}
        </div>

        {/* 中：嘉宾卡片 */}
        {participants.length > 0 && (
          <div className="guest-panel__grid">
            {[...participants]
              .sort((a, b) => a.order - b.order)
              .map((p) => (
                <GuestCard
                  key={p.id}
                  participant={p}
                  status={guestStatuses[p.id] || "idle"}
                  isActive={activeSpeakerId === p.id}
                />
              ))}
          </div>
        )}

        {/* 右：控制 */}
        <div className="guest-panel__controls">
          {discussionStatus === "completed" && (
            <button className="studio-btn studio-btn--ghost" onClick={onReset}>
              ↻ 新讨论
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default GuestPanel;