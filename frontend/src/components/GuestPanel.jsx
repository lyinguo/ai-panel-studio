import React from "react";
import GuestCard from "./GuestCard";

function GuestPanel({ participants, guestStatuses, discussionStatus }) {
  return (
    <div className="guest-panel">
      <div className="guest-panel__inner">
        <div className="guest-panel__brand">
          <span className="guest-panel__logo">🎙</span>
          <span className="guest-panel__title">圆桌演播厅</span>
          {discussionStatus === "in_progress" && (
            <span className="guest-panel__live">● 直播中</span>
          )}
        </div>

        {participants.length > 0 && (
          <div className="guest-panel__grid">
            {[...participants].sort((a, b) => a.order - b.order).map((p) => (
              <GuestCard
                key={p.id}
                participant={p}
                status={guestStatuses[p.id] || "idle"}
              />
            ))}
          </div>
        )}

        <div className="guest-panel__controls">
          {discussionStatus === "completed" && (
            <button className="studio-btn studio-btn--ghost" onClick={() => window.history.back()}>
              ↻ 返回
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default GuestPanel;