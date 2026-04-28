import React, { useEffect, useRef, useState } from "react";
import { api } from "@/utils/api";
import { storage } from "@/utils/storage";
import { pwaManager } from "@/lib/pwa-utils";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ImageUpload } from "@/components/ImageUpload";
import { ClassificationResult as ClassificationResultComponent } from "@/components/ClassificationResult";
import { useTranslation } from "next-i18next";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import type { GetStaticProps } from "next";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { useKeyboardShortcuts } from "@/utils/useKeyboardShortcuts";
import { ClassificationResult, HistoryEntry, AppError } from "@/types";
import { useRouter } from "next/router";

const HISTORY_KEY = "classification_history";
const MAX_HISTORY_ITEMS = 50;

export default function Classify() {
  const { t } = useTranslation("common");
  const router = useRouter();
  const [image, setImage] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<AppError | null>(null);
  const [classification, setClassification] = useState<ClassificationResult | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Load history from local storage on mount
  useEffect(() => {
    const savedHistory = storage.get<HistoryEntry[]>(HISTORY_KEY, []);
    setHistory(savedHistory);
  }, []);

  // Save history whenever it changes
  useEffect(() => {
    if (history.length > 0) {
      storage.set(HISTORY_KEY, history.slice(0, MAX_HISTORY_ITEMS));
    }
  }, [history]);

  // Cleanup blob URLs to prevent memory leaks
  useEffect(() => {
    return () => {
      if (image && image.startsWith('blob:')) {
        URL.revokeObjectURL(image);
      }
    };
  }, [image]);

  const handleReset = () => {
    setImage(null);
    setImageFile(null);
    setClassification(null);
    setError(null);
    setUploadProgress(0);
    setUploadStatus('');
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file size (e.g., 10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        setError({
          message: t('error_file_too_large', 'File is too large. Max size is 10MB.'),
          code: 'FILE_TOO_LARGE'
        });
        return;
      }

      const imageUrl = URL.createObjectURL(file);
      setImage(imageUrl);
      setImageFile(file);
      setError(null);
      setClassification(null);
      setUploadProgress(0);
      setUploadStatus('');
    }
  };

  const handleClassify = async () => {
    if (!imageFile && !image) return;

    setLoading(true);
    setUploadProgress(0);
    setError(null);

    // Announce to screen readers that classification is starting
    const announcement = document.getElementById('classification-announcement');
    if (announcement) {
      announcement.textContent = t('classifying', 'Classifying food...');
    }

    try {
      const formData = new FormData();
      if (imageFile) {
        formData.append('image', imageFile);
      } else if (image) {
        // Fallback for cases where we only have a blob URL (e.g., from camera)
        formData.append('image_url', image);
      }

      const response = await api.post<ClassificationResult>('/api/classify', formData, {
        retries: 2,
        retryDelay: 1000
      }, (progress, status) => {
        setUploadProgress(progress);
        if (status) setUploadStatus(status);
        if (announcement && progress % 25 === 0) {
          const statusMsg = status === 'uploading' ? t('uploading') : status === 'processing' ? t('processing') : '';
          announcement.textContent = `${statusMsg} ${t('upload_progress_voice', 'Upload progress: {{progress}}%', { progress })}`;
        }
      });

      if (response.error) {
        setError({
          message: response.error,
          status: response.status
        });
        if (announcement) announcement.textContent = t('error_prefix', 'Error: ') + response.error;
      } else if (response.data) {
        const result = response.data;
        setClassification(result);
        
        // Add to history
        const newEntry: HistoryEntry = {
          ...result,
          id: Date.now(),
          timestamp: result.timestamp || new Date().toISOString()
        };
        
        setHistory((prev: HistoryEntry[]) => [newEntry, ...prev].slice(0, MAX_HISTORY_ITEMS));
        
        // Announce result to screen reader
        if (announcement) {
          announcement.textContent = t('classification_complete', 'Classification complete. Result: {{food}} with {{confidence}}% confidence', {
            food: result.food || result.prediction,
            confidence: (result.confidence * 100).toFixed(0)
          });
        }

        // Cache for offline access
        try {
          pwaManager.cacheClassification({
            id: newEntry.id,
            timestamp: newEntry.timestamp,
            food: result.food || result.prediction || 'Unknown Food',
            confidence: result.confidence,
            calories: result.calories,
            imageUrl: image || '',
            cachedAt: new Date().toISOString()
          });
        } catch (cacheError) {
          console.warn('Failed to cache classification:', cacheError);
          // Non-critical error, continue execution
        }
      }
    } catch (err: any) {
      setError({
        message: t('error_classify_retry'),
        details: err
      });
      if (announcement) announcement.textContent = t('error_classify_retry');
      console.error('Classification error:', err);
    } finally {
      setLoading(false);
      // Keep progress at 100 for a moment before resetting
      setUploadProgress(100);
      setTimeout(() => setUploadProgress(0), 1000);
    }
  };

  const handleOpenPicker = () => {
    fileInputRef.current?.click();
  };

  useKeyboardShortcuts([
    { key: 'o', action: handleOpenPicker },
    { key: 'c', action: () => image && !loading && handleClassify() },
    { key: 'r', action: handleReset },
    { key: 'Escape', action: handleReset },
  ]);

  return (
    <div className="min-h-screen flex flex-col items-center p-3 sm:p-4 md:p-8 bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
      <div className="w-full max-w-6xl flex justify-between items-center mb-4">
        <button
          onClick={() => router.push('/')}
          className="text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 px-4 py-2 rounded-lg transition-colors"
          aria-label={t('back_to_home', 'Back to home')}
        >
          ← {t('back', 'Back')}
        </button>
        <LanguageSwitcher />
      </div>

      <header className="text-center mb-6 sm:mb-8 md:mb-12 px-2">
        <h1 className="text-3xl sm:text-4xl md:text-6xl font-black mb-3 sm:mb-4 text-transparent bg-clip-text bg-gradient-to-r from-indigo-500 to-emerald-500 leading-tight">
          {t("classify_food_title", "Classify Food")}
        </h1>
        <p className="text-gray-600 dark:text-gray-400 text-xs sm:text-sm md:text-lg max-w-xs sm:max-w-sm md:max-w-xl mx-auto px-2">
          {t("classify_description", "Upload an image to identify food and get nutritional insights")}
        </p>
        <p className="text-gray-500 dark:text-gray-500 text-xs sm:text-sm mt-2">
          {t("shortcut_hint", "Press 'O' for camera, 'C' to classify, 'R' to reset")}
        </p>
      </header>

      {/* Main Action Area */}
      <div className="w-full max-w-4xl flex flex-col items-center px-2 sm:px-4">
        {/* Screen reader announcements */}
        <div id="classification-announcement" role="status" aria-live="polite" className="sr-only" />
        <div id="error-announcement" role="alert" aria-live="assertive" className="sr-only" />

        <input
          type="file"
          accept="image/*"
          capture="environment"
          ref={fileInputRef}
          onChange={handleImageChange}
          className="hidden"
          aria-label={t("select_image_file")}
        />

        {!image && (
          <ImageUpload
            onImageSelect={(file, imageUrl) => {
              setImage(imageUrl);
              setImageFile(file);
              setError(null);
              setClassification(null);
            }}
            onError={setError}
            loading={loading}
            disabled={loading}
            uploadProgress={uploadProgress}
            uploadStatus={uploadStatus}
          />
        )}

        {error && (
          <div className="w-full mb-6 sm:mb-8 mt-4 max-w-md animate-shake px-2">
            <ErrorMessage
              error={error}
              onRetry={() => handleClassify()}
              onDismiss={() => setError(null)}
              variant="inline"
            />
          </div>
        )}

        {image && (
          <div className="w-full space-y-6 sm:space-y-8 animate-fade-in px-2" role="region" aria-label={t("image_preview")}>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 sm:gap-8 items-start">
              <div className="relative group overflow-hidden rounded-[1.5rem] sm:rounded-[2rem] shadow-2xl border-4 sm:border-6 sm:border-8 border-white dark:border-gray-800 transition-transform hover:scale-[1.02] duration-500">
                <img
                  src={image}
                  alt={t("preview_alt")}
                  className="w-full h-auto object-cover max-h-64 sm:max-h-80 md:max-h-[500px]"
                />
                <button
                  onClick={handleReset}
                  className="absolute top-2 right-2 sm:top-4 sm:right-4 bg-black/40 backdrop-blur-xl text-white p-2 sm:p-3 rounded-full hover:bg-red-500 transition-all focus:outline-none shadow-lg active:scale-90 min-w-[36px] sm:min-w-[44px] min-h-[36px] sm:min-h-[44px] flex items-center justify-center touch-manipulation"
                  title={t("clear_image", "Clear (R)")}
                  aria-label={t("clear_image", "Clear image")}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 sm:h-5 sm:w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>

              <div className="flex flex-col gap-4 sm:gap-6">
                <button
                  onClick={handleClassify}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-3 sm:gap-4 bg-emerald-600 text-white px-6 sm:px-8 py-5 sm:py-6 md:py-10 rounded-[1.5rem] sm:rounded-[2rem] shadow-2xl hover:bg-emerald-700 disabled:bg-gray-400 transition-all active:scale-95 text-xl sm:text-2xl font-black group min-h-[56px] sm:min-h-[64px] touch-manipulation relative overflow-hidden"
                  aria-label={loading ? t('classifying') : t('classify_food')}
                >
                  {loading ? (
                    <div className="flex flex-col items-center gap-2">
                      <div className="flex items-center gap-3">
                        <div className="animate-spin h-6 w-6 sm:h-7 sm:w-7 border-4 border-white border-t-transparent rounded-full" />
                        <span>
                          {uploadStatus === 'uploading' ? t('uploading', 'Uploading...') : 
                           uploadStatus === 'processing' ? t('processing', 'Analyzing...') : 
                           t('classifying')}
                        </span>
                      </div>
                      {uploadProgress > 0 && (
                        <span className="text-xs font-medium opacity-80">{Math.round(uploadProgress)}%</span>
                      )}
                    </div>
                  ) : (
                    <>
                      <span>{t('classify_food')}</span>
                      <kbd className="hidden sm:inline-block px-3 py-1 text-sm bg-emerald-500/50 rounded border border-emerald-400 uppercase">C</kbd>
                    </>
                  )}
                  
                  {/* Progress bar overlay */}
                  {loading && uploadProgress > 0 && (
                    <div className="absolute bottom-0 left-0 right-0 h-2 bg-emerald-800/30">
                      <div 
                        className={`h-full bg-white/80 transition-all duration-300 ${uploadProgress === 100 && uploadStatus === 'processing' ? 'animate-pulse' : ''}`}
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  )}
                </button>

                {classification && (
                  <ClassificationResultComponent result={classification} loading={loading} />
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Recent Classifications */}
      {history.length > 0 && (
        <section className="w-full max-w-4xl mt-12 md:mt-16 pb-12">
          <h2 className="text-2xl md:text-3xl font-black text-gray-900 dark:text-white mb-6 flex items-center gap-3">
            {t("recent_classifications", "Recent Classifications")}
            <span className="text-sm bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300 font-black py-1 px-3 rounded-full">{history.length}</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {history.slice(0, 6).map((entry: HistoryEntry) => (
              <div
                key={entry.id}
                className="bg-white dark:bg-gray-800 p-4 rounded-2xl shadow-lg border border-gray-50 dark:border-gray-700/50 hover:shadow-xl hover:-translate-y-1 transition-all duration-300"
              >
                <div className="flex justify-between items-start mb-3">
                  <span className="bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-[10px] font-black px-2 py-1 rounded-lg uppercase tracking-widest">
                    {new Date(entry.id).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  </span>
                  <div className="flex items-center gap-1 bg-emerald-50 dark:bg-emerald-900/30 px-2 py-1 rounded-lg">
                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                    <span className="text-emerald-600 dark:text-emerald-400 font-black text-xs">{(entry.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <h4 className="text-xl font-black text-gray-900 dark:text-white capitalize mb-1 line-clamp-1">
                  {entry.food || entry.prediction}
                </h4>
                {entry.calories && (
                  <p className="text-sm text-gray-400 dark:text-gray-500 font-bold flex items-center gap-1">
                    <span className="text-orange-500">🔥</span> {entry.calories} kcal
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export const getStaticProps: GetStaticProps = async ({ locale }) => ({
  props: {
    ...(await serverSideTranslations(locale ?? "en", ["common"])),
  },
});
