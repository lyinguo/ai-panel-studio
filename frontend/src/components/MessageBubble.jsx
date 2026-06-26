import React from "react";

function MessageBubble({ message, isTyping, isLatest }) {
  const isHost = message.role === "host";

  return (
    <div
      className={`msg-bubble ${isHost ? "msg-bubble--host" : ""} ${isTyping ? "msg-bubble--typing" : ""} ${isLatest && !isTyping ? "msg-bubble--latest" : ""}`}
    >
      {/* 发言人信息行 */}
      <div className="msg-bubble__meta">
        <span
          className="msg-bubble__speaker-indicator"
          style={{ backgroundColor: message.color_code }}
        />
        <span className="msg-bubble__name" style={{ color: message.color_code }}>
          {message.participant_name}
        </span>
        <span className="msg-bubble__role-tag">
          {message.role === "host" ? "主持人" : "专家"}
        </span>
        <span className="msg-bubble__title">{message.title}</span>
        {isTyping && <span className="msg-bubble__typing-badge">输入中</span>}
      </div>

      {/* 发言内容 */}
      <div className="msg-bubble__content">
        <span
          className="msg-bubble__accent-line"
          style={{ backgroundColor: message.color_code }}
        />
        <span className="msg-bubble__text">
          {message.content || ""}
          {isTyping && <span className="msg-bubble__cursor" />}
        </span>
      </div>
    </div>
  );
}

export default MessageBubble;