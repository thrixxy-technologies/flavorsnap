import { AnnotationTool } from "@/utils/annotation";

interface AnnotationToolsProps {
  activeTool: AnnotationTool;
  draftLabel: string;
  canUndo: boolean;
  canRedo: boolean;
  hasImage: boolean;
  isPolygonOpen: boolean;
  selectedCount: number;
  isSaving: boolean;
  onToolChange: (tool: AnnotationTool) => void;
  onLabelChange: (value: string) => void;
  onUndo: () => void;
  onRedo: () => void;
  onFinishPolygon: () => void;
  onSave: () => void;
  onExport: () => void;
  onDeleteSelected: () => void;
}

const toolButtonClass = (active: boolean) =>
  `rounded-2xl border px-4 py-3 text-sm font-semibold transition ${
    active
      ? "border-amber-500 bg-amber-500 text-white shadow-lg"
      : "border-slate-200 bg-white text-slate-700 hover:border-amber-300 hover:bg-amber-50"
  }`;

export function AnnotationTools({
  activeTool,
  draftLabel,
  canUndo,
  canRedo,
  hasImage,
  isPolygonOpen,
  selectedCount,
  isSaving,
  onToolChange,
  onLabelChange,
  onUndo,
  onRedo,
  onFinishPolygon,
  onSave,
  onExport,
  onDeleteSelected,
}: AnnotationToolsProps) {
  return (
    <div className="space-y-4 rounded-[2rem] bg-white p-4 shadow-xl ring-1 ring-slate-200">
      <div>
        <p className="text-sm font-bold uppercase tracking-[0.2em] text-slate-500">Tools</p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <button className={toolButtonClass(activeTool === "select")} onClick={() => onToolChange("select")} type="button">
            Select
          </button>
          <button className={toolButtonClass(activeTool === "bbox")} onClick={() => onToolChange("bbox")} type="button" disabled={!hasImage}>
            Bounding Box
          </button>
          <button className={toolButtonClass(activeTool === "polygon")} onClick={() => onToolChange("polygon")} type="button" disabled={!hasImage}>
            Polygon
          </button>
        </div>
      </div>

      <label className="block">
        <span className="mb-2 block text-sm font-semibold text-slate-700">Label</span>
        <input
          className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-amber-400"
          placeholder="e.g. predicted soup"
          value={draftLabel}
          onChange={(event) => onLabelChange(event.target.value)}
        />
      </label>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <button className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white disabled:bg-slate-300" onClick={onUndo} type="button" disabled={!canUndo}>
          Undo
        </button>
        <button className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white disabled:bg-slate-300" onClick={onRedo} type="button" disabled={!canRedo}>
          Redo
        </button>
        <button className="rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white disabled:bg-emerald-300" onClick={onSave} type="button" disabled={!hasImage || isSaving}>
          {isSaving ? "Saving..." : "Save"}
        </button>
        <button className="rounded-2xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white disabled:bg-sky-300" onClick={onExport} type="button" disabled={!hasImage}>
          Export COCO
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <button
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900 disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
          onClick={onFinishPolygon}
          type="button"
          disabled={!isPolygonOpen}
        >
          Finish Polygon
        </button>
        <button
          className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
          onClick={onDeleteSelected}
          type="button"
          disabled={selectedCount === 0}
        >
          Delete Selected
        </button>
      </div>

      <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
        <p className="font-semibold text-slate-700">Keyboard shortcuts</p>
        <p className="mt-2">`B` box, `P` polygon, `V` select, `Delete` remove, `Ctrl/Cmd+Z` undo, `Shift+Ctrl/Cmd+Z` redo, `Enter` finish polygon, `Esc` cancel draft.</p>
      </div>
    </div>
  );
}
