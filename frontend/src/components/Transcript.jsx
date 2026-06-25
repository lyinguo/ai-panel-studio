import React, { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

function Transcript({ messages, discussionStatus }) {
  const bottomRef = useRef(null);

  // 平滑自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="transcript">
      <div className="transcript__header">
        <h2 className="transcript__title">📺 讨论现场</h2>
        <span className="transcript__count">
          {messages.length > 0 ? `${messages.length} 条发言` : ""}
        </span>
      </div>

      <div className="transcript__scroll">
        <div className="transcript__inner">
          {messages.length === 0 ? (
            <div className="transcript__empty">
              <div className="transcript__empty-icon">🎬</div>
              <p>点击「开始讨论」进入直播现场</p>
              <p className="transcript__empty-hint">
                将实时展示嘉宾的精彩观点碰撞
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {discussionStatus === "completed" && (
        <div className="transcript__ending">
          —— 讨论已结束，感谢各位嘉宾的精彩发言 ——
        </div>
      )}
    </div>
  );
}

export default Transcript;