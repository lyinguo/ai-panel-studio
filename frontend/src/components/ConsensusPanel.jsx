import React from "react";

function ConsensusPanel({ consensus, discussionStatus }) {
  const hasContent =
    consensus.agreements.length > 0 || consensus.divergences.length > 0;

  if (!hasContent && discussionStatus === "idle") return null;

  return (
    <div className={`consensus ${hasContent ? "consensus--visible" : ""}`}>
      <div className="consensus__header">
        <span className="consensus__title">📋 共识看板</span>
        {hasContent && (
          <span className="consensus__badge">
            {consensus.agreements.length}·{consensus.divergences.length}
          </span>
        )}
      </div>

      {hasContent && (
        <div className="consensus__body">
          {consensus.agreements.length > 0 && (
            <div className="consensus__group">
              <div className="consensus__group-title consensus__group-title--agree">
                <span>✅ 已达共识</span>
              </div>
              {consensus.agreements.map((item, i) => (
                <div key={i} className="consensus__item consensus__item--agree">
                  {item}
                </div>
              ))}
            </div>
          )}

          {consensus.divergences.length > 0 && (
            <div className="consensus__group">
              <div className="consensus__group-title consensus__group-title--diverge">
                <span>❌ 仍存分歧</span>
              </div>
              {consensus.divergences.map((item, i) => (
                <div key={i} className="consensus__item consensus__item--diverge">
                  {item}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ConsensusPanel;