export type AnnotationType = "bbox" | "polygon";
export type AnnotationTool = "select" | AnnotationType;

export interface Point {
  x: number;
  y: number;
}

export interface Annotation {
  id: string;
  type: AnnotationType;
  coordinates: number[];
  label: string;
  confidence?: number;
  timestamp: string;
}

export interface AnnotationDocument {
  imageId: string;
  imageName: string;
  imageWidth: number;
  imageHeight: number;
  imageUrl?: string;
  annotations: Annotation[];
  createdAt: string;
  updatedAt: string;
}

export interface CocoExport {
  info: {
    description: string;
    version: string;
    year: number;
    created_at: string;
  };
  images: Array<{
    id: string;
    file_name: string;
    width: number;
    height: number;
  }>;
  annotations: Array<{
    id: number;
    image_id: string;
    category_id: number;
    segmentation: number[][];
    area: number;
    bbox: number[];
    iscrowd: 0;
    confidence?: number;
  }>;
  categories: Array<{
    id: number;
    name: string;
    supercategory: string;
  }>;
}

export function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export function createAnnotationId() {
  return `ann_${Math.random().toString(36).slice(2, 10)}`;
}

export function createImageId(file: File) {
  const baseName = file.name.replace(/[^a-zA-Z0-9_-]/g, "-").toLowerCase();
  return `${baseName}-${file.size}-${file.lastModified}`;
}

export function toImagePoint(
  clientX: number,
  clientY: number,
  rect: DOMRect,
  imageWidth: number,
  imageHeight: number,
): Point {
  const x = clamp(((clientX - rect.left) / rect.width) * imageWidth, 0, imageWidth);
  const y = clamp(((clientY - rect.top) / rect.height) * imageHeight, 0, imageHeight);
  return { x, y };
}

export function createBoundingBox(start: Point, end: Point): number[] {
  const x = Math.min(start.x, end.x);
  const y = Math.min(start.y, end.y);
  const width = Math.abs(end.x - start.x);
  const height = Math.abs(end.y - start.y);
  return [x, y, width, height];
}

export function isValidBoundingBox(coordinates: number[]) {
  return coordinates.length === 4 && coordinates[2] > 4 && coordinates[3] > 4;
}

export function isValidPolygon(points: Point[]) {
  return points.length >= 3;
}

export function flattenPoints(points: Point[]) {
  return points.flatMap((point) => [point.x, point.y]);
}

export function unflattenPoints(coordinates: number[]): Point[] {
  const points: Point[] = [];
  for (let index = 0; index < coordinates.length; index += 2) {
    points.push({ x: coordinates[index], y: coordinates[index + 1] });
  }
  return points;
}

export function polygonToBoundingBox(coordinates: number[]): number[] {
  const points = unflattenPoints(coordinates);
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const maxX = Math.max(...xs);
  const maxY = Math.max(...ys);
  return [minX, minY, maxX - minX, maxY - minY];
}

export function getAnnotationBoundingBox(annotation: Annotation) {
  return annotation.type === "bbox"
    ? annotation.coordinates
    : polygonToBoundingBox(annotation.coordinates);
}

export function annotationToSvgPoints(annotation: Annotation) {
  return unflattenPoints(annotation.coordinates)
    .map((point) => `${point.x},${point.y}`)
    .join(" ");
}

export function polygonArea(coordinates: number[]) {
  const points = unflattenPoints(coordinates);
  let area = 0;
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index];
    const next = points[(index + 1) % points.length];
    area += current.x * next.y - next.x * current.y;
  }
  return Math.abs(area / 2);
}

export function annotationArea(annotation: Annotation) {
  if (annotation.type === "bbox") {
    return annotation.coordinates[2] * annotation.coordinates[3];
  }
  return polygonArea(annotation.coordinates);
}

export function annotationToCocoSegmentation(annotation: Annotation) {
  if (annotation.type === "polygon") {
    return [annotation.coordinates];
  }

  const [x, y, width, height] = annotation.coordinates;
  return [[x, y, x + width, y, x + width, y + height, x, y + height]];
}

export function exportAnnotationsToCoco(document: AnnotationDocument): CocoExport {
  const categoryMap = new Map<string, number>();

  document.annotations.forEach((annotation) => {
    if (!categoryMap.has(annotation.label)) {
      categoryMap.set(annotation.label, categoryMap.size + 1);
    }
  });

  return {
    info: {
      description: "FlavorSnap image annotations",
      version: "1.0.0",
      year: new Date().getFullYear(),
      created_at: new Date().toISOString(),
    },
    images: [
      {
        id: document.imageId,
        file_name: document.imageName,
        width: document.imageWidth,
        height: document.imageHeight,
      },
    ],
    annotations: document.annotations.map((annotation, index) => ({
      id: index + 1,
      image_id: document.imageId,
      category_id: categoryMap.get(annotation.label) ?? 1,
      segmentation: annotationToCocoSegmentation(annotation),
      area: annotationArea(annotation),
      bbox: getAnnotationBoundingBox(annotation),
      iscrowd: 0 as const,
      confidence: annotation.confidence,
    })),
    categories: Array.from(categoryMap.entries()).map(([name, id]) => ({
      id,
      name,
      supercategory: "food",
    })),
  };
}

export function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function annotationLabel(annotation: Annotation, index: number) {
  return annotation.label || `${annotation.type.toUpperCase()} ${index + 1}`;
}
