"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { listBlacklist, resolveBlacklistEntry, type BlacklistEntry } from "@/lib/api";
import { useBfcacheGuard } from "@/lib/useBfcacheGuard";

// Admin blacklist review — shares the same mocked Gov Employee session as
// /review (any employee ID/password works). A real deployment would gate
// this behind a separate admin role; out of scope for this demo tier.
export default function AdminBlacklist() {
  const router = useRouter();
  useBfcacheGuard();
  const [employee, setEmployee] = useState<string | null>(null);
  const [entries, setEntries] = useState<BlacklistEntry[]>([]);
  const [showResolved, setShowResolved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    const emp = sessionStorage.getItem("gov_employee");
    if (!emp) {
      router.push("/review/login");
      return;
    }
    setEmployee(emp);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router, showResolved]);

  async function load() {
    setLoading(true);
    try {
      const all = await listBlacklist(showResolved ? undefined : false);
      setEntries(all);
    } finally {
      setLoading(false);
    }
  }

  async function handleResolve(entryId: string, resolution: "dismissed" | "document_rejected") {
    setBusyId(entryId);
    try {
      await resolveBlacklistEntry(entryId, resolution, employee ?? undefined);
      await load();
    } finally {
      setBusyId(null);
    }
  }

  if (!employee) return null;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-slate-900 text-white px-8 py-4 flex items-center justify-between">
        <div>
          <h1 className="font-bold text-lg">Admin — Blacklist Review</h1>
          <p className="text-xs text-slate-400">Signed in as {employee}</p>
        </div>
        <div className="flex gap-3">
          <Link href="/review" className="text-sm text-slate-300 hover:text-white">
            ← Review queue
          </Link>
          <Link href="/" className="text-sm text-slate-300 hover:text-white">
            Public site
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-bold text-lg">
            {showResolved ? "All flags" : "Unresolved flags"} ({entries.length})
          </h2>
          <div className="flex gap-3 items-center">
            <label className="flex items-center gap-1.5 text-xs text-slate-500">
              <input
                type="checkbox"
                checked={showResolved}
                onChange={(e) => setShowResolved(e.target.checked)}
              />
              Show resolved too
            </label>
            <button onClick={load} className="text-xs font-semibold text-indigo-600 hover:underline">
              Refresh
            </button>
          </div>
        </div>

        <p className="text-xs text-slate-500 mb-6">
          Documents flagged by reviewers for wrong AI output or a suspicious
          upload — separate queue from ordinary review, for an admin to make
          the final call.
        </p>

        {loading && <p className="text-sm text-slate-500">Loading…</p>}

        {!loading && entries.length === 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-sm text-slate-500">
            No {showResolved ? "" : "unresolved "}flags. Reviewers can flag a
            document from its{" "}
            <Link href="/review" className="text-indigo-600 font-semibold hover:underline">
              review page
            </Link>{" "}
            using "🚩 Flag for admin review".
          </div>
        )}

        <div className="space-y-3">
          {entries.map((entry) => (
            <div
              key={entry.id}
              className={`bg-white rounded-xl border p-4 ${
                entry.resolved ? "border-slate-200" : "border-amber-300"
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Link
                      href={`/review/${entry.document_id}`}
                      className="font-semibold text-sm text-indigo-600 hover:underline"
                    >
                      {entry.document_id}
                    </Link>
                    {entry.resolved ? (
                      <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                        {entry.resolution === "document_rejected" ? "Rejected" : "Dismissed"}
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                        Unresolved
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-700">{entry.reason}</p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Flagged by {entry.flagged_by ?? "unknown"} &middot;{" "}
                    {new Date(entry.created_at).toLocaleString()}
                    {entry.resolved && entry.resolved_by && (
                      <> &middot; resolved by {entry.resolved_by}</>
                    )}
                  </p>
                </div>
                {!entry.resolved && (
                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      onClick={() => handleResolve(entry.id, "document_rejected")}
                      disabled={busyId === entry.id}
                      className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white disabled:opacity-40"
                    >
                      Reject document
                    </button>
                    <button
                      onClick={() => handleResolve(entry.id, "dismissed")}
                      disabled={busyId === entry.id}
                      className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-40"
                    >
                      Dismiss flag
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
