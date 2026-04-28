export interface ClassificationResult {
  prediction: string;
  confidence: number;
  predictions?: Array<{
    class: string;
    confidence: number;
  }>;
  top_prediction?: {
    class: string;
    confidence: number;
  };
  processing_time: number;
  timestamp: string;
  request_id: string;
  cached?: boolean;
  model_version?: string;
  image_hash?: string;
  food?: string; // Legacy field for backward compatibility
  calories?: number;
}

export interface HistoryEntry extends ClassificationResult {
  id: number;
  timestamp: string;
}

export interface ApiErrorResponse {
  error: string;
  message?: string;
  code?: string;
}

export interface AppError {
  message: string;
  code?: string;
  details?: any;
  status?: number;
}

export interface CacheStats {
  entries: number;
  maxEntries: number;
  defaultTTL: number;
}

export interface ImageAnnotation {
  id: string;
  type: "bbox" | "polygon";
  coordinates: number[];
  label: string;
  confidence?: number;
  timestamp: string;
}
