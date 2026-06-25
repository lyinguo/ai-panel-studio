import React from "react";
import GuestCard from "./GuestCard";

function GuestPanel({
  participants,
  guestStatuses,
  discussionStatus,
  topic,
  expertCount,
  onTopicChange,
  onExpertCountChange,
  onStart,
  onReset,
}) {
  const isIdle = discussionStatus === "idle";

  return (
    <div className="guest-panel">
      <div className="guest-panel__header">
        <h2 className="guest-panel__title">🎙 嘉宾席</h2>
        <div className="guest-panel__controls">
          {isIdle && (
            <button
              className="btn btn--start"
              onClick={onStart}
              disabled={!topic.trim()}
            >
              ▶ 开始讨论
            </button>
          )}
          {discussionStatus === "in_progress" && (
            <span className="guest-panel__live-badge">● 直播中</span>
          )}
          {discussionStatus === "completed" && (
            <button className="btn btn--reset" onClick={onReset}>
              ↻ 重新开始
            </button>
          )}
        </div>
      </div>

      {/* 空闲态：输入表单 */}
      {isIdle && (
        <div className="guest-panel__setup">
          <div className="setup-form">
            <div className="setup-form__field">
              <label className="setup-form__label">讨论话题</label>
              <input
                className="setup-form__input"
                type="text"
                placeholder="例如：AGI 是否应该暂停研发"
                value={topic}
                onChange={(e) => onTopicChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && topic.trim()) onStart();
                }}
              />
            </div>
            <div className="setup-form__field setup-form__field--narrow">
              <label className="setup-form__label">专家人数</label>
              <select
                className="setup-form__select"
                value={expertCount}
                onChange={(e) => onExpertCountChange(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
                  <option key={n} value={n}>
                    {n} 位
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* 嘉宾卡片网格 */}
      {participants.length > 0 && (
        <div className="guest-panel__grid">
          {[...participants]
            .sort((a, b) => a.order - b.order)
            .map((p) => (
              <GuestCard
                key={p.id}
                participant={p}
                status={guestStatuses[p.id] || "idle"}
              />
            ))}
        </div>
      )}
    </div>
  );
}

export default GuestPanel;