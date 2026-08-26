import dynamic from "next/dynamic";
import ChatLoader from "./ChatLoader"
import { fetchAccessToken } from "hume";


export default async function Page() {
  const accessToken = await fetchAccessToken({
    apiKey: String(process.env.HUME_API_KEY),
    secretKey: String(process.env.HUME_SECRET_KEY),
  });

  return (
    <div className={"grow flex flex-col"}>
      <ChatLoader accessToken={accessToken} />
    </div>
  );
}