"use client";
import {
  useVoice,
  VoiceReadyState
} from "@humeai/voice-react";

export default function StartCall({
  accessToken,
}: {
  accessToken: string;
}) {
  const { connect, disconnect, readyState } = useVoice();

  if (readyState === VoiceReadyState.OPEN) {
    return (
      <button
        onClick={() => {
          disconnect();
        }}
      >
        End Session
      </button>
    );
  }

  return (
    <button
      onClick={() => {
        connect({
          auth: { type: "accessToken", value: accessToken }
        })
          .then(() => {
            /* handle success */
          })
          .catch(() => {
            /* handle error */
          });
      }}
    >
      Start Session
    </button>
  );
}