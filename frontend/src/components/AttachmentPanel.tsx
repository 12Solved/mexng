import { useState } from "react"
import type { Attachment } from '../types/email';
import { downloadAttachment, downloadAllAttachments } from "../services/emailServices"
import DownloadIcon from './DownloadIcon';
import SpinnerIcon from './SpinnerIcon';

const TYPE_MAP: Record<string, { label: string; bg: string; color: string }> = {
  "application/pdf": { label: "PDF", bg: "#FAECE7", color: "#993C1D" },
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": { label: "XLS", bg: "#EAF3DE", color: "#3B6D11" },
  "image/jpeg": { label: "JPG", bg: "#E6F1FB", color: "#185FA5" },
  "image/png": { label: "PNG", bg: "#E6F1FB", color: "#185FA5" },
  "text/plain": { label: "TXT", bg: "#F1EFE8", color: "#5F5E5A" },
  "text/csv": { label: "CSV", bg: "#EAF3DE", color: "#3B6D11" },
  "application/zip": { label: "ZIP", bg: "#FAEEDA", color: "#854F0B" },
}

function getTypeInfo(contentType: string | null) {
  if (contentType && TYPE_MAP[contentType]) return TYPE_MAP[contentType]
  const ext = (contentType ?? "bin").split("/").pop()?.toUpperCase().slice(0, 4) ?? "BIN"
  return { label: ext, bg: "#F1EFE8", color: "#5F5E5A" }
}

function formatSize(bytes: number | null): string {
  if (bytes == null) return "unknown size"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1_048_576).toFixed(1)} MB`
}

export function AttachmentsPanel({ emailId, attachments }: { emailId: number; attachments: Attachment[] }) {
  const [saved, setSaved] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState<Set<number>>(new Set())
  const [allLoading, setAllLoading] = useState(false)

  const handleDownload = async (att: Attachment) => {
    setLoading(prev => new Set([...prev, att.id]))
    try {
      await downloadAttachment(emailId, att.id, att.filename)
      setSaved(prev => new Set([...prev, att.id]))
      setTimeout(() => setSaved(prev => { const n = new Set(prev); n.delete(att.id); return n }), 2500)
    } catch (e) {
      console.error("Download failed", e)
    } finally {
      setLoading(prev => { const n = new Set(prev); n.delete(att.id); return n })
    }
  }
  const downloadAll = async () => {
    setAllLoading(true)
    try {
      await downloadAllAttachments(emailId, attachments)
    } catch (e) {
      console.error("Download all failed", e)
    } finally {
      setAllLoading(false)
    }
  }


  if (!attachments.length) return null

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-widest">
          {attachments.length} attachment{attachments.length !== 1 ? "s" : ""}
        </span>
        <button
          onClick={downloadAll}
          disabled={allLoading}
          className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md border border-border transition-colors cursor-pointer ${
            allLoading ? "opacity-50 cursor-wait" : "hover:bg-muted hover:border-input"
          }`}
        >
          {allLoading ? <SpinnerIcon /> : <DownloadIcon />}
          {allLoading ? "Downloading…" : "Download all"}
        </button>
      </div>

      <div className="flex flex-col gap-1.5">
        {attachments.map(att => {
          const ti = getTypeInfo(att.content_type)
          const isSaved = saved.has(att.id)
          const isLoading = loading.has(att.id)
          return (
            <div key={att.id} className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg border border-border hover:border-border/80 transition-colors">
              <div
                className="w-8 h-8 rounded-md flex items-center justify-center text-[11px] font-medium shrink-0"
                style={{ background: ti.bg, color: ti.color }}
              >
                {ti.label}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{att.filename}</p>
                <p className="text-xs text-muted-foreground flex gap-2 mt-0.5">
                  <span>{formatSize(att.size)}</span>
                  <span>{att.content_type ?? "unknown type"}</span>
                </p>
              </div>
              <button
                onClick={() => handleDownload(att)}
                disabled={isLoading || isSaved}
                className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-md border transition-colors shrink-0 cursor-pointer ${
                  isSaved
                    ? "border-green-300 text-green-700"
                    : isLoading
                      ? "border-border text-muted-foreground opacity-50 cursor-wait"
                      : "border-border text-muted-foreground hover:text-foreground hover:border-input"
                }`}
              >
                {isSaved ? <CheckIcon /> : isLoading ? <SpinnerIcon /> : <DownloadIcon />}
                {isSaved ? "Saved" : isLoading ? "Downloading…" : "Download"}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}



function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 8l3.5 3.5L13 4" />
    </svg>
  )
}
