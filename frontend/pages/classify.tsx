import React, { useEffect, useRef, useState } from "react";
import { api } from "@/utils/api";
import { storage } from "@/utils/storage";
import { pwaManager } from "@/lib/pwa-utils";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ImageUpload } from "@/components/ImageUpload";
import { ClassificationResult as ClassificationResultComponent } from "@/components/ClassificationResult";
import { ThemeToggle } from "@/components/ThemeToggle";
import { VoiceControl } from "@/components/VoiceControl";
import { useTranslation } from "next-i18next";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import type { GetStaticProps } from "next";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { useKeyboardShortcuts } from "@/utils/useKeyboardShortcuts";
import { ClassificationResult, HistoryEntry, AppError } from "@/types";
import { useRouter } from "next/router";
import { VoiceCommand } from "@/hooks/useVoiceCommands";

interface PredictionResult {
  label: string;
  confidence: number;
}

interface ClassificationResponse {
  success: boolean;
  classification_id?: string;
  label: string;
  confidence: number;
  all_predictions: PredictionResult[];
  processing_time: number;
  model_version: string;
  image_info?: {
    original_filename: string;
    file_size: number;
    mime_type: string;
    processed_size: number;
  };
}

export default function Classify() {
  const router = useRouter();
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<ClassificationResponse | null>(null);
  const [error, setError] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImageSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type
      const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        setError("Invalid file type. Please upload a JPEG, PNG, or WebP image.");
        return;
      }

      // Validate file size (10MB)
      if (file.size > 10 * 1024 * 1024) {
        setError("File size exceeds 10MB limit.");
        return;
      }

      setSelectedImage(file);
      setPreview(URL.createObjectURL(file));
      setError("");
      setResult(null);
    }
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
      const syntheticEvent = {
        target: { files: [file] }
      } as React.ChangeEvent<HTMLInputElement>;
      handleImageSelect(syntheticEvent);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  const classifyImage = async () => {
    if (!selectedImage) {
      setError("Please select an image first.");
      return;
    }

    setIsProcessing(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append('image', selectedImage);

      // Use our API utility
      const response = await predictionAPI.classifyImage(formData);

      setResult(response.data);
    } catch (err: any) {
      if (err.response?.data) {
        setError(err.response.data.error || err.response.data.message || 'Classification failed');
      } else {
        setError('Failed to connect to the server. Please try again.');
      }
      console.error('Classification error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const resetForm = () => {
    setSelectedImage(null);
    setPreview("");
    setResult(null);
    setError("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Handle voice commands
  const handleVoiceCommand = (command: VoiceCommand) => {
    switch (command) {
      case 'upload':
        handleOpenPicker();
        break;
      case 'classify':
        if (image && !loading) {
          handleClassify();
        }
        break;
      case 'reset':
        handleReset();
        break;
      case 'help':
        // Show help modal or alert
        alert(t('voice_help', 'Voice commands: "upload" to open camera, "classify" to analyze, "reset" to clear, "cancel" to stop'));
        break;
      case 'cancel':
        // Cancel any ongoing operation
        if (loading) {
          setLoading(false);
          setUploadProgress(0);
        }
        break;
    }
  };

  useKeyboardShortcuts([
    { key: 'o', action: handleOpenPicker },
    { key: 'c', action: () => image && !loading && handleClassify() },
    { key: 'r', action: handleReset },
    { key: 'Escape', action: handleReset },
    { key: 'v', action: () => document.getElementById('voice-toggle')?.click() },
  ]);

  return (
    <div className="min-h-screen flex flex-col items-center p-3 sm:p-4 md:p-8 bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
      <div className="w-full max-w-6xl flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push('/')}
            className="text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 px-4 py-2 rounded-lg transition-colors"
            aria-label={t('back_to_home', 'Back to home')}
          >
            ← {t('back', 'Back')}
          </button>
          <ThemeToggle />
        </div>
        <div className="flex items-center gap-2">
          <VoiceControl 
            onCommand={handleVoiceCommand}
            disabled={loading}
            className="mr-2"
          />
          <LanguageSwitcher />
        </div>
      </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Upload Section */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Upload Image</h2>
            
            {/* Drop Zone */}
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                selectedImage
                  ? "border-green-400 bg-green-50"
                  : "border-gray-300 hover:border-gray-400"
              }`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
            >
              {preview ? (
                <div className="space-y-4">
                  <Image
                    src={preview}
                    alt="Preview"
                    width={200}
                    height={200}
                    className="mx-auto rounded-lg object-cover"
                  />
                  <p className="text-sm text-gray-600">{selectedImage?.name}</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="w-16 h-16 mx-auto bg-gray-200 rounded-full flex items-center justify-center">
                    <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-gray-600 mb-2">
                      Drag and drop your image here, or
                    </p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/jpeg,image/jpg,image/png,image/webp"
                      onChange={handleImageSelect}
                      className="hidden"
                      id="file-upload"
                    />
                    <label
                      htmlFor="file-upload"
                      className="cursor-pointer bg-orange-500 text-white px-4 py-2 rounded-lg hover:bg-orange-600 transition"
                    >
                      Browse Files
                    </label>
                  </div>
                  <p className="text-xs text-gray-500">
                    Supported formats: JPEG, PNG, WebP (Max 10MB)
                  </p>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex gap-4">
              <button
                onClick={classifyImage}
                disabled={!selectedImage || isProcessing}
                className="flex-1 bg-orange-500 text-white py-3 rounded-lg font-semibold hover:bg-orange-600 transition disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {isProcessing ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Processing...
                  </span>
                ) : (
                  "Classify Food"
                )}
              </button>
              <button
                onClick={resetForm}
                disabled={isProcessing}
                className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
              >
                Reset
              </button>
            </div>

            {/* Error Display */}
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-600 text-sm">{error}</p>
              </div>
            )}
          </div>

          {/* Results Section */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Classification Results</h2>
            
            {result ? (
              <div className="space-y-6">
                {/* Primary Result */}
                <div className="text-center p-6 bg-gradient-to-r from-orange-100 to-red-100 rounded-lg">
                  <h3 className="text-2xl font-bold text-gray-800 mb-2">
                    {result.label}
                  </h3>
                  <div className="text-3xl font-bold text-orange-600 mb-2">
                    {result.confidence}%
                  </div>
                  <p className="text-sm text-gray-600">
                    Confidence Score
                  </p>
                </div>

                {/* All Predictions */}
                <div>
                  <h4 className="font-semibold mb-3">All Predictions</h4>
                  <div className="space-y-2">
                    {result.all_predictions.map((prediction, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <span className="font-medium">{prediction.label}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-orange-500 h-2 rounded-full"
                              style={{ width: `${prediction.confidence}%` }}
                            />
                          </div>
                          <span className="text-sm font-semibold w-12 text-right">
                            {prediction.confidence}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Additional Info */}
                <div className="text-xs text-gray-500 space-y-1">
                  <p>Processing Time: {result.processing_time}s</p>
                  <p>Model Version: {result.model_version}</p>
                  {result.image_info && (
                    <p>File Size: {(result.image_info.file_size / 1024 / 1024).toFixed(2)}MB</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-400">
                <div className="w-16 h-16 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-4">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <p>Upload an image to see classification results</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
