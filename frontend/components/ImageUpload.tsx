import { useRef, useState, useCallback, DragEvent, ChangeEvent, TouchEvent, KeyboardEvent } from 'react';
import { useTranslation } from 'next-i18next';
import { AppError } from '../types';

interface ImageUploadProps {
  onImageSelect: (file: File, imageUrl: string) => void;
  onError?: (error: AppError) => void;
  loading?: boolean;
  disabled?: boolean;
  uploadProgress?: number; // Progress percentage (0-100)
  uploadStatus?: string; // Current status of the upload/async operation
}

export function ImageUpload({ onImageSelect, onError, loading = false, disabled = false, uploadProgress, uploadStatus }: ImageUploadProps) {
  const { t } = useTranslation('common');
  const [isDragging, setIsDragging] = useState(false);
  const [isTouching, setIsTouching] = useState(false);
  const [uploadState, setUploadState] = useState<ImageUploadState>({
    file: null,
    preview: null,
    progress: {
      loaded: 0,
      total: 0,
      percentage: 0,
      speed: 0,
      estimatedTimeRemaining: 0,
      chunks: { completed: 0, total: 0, size: chunkSize }
    },
    isUploading: false,
    isPaused: false,
    error: null,
    uploadId: null
  });
  const [blurPlaceholder, setBlurPlaceholder] = useState<BlurPlaceholder | null>(null);
  const [exifData, setExifData] = useState<EXIFData | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounter = useRef(0);
  const uploadControllerRef = useRef<AbortController | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Generate blur placeholder
  const generateBlurPlaceholder = useCallback(async (file: File): Promise<BlurPlaceholder | null> => {
    if (!enableBlurUp) return null;
    
    try {
      const img = new Image();
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      return new Promise((resolve) => {
        img.onload = () => {
          // Create tiny version for blur
          const width = 40;
          const height = (img.height / img.width) * width;
          
          canvas.width = width;
          canvas.height = height;
          
          if (ctx) {
            ctx.drawImage(img, 0, 0, width, height);
            
            // Apply blur effect
            ctx.filter = 'blur(2px)';
            ctx.drawImage(canvas, 0, 0);
            
            const dataUrl = canvas.toDataURL('image/jpeg', 0.3);
            resolve({
              dataUrl,
              width: img.width,
              height: img.height
            });
          } else {
            resolve(null);
          }
        };
        
        img.onerror = () => resolve(null);
        img.src = URL.createObjectURL(file);
      });
    } catch (error) {
      console.warn('Failed to generate blur placeholder:', error);
      return null;
    }
  }, [enableBlurUp]);

  // Extract EXIF data
  const extractEXIFData = useCallback(async (file: File): Promise<EXIFData | null> => {
    if (!showEXIF) return null;
    
    try {
      // Simple EXIF extraction (in production, use a library like exif-js)
      const img = new Image();
      
      return new Promise((resolve) => {
        img.onload = () => {
          resolve({
            imageWidth: img.width,
            imageHeight: img.height,
            // In a real implementation, extract actual EXIF data
            make: 'Unknown',
            model: 'Unknown',
            dateTime: new Date().toISOString(),
            orientation: 1
          });
        };
        
        img.onerror = () => resolve(null);
        img.src = URL.createObjectURL(file);
      });
    } catch (error) {
      console.warn('Failed to extract EXIF data:', error);
      return null;
    }
  }, [showEXIF]);

  // Validate file
  const validateFile = useCallback((file: File): { isValid: boolean; error?: string } => {
    if (!acceptedFormats.includes(file.type)) {
      return {
        isValid: false,
        error: t('invalid_file_type', { formats: acceptedFormats.join(', ') })
      };
    }
    
    if (file.size > maxSize) {
      return {
        isValid: false,
        error: t('file_too_large', { maxSize: (maxSize / 1024 / 1024).toFixed(1) })
      };
    }
    
    return { isValid: true };
  }, [acceptedFormats, maxSize, t]);

  // Chunked upload implementation
  const uploadInChunks = useCallback(async (file: File): Promise<UploadResponse> => {
    const totalChunks = Math.ceil(file.size / chunkSize);
    const uploadId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    setUploadState(prev => ({
      ...prev,
      uploadId,
      progress: {
        ...prev.progress,
        chunks: { completed: 0, total: totalChunks, size: chunkSize }
      }
    }));

    let uploadedBytes = 0;
    const startTime = Date.now();

    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      if (uploadControllerRef.current?.signal.aborted) {
        throw new UploadError('Upload cancelled', 'CANCELLED');
      }

      const start = chunkIndex * chunkSize;
      const end = Math.min(start + chunkSize, file.size);
      const chunk = file.slice(start, end);

      const formData = new FormData();
      formData.append('file', chunk);
      formData.append('uploadId', uploadId);
      formData.append('chunkIndex', chunkIndex.toString());
      formData.append('totalChunks', totalChunks.toString());
      formData.append('fileName', file.name);
      formData.append('fileType', file.type);
      formData.append('fileSize', file.size.toString());

      try {
        const response = await api.post('/api/upload/chunk', formData, {
          signal: uploadControllerRef.current?.signal,
          headers: {
            'X-Upload-ID': uploadId,
            'X-Chunk-Index': chunkIndex.toString(),
            'X-Total-Chunks': totalChunks.toString()
          }
        });

        if (!response.data?.success) {
          throw new UploadError(response.data?.error || 'Chunk upload failed', 'CHUNK_ERROR');
        }

        uploadedBytes += end - start;
        const elapsed = (Date.now() - startTime) / 1000;
        const speed = uploadedBytes / elapsed;
        const remaining = file.size - uploadedBytes;
        const estimatedTimeRemaining = speed > 0 ? remaining / speed : 0;

        const progress: ImageUploadProgress = {
          loaded: uploadedBytes,
          total: file.size,
          percentage: (uploadedBytes / file.size) * 100,
          speed,
          estimatedTimeRemaining,
          chunks: {
            completed: chunkIndex + 1,
            total: totalChunks,
            size: chunkSize
          }
        };

        setUploadState(prev => ({
          ...prev,
          progress
        }));

        onUploadProgress?.(progress);

        // Announce progress for screen readers
        if (accessibility?.announceProgress) {
          const announcement = t('upload_progress', {
            percentage: Math.round(progress.percentage),
            speed: formatBytes(speed),
            remaining: formatTime(estimatedTimeRemaining)
          });
          announceToScreenReader(announcement);
        }

      } catch (error) {
        if (error instanceof UploadError) {
          throw error;
        }
        throw new UploadError('Network error during chunk upload', 'NETWORK_ERROR', error);
      }
    }

    // Complete upload
    const completeResponse = await api.post('/api/upload/complete', {
      uploadId,
      fileName: file.name,
      fileType: file.type,
      fileSize: file.size
    });

    return completeResponse.data || { success: true, uploadId };
  }, [chunkSize, onUploadProgress, accessibility, t]);

  // Regular upload for smaller files
  const uploadFile = useCallback(async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('optimize', 'true');
    formData.append('generateThumbnail', 'true');

    const startTime = Date.now();

    try {
      const response = await api.post('/api/upload', formData, {
        signal: uploadControllerRef.current?.signal,
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const loaded = progressEvent.loaded;
            const total = progressEvent.total;
            const elapsed = (Date.now() - startTime) / 1000;
            const speed = loaded / elapsed;
            const remaining = total - loaded;
            const estimatedTimeRemaining = speed > 0 ? remaining / speed : 0;

            const progress: ImageUploadProgress = {
              loaded,
              total,
              percentage: (loaded / total) * 100,
              speed,
              estimatedTimeRemaining,
              chunks: { completed: 1, total: 1, size: total }
            };

            setUploadState(prev => ({
              ...prev,
              progress
            }));

            onUploadProgress?.(progress);
          }
        }
      });

      return response.data || { success: true };
    } catch (error) {
      throw new UploadError('Upload failed', 'UPLOAD_ERROR', error);
    }
  }, [onUploadProgress]);

  // Main upload handler
  const handleUpload = useCallback(async (file: File) => {
    const validation = validateFile(file);
    if (!validation.isValid) {
      setUploadState(prev => ({
        ...prev,
        error: validation.error
      }));
      onUploadError?.(validation.error!);
      return;
    }

    // Reset state
    setUploadState({
      file,
      preview: URL.createObjectURL(file),
      progress: {
        loaded: 0,
        total: file.size,
        percentage: 0,
        speed: 0,
        estimatedTimeRemaining: 0,
        chunks: { completed: 0, total: 1, size: chunkSize }
      },
      isUploading: true,
      isPaused: false,
      error: null,
      uploadId: null
    });

  const getStatusMessage = (status?: string) => {
    if (!status) return t('processing');
    switch (status) {
      case 'starting': return t('status_starting', 'Starting...');
      case 'uploading': return t('status_uploading', 'Uploading image...');
      case 'processing': return t('status_processing', 'Analyzing food...');
      case 'complete': return t('status_complete', 'Analysis complete!');
      case 'cached': return t('status_cached', 'Retrieved from cache');
      default: return t('status_processing', 'Processing...');
    }
  };

  const handleDragEnter = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    dragCounter.current = 0;

    if (disabled || loading) return;

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type.startsWith('image/')) {
        handleUpload(file);
        const imageUrl = URL.createObjectURL(file);
        onImageSelect(file, imageUrl);
      } else {
        onError?.({
          message: t('error_invalid_image_type', 'Invalid file type. Please upload an image.'),
          code: 'INVALID_FILE_TYPE'
        });
      }
    }
  }, [onImageSelect, onError, disabled, loading, t]);

  const handleTouchStart = useCallback((e: TouchEvent<HTMLDivElement>) => {
    if (disabled || loading) return;
    setIsTouching(true);
  }, [disabled, loading]);

  const handleTouchEnd = useCallback((e: TouchEvent<HTMLDivElement>) => {
    if (disabled || loading) return;
    setIsTouching(false);
  }, [disabled, loading]);

  const handleFileInput = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type.startsWith('image/')) {
        handleUpload(file);
        const imageUrl = URL.createObjectURL(file);
        onImageSelect(file, imageUrl);
      } else {
        onError?.({
          message: t('error_invalid_image_type', 'Invalid file type. Please upload an image.'),
          code: 'INVALID_FILE_TYPE'
        });
      }
    }
    // Reset input value to allow selecting the same file again
    if (e.target) {
      e.target.value = '';
    }
  }, [onImageSelect, onError, t]);

  const handleClick = useCallback(() => {
    if (!disabled && !loading) {
      fileInputRef.current?.click();
    }
  }, [disabled, loading]);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLDivElement>) => {
    if (disabled || loading) return;
    
    // Support Enter and Space keys for activation
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
    
    // Support Escape key to blur focus
    if (e.key === 'Escape') {
      e.preventDefault();
      if (fileInputRef.current) {
        fileInputRef.current.blur();
      }
      e.currentTarget.blur();
    }
    
    // Allow default Tab behavior for navigation
  }, [disabled, loading, handleClick]);

  return (
    <div className="w-full max-w-md mx-auto px-4 sm:px-0">
      <div
        className={`
          relative border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center cursor-pointer transition-all duration-200
          min-h-[120px] sm:min-h-[150px] flex flex-col items-center justify-center
          ${isDragging 
            ? 'border-accent bg-accent/10 scale-105' 
            : isTouching 
            ? 'border-accent bg-accent/5' 
            : 'border-gray-300 dark:border-gray-600 hover:border-accent/50 hover:bg-accent/5'
          }
          ${disabled || loading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onClick={handleClick}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label={t('upload_image_area', 'Image upload area')}
        aria-describedby={uploadProgress !== undefined && uploadProgress > 0 && uploadProgress < 100 ? 'upload-progress' : undefined}
        aria-disabled={disabled || loading}
        aria-pressed={isDragging}
        aria-busy={loading}
        onKeyDown={handleKeyDown}
        data-testid="image-upload-drop-zone"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptedFormats.join(',')}
          onChange={handleFileInput}
          className="hidden"
          disabled={disabled || loading}
          aria-label={t('select_image_file')}
          tabIndex={-1} // Hide from tab order since parent is focusable
        />
        
        {!uploadState.file ? (
          <div className="flex flex-col items-center space-y-3 sm:space-y-4">
            {/* Upload Icon */}
            <div className={`
              w-12 h-12 sm:w-16 sm:h-16 rounded-full flex items-center justify-center transition-colors
              ${isDragging || isTouching 
                ? 'bg-accent text-white' 
                : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400'
              }
            `}>
              {loading ? (
                <svg className="animate-spin h-6 w-6 sm:h-8 sm:w-8" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              ) : (
                <svg className="h-6 w-6 sm:h-8 sm:w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              )}
            </div>
            
            <div className="text-center">
              <p className="text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300 mb-1">
                {loading ? t('processing') : isDragging ? t('drop_image_here') : t('drag_drop_image')}
              </p>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-500">
                {t('or_click_to_select')}
              </p>
            </div>
          </div>
          
          <div className="text-center">
            <p className="text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300 mb-1">
              {loading ? getStatusMessage(uploadStatus) : isDragging ? t('drop_image_here') : t('drag_drop_image')}
            </p>
            {!loading && (
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-500">
                {t('or_click_to_select')}
              </p>
            )}
          </div>
        )}
        
        {/* Mobile-specific hint */}
        {!loading && (
          <div className="absolute bottom-2 left-2 right-2 sm:hidden">
            <p className="text-xs text-gray-400 text-center" aria-hidden="true">
              {t('tap_to_upload')}
            </p>
          </div>
        )}
        
        {/* Drag overlay for screen readers */}
        {isDragging && (
          <div 
            className="absolute inset-0 bg-accent/20 rounded-2xl flex items-center justify-center pointer-events-none"
            aria-live="polite"
            aria-atomic="true"
          >
            <p className="text-accent font-medium text-lg">
              {t('drop_image_here', 'Drop image here to upload')}
            </p>
          </div>
        )}
      </div>
      
      {/* Upload progress bar */}
      {((uploadProgress !== undefined && uploadProgress > 0) || loading) && (
        <div className="mt-3">
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              {getStatusMessage(uploadStatus)}
            </span>
            {uploadProgress !== undefined && (
              <span className="text-xs font-medium text-accent">
                {Math.round(uploadProgress)}%
              </span>
            )}
          </div>
          <div 
            id="upload-progress"
            className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={uploadProgress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={t('upload_progress', 'Upload progress: {{progress}}%', { progress: uploadProgress })}
          >
            <div 
              className={`h-full bg-accent transition-all duration-300 ease-out ${uploadProgress === 100 && uploadStatus === 'processing' ? 'animate-pulse' : ''}`}
              style={{ width: `${uploadProgress ?? 0}%` }}
            />
          </div>
          <div className="sr-only" aria-live="polite" aria-atomic="true">
            {t('upload_progress_announcement', 'Upload progress: {{progress}}% - {{status}}', { 
              progress: uploadProgress, 
              status: getStatusMessage(uploadStatus) 
            })}
          </div>
        </div>
      )}
      
      {/* File type hint */}
      <div className="mt-3 text-center">
        <p className="text-xs text-gray-400" role="note" aria-label={t('supported_formats_hint', 'Supported image formats: JPG, PNG, GIF, WebP, HEIC')}>
          {t('supported_formats')}: JPG, PNG, GIF, WebP, HEIC
        </p>
      </div>
    </div>
  );
}

// Utility functions
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

function announceToScreenReader(message: string) {
  const announcement = document.createElement('div');
  announcement.setAttribute('aria-live', 'polite');
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only';
  announcement.textContent = message;
  
  document.body.appendChild(announcement);
  
  setTimeout(() => {
    document.body.removeChild(announcement);
  }, 1000);
}
