"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { listDocuments, type AnalyzeResult } from "@/lib/api";
import { useBfcacheGuard } from "@/lib/useBfcacheGuard";

export default function ReviewDashboard() {
  const router = useRouter();
  useBfcacheGuard();
  const [employee, setEmployee] = useState<string | null>(null);
  const [docs, setDocs] = useState<AnalyzeResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const emp = sessionStorage.getItem("gov_employee");
    if (!emp) {
      router.push("/review/login");
      return;
    }
    setEmployee(emp);
    loadDocs();
  }, [router]);

  async function loadDocs() {
    setLoading(true);
    setError(null);
    try {
      const all = await listDocuments();
      setDocs(all);
    } catch (e) {
      setError(
        e instanceof Error
          ? `Could not reach the server: ${e.message}. Check that the backend (port 8000) is reachable from this device.`
          : "Could not reach the server."
      );
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    sessionStorage.removeItem("gov_employee");
    router.push("/review/login");
  }

  if (!employee) return null;

  const pending = docs.filter((d) => d.status === "pending_review");
  const resolved = docs.filter((d) => d.status !== "pending_review");

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-slate-900 text-white px-8 py-4 flex items-center justify-between">
        <div>
          <h1 className="font-bold text-lg">Gov Employee Portal</h1>
          <p className="text-xs text-slate-400">Signed in as {employee}</p>
        </div>
        <div className="flex gap-3">
          <Link href="/admin/blacklist" className="text-sm text-slate-300 hover:text-white">
            🚩 Admin: Blacklist
          </Link>
          <Link href="/" className="text-sm text-slate-300 hover:text-white">
            ← Public site
          </Link>
          <button onClick={logout} className="text-sm text-slate-300 hover:text-white">
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-bold text-lg">Pending review ({pending.length})</h2>
          <button
            onClick={loadDocs}
            className="text-xs font-semibold text-indigo-600 hover:underline"
          >
            Refresh
          </button>
        </div>

        {loading && <p className="text-sm text-slate-500">Loading…</p>}

        {error && (
          <div className="bg-rose-50 border border-rose-300 text-rose-700 rounded-xl p-4 text-sm mb-6">
            ⚠ {error}
          </div>
        )}

        {!loading && !error && pending.length === 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-sm text-slate-500">
            No documents pending review. Upload a low-confidence scan on the{" "}
            <Link href="/" className="text-indigo-600 font-semibold hover:underline">
              public site
            </Link>{" "}
            to see one here.
          </div>
        )}

        <div className="space-y-3 mb-10">
          {pending.map((d) => (
            <Link
              key={d.document_id}
              href={`/review/${d.document_id}`}
              className="block bg-white rounded-xl border border-amber-200 p-4 hover:border-amber-400 transition"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-sm">{d.filename}</p>
                  <p className="text-xs text-slate-400">{d.document_id}</p>
                </div>
                <div className="text-right">
                  <span className="inline-block px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 text-xs font-bold">
                    ⏳ Pending — {Math.round(d.overall_confidence * 100)}%
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>

        {resolved.length > 0 && (
          <>
            <h2 className="font-bold text-lg mb-4">Resolved ({resolved.length})</h2>
            <div className="space-y-2">
              {resolved.map((d) => (
                <div
                  key={d.document_id}
                  className="flex items-center justify-between bg-white rounded-lg border border-slate-200 px-4 py-3 text-sm"
                >
                  <span className="font-medium">{d.filename}</span>
                  <span className="text-xs text-slate-400">{d.status}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
