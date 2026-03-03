import { useRef, useState, useCallback, DragEvent, ChangeEvent, TouchEvent } from 'react';
import { useTranslation } from 'next-i18next';

interface ImageUploadProps {
  onImageSelect: (file: File, imageUrl: string) => void;
  loading?: boolean;
  disabled?: boolean;
}

export function ImageUpload({ onImageSelect, loading = false, disabled = false }: ImageUploadProps) {
  const { t } = useTranslation('common');
  const [isDragging, setIsDragging] = useState(false);
  const [isTouching, setIsTouching] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounter = useRef(0);

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
        const imageUrl = URL.createObjectURL(file);
        onImageSelect(file, imageUrl);
      }
    }
  }, [onImageSelect, disabled, loading]);

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
        const imageUrl = URL.createObjectURL(file);
        onImageSelect(file, imageUrl);
      }
    }
    // Reset input value to allow selecting the same file again
    if (e.target) {
      e.target.value = '';
    }
  }, [onImageSelect]);

  const handleClick = useCallback(() => {
    if (!disabled && !loading) {
      fileInputRef.current?.click();
    }
  }, [disabled, loading]);

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
        aria-label={t('upload_image_area')}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            handleClick();
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileInput}
          className="hidden"
          disabled={disabled || loading}
          aria-label={t('select_image_file')}
        />
        
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
        
        {/* Mobile-specific hint */}
        <div className="absolute bottom-2 left-2 right-2 sm:hidden">
          <p className="text-xs text-gray-400 text-center">
            {t('tap_to_upload')}
          </p>
        </div>
      </div>
      
      {/* File type hint */}
      <div className="mt-3 text-center">
        <p className="text-xs text-gray-400">
          {t('supported_formats')}: JPG, PNG, GIF, WebP, HEIC
        </p>
      </div>
    </div>
  );
}
