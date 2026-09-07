import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

const supabase = createClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_KEY!
);

export async function POST(request: Request) {
  const { name, sessionMode } = await request.json();

  const { data, error } = await supabase
    .from("users")
    .insert({
      name,
      session_mode: sessionMode,
      timezone: "America/Chicago",
    })
    .select()
    .single();

    console.log("Supabase error:", error);
    console.log("Supabase data", data);
    if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ user: data });
}