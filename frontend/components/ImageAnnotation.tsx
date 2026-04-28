"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { AnnotationTools } from "@/components/AnnotationTools";
import {
  Annotation,
  AnnotationDocument,
  AnnotationTool,
  Point,
  annotationLabel,
  annotationToSvgPoints,
  createAnnotationId,
  createBoundingBox,
  createImageId,
  downloadJson,
  exportAnnotationsToCoco,
  flattenPoints,
  getAnnotationBoundingBox,
  isValidBoundingBox,
  isValidPolygon,
  toImagePoint,
  unflattenPoints,
} from "@/utils/annotation";

interface HistoryState {
  past: Annotation[][];
  present: Annotation[];
  future: Annotation[][];
}

const MAX_HISTORY = 100;

function nextHistory(history: HistoryState, nextPresent: Annotation[]) {
  const nextPast = [...history.past, history.present].slice(-MAX_HISTORY);
  return {
    past: nextPast,
    present: nextPresent,
    future: [],
  };
}

export function ImageAnnotation() {
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [imageSrc, setImageSrc] = useState<string>("");
  const [imageName, setImageName] = useState<string>("");
  const [imageId, setImageId] = useState<string>("");
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
  const [activeTool, setActiveTool] = useState<AnnotationTool>("bbox");
  const [draftLabel, setDraftLabel] = useState("region-of-interest");
  const [selectedAnnotationId, setSelectedAnnotationId] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryState>({ past: [], present: [], future: [] });
  const [bboxStart, setBboxStart] = useState<Point | null>(null);
  const [bboxCurrent, setBboxCurrent] = useState<Point | null>(null);
  const [polygonDraft, setPolygonDraft] = useState<Point[]>([]);
  const [status, setStatus] = useState("Upload an image to start annotating.");
  const [isSaving, setIsSaving] = useState(false);

  const annotations = history.present;
  const selectedAnnotation = annotations.find((annotation) => annotation.id === selectedAnnotationId) ?? null;

  const pendingBoundingBox = useMemo(() => {
    if (!bboxStart || !bboxCurrent) {
      return null;
    }
    return createBoundingBox(bboxStart, bboxCurrent);
  }, [bboxCurrent, bboxStart]);

  const applyAnnotations = (nextPresent: Annotation[]) => {
    setHistory((current) => nextHistory(current, nextPresent));
  };

  const replaceAnnotations = (nextPresent: Annotation[]) => {
    setHistory({ past: [], present: nextPresent, future: [] });
  };

  const resetDrafts = () => {
    setBboxStart(null);
    setBboxCurrent(null);
    setPolygonDraft([]);
  };

  const updateSelectedLabel = (label: string) => {
    setDraftLabel(label);
    if (!selectedAnnotationId) {
      return;
    }

    applyAnnotations(
      annotations.map((annotation) =>
        annotation.id === selectedAnnotationId ? { ...annotation, label } : annotation,
      ),
    );
  };

  const loadAnnotations = async (nextImageId: string) => {
    try {
      const response = await fetch(`/api/annotations?imageId=${encodeURIComponent(nextImageId)}`);
      if (response.status === 404) {
        replaceAnnotations([]);
        setStatus("No saved annotations yet for this image.");
        return;
      }

      if (!response.ok) {
        throw new Error("Unable to load annotations.");
      }

      const document = (await response.json()) as AnnotationDocument;
      replaceAnnotations(document.annotations ?? []);
      setStatus(`Loaded ${document.annotations.length} saved annotation(s).`);
    } catch (error) {
      console.error(error);
      replaceAnnotations([]);
      setStatus("Image loaded, but saved annotations could not be fetched.");
    }
  };

  const handleImageSelection = async (file: File) => {
    const nextImageSrc = URL.createObjectURL(file);
    const nextImageId = createImageId(file);

    setImageSrc((current) => {
      if (current) {
        URL.revokeObjectURL(current);
      }
      return nextImageSrc;
    });
    setImageName(file.name);
    setImageId(nextImageId);
    setSelectedAnnotationId(null);
    resetDrafts();
    await loadAnnotations(nextImageId);
  };

  const getImagePointFromEvent = (event: PointerEvent | ReactPointerEvent<HTMLDivElement>) => {
    if (!overlayRef.current || !imageSize.width || !imageSize.height) {
      return null;
    }

    const rect = overlayRef.current.getBoundingClientRect();
    return toImagePoint(event.clientX, event.clientY, rect, imageSize.width, imageSize.height);
  };

  const commitBoundingBox = () => {
    if (!pendingBoundingBox || !isValidBoundingBox(pendingBoundingBox)) {
      resetDrafts();
      return;
    }

    const annotation: Annotation = {
      id: createAnnotationId(),
      type: "bbox",
      coordinates: pendingBoundingBox,
      label: draftLabel.trim() || "unlabeled-region",
      timestamp: new Date().toISOString(),
    };

    const nextAnnotations = [...annotations, annotation];
    applyAnnotations(nextAnnotations);
    setSelectedAnnotationId(annotation.id);
    setStatus("Bounding box added.");
    resetDrafts();
  };

  const commitPolygon = () => {
    if (!isValidPolygon(polygonDraft)) {
      setStatus("A polygon needs at least three points.");
      return;
    }

    const annotation: Annotation = {
      id: createAnnotationId(),
      type: "polygon",
      coordinates: flattenPoints(polygonDraft),
      label: draftLabel.trim() || "unlabeled-region",
      timestamp: new Date().toISOString(),
    };

    const nextAnnotations = [...annotations, annotation];
    applyAnnotations(nextAnnotations);
    setSelectedAnnotationId(annotation.id);
    setPolygonDraft([]);
    setStatus("Polygon annotation added.");
  };

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!imageSrc) {
      return;
    }

    if (activeTool === "bbox") {
      const point = getImagePointFromEvent(event);
      if (!point) {
        return;
      }
      setSelectedAnnotationId(null);
      setBboxStart(point);
      setBboxCurrent(point);
      event.currentTarget.setPointerCapture(event.pointerId);
    }
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (activeTool !== "bbox" || !bboxStart) {
      return;
    }
    const point = getImagePointFromEvent(event);
    if (point) {
      setBboxCurrent(point);
    }
  };

  const handlePointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (activeTool === "bbox" && bboxStart) {
      const point = getImagePointFromEvent(event);
      if (point) {
        setBboxCurrent(point);
      }
      commitBoundingBox();
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const handleOverlayClick = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (activeTool !== "polygon" || !imageSrc || !overlayRef.current) {
      return;
    }

    const point = getImagePointFromEvent(event.nativeEvent as unknown as PointerEvent);
    if (!point) {
      return;
    }

    if (polygonDraft.length >= 3) {
      const first = polygonDraft[0];
      const distance = Math.hypot(first.x - point.x, first.y - point.y);
      if (distance < 18) {
        commitPolygon();
        return;
      }
    }

    setPolygonDraft((current) => [...current, point]);
    setStatus(`Polygon point ${polygonDraft.length + 1} added.`);
  };

  const handleUndo = () => {
    setHistory((current) => {
      if (current.past.length === 0) {
        return current;
      }
      const previous = current.past[current.past.length - 1];
      return {
        past: current.past.slice(0, -1),
        present: previous,
        future: [current.present, ...current.future].slice(0, MAX_HISTORY),
      };
    });
    setStatus("Undid last annotation change.");
  };

  const handleRedo = () => {
    setHistory((current) => {
      if (current.future.length === 0) {
        return current;
      }
      const [nextPresent, ...remainingFuture] = current.future;
      return {
        past: [...current.past, current.present].slice(-MAX_HISTORY),
        present: nextPresent,
        future: remainingFuture,
      };
    });
    setStatus("Reapplied annotation change.");
  };

  const handleDeleteSelected = () => {
    if (!selectedAnnotationId) {
      return;
    }
    applyAnnotations(annotations.filter((annotation) => annotation.id !== selectedAnnotationId));
    setSelectedAnnotationId(null);
    setStatus("Selected annotation deleted.");
  };

  const handleSave = async () => {
    if (!imageId || !imageName || !imageSize.width || !imageSize.height) {
      setStatus("Choose an image before saving annotations.");
      return;
    }

    const now = new Date().toISOString();
    const document: AnnotationDocument = {
      imageId,
      imageName,
      imageWidth: imageSize.width,
      imageHeight: imageSize.height,
      imageUrl: imageSrc,
      annotations,
      createdAt: now,
      updatedAt: now,
    };

    try {
      setIsSaving(true);
      const response = await fetch("/api/annotations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(document),
      });

      if (!response.ok) {
        throw new Error("Save failed.");
      }

      setStatus(`Saved ${annotations.length} annotation(s) to the backend.`);
    } catch (error) {
      console.error(error);
      setStatus("Annotations could not be saved.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleExport = () => {
    if (!imageId || !imageName || !imageSize.width || !imageSize.height) {
      setStatus("Choose an image before exporting annotations.");
      return;
    }

    const document: AnnotationDocument = {
      imageId,
      imageName,
      imageWidth: imageSize.width,
      imageHeight: imageSize.height,
      imageUrl: imageSrc,
      annotations,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    downloadJson(`${imageId}-annotations.coco.json`, exportAnnotationsToCoco(document));
    setStatus("COCO export downloaded.");
  };

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isTyping = target?.tagName === "INPUT" || target?.tagName === "TEXTAREA";

      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        if (event.shiftKey) {
          handleRedo();
        } else {
          handleUndo();
        }
        return;
      }

      if (isTyping) {
        return;
      }

      if (event.key.toLowerCase() === "b") {
        setActiveTool("bbox");
      } else if (event.key.toLowerCase() === "p") {
        setActiveTool("polygon");
      } else if (event.key.toLowerCase() === "v") {
        setActiveTool("select");
      } else if (event.key === "Delete" || event.key === "Backspace") {
        handleDeleteSelected();
      } else if (event.key === "Enter" && polygonDraft.length >= 3) {
        commitPolygon();
      } else if (event.key === "Escape") {
        resetDrafts();
        setStatus("Draft annotation cleared.");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [polygonDraft.length, selectedAnnotationId, annotations]);

  useEffect(() => {
    return () => {
      if (imageSrc) {
        URL.revokeObjectURL(imageSrc);
      }
    };
  }, [imageSrc]);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-5">
        <div className="rounded-[2rem] bg-white p-5 shadow-xl ring-1 ring-slate-200">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-2xl font-black text-slate-900">Annotate image regions</h2>
              <p className="mt-1 text-sm text-slate-600">Draw bounding boxes or polygons, add labels, and save feedback for later review.</p>
            </div>
            <button
              className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white"
              onClick={() => fileInputRef.current?.click()}
              type="button"
            >
              Upload image
            </button>
          </div>

          <input
            ref={fileInputRef}
            accept="image/*"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                void handleImageSelection(file);
              }
              event.target.value = "";
            }}
            type="file"
          />

          <div className="mt-5 rounded-3xl bg-slate-950/95 p-3 sm:p-4">
            {imageSrc ? (
              <div
                ref={overlayRef}
                className={`relative mx-auto overflow-hidden rounded-[1.5rem] bg-slate-900 ${activeTool !== "select" ? "cursor-crosshair" : "cursor-default"}`}
                onClick={handleOverlayClick}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                style={{ touchAction: "none" }}
              >
                <img
                  alt="Annotation target"
                  className="max-h-[70vh] w-full object-contain"
                  onLoad={(event) => {
                    setImageSize({
                      width: event.currentTarget.naturalWidth,
                      height: event.currentTarget.naturalHeight,
                    });
                  }}
                  src={imageSrc}
                />

                <svg
                  className="absolute inset-0 h-full w-full"
                  preserveAspectRatio="none"
                  viewBox={`0 0 ${imageSize.width || 1} ${imageSize.height || 1}`}
                >
                  {annotations.map((annotation, index) => {
                    const isSelected = annotation.id === selectedAnnotationId;
                    const [x, y, width, height] = getAnnotationBoundingBox(annotation);
                    return (
                      <g
                        key={annotation.id}
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedAnnotationId(annotation.id);
                          setDraftLabel(annotation.label);
                          setActiveTool("select");
                        }}
                      >
                        {annotation.type === "bbox" ? (
                          <rect
                            fill={isSelected ? "rgba(245, 158, 11, 0.15)" : "rgba(14, 165, 233, 0.12)"}
                            height={height}
                            rx={10}
                            stroke={isSelected ? "#f59e0b" : "#38bdf8"}
                            strokeWidth={isSelected ? 4 : 3}
                            width={width}
                            x={x}
                            y={y}
                          />
                        ) : (
                          <polygon
                            fill={isSelected ? "rgba(245, 158, 11, 0.18)" : "rgba(16, 185, 129, 0.15)"}
                            points={annotationToSvgPoints(annotation)}
                            stroke={isSelected ? "#f59e0b" : "#10b981"}
                            strokeLinejoin="round"
                            strokeWidth={isSelected ? 4 : 3}
                          />
                        )}

                        <rect fill="rgba(15, 23, 42, 0.9)" height={28} rx={8} width={180} x={x} y={Math.max(8, y - 32)} />
                        <text fill="white" fontSize="14" fontWeight="700" x={x + 10} y={Math.max(26, y - 14)}>
                          {annotationLabel(annotation, index)}
                        </text>
                      </g>
                    );
                  })}

                  {pendingBoundingBox && (
                    <rect
                      fill="rgba(245, 158, 11, 0.15)"
                      height={pendingBoundingBox[3]}
                      stroke="#f59e0b"
                      strokeDasharray="10 8"
                      strokeWidth={3}
                      width={pendingBoundingBox[2]}
                      x={pendingBoundingBox[0]}
                      y={pendingBoundingBox[1]}
                    />
                  )}

                  {polygonDraft.length > 0 && (
                    <>
                      <polyline
                        fill="rgba(250, 204, 21, 0.12)"
                        points={polygonDraft.map((point) => `${point.x},${point.y}`).join(" ")}
                        stroke="#facc15"
                        strokeDasharray="8 6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={3}
                      />
                      {polygonDraft.map((point, index) => (
                        <circle
                          key={`${point.x}-${point.y}-${index}`}
                          cx={point.x}
                          cy={point.y}
                          fill={index === 0 && polygonDraft.length >= 3 ? "#22c55e" : "#facc15"}
                          r={7}
                        />
                      ))}
                    </>
                  )}
                </svg>
              </div>
            ) : (
              <div className="flex min-h-[420px] items-center justify-center rounded-[1.5rem] border border-dashed border-slate-600 bg-slate-900 text-center text-slate-300">
                <div className="max-w-md px-6">
                  <p className="text-lg font-semibold">No image selected</p>
                  <p className="mt-2 text-sm text-slate-400">Upload an image to start drawing bounding boxes, polygon masks, and labels.</p>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="rounded-[2rem] bg-white p-5 shadow-xl ring-1 ring-slate-200">
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
            <span className="rounded-full bg-amber-100 px-3 py-1 font-semibold text-amber-900">{annotations.length} annotation(s)</span>
            <span className="rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-700">Active tool: {activeTool}</span>
            {imageName && <span className="rounded-full bg-sky-100 px-3 py-1 font-semibold text-sky-900">{imageName}</span>}
          </div>
          <p aria-live="polite" className="mt-4 text-sm text-slate-700">
            {status}
          </p>
        </div>
      </div>

      <div className="space-y-6">
        <AnnotationTools
          activeTool={activeTool}
          canRedo={history.future.length > 0}
          canUndo={history.past.length > 0}
          draftLabel={draftLabel}
          hasImage={Boolean(imageSrc)}
          isPolygonOpen={polygonDraft.length >= 3}
          isSaving={isSaving}
          onDeleteSelected={handleDeleteSelected}
          onExport={handleExport}
          onFinishPolygon={commitPolygon}
          onLabelChange={updateSelectedLabel}
          onRedo={handleRedo}
          onSave={handleSave}
          onToolChange={setActiveTool}
          onUndo={handleUndo}
          selectedCount={selectedAnnotationId ? 1 : 0}
        />

        <div className="rounded-[2rem] bg-white p-5 shadow-xl ring-1 ring-slate-200">
          <h3 className="text-lg font-black text-slate-900">Annotations</h3>
          <div className="mt-4 space-y-3">
            {annotations.length === 0 ? (
              <p className="text-sm text-slate-500">No annotations yet. Draw on the image to add your first review marker.</p>
            ) : (
              annotations.map((annotation, index) => {
                const bbox = getAnnotationBoundingBox(annotation);
                const isSelected = annotation.id === selectedAnnotationId;
                return (
                  <button
                    key={annotation.id}
                    className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                      isSelected
                        ? "border-amber-400 bg-amber-50"
                        : "border-slate-200 bg-slate-50 hover:border-slate-300"
                    }`}
                    onClick={() => {
                      setSelectedAnnotationId(annotation.id);
                      setDraftLabel(annotation.label);
                    }}
                    type="button"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-900">{annotationLabel(annotation, index)}</p>
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{annotation.type}</p>
                      </div>
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-600">
                        {Math.round(bbox[2])} x {Math.round(bbox[3])}
                      </span>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {selectedAnnotation && (
            <div className="mt-5 rounded-2xl bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-700">Selected annotation</p>
              <label className="mt-3 block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Edit label</span>
                <input
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-amber-400"
                  onChange={(event) => updateSelectedLabel(event.target.value)}
                  value={draftLabel}
                />
              </label>
              {selectedAnnotation.type === "polygon" && (
                <p className="mt-3 text-xs text-slate-500">
                  {unflattenPoints(selectedAnnotation.coordinates).length} polygon points
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
