import React from "react";
import GuestPanel from "../components/GuestPanel";
import Transcript from "../components/Transcript";
import ConsensusPanel from "../components/ConsensusPanel";
import useStudioStore from "../stores/studioStore";

function Studio() {
  const {
    participants,
    messages,
    consensus,
    guestStatuses,
    discussionStatus,
    startDiscussion,
    resetDiscussion,
  } = useStudioStore();

  return (
    <div className="studio">
      {/* 嘉宾席面板 */}
      <GuestPanel
        participants={participants}
        guestStatuses={guestStatuses}
        discussionStatus={discussionStatus}
        onStart={startDiscussion}
        onReset={resetDiscussion}
      />

      {/* 主体区域 */}
      <div className="studio__main">
        <Transcript messages={messages} discussionStatus={discussionStatus} />
        <ConsensusPanel
          consensus={consensus}
          discussionStatus={discussionStatus}
        />
      </div>
    </div>
  );
}

export default Studio;
