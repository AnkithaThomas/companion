"use client";
import dynamic from "next/dynamic";

const Chat = dynamic(() => import("./Chat"), { ssr: false });

export default function ChatLoader({
  accessToken,
  userId,
}: {
  accessToken: string;
  userId?: string;
}) {
  return <Chat accessToken={accessToken} userId={userId} />;
}