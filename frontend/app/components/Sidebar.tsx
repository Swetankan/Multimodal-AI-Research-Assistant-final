"use client";

import { Bot, FileText, PanelLeftClose, PanelLeftOpen, SlidersHorizontal, X } from "lucide-react";
import { DocumentMetadata, ModelProvider } from "@/lib/api";
import { cn } from "@/lib/utils";

export type QueryMode = "current" | "selected" | "all";

interface SidebarProps {
  provider: ModelProvider;
  model: string;
  models: string[];
  chunkSize: number;
  topK: number;
  denseWeight: number;
  bm25Weight: number;
  candidatePoolSize: number;
  documents: DocumentMetadata[];
  selectedDocumentIds: string[];
  queryMode: QueryMode;
  isOpen: boolean;
  isCollapsed: boolean;
  onClose: () => void;
  onToggleCollapse: () => void;
  onProviderChange: (value: ModelProvider) => void;
  onModelChange: (value: string) => void;
  onChunkSizeChange: (value: number) => void;
  onTopKChange: (value: number) => void;
  onDenseWeightChange: (value: number) => void;
  onBm25WeightChange: (value: number) => void;
  onCandidatePoolSizeChange: (value: number) => void;
  onDocumentSelectionChange: (documentIds: string[]) => void;
  onQueryModeChange: (value: QueryMode) => void;
}

export function Sidebar({
  provider,
  model,
  models,
  chunkSize,
  topK,
  denseWeight,
  bm25Weight,
  candidatePoolSize,
  documents,
  selectedDocumentIds,
  queryMode,
  isOpen,
  isCollapsed,
  onClose,
  onToggleCollapse,
  onProviderChange,
  onModelChange,
  onChunkSizeChange,
  onTopKChange,
  onDenseWeightChange,
  onBm25WeightChange,
  onCandidatePoolSizeChange,
  onDocumentSelectionChange,
  onQueryModeChange
}: SidebarProps) {
  const selectedDocuments = new Set(selectedDocumentIds);

  const toggleDocument = (documentId: string) => {
    const next = selectedDocuments.has(documentId)
      ? selectedDocumentIds.filter((item) => item !== documentId)
      : [...selectedDocumentIds, documentId];
    onDocumentSelectionChange(next);
  };

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className={cn(
          "fixed inset-0 z-30 bg-black/60 backdrop-blur-sm transition-opacity duration-300 lg:hidden",
          isOpen ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
        )}
        onClick={onClose}
      />

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex shrink-0 flex-col overflow-hidden",
          "border-r border-emerald-500/10 bg-black/65 backdrop-blur-2xl backdrop-saturate-150",
          "transition-[width,transform] duration-300 ease-in-out",
          "lg:static lg:z-0",
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
          isCollapsed ? "w-[68px]" : "w-[272px]"
        )}
        style={{ boxShadow: "inset -1px 0 0 0 rgba(16,185,129,0.08)" }}
      >
        {/* ── Header row ── */}
        <div className="flex h-14 shrink-0 items-center justify-between px-3">
          {/* Logo / icon — always visible */}
          <button
            type="button"
            onClick={onToggleCollapse}
            aria-label={isCollapsed ? "Expand controls" : "Collapse controls"}
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl",
              "border border-white/10 bg-white/5 text-slate-300",
              "transition-colors hover:bg-white/10 hover:text-emerald-400"
            )}
          >
            {isCollapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </button>

          {/* Title — fades out when collapsed */}
          <div
            className={cn(
              "ml-2 flex min-w-0 flex-1 flex-col transition-[opacity,transform] duration-200",
              isCollapsed ? "pointer-events-none -translate-x-1 opacity-0" : "translate-x-0 opacity-100"
            )}
          >
            <span className="text-[10px] uppercase tracking-[0.28em] text-slate-500">Controls</span>
            <span className="text-sm font-semibold text-slate-100">Settings</span>
          </div>

          {/* Mobile close button */}
          <button
            type="button"
            className={cn(
              "ml-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl",
              "border border-white/10 bg-white/5 text-slate-300",
              "transition-colors hover:bg-white/10 lg:hidden",
              isCollapsed ? "opacity-0 pointer-events-none" : "opacity-100"
            )}
            onClick={onClose}
            aria-label="Close controls"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Thin divider */}
        <div className="mx-3 h-px bg-white/5" />

        {/* ── Collapsed icon strip ── */}
        <div
          className={cn(
            "flex flex-col items-center gap-3 px-3 pt-4",
            "transition-[opacity,transform] duration-200",
            isCollapsed ? "pointer-events-auto opacity-100 translate-x-0" : "pointer-events-none absolute opacity-0 -translate-x-2"
          )}
        >
          <button
            type="button"
            onClick={onToggleCollapse}
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-400 transition hover:bg-emerald-500/20"
            aria-label="Expand settings"
          >
            <SlidersHorizontal className="h-4.5 w-4.5" />
          </button>
          {documents.length > 0 && (
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-400">
              <FileText className="h-4 w-4" />
            </div>
          )}
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-400">
            <Bot className="h-4 w-4" />
          </div>
        </div>

        {/* ── Full content panel ── */}
        <div
          className={cn(
            "scrollbar-thin flex-1 overflow-y-auto px-3 pb-5 pt-3",
            "transition-[opacity,transform] duration-200",
            isCollapsed ? "pointer-events-none opacity-0 translate-x-2" : "pointer-events-auto opacity-100 translate-x-0"
          )}
        >
          <p className="mb-4 text-[13px] leading-6 text-slate-500">
            Tune retrieval settings and switch models anytime.
          </p>

          <div className="space-y-3">
            {/* Documents card */}
            {documents.length > 0 && (
              <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-3.5">
                <label className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <FileText className="h-3.5 w-3.5 text-emerald-400" />
                  Documents
                </label>

                {/* Query mode toggle */}
                <div className="mb-3 grid grid-cols-3 gap-1 rounded-xl border border-white/8 bg-black/30 p-1 text-xs">
                  {(["current", "selected", "all"] as const).map((value) => (
                    <button
                      key={value}
                      type="button"
                      className={cn(
                        "rounded-lg py-1.5 capitalize text-slate-400 transition-all duration-150",
                        queryMode === value
                          ? "bg-emerald-500/15 text-emerald-300 shadow-sm"
                          : "hover:bg-white/5 hover:text-slate-200"
                      )}
                      onClick={() => onQueryModeChange(value)}
                    >
                      {value}
                    </button>
                  ))}
                </div>

                {/* Document list */}
                <div className="space-y-1.5">
                  {documents.map((document) => (
                    <label
                      key={document.document_id}
                      className="flex cursor-pointer items-start gap-2.5 rounded-xl border border-white/6 bg-black/20 p-2.5 text-xs text-slate-300 transition-colors hover:bg-white/[0.04]"
                    >
                      <input
                        type="checkbox"
                        className="mt-0.5 h-3.5 w-3.5 shrink-0 rounded accent-emerald-400"
                        checked={selectedDocuments.has(document.document_id)}
                        onChange={() => toggleDocument(document.document_id)}
                      />
                      <span className="min-w-0">
                        <span className="block truncate font-medium text-slate-200">
                          {document.filename}
                        </span>
                        <span className="mt-0.5 block text-[11px] text-slate-500">
                          {document.chunk_count} chunks
                          {document.extraction?.total_pages ? ` · ${document.extraction.total_pages} pages` : ""}
                        </span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Provider card */}
            <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-3.5">
              <label className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <Bot className="h-3.5 w-3.5 text-emerald-400" />
                Provider
              </label>
              <select
                value={provider}
                className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-slate-200 outline-none transition focus:border-emerald-500/40 focus:ring-1 focus:ring-emerald-500/20"
                onChange={(e) => onProviderChange(e.target.value as ModelProvider)}
              >
                <option value="openrouter">OpenRouter</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>

            {/* Model card */}
            <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-3.5">
              <label className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <SlidersHorizontal className="h-3.5 w-3.5 text-emerald-400" />
                Model
              </label>
              <select
                value={model}
                className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-slate-200 outline-none transition focus:border-emerald-500/40 focus:ring-1 focus:ring-emerald-500/20"
                onChange={(e) => onModelChange(e.target.value)}
              >
                {models.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>

            {/* Retrieval sliders card */}
            <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-3.5">
              <label className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <SlidersHorizontal className="h-3.5 w-3.5 text-emerald-400" />
                Retrieval
              </label>

              <div className="space-y-4">
                {/* Chunk size */}
                <SliderRow
                  label="Chunk size"
                  value={chunkSize}
                  display={String(chunkSize)}
                  min={300}
                  max={1200}
                  step={50}
                  onChange={onChunkSizeChange}
                />

                {/* Top-k */}
                <SliderRow
                  label="Top-k"
                  value={topK}
                  display={String(topK)}
                  min={2}
                  max={8}
                  step={1}
                  onChange={onTopKChange}
                />

                {/* Dense weight */}
                <SliderRow
                  label="Dense weight"
                  value={denseWeight}
                  display={denseWeight.toFixed(2)}
                  min={0}
                  max={1}
                  step={0.05}
                  onChange={onDenseWeightChange}
                />

                {/* BM25 weight */}
                <SliderRow
                  label="BM25 weight"
                  value={bm25Weight}
                  display={bm25Weight.toFixed(2)}
                  min={0}
                  max={1}
                  step={0.05}
                  onChange={onBm25WeightChange}
                />

                {/* Candidate pool */}
                <SliderRow
                  label="Candidate pool"
                  value={candidatePoolSize}
                  display={String(candidatePoolSize)}
                  min={8}
                  max={60}
                  step={4}
                  onChange={onCandidatePoolSizeChange}
                />

                {/* Reranker toggle (disabled) */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Reranker</span>
                  <span className="rounded-md border border-white/8 bg-white/5 px-2 py-0.5 text-[10px] text-slate-600">
                    disabled
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

/* ── Reusable slider row ── */
function SliderRow({
  label,
  value,
  display,
  min,
  max,
  step,
  onChange
}: {
  label: string;
  value: number;
  display: string;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs text-slate-400">{label}</span>
        <span className="font-mono text-xs tabular-nums text-emerald-400">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        className="slider-emerald w-full"
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}
