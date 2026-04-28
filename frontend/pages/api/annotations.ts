import type { NextApiRequest, NextApiResponse } from "next";
import fs from "fs/promises";
import path from "path";
import { exportAnnotationsToCoco } from "@/utils/annotation";

interface Annotation {
  id: string;
  type: "bbox" | "polygon";
  coordinates: number[];
  label: string;
  confidence?: number;
  timestamp: string;
}

interface AnnotationDocument {
  imageId: string;
  imageName: string;
  imageWidth: number;
  imageHeight: number;
  imageUrl?: string;
  annotations: Annotation[];
  createdAt: string;
  updatedAt: string;
}

type Data =
  | AnnotationDocument
  | { documents: AnnotationDocument[] }
  | { saved: true; document: AnnotationDocument }
  | { error: string };

const storageDir = path.join(process.cwd(), "data");
const storageFile = path.join(storageDir, "annotations.json");

async function ensureStorage() {
  await fs.mkdir(storageDir, { recursive: true });
  try {
    await fs.access(storageFile);
  } catch {
    await fs.writeFile(storageFile, "[]", "utf8");
  }
}

async function readDocuments(): Promise<AnnotationDocument[]> {
  await ensureStorage();
  const raw = await fs.readFile(storageFile, "utf8");
  return JSON.parse(raw) as AnnotationDocument[];
}

async function writeDocuments(documents: AnnotationDocument[]) {
  await ensureStorage();
  await fs.writeFile(storageFile, JSON.stringify(documents, null, 2), "utf8");
}

function sanitizeAnnotationDocument(document: AnnotationDocument): AnnotationDocument {
  return {
    imageId: String(document.imageId ?? "").trim(),
    imageName: String(document.imageName ?? "image").trim(),
    imageWidth: Number(document.imageWidth ?? 0),
    imageHeight: Number(document.imageHeight ?? 0),
    imageUrl: typeof document.imageUrl === "string" ? document.imageUrl : undefined,
    createdAt: document.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    annotations: Array.isArray(document.annotations)
      ? document.annotations.map((annotation) => ({
          id: String(annotation.id ?? ""),
          type: annotation.type === "polygon" ? "polygon" : "bbox",
          coordinates: Array.isArray(annotation.coordinates)
            ? annotation.coordinates.map((value) => Number(value)).filter((value) => Number.isFinite(value))
            : [],
          label: String(annotation.label ?? "unlabeled-region").slice(0, 120),
          confidence:
            typeof annotation.confidence === "number" && Number.isFinite(annotation.confidence)
              ? annotation.confidence
              : undefined,
          timestamp: annotation.timestamp || new Date().toISOString(),
        }))
      : [],
  };
}

export default async function handler(req: NextApiRequest, res: NextApiResponse<Data | object>) {
  try {
    if (req.method === "GET") {
      const documents = await readDocuments();
      const imageId = typeof req.query.imageId === "string" ? req.query.imageId : "";
      const format = typeof req.query.format === "string" ? req.query.format : "";

      if (!imageId) {
        return res.status(200).json({ documents });
      }

      const document = documents.find((entry) => entry.imageId === imageId);
      if (!document) {
        return res.status(404).json({ error: "Annotations not found for this image." });
      }

      if (format === "coco") {
        return res.status(200).json(exportAnnotationsToCoco(document));
      }

      return res.status(200).json(document);
    }

    if (req.method === "POST") {
      const payload = sanitizeAnnotationDocument(req.body as AnnotationDocument);

      if (!payload.imageId || !payload.imageWidth || !payload.imageHeight) {
        return res.status(400).json({ error: "Invalid annotation payload." });
      }

      const documents = await readDocuments();
      const index = documents.findIndex((entry) => entry.imageId === payload.imageId);

      if (index >= 0) {
        payload.createdAt = documents[index].createdAt;
        documents[index] = payload;
      } else {
        documents.push(payload);
      }

      await writeDocuments(documents);
      return res.status(200).json({ saved: true, document: payload });
    }

    return res.status(405).json({ error: "Method not allowed." });
  } catch (error) {
    console.error("Annotation API error:", error);
    return res.status(500).json({ error: "Unable to process annotation request." });
  }
}
