"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import {
  approveDocument,
  blacklistDocument,
  getDocument,
  getGovernmentRecord,
  rejectDocument,
  saveBoundary,
  updateDocumentFields,
  type AnalyzeResult,
  type ExtractedField,
  type GovernmentRecord,
} from "@/lib/api";
import { PLOT_BBOXES } from "@/lib/plots";
import { useBfcacheGuard } from "@/lib/useBfcacheGuard";

const CANVAS_W = 600;
const CANVAS_H = 420;

export default function ReviewDocument() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useBfcacheGuard();

  const [employee, setEmployee] = useState<string | null>(null);
  const [doc, setDoc] = useState<AnalyzeResult | null>(null);
  const [points, setPoints] = useState<number[][]>([]);
  const [mode, setMode] = useState<"view" | "draw">("view");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [govRecord, setGovRecord] = useState<GovernmentRecord | null>(null);
  const bgImageRef = useRef<HTMLImageElement | null>(null);
  const [bgLoaded, setBgLoaded] = useState(false);
  const [editingFields, setEditingFields] = useState(false);
  const [draftFields, setDraftFields] = useState<ExtractedField[]>([]);

  useEffect(() => {
    const img = new Image();
    img.src = "/dummy-land.svg";
    img.onload = () => {
      bgImageRef.current = img;
      setBgLoaded(true);
    };
  }, []);

  useEffect(() => {
    const emp = sessionStorage.getItem("gov_employee");
    if (!emp) {
      router.push("/review/login");
      return;
    }
    setEmployee(emp);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  async function load() {
    const d = await getDocument(params.id);
    setDoc(d);
    if (d.boundary) setPoints(d.boundary);
    if (d.plot_id) {
      try {
        const record = await getGovernmentRecord(d.plot_id);
        setGovRecord(record);
      } catch {
        setGovRecord(null);
      }
    }
  }

  useEffect(() => {
    draw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, bgLoaded, doc]);

  function draw() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);

    if (bgImageRef.current) {
      // real dummy land/parcel image as the sketch surface
      ctx.drawImage(bgImageRef.current, 0, 0, CANVAS_W, CANVAS_H);
    } else {
      // fallback while the image is still loading
      ctx.fillStyle = "#f4f1e8";
      ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
      ctx.fillStyle = "#a89f87";
      ctx.font = "12px sans-serif";
      ctx.fillText("Loading land image…", 16, 20);
    }

    if (points.length === 0) return;

    // lines
    ctx.strokeStyle = "#4338ca";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i][0], points[i][1]);
    }
    if (points.length > 2) ctx.closePath();
    ctx.stroke();

    // fill if closed polygon
    if (points.length > 2) {
      ctx.fillStyle = "rgba(67, 56, 202, 0.12)";
      ctx.fill();
    }

    // dots
    points.forEach(([x, y], i) => {
      ctx.fillStyle = "#4338ca";
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#1e1b4b";
      ctx.font = "10px sans-serif";
      ctx.fillText(String(i + 1), x + 7, y - 7);
    });
  }

  function handleCanvasClick(e: React.MouseEvent<HTMLCanvasElement>) {
    if (mode !== "draw") return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = Math.round(e.clientX - rect.left);
    const y = Math.round(e.clientY - rect.top);
    setPoints((prev) => [...prev, [x, y]]);
  }

  function undoPoint() {
    setPoints((prev) => prev.slice(0, -1));
  }

  function clearPoints() {
    setPoints([]);
  }

  async function handleApprove() {
    setBusy(true);
    setMessage(null);
    try {
      const updated = await approveDocument(params.id);
      setDoc(updated);
      setMessage("Approved as-is.");
    } finally {
      setBusy(false);
    }
  }

  async function handleReject() {
    const reason = window.prompt(
      "Why is this document being rejected? (shown on the record)"
    );
    if (!reason || !reason.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      const updated = await rejectDocument(params.id, reason.trim());
      setDoc(updated);
      setMessage("Document rejected.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Reject failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleBlacklistFlag() {
    const reason = window.prompt(
      "Flag this document for admin review — what's wrong? " +
        "(e.g. AI extracted the wrong field, or the upload itself looks fraudulent)"
    );
    if (!reason || !reason.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      await blacklistDocument(params.id, reason.trim(), employee ?? undefined);
      setMessage("Flagged for admin review.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Flag failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveBoundary() {
    if (points.length < 3) {
      setMessage("Draw at least 3 points to close a boundary.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const updated = await saveBoundary(params.id, points);
      setDoc(updated);
      setMode("view");
      setMessage("Boundary saved.");
    } finally {
      setBusy(false);
    }
  }

  function startEditingFields() {
    if (!doc) return;
    setDraftFields(doc.fields.map((f) => ({ ...f })));
    setEditingFields(true);
    setMessage(null);
  }

  function cancelEditingFields() {
    setEditingFields(false);
    setDraftFields([]);
  }

  function updateDraftFieldValue(index: number, value: string) {
    setDraftFields((prev) =>
      prev.map((f, i) => (i === index ? { ...f, value } : f))
    );
  }

  async function handleSaveFieldCorrections() {
    setBusy(true);
    setMessage(null);
    try {
      // Manual corrections are treated as high-confidence (reviewer-verified).
      const corrected = draftFields.map((f) => ({ ...f, confidence: 1.0 }));
      const updated = await updateDocumentFields(params.id, corrected);
      setDoc(updated);
      setEditingFields(false);
      setMessage("Field corrections saved.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Failed to save corrections.");
    } finally {
      setBusy(false);
    }
  }

  if (!employee || !doc) return null;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-slate-900 text-white px-8 py-4 flex items-center justify-between">
        <div>
          <h1 className="font-bold text-lg">{doc.filename}</h1>
          <p className="text-xs text-slate-400">{doc.document_id} &middot; reviewer: {employee}</p>
        </div>
        <Link href="/review" className="text-sm text-slate-300 hover:text-white">
          ← Back to queue
        </Link>
      </header>

      <main className="max-w-6xl mx-auto p-8 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl border border-slate-300 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-sm text-slate-700">📤 Document uploaded by user</h2>
              <span className="text-[10px] font-bold uppercase tracking-wide text-amber-700 bg-amber-100 rounded-full px-2 py-0.5">
                AI-extracted, unverified
              </span>
            </div>
            <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 font-mono text-xs text-slate-700 space-y-1.5">
              <p className="text-[10px] text-slate-400 mb-2">{doc.filename}</p>
              {doc.fields.map((f) => (
                <div key={f.name} className="flex justify-between gap-2">
                  <span className="text-slate-500">{f.label}:</span>
                  <span className="font-semibold">{f.value}</span>
                </div>
              ))}
              <div className="flex justify-between gap-2 pt-1.5 mt-1.5 border-t border-slate-200 text-[10px] text-slate-400">
                <span>Overall AI confidence</span>
                <span>{Math.round(doc.overall_confidence * 100)}%</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-indigo-300 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-sm text-slate-700">🏛 Khata record on file with government</h2>
              <span className="text-[10px] font-bold uppercase tracking-wide text-indigo-700 bg-indigo-100 rounded-full px-2 py-0.5">
                Official record
              </span>
            </div>
            {govRecord ? (
              <div className="rounded-lg border border-indigo-200 bg-indigo-50/40 p-4 font-mono text-xs text-slate-700 space-y-1.5">
                <p className="text-[10px] text-slate-400 mb-2">
                  {govRecord.plot_label} &middot; on file since {govRecord.on_file_since}
                </p>
                <div className="flex justify-between gap-2"><span className="text-slate-500">Khata No.:</span><span className="font-semibold">{govRecord.khata_no}</span></div>
                <div className="flex justify-between gap-2"><span className="text-slate-500">Khasra No.:</span><span className="font-semibold">{govRecord.khasra_no}</span></div>
                <div className="flex justify-between gap-2"><span className="text-slate-500">Survey No.:</span><span className="font-semibold">{govRecord.survey_no}</span></div>
                <div className="flex justify-between gap-2"><span className="text-slate-500">Owner Name:</span><span className="font-semibold">{govRecord.owner_name}</span></div>
                <div className="flex justify-between gap-2"><span className="text-slate-500">Area:</span><span className="font-semibold">{govRecord.area} acres</span></div>
                <div className="flex justify-between gap-2"><span className="text-slate-500">Mutation:</span><span className="font-semibold">{govRecord.mutation}</span></div>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-xs text-slate-400 text-center">
                No matching official record on file for this document (not
                linked to one of the 4 demo plots).
              </div>
            )}
          </div>
        </div>

        {govRecord && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <h2 className="font-semibold text-sm text-slate-700 mb-3">
              🗺 Plot location on the cadastral map — {govRecord.plot_label}
            </h2>
            <div className="flex flex-col sm:flex-row gap-4 items-start">
              <div className="rounded-lg border border-slate-300 overflow-hidden shrink-0">
                <svg
                  width="260"
                  height="200"
                  viewBox={`${PLOT_BBOXES[doc.plot_id ?? "1"]?.x ?? 0} ${PLOT_BBOXES[doc.plot_id ?? "1"]?.y ?? 0} ${PLOT_BBOXES[doc.plot_id ?? "1"]?.w ?? 600} ${PLOT_BBOXES[doc.plot_id ?? "1"]?.h ?? 420}`}
                >
                  <image href="/dummy-land.svg" x="0" y="0" width="600" height="420" />
                  {PLOT_BBOXES[doc.plot_id ?? "1"] && (
                    <polygon
                      points={PLOT_BBOXES[doc.plot_id ?? "1"].polygon.map((p) => p.join(",")).join(" ")}
                      fill="rgba(220, 38, 38, 0.18)"
                      stroke="#dc2626"
                      strokeWidth={3}
                    />
                  )}
                </svg>
              </div>
              <div className="text-xs text-slate-500 space-y-1">
                <p>Zoomed view of {govRecord.plot_label} on the full cadastral map, outlined in red.</p>
                <p className="text-slate-400">
                  Full map is also the sketch surface below, for hand-drawing a
                  corrected boundary if the AI's parcel outline needs a fix.
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-5 gap-6">
        <div className="col-span-3 bg-white rounded-2xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-sm">Dummy land image — mark boundary</h2>
            <div className="flex gap-2">
              <button
                onClick={() => setMode(mode === "draw" ? "view" : "draw")}
                className={`text-xs font-semibold px-3 py-1.5 rounded-lg border ${
                  mode === "draw"
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "border-slate-300 text-slate-700 hover:bg-slate-50"
                }`}
              >
                {mode === "draw" ? "✎ Drawing…" : "✎ Draw boundary"}
              </button>
              <button
                onClick={undoPoint}
                disabled={points.length === 0}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-40"
              >
                Undo point
              </button>
              <button
                onClick={clearPoints}
                disabled={points.length === 0}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-40"
              >
                Clear
              </button>
            </div>
          </div>
          <canvas
            ref={canvasRef}
            width={CANVAS_W}
            height={CANVAS_H}
            onClick={handleCanvasClick}
            className={`rounded-lg border border-slate-300 ${mode === "draw" ? "cursor-crosshair" : "cursor-default"}`}
          />
          <p className="text-xs text-slate-500 mt-3">
            {mode === "draw"
              ? `Click directly on the land image to drop boundary points (dots), connected in order (lines). ${points.length} point(s) placed — need 3+ to save.`
              : "Click \"Draw boundary\" to sketch the parcel outline by hand on the dummy satellite image below."}
          </p>
          <div className="mt-4 flex gap-2">
            <button
              onClick={handleSaveBoundary}
              disabled={busy || points.length < 3}
              className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg py-2.5 disabled:opacity-40"
            >
              Save hand-drawn boundary
            </button>
          </div>
        </div>

        <div className="col-span-2 space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-sm">Extracted fields</h2>
              {!editingFields ? (
                <button
                  onClick={startEditingFields}
                  disabled={busy}
                  className="text-xs font-semibold text-indigo-600 hover:underline disabled:opacity-40"
                >
                  ✎ Edit fields
                </button>
              ) : (
                <div className="flex gap-3">
                  <button
                    onClick={handleSaveFieldCorrections}
                    disabled={busy}
                    className="text-xs font-semibold text-emerald-600 hover:underline disabled:opacity-40"
                  >
                    Save corrections
                  </button>
                  <button
                    onClick={cancelEditingFields}
                    disabled={busy}
                    className="text-xs font-semibold text-slate-400 hover:underline disabled:opacity-40"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
            {doc.fields_edited_by_reviewer && !editingFields && (
              <p className="text-[10px] font-semibold text-indigo-600 bg-indigo-50 rounded px-2 py-1 mb-3 inline-block">
                ✓ Manually corrected by reviewer
              </p>
            )}
            {!editingFields ? (
              <table className="w-full text-sm">
                <tbody>
                  {doc.fields.map((f) => (
                    <tr key={f.name} className="border-t border-slate-100">
                      <td className="py-2 text-slate-500 text-xs">{f.label}</td>
                      <td className="py-2 font-medium text-xs">{f.value}</td>
                      <td className="py-2 text-right text-xs font-bold">
                        {Math.round(f.confidence * 100)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="space-y-2">
                {draftFields.map((f, i) => (
                  <div key={f.name} className="flex items-center gap-2">
                    <label className="text-xs text-slate-500 w-28 shrink-0">{f.label}</label>
                    <input
                      value={f.value}
                      onChange={(e) => updateDraftFieldValue(i, e.target.value)}
                      className="flex-1 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-indigo-300"
                    />
                  </div>
                ))}
                <p className="text-[11px] text-slate-400 pt-1">
                  Correct any field the AI misread, then Save corrections —
                  no need to reject the whole document for a small mistake.
                </p>
              </div>
            )}
          </div>

          {govRecord && (
            <div className="bg-white rounded-2xl border border-indigo-200 p-5">
              <div className="flex items-center justify-between mb-1">
                <h2 className="font-semibold text-sm">🏛 AI vs. Official Government Record</h2>
              </div>
              <p className="text-xs text-slate-500 mb-3">
                {govRecord.plot_label} &middot; on file since {govRecord.on_file_since}. Use this
                to check whether the AI extracted the fields correctly.
              </p>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-400 text-[10px] uppercase tracking-wide">
                    <th className="text-left py-1.5">Field</th>
                    <th className="text-left py-1.5">AI extracted</th>
                    <th className="text-left py-1.5">Government record</th>
                    <th className="text-right py-1.5">Match</th>
                  </tr>
                </thead>
                <tbody>
                  {doc.fields.map((f) => {
                    const govKey = f.name as keyof GovernmentRecord;
                    const govValue = govRecord[govKey] as string | undefined;
                    const isMatch =
                      govValue !== undefined &&
                      govValue.toString().trim().toLowerCase() ===
                        f.value.toString().trim().toLowerCase();
                    return (
                      <tr key={f.name} className="border-t border-slate-100">
                        <td className="py-2 text-slate-500">{f.label}</td>
                        <td className="py-2 font-medium">{f.value}</td>
                        <td className="py-2 font-medium">{govValue ?? "—"}</td>
                        <td className="py-2 text-right">
                          {govValue === undefined ? (
                            <span className="text-slate-300">n/a</span>
                          ) : isMatch ? (
                            <span className="text-emerald-600 font-bold">✓ match</span>
                          ) : (
                            <span className="text-rose-600 font-bold">✗ mismatch</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <h2 className="font-semibold text-sm mb-1">Executive decision</h2>
            <p className="text-xs text-slate-500 mb-4">
              Current status:{" "}
              <span className="font-semibold text-slate-700">{doc.status}</span>
            </p>
            {doc.status === "rejected" && doc.rejection_reason && (
              <div className="rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs p-3 mb-3">
                <span className="font-semibold">Rejected:</span> {doc.rejection_reason}
              </div>
            )}
            <button
              onClick={handleApprove}
              disabled={busy}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold rounded-lg py-2.5 mb-2 disabled:opacity-40"
            >
              ✓ Approve as-is
            </button>
            <button
              onClick={handleReject}
              disabled={busy}
              className="w-full bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold rounded-lg py-2.5 mb-2 disabled:opacity-40"
            >
              ✗ Reject
            </button>
            <button
              onClick={handleBlacklistFlag}
              disabled={busy}
              className="w-full border border-amber-400 text-amber-700 hover:bg-amber-50 text-sm font-semibold rounded-lg py-2.5 mb-2 disabled:opacity-40"
            >
              🚩 Flag for admin review
            </button>
            <p className="text-[11px] text-slate-400">
              Approve if correct, Edit fields for small AI mistakes, Reject
              if the AI/upload is clearly wrong, or Flag it to escalate for
              a separate admin decision. Use the boundary tool on the left
              to hand-correct the parcel outline.
            </p>
            {message && (
              <p className="text-xs font-semibold text-indigo-600 mt-3">{message}</p>
            )}
          </div>
        </div>
        </div>
      </main>
    </div>
  );
}
