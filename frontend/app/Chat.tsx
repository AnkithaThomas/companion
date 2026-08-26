import { VoiceProvider } from "@humeai/voice-react";
import Messages from "./Messages";
import StartCall from "./StartCall";

export default function Chat({
  accessToken,
}: {
  accessToken: string;
}) {
  return (
    <VoiceProvider>
      <Messages />
      <StartCall accessToken={accessToken} />
    </VoiceProvider>
  );
}