import React from "react";

const STATUS_CONFIG = {
  idle: { label: "待机", color: "#6B7280" },
  thinking: { label: "思考中", color: "#F59E0B" },
  speaking: { label: "发言中", color: "#10B981" },
};

function GuestCard({ participant, status, isActive }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.idle;
  const initial = participant.name.charAt(0);

  return (
    <div className={`guest-card ${isActive ? "guest-card--active" : ""}`}>
      {/* 光环层 */}
      {isActive && (
        <div
          className="guest-card__glow"
          style={{ background: `radial-gradient(circle, ${participant.color_code}44 0%, transparent 70%)` }}
        />
      )}

      {/* 头像 */}
      <div
        className={`guest-card__avatar ${status === "speaking" ? "guest-card__avatar--speaking" : ""}`}
        style={{ borderColor: participant.color_code }}
      >
        <span className="guest-card__initial" style={{ color: participant.color_code }}>
          {initial}
        </span>
        {/* 状态指示点 */}
        <span
          className={`guest-card__dot ${status === "thinking" || status === "speaking" ? "guest-card__dot--pulse" : ""}`}
          style={{ backgroundColor: cfg.color, boxShadow: `0 0 6px ${cfg.color}88` }}
        />
      </div>

      {/* 名称 */}
      <div className="guest-card__name" style={{ color: isActive ? participant.color_code : "#e2e8f0" }}>
        {participant.name}
      </div>

      {/* 角色 */}
      <div className="guest-card__role">
        {participant.role === "host" ? "主持人" : "专家"}
      </div>

      {/* 状态条 */}
      <div className="guest-card__status-bar" style={{ backgroundColor: cfg.color }} />
    </div>
  );
}

export default GuestCard;