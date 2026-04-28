// Global type definitions for FlavorSnap application

export interface ImageUploadProgress {
  loaded: number;
  total: number;
  percentage: number;
  speed: number; // bytes per second
  estimatedTimeRemaining: number; // seconds
  chunks: {
    completed: number;
    total: number;
    size: number;
  };
}

export interface ImageUploadState {
  file: File | null;
  preview: string | null;
  progress: ImageUploadProgress;
  isUploading: boolean;
  isPaused: boolean;
  error: string | null;
  uploadId: string | null;
  optimizedData?: {
    originalSize: number;
    optimizedSize: number;
    compressionRatio: number;
    format: string;
    dimensions: [number, number];
  };
  exifData?: EXIFData;
}

export interface EXIFData {
  make?: string;
  model?: string;
  dateTime?: string;
  exposureTime?: string;
  fNumber?: number;
  iso?: number;
  focalLength?: number;
  flash?: boolean;
  gps?: {
    latitude: number;
    longitude: number;
    altitude?: number;
  };
  imageWidth?: number;
  imageHeight?: number;
  orientation?: number;
}

export interface ChunkUploadOptions {
  chunkSize: number;
  maxRetries: number;
  retryDelay: number;
  concurrentUploads: number;
}

export interface UploadResponse {
  success: boolean;
  uploadId?: string;
  url?: string;
  thumbnailUrl?: string;
  optimizedUrl?: string;
  metadata?: {
    size: number;
    format: string;
    dimensions: [number, number];
    exif?: EXIFData;
  };
  error?: string;
}

export interface BlurPlaceholder {
  dataUrl: string;
  width: number;
  height: number;
}

export interface ProgressiveImageProps {
  src: string;
  alt: string;
  placeholder?: BlurPlaceholder;
  onLoad?: () => void;
  onError?: (error: Error) => void;
  className?: string;
  priority?: boolean;
}

export interface ImageValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  securityScore: number;
  metadata?: {
    fileSize: number;
    format: string;
    dimensions: [number, number];
    detectedMimeType: string;
  };
}

export interface ImageOptimizationResult {
  success: boolean;
  originalSize: number;
  optimizedSize: number;
  compressionRatio: number;
  format: string;
  dimensions: [number, number];
  processingTime: number;
  errors: string[];
  warnings: string[];
  optimizedData?: string; // base64
}

// API Types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: number;
}

export interface ApiOptions extends RequestInit {
  retries?: number;
  retryDelay?: number;
}

// Component Props Types
export interface ImageUploadProps {
  onImageSelect: (file: File, imageUrl: string) => void;
  onUploadProgress?: (progress: ImageUploadProgress) => void;
  onUploadComplete?: (response: UploadResponse) => void;
  onUploadError?: (error: string) => void;
  loading?: boolean;
  disabled?: boolean;
  maxSize?: number; // bytes
  acceptedFormats?: string[];
  enableChunkedUpload?: boolean;
  chunkSize?: number;
  showProgress?: boolean;
  showPreview?: boolean;
  showEXIF?: boolean;
  enableBlurUp?: boolean;
  accessibility?: {
    ariaLabel?: string;
    ariaDescription?: string;
    announceProgress?: boolean;
  };
}

// Tutorial Types
export interface TutorialStep {
  id: string;
  title: string;
  description: string;
  content: React.ReactNode;
  target?: string; // CSS selector for tooltip target
  position?: 'top' | 'bottom' | 'left' | 'right' | 'center';
  action?: {
    type: 'click' | 'input' | 'wait' | 'navigate';
    target?: string;
    value?: any;
    delay?: number;
  };
  validation?: {
    type: 'element_exists' | 'element_visible' | 'text_contains' | 'custom';
    target: string;
    value?: any;
    custom?: (element: Element) => boolean;
  };
  skipable?: boolean;
  timeout?: number;
}

export interface TutorialState {
  isActive: boolean;
  currentStep: number;
  steps: TutorialStep[];
  isCompleted: boolean;
  isPaused: boolean;
  progress: number;
  startTime?: Date;
  endTime?: Date;
  skipReason?: string;
}

export interface TutorialProgress {
  userId?: string;
  tutorialId: string;
  startedAt: Date;
  completedAt?: Date;
  currentStep: number;
  totalSteps: number;
  timeSpent: number; // seconds
  skipped: boolean;
  skipReason?: string;
  interactions: {
    stepId: string;
    action: string;
    timestamp: Date;
    data?: any;
  }[];
}

// Search Types
export interface SearchQuery {
  text: string;
  filters?: SearchFilters;
  sort?: SearchSortOptions;
  page?: number;
  limit?: number;
}

export interface SearchFilters {
  categories?: string[];
  tags?: string[];
  dateRange?: {
    start: Date;
    end: Date;
  };
  sizeRange?: {
    min: number;
    max: number;
  };
  format?: string[];
  confidence?: {
    min: number;
    max: number;
  };
}

export interface SearchSortOptions {
  field: 'relevance' | 'date' | 'size' | 'confidence' | 'popularity';
  order: 'asc' | 'desc';
}

export interface SearchResult {
  id: string;
  title: string;
  description: string;
  imageUrl: string;
  thumbnailUrl: string;
  score: number;
  metadata: {
    format: string;
    size: number;
    dimensions: [number, number];
    uploadedAt: Date;
    tags: string[];
    category: string;
    confidence: number;
  };
  highlights?: {
    title?: string;
    description?: string;
    tags?: string[];
  };
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
  facets?: {
    categories: { [key: string]: number };
    tags: { [key: string]: number };
    formats: { [key: string]: number };
  };
  suggestions?: string[];
  searchTime: number;
}

// Analytics Types
export interface AnalyticsEvent {
  event: string;
  properties?: Record<string, any>;
  timestamp: Date;
  userId?: string;
  sessionId?: string;
}

export interface TutorialAnalytics {
  tutorialId: string;
  userId?: string;
  startedAt: Date;
  completedAt?: Date;
  currentStep: number;
  totalSteps: number;
  completionRate: number;
  averageTimePerStep: number;
  dropOffPoints: number[];
  interactions: AnalyticsEvent[];
}

// Error Types
export class UploadError extends Error {
  constructor(
    message: string,
    public code: string,
    public details?: any
  ) {
    super(message);
    this.name = 'UploadError';
  }
}

export class ValidationError extends Error {
  constructor(
    message: string,
    public field: string,
    public value: any
  ) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class NetworkError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: any
  ) {
    super(message);
    this.name = 'NetworkError';
  }
}

// Utility Types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;

export type OptionalFields<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
