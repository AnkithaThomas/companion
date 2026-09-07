import ChatLoader from "./ChatLoader"
import { fetchAccessToken } from "hume";

export const dynamic = "force-dynamic";
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ user?: string }>;
}) {
  const { user } = await searchParams;
  const accessToken = await fetchAccessToken({
  apiKey: String(process.env.HUME_API_KEY),
  secretKey: String(process.env.HUME_SECRET_KEY),
  });
  console.log("Access token:", accessToken);

  return (
    <div className={"grow flex flex-col"}>
      <ChatLoader accessToken={accessToken} userId={user} />
    </div>
  );
}