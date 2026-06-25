import React from "react";
import GuestCard from "./GuestCard";

function GuestPanel({ participants, guestStatuses, discussionStatus, onStart, onReset }) {
  return (
    <div className="guest-panel">
      <div className="guest-panel__header">
        <h2 className="guest-panel__title">🎙 嘉宾席</h2>
        <div className="guest-panel__controls">
          {discussionStatus === "idle" && (
            <button className="btn btn--start" onClick={onStart}>
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

      <div className="guest-panel__grid">
        {participants
          .sort((a, b) => a.order - b.order)
          .map((p) => (
            <GuestCard
              key={p.id}
              participant={p}
              status={guestStatuses[p.id] || "idle"}
            />
          ))}
      </div>
    </div>
  );
}

export default GuestPanel;