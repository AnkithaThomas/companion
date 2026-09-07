"use client";
import { useState } from "react";
import { userRouter } from "next/naviagtion"

const router = useRouter();

export default function SignupPage() {
  const [name, setName] = useState("");
  const [sessionMode, setSessionMode] = useState("self_initiated");

  async function handleSubmit(e: React.FormEvent) {
  e.preventDefault();
  const response = await fetch("/api/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, sessionMode }),
  });
  const result = await response.json();
  router.push(`/?user=${result.user.id}`);
}

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Name"
      />
      <select value={sessionMode} onChange={(e) => setSessionMode(e.target.value)}>
        <option value="self_initiated">Self-initiated</option>
        <option value="scheduled">Scheduled</option>
      </select>
      <button type="submit">Create User</button>
    </form>
  );
}