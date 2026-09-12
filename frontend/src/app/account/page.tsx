"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { listDocuments, type AnalyzeResult } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

function StatusPill({ status }: { status: AnalyzeResult["status"] }) {
  const map: Record<AnalyzeResult["status"], { label: string; cls: string }> = {
    auto_approved: { label: "✓ Auto-approved", cls: "bg-emerald-100 text-emerald-800" },
    pending_review: { label: "⏳ Pending review", cls: "bg-amber-100 text-amber-800" },
    approved: { label: "✓ Approved by reviewer", cls: "bg-emerald-100 text-emerald-800" },
    boundary_drawn: { label: "✎ Boundary drawn", cls: "bg-indigo-100 text-indigo-800" },
    rejected: { label: "✗ Rejected", cls: "bg-rose-100 text-rose-800" },
  };
  const s = map[status];
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${s.cls}`}>{s.label}</span>;
}

export default function AccountDocuments() {
  const router = useRouter();
  const { username, ready, clearSession } = useAuth();
  const [docs, setDocs] = useState<AnalyzeResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    if (!username) {
      router.push("/account/login");
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, username]);

  async function load() {
    setLoading(true);
    try {
      const mine = await listDocuments({ mine: true });
      setDocs(mine);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    clearSession();
    router.push("/");
  }

  if (!ready || !username) return null;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-8 py-4 flex items-center justify-between">
        <div>
          <h1 className="font-bold text-lg text-slate-900">My Documents</h1>
          <p className="text-xs text-slate-500">Signed in as {username}</p>
        </div>
        <div className="flex gap-4 items-center">
          <Link href="/" className="text-sm text-slate-500 hover:text-slate-900">
            + Upload new
          </Link>
          <button onClick={logout} className="text-sm text-slate-500 hover:text-slate-900">
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-semibold text-slate-700">
            {docs.length} document{docs.length === 1 ? "" : "s"} uploaded
          </h2>
          <button onClick={load} className="text-xs font-semibold text-indigo-600 hover:underline">
            Refresh
          </button>
        </div>

        {loading && <p className="text-sm text-slate-500">Loading…</p>}

        {!loading && docs.length === 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-sm text-slate-500">
            No documents yet.{" "}
            <Link href="/" className="text-indigo-600 font-semibold hover:underline">
              Upload your first scan
            </Link>{" "}
            — it'll show up here automatically since you're signed in.
          </div>
        )}

        <div className="space-y-3">
          {docs.map((d) => (
            <div
              key={d.document_id}
              className="bg-white rounded-xl border border-slate-200 p-4 flex items-center justify-between"
            >
              <div>
                <p className="font-semibold text-sm">{d.filename}</p>
                <p className="text-xs text-slate-400">
                  {d.document_id} &middot; {new Date(d.processed_at).toLocaleString()}
                </p>
              </div>
              <div className="text-right space-y-1">
                <StatusPill status={d.status} />
                <p className="text-xs text-slate-400">
                  {Math.round(d.overall_confidence * 100)}% confidence
                </p>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
