import { useRef, useState, useCallback, DragEvent, ChangeEvent, TouchEvent, useEffect } from 'react';
import { useTranslation } from 'next-i18next';
import { 
  ImageUploadProps, 
  ImageUploadState, 
  ImageUploadProgress, 
  EXIFData, 
  BlurPlaceholder,
  UploadResponse,
  UploadError
} from '../types';
import { api } from '../utils/api';

export function ImageUpload({ 
  onImageSelect, 
  onUploadProgress,
  onUploadComplete,
  onUploadError,
  loading = false, 
  disabled = false,
  maxSize = 10 * 1024 * 1024, // 10MB
  acceptedFormats = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/heic'],
  enableChunkedUpload = true,
  chunkSize = 1024 * 1024, // 1MB chunks
  showProgress = true,
  showPreview = true,
  showEXIF = true,
  enableBlurUp = true,
  accessibility
}: ImageUploadProps) {
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

    try {
      uploadControllerRef.current = new AbortController();

      // Generate blur placeholder and extract EXIF data
      const [blur, exif] = await Promise.all([
        generateBlurPlaceholder(file),
        extractEXIFData(file)
      ]);

      setBlurPlaceholder(blur);
      setExifData(exif);

      // Choose upload method
      const shouldUseChunkedUpload = enableChunkedUpload && file.size > 5 * 1024 * 1024; // 5MB threshold
      const response = shouldUseChunkedUpload ? await uploadInChunks(file) : await uploadFile(file);

      setUploadState(prev => ({
        ...prev,
        isUploading: false,
        progress: {
          ...prev.progress,
          percentage: 100
        }
      }));

      onUploadComplete?.(response);

    } catch (error) {
      const errorMessage = error instanceof UploadError ? error.message : t('upload_failed');
      
      setUploadState(prev => ({
        ...prev,
        isUploading: false,
        error: errorMessage
      }));

      onUploadError?.(errorMessage);
    }
  }, [validateFile, generateBlurPlaceholder, extractEXIFData, enableChunkedUpload, uploadInChunks, uploadFile, onUploadComplete, onUploadError, chunkSize, t]);

  // Pause/Resume upload
  const togglePauseUpload = useCallback(() => {
    if (uploadControllerRef.current) {
      uploadControllerRef.current.abort();
      uploadControllerRef.current = null;
      
      setUploadState(prev => ({
        ...prev,
        isPaused: true,
        isUploading: false
      }));
    } else {
      // Resume upload
      if (uploadState.file) {
        handleUpload(uploadState.file);
      }
    }
  }, [uploadState.file, handleUpload]);

  // Cancel upload
  const cancelUpload = useCallback(() => {
    if (uploadControllerRef.current) {
      uploadControllerRef.current.abort();
      uploadControllerRef.current = null;
    }

    setUploadState({
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

    setBlurPlaceholder(null);
    setExifData(null);
  }, [chunkSize]);

  // Drag and drop handlers
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
      }
    }
  }, [handleUpload, onImageSelect, disabled, loading]);

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
      }
    }
    // Reset input value to allow selecting the same file again
    if (e.target) {
      e.target.value = '';
    }
  }, [handleUpload, onImageSelect]);

  const handleClick = useCallback(() => {
    if (!disabled && !loading) {
      fileInputRef.current?.click();
    }
  }, [disabled, loading]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (uploadControllerRef.current) {
        uploadControllerRef.current.abort();
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, []);

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
        tabIndex={0}
        aria-label={accessibility?.ariaLabel || t('upload_image_area')}
        aria-describedby={accessibility?.ariaDescription}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            handleClick();
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptedFormats.join(',')}
          onChange={handleFileInput}
          className="hidden"
          disabled={disabled || loading}
          aria-label={t('select_image_file')}
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
        ) : (
          <div className="w-full">
            {showPreview && uploadState.preview && (
              <div className="mb-4">
                <div className="relative inline-block">
                  {/* Blur placeholder */}
                  {blurPlaceholder && (
                    <div 
                      className="absolute inset-0 blur-sm transition-opacity duration-300"
                      style={{
                        backgroundImage: `url(${blurPlaceholder.dataUrl})`,
                        backgroundSize: 'cover',
                        backgroundPosition: 'center',
                        filter: 'blur(10px)',
                        transform: 'scale(1.1)'
                      }}
                    />
                  )}
                  <img
                    src={uploadState.preview}
                    alt={t('uploaded_image_preview')}
                    className="max-w-full max-h-48 rounded-lg shadow-md relative z-10"
                    onLoad={() => {
                      // Fade in the actual image
                      const img = event?.target as HTMLImageElement;
                      if (img) {
                        img.style.opacity = '0';
                        setTimeout(() => {
                          img.style.transition = 'opacity 0.3s ease-in-out';
                          img.style.opacity = '1';
                        }, 100);
                      }
                    }}
                  />
                </div>
              </div>
            )}

            {/* EXIF Data */}
            {showEXIF && exifData && (
              <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-xs">
                <h4 className="font-semibold mb-2">{t('image_details')}</h4>
                <div className="grid grid-cols-2 gap-2 text-gray-600 dark:text-gray-400">
                  {exifData.imageWidth && (
                    <div>{t('dimensions')}: {exifData.imageWidth} × {exifData.imageHeight}</div>
                  )}
                  {exifData.make && (
                    <div>{t('camera')}: {exifData.make} {exifData.model}</div>
                  )}
                  {exifData.dateTime && (
                    <div>{t('taken')}: {new Date(exifData.dateTime).toLocaleDateString()}</div>
                  )}
                </div>
              </div>
            )}

            {/* Upload Progress */}
            {showProgress && uploadState.isUploading && (
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">{t('uploading')}</span>
                  <span className="text-sm text-gray-500">
                    {Math.round(uploadState.progress.percentage)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-accent h-2 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${uploadState.progress.percentage}%` }}
                  />
                </div>
                <div className="flex justify-between mt-2 text-xs text-gray-500">
                  <span>{formatBytes(uploadState.progress.loaded)} / {formatBytes(uploadState.progress.total)}</span>
                  <span>{formatBytes(uploadState.progress.speed)}/s</span>
                  {uploadState.progress.estimatedTimeRemaining > 0 && (
                    <span>{formatTime(uploadState.progress.estimatedTimeRemaining)}</span>
                  )}
                </div>
                {uploadState.progress.chunks.total > 1 && (
                  <div className="text-xs text-gray-500 mt-1">
                    {t('chunk_progress', { 
                      completed: uploadState.progress.chunks.completed,
                      total: uploadState.progress.chunks.total
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Upload Controls */}
            <div className="flex gap-2 justify-center">
              {uploadState.isUploading && (
                <button
                  onClick={togglePauseUpload}
                  className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors text-sm"
                  aria-label={uploadState.isPaused ? t('resume_upload') : t('pause_upload')}
                >
                  {uploadState.isPaused ? t('resume') : t('pause')}
                </button>
              )}
              {(uploadState.isUploading || uploadState.isPaused) && (
                <button
                  onClick={cancelUpload}
                  className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors text-sm"
                  aria-label={t('cancel_upload')}
                >
                  {t('cancel')}
                </button>
              )}
            </div>

            {/* Error Display */}
            {uploadState.error && (
              <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-red-600 dark:text-red-400 text-sm">{uploadState.error}</p>
              </div>
            )}
          </div>
        )}
        
        {/* Mobile-specific hint */}
        {!uploadState.file && (
          <div className="absolute bottom-2 left-2 right-2 sm:hidden">
            <p className="text-xs text-gray-400 text-center">
              {t('tap_to_upload')}
            </p>
          </div>
        )}
      </div>
      
      {/* File type hint */}
      {!uploadState.file && (
        <div className="mt-3 text-center">
          <p className="text-xs text-gray-400">
            {t('supported_formats')}: {acceptedFormats.map(f => f.split('/')[1].toUpperCase()).join(', ')}
          </p>
          <p className="text-xs text-gray-400">
            {t('max_size')}: {(maxSize / 1024 / 1024).toFixed(1)}MB
          </p>
        </div>
      )}
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
