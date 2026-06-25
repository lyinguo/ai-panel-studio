import React from "react";

const STATUS_CONFIG = {
  idle: { label: "待机", color: "#666", pulse: false },
  thinking: { label: "思考中", color: "#F0AD4E", pulse: true },
  speaking: { label: "发言中", color: "#5CB85C", pulse: true },
};

function GuestCard({ participant, status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.idle;

  return (
    <div
      className={`guest-card ${status === "speaking" ? "guest-card--active" : ""}`}
      style={{ borderLeftColor: participant.color_code }}
    >
      {/* 头像区 */}
      <div
        className="guest-card__avatar"
        style={{ borderColor: participant.color_code }}
      >
        <span style={{ color: participant.color_code }}>
          {participant.name[0]}
        </span>
        {/* 状态指示器 */}
        <span
          className={`guest-card__indicator ${cfg.pulse ? "guest-card__indicator--pulse" : ""}`}
          style={{ backgroundColor: cfg.color }}
        />
      </div>

      {/* 信息区 */}
      <div className="guest-card__info">
        <div className="guest-card__name-row">
          <span className="guest-card__role-tag" style={{ backgroundColor: participant.color_code + "22", color: participant.color_code }}>
            {participant.role === "host" ? "主持人" : "专家"}
          </span>
          <span className="guest-card__name" style={{ color: participant.color_code }}>
            {participant.name}
          </span>
        </div>
        <div className="guest-card__title">{participant.title}</div>
        <div className="guest-card__stance">{participant.stance}</div>
      </div>

      {/* 状态标签 */}
      <div className="guest-card__status" style={{ color: cfg.color }}>
        <span
          className={`guest-card__status-dot ${cfg.pulse ? "guest-card__status-dot--pulse" : ""}`}
          style={{ backgroundColor: cfg.color }}
        />
        {cfg.label}
      </div>
    </div>
  );
}

export default GuestCard;