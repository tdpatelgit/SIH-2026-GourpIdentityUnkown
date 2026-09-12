"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

// Mocked auth — hackathon-demo tier, no real backend auth.
// Any non-empty username/password combo logs in; credentials are not
// checked against anything real. Session is a sessionStorage flag only.
export default function ReviewLogin() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Enter both employee ID and password.");
      return;
    }
    sessionStorage.setItem("gov_employee", username.trim());
    router.push("/review");
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-xl p-8">
        <div className="text-center mb-6">
          <div className="mx-auto mb-3 w-12 h-12 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold text-lg">
            🏛
          </div>
          <h1 className="text-lg font-bold text-slate-900">Gov Employee Portal</h1>
          <p className="text-sm text-slate-500">Land Record Review &amp; Validation</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">Employee ID</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. LR-EMP-2201"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              style={{ color: "#091540" }}
            />
          </div>
          {error && <p className="text-xs text-rose-600">{error}</p>}
          <button
            type="submit"
            className="w-full rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm py-2.5"
          >
            Sign in
          </button>
        </form>
        <p className="text-[11px] text-slate-400 mt-5 text-center">
          Demo login — any employee ID / password combination works.
        </p>
      </div>
    </div>
  );
}
