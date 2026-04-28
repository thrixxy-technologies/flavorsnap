'use client';

import { useCallback, useState } from 'react';

interface ARCapabilities {
  arSupported: boolean;
  webglSupported: boolean;
  cameraSupported: boolean;
  maxTextureSize: number;
}

interface FoodRecognitionResult {
  id: string;
  label: string;
  confidence: number;
  boundingBox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export const useAR = () => {
  const [arSession, setARSession] = useState<any>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  const getDeviceCapabilities = useCallback(async (): Promise<ARCapabilities> => {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
    
    return {
      arSupported: typeof XRSession !== 'undefined' || 'mediaDevices' in navigator,
      webglSupported: gl !== null,
      cameraSupported: 'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices,
      maxTextureSize: gl ? gl.getParameter(gl.MAX_TEXTURE_SIZE) : 0,
    };
  }, []);

  const initializeAR = useCallback(async (canvas: HTMLCanvasElement) => {
    try {
      const capabilities = await getDeviceCapabilities();
      
      if (!capabilities.arSupported) {
        console.error('AR not supported');
        return;
      }

      // Initialize WebGL context
      const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
      if (!gl) {
        throw new Error('WebGL not supported');
      }

      // Set up AR session
      const session = {
        canvas,
        gl,
        isActive: true,
        timestamp: Date.now(),
      };

      setARSession(session);
      setIsInitialized(true);

      return session;
    } catch (error) {
      console.error('Failed to initialize AR:', error);
      throw error;
    }
  }, [getDeviceCapabilities]);

  const recognizeFood = useCallback(async (imageData: string): Promise<FoodRecognitionResult | null> => {
    try {
      const response = await fetch('/api/ar/recognize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData }),
      });

      if (!response.ok) {
        throw new Error('Recognition failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Food recognition error:', error);
      return null;
    }
  }, []);

  const renderModel = useCallback(
    async (canvas: HTMLCanvasElement, modelUrl: string, scale: { x: number; y: number; z: number }) => {
      if (!arSession) {
        console.error('AR session not initialized');
        return;
      }

      try {
        const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
        if (!gl) return;

        // Fetch 3D model
        const modelResponse = await fetch(modelUrl);
        const modelData = await modelResponse.arrayBuffer();

        // Load and render model (simplified)
        gl.clearColor(0.0, 0.0, 0.0, 1.0);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

        // Here you would typically use Three.js, Babylon.js, or similar
        // to load and render the actual 3D model
        console.log('Rendering model with scale:', scale);
      } catch (error) {
        console.error('Model rendering error:', error);
      }
    },
    [arSession]
  );

  const captureARScreenshot = useCallback(async (canvas: HTMLCanvasElement): Promise<Blob | null> => {
    try {
      return await new Promise((resolve) => {
        canvas.toBlob((blob) => resolve(blob), 'image/png');
      });
    } catch (error) {
      console.error('Screenshot capture error:', error);
      return null;
    }
  }, []);

  const recordARSession = useCallback(async (canvas: HTMLCanvasElement, duration: number) => {
    try {
      const stream = canvas.captureStream(30); // 30 FPS
      const mediaRecorder = new MediaRecorder(stream);
      const chunks: BlobPart[] = [];

      mediaRecorder.ondataavailable = (event) => chunks.push(event.data);
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'video/webm' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `ar-session-${Date.now()}.webm`;
        link.click();
      };

      mediaRecorder.start();
      setTimeout(() => mediaRecorder.stop(), duration);
    } catch (error) {
      console.error('Recording error:', error);
    }
  }, []);

  const getPerformanceMetrics = useCallback((): { fps: number; latency: number } | null => {
    if (!arSession) return null;

    return {
      fps: 60, // Would be calculated from frame timing
      latency: 50, // Would be calculated from model-to-render time
    };
  }, [arSession]);

  return {
    isInitialized,
    initializeAR,
    getDeviceCapabilities,
    recognizeFood,
    renderModel,
    captureARScreenshot,
    recordARSession,
    getPerformanceMetrics,
  };
};
