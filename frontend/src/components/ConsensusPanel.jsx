import React from "react";

function ConsensusPanel({ consensus, discussionStatus }) {
  const hasContent =
    consensus.agreements.length > 0 || consensus.divergences.length > 0;

  if (!hasContent && discussionStatus === "idle") {
    return (
      <div className="consensus">
        <div className="consensus__header">
          <h2 className="consensus__title">📋 动态共识</h2>
        </div>
        <div className="consensus__empty">
          <p>讨论开始后将实时提炼共识与分歧</p>
        </div>
      </div>
    );
  }

  return (
    <div className="consensus">
      <div className="consensus__header">
        <h2 className="consensus__title">📋 动态共识</h2>
        {hasContent && (
          <span className="consensus__badge">
            {consensus.agreements.length} 共识 · {consensus.divergences.length}{" "}
            分歧
          </span>
        )}
      </div>

      <div className="consensus__body">
        {/* 共识 */}
        {consensus.agreements.length > 0 && (
          <div className="consensus__section">
            <div className="consensus__section-title consensus__section-title--agree">
              ✅ 已达共识
            </div>
            <ul className="consensus__list">
              {consensus.agreements.map((item, i) => (
                <li key={i} className="consensus__item consensus__item--agree">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 分歧 */}
        {consensus.divergences.length > 0 && (
          <div className="consensus__section">
            <div className="consensus__section-title consensus__section-title--diverge">
              ❌ 仍存分歧
            </div>
            <ul className="consensus__list">
              {consensus.divergences.map((item, i) => (
                <li
                  key={i}
                  className="consensus__item consensus__item--diverge"
                >
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default ConsensusPanel;