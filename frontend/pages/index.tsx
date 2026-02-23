/* eslint-disable @typescript-eslint/no-explicit-any */
import { useRef, useState } from "react";
import { api } from "@/utils/api";
import { ErrorMessage } from "@/components/ErrorMessage";
import { useTranslation } from "next-i18next";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import type { GetStaticProps } from "next";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { compressImage, validateImageFile, formatFileSize } from "@/utils/imageCompression";
import Layout from "@/components/Layout";
import Head from "next/head";

export default function Classify() {
  const { t } = useTranslation("common");
  const [image, setImage] = useState<string | null>(null);
  const [originalFile, setOriginalFile] = useState<File | null>(null);
  const [compressedFile, setCompressedFile] = useState<File | null>(null);
  const [compressionInfo, setCompressionInfo] = useState<{ originalSize: number; compressedSize: number; ratio: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [compressing, setCompressing] = useState(false);
  const [compressionProgress, setCompressionProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [classification, setClassification] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleImageChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file
    const validation = validateImageFile(file);
    if (!validation.isValid) {
      setError(validation.error || t('invalid_file'));
      return;
    }

    setOriginalFile(file);
    setError(null);
    setClassification(null);
    setCompressing(true);
    setCompressionProgress(0);

    try {
      const result = await compressImage(file, {}, (progress) => {
        setCompressionProgress(progress);
      });

      setCompressedFile(result.compressedFile);
      setCompressionInfo({
        originalSize: result.originalSize,
        compressedSize: result.compressedSize,
        ratio: result.compressionRatio,
      });

      const imageUrl = URL.createObjectURL(result.compressedFile);
      setImage(imageUrl);

      console.log(`Image compressed: ${formatFileSize(result.originalSize)} → ${formatFileSize(result.compressedSize)} (${result.compressionRatio.toFixed(1)}% reduction)`);
    } catch (err) {
      setError(t('compression_failed'));
      console.error('Compression error:', err);
    } finally {
      setCompressing(false);
      setCompressionProgress(0);
    }
  };

  const handleClassify = async () => {
    if (!image || !compressedFile) return;

    setLoading(true);
    setError(null);

    // Track classify button click
    analytics.trackButtonClick('classify_food', 'main_page');

    // Announce to screen readers that classification is starting
    const announcement = document.getElementById('classification-announcement');
    if (announcement) {
      announcement.textContent = t('classifying');
    }

    try {
      // Create FormData to send the compressed file
      const formData = new FormData();
      formData.append('image', compressedFile);

      const response = await fetch('/api/classify', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.error) {
        setError(result.error);
      } else {
        setClassification(result);
      }
    } catch (err) {
      setError(t('error_classify_retry'));
      console.error('Classification error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout title="FlavorSnap - AI Food Classification" description="Instantly identify food with AI-powered image recognition">
      <div className="flex flex-col items-center justify-center p-6">
        <h1 className="text-3xl font-bold mb-6">{t("snap_your_food")} 🍛</h1>

        {/* Screen reader announcements */}
        <div
          id="classification-announcement"
          role="status"
          aria-live="polite"
          className="sr-only"
        />

        <div
          id="error-announcement"
          role="alert"
          aria-live="assertive"
          className="sr-only"
        />

        <input
          type="file"
          accept="image/*"
          capture="environment"
          ref={fileInputRef}
          onChange={handleImageChange}
          className="hidden"
          aria-label={t("select_image_file")}
        />

        <button
          onClick={() => fileInputRef.current?.click()}
          onKeyPress={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
          className="bg-accent text-white px-6 py-3 rounded-full mb-4 focus:outline-none focus:ring-4 focus:ring-accent/50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
          aria-label={t("open_camera")}
        >
          {t("open_camera")}
        </button>

        {compressing && (
          <div className="mt-6 text-center">
            <div className="mb-2">
              <span className="text-sm font-medium">{t('compressing_image')}...</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${compressionProgress}%` }}
                role="progressbar"
                aria-valuenow={compressionProgress}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={t('compression_progress', { progress: compressionProgress })}
              />
            </div>
            <span className="text-xs text-gray-600">{compressionProgress}%</span>
          </div>
        )}

        {error && (
          <ErrorMessage
            message={error}
            onRetry={() => handleClassify()}
            onDismiss={() => setError(null)}
          />
        )}
        {image && (
          <div className="mt-6 text-center" role="region" aria-label={t("image_preview")}>
            {compressionInfo && (
              <div className="mb-4 p-3 bg-blue-50 rounded-lg text-sm">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium">{t('compression_info')}:</span>
                  <span className="text-green-600 font-medium">
                    {compressionInfo.ratio.toFixed(1)}% {t('reduced')}
                  </span>
                </div>
                <div className="text-xs text-gray-600">
                  {t('original_size')}: {formatFileSize(compressionInfo.originalSize)} → {t('compressed_size')}: {formatFileSize(compressionInfo.compressedSize)}
                </div>
              </div>
            )}

            <img
              src={image}
              alt={t("preview_alt")}
              className="rounded-xl shadow-md max-w-sm mx-auto mb-4"
            />

            <button
              onClick={handleClassify}
              onKeyPress={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleClassify();
                }
              }}
              disabled={loading || compressing}
              className="bg-blue-600 text-white px-6 py-3 rounded-full hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed focus:outline-none focus:ring-4 focus:ring-blue-600/50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
              aria-label={loading ? t('classifying') : t('classify_food')}
              aria-describedby={loading ? 'classification-announcement' : undefined}
            >
              {loading ? t('classifying') : t('classify_food')}
            </button>

            {classification && (
              <div
                className="mt-6 p-4 bg-green-50 rounded-lg max-w-sm mx-auto"
                role="region"
                aria-label={t('classification_result')}
              >
                <h3 className="font-semibold text-green-800 mb-2">{t('classification_result')}:</h3>
                <p className="text-green-700">{JSON.stringify(classification, null, 2)}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );

  export const getStaticProps: GetStaticProps = async ({ locale }) => ({
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
  });
