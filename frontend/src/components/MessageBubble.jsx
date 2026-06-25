import React from "react";

function MessageBubble({ message, isTyping }) {
  const isHost = message.role === "host";

  return (
    <div className={`msg-bubble ${isHost ? "msg-bubble--host" : ""} ${isTyping ? "msg-bubble--typing" : ""}`}>
      {/* 发言人信息 */}
      <div className="msg-bubble__meta">
        <span
          className="msg-bubble__name"
          style={{ color: message.color_code }}
        >
          {message.participant_name}
        </span>
        <span className="msg-bubble__title">{message.title}</span>
        {isTyping && <span className="msg-bubble__typing-badge">生成中...</span>}
      </div>

      {/* 发言内容 — 纯文本无 Markdown/JSON，打字中带光标 */}
      <div className="msg-bubble__content" style={{ borderLeftColor: message.color_code }}>
        {message.content || ""}
        {isTyping && <span className="msg-bubble__cursor" />}
      </div>
    </div>
  );
}

export default MessageBubble;