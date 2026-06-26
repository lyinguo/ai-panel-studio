import React, { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

function Transcript({ messages, typingMessage, discussionStatus }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typingMessage?.content]);

  const isCompleted = discussionStatus === "completed";

  return (
    <div className="transcript">
      {/* 空态 */}
      {messages.length === 0 && !typingMessage ? (
        <div className="transcript__empty">
          <div className="transcript__empty-icon">🎬</div>
          <p className="transcript__empty-title">
            {isCompleted ? "暂无发言记录" : "等待讨论开始"}
          </p>
          <p className="transcript__empty-hint">
            {isCompleted
              ? "该讨论没有生成发言记录"
              : "输入话题并点击「开始讨论」观看 AI 专家实时辩论"
            }
          </p>
        </div>
      ) : (
        <div className="transcript__scroll">
          <div className="transcript__inner">
            {messages.map((msg, idx) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                isLatest={idx === messages.length - 1 && !typingMessage}
              />
            ))}

            {typingMessage && (
              <MessageBubble message={typingMessage} isTyping isLatest />
            )}

            {/* 讨论结果摘要 */}
            {isCompleted && messages.length > 0 && (
              <div className="transcript__result">
                <div className="transcript__result-line" />
                <div className="transcript__result-title">📝 讨论记录</div>
                <div className="transcript__result-meta">
                  共 {messages.length} 条发言
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>
      )}

      {isCompleted && messages.length > 0 && (
        <div className="transcript__ending">
          <span className="transcript__ending-line" />
          <span className="transcript__ending-text">讨论已结束</span>
          <span className="transcript__ending-line" />
        </div>
      )}
    </div>
  );
}

export default Transcript;