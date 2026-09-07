import dynamic from "next/dynamic";
import ChatLoader from "./ChatLoader"
import { fetchAccessToken } from "hume";


export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ user?: string }>;
}) {
  const { user } = await searchParams;
  const accessToken = await fetchAccessToken({...});

  return (
    <div className={"grow flex flex-col"}>
      <ChatLoader accessToken={accessToken} userId={user} />
    </div>
  );
}