import React from "react";
import GuestPanel from "../components/GuestPanel";
import Transcript from "../components/Transcript";
import ConsensusPanel from "../components/ConsensusPanel";
import useStudioStore from "../stores/studioStore";
import useDiscussion from "../hooks/useDiscussion";

function Studio() {
  const {
    participants,
    messages,
    typingMessage,
    consensus,
    guestStatuses,
    discussionStatus,
    topic,
    expertCount,
    setTopic,
    setExpertCount,
    resetDiscussion,
  } = useStudioStore();

  const { startDiscussion } = useDiscussion();

  const handleStart = () => {
    if (!topic.trim()) return;
    startDiscussion(topic.trim(), expertCount);
  };

  const handleReset = () => {
    resetDiscussion();
  };

  return (
    <div className="studio">
      <GuestPanel
        participants={participants}
        guestStatuses={guestStatuses}
        discussionStatus={discussionStatus}
        topic={topic}
        expertCount={expertCount}
        onTopicChange={setTopic}
        onExpertCountChange={setExpertCount}
        onStart={handleStart}
        onReset={handleReset}
      />

      <div className="studio__main">
        <Transcript
          messages={messages}
          typingMessage={typingMessage}
          discussionStatus={discussionStatus}
        />
        <ConsensusPanel
          consensus={consensus}
          discussionStatus={discussionStatus}
        />
      </div>
    </div>
  );
}

export default Studio;