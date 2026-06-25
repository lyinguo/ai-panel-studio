import React from "react";

function MessageBubble({ message }) {
  const isHost = message.role === "host";

  return (
    <div className={`msg-bubble ${isHost ? "msg-bubble--host" : ""}`}>
      {/* 发言人信息 */}
      <div className="msg-bubble__meta">
        <span
          className="msg-bubble__name"
          style={{ color: message.color_code }}
        >
          {message.participant_name}
        </span>
        <span className="msg-bubble__title">{message.title}</span>
      </div>

      {/* 发言内容 —— 纯文本，无 Markdown/JSON */}
      <div className="msg-bubble__content" style={{ borderLeftColor: message.color_code }}>
        {message.content}
      </div>
    </div>
  );
}

export default MessageBubble;