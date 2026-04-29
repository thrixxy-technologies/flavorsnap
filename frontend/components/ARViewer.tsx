'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useAR } from '@/hooks/useAR';

interface ARFoodModel {
  id: string;
  name: string;
  modelUrl: string;
  scale: { x: number; y: number; z: number };
  metadata: Record<string, any>;
}

export const ARViewer: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [models, setModels] = useState<ARFoodModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<ARFoodModel | null>(null);
  const { initializeAR, recognizeFood, renderModel, getDeviceCapabilities } = useAR();

  useEffect(() => {
    const initAR = async () => {
      setLoading(true);
      try {
        const capabilities = await getDeviceCapabilities();
        
        if (!capabilities.arSupported) {
          alert('AR is not supported on this device');
          return;
        }

        if (canvasRef.current) {
          await initializeAR(canvasRef.current);
        }
      } finally {
        setLoading(false);
      }
    };

    initAR();
  }, [initializeAR, getDeviceCapabilities]);

  const handleCameraCapture = async () => {
    setLoading(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      });

      if (canvasRef.current) {
        const context = canvasRef.current.getContext('2d');
        if (context) {
          const video = document.createElement('video');
          video.srcObject = stream;
          video.play();

          video.onloadedmetadata = async () => {
            canvasRef.current!.width = video.videoWidth;
            canvasRef.current!.height = video.videoHeight;
            context.drawImage(video, 0, 0);

            const imageData = canvasRef.current!.toDataURL('image/jpeg');
            const foodData = await recognizeFood(imageData);

            if (foodData) {
              const arModel: ARFoodModel = {
                id: foodData.id,
                name: foodData.label,
                modelUrl: `/models/food/${foodData.id}.glb`,
                scale: { x: 1, y: 1, z: 1 },
                metadata: foodData,
              };

              setModels((prev) => [...prev, arModel]);
              setSelectedModel(arModel);
            }

            // Stop camera
            stream.getTracks().forEach((track) => track.stop());
          };
        }
      }
    } catch (error) {
      console.error('Camera error:', error);
      alert('Failed to access camera');
    } finally {
      setLoading(false);
    }
  };

  const handleRenderModel = async (model: ARFoodModel) => {
    setLoading(true);
    try {
      const canvas = canvasRef.current;
      if (canvas) {
        await renderModel(canvas, model.modelUrl, model.scale);
        setSelectedModel(model);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleScaleChange = (axis: 'x' | 'y' | 'z', value: number) => {
    if (selectedModel) {
      setSelectedModel({
        ...selectedModel,
        scale: {
          ...selectedModel.scale,
          [axis]: value,
        },
      });
    }
  };

  const handleRotateModel = () => {
    if (selectedModel) {
      const newModel = { ...selectedModel };
      if (canvasRef.current) {
        renderModel(
          canvasRef.current,
          newModel.modelUrl,
          newModel.scale
        );
      }
    }
  };

  const handleShareARScene = async () => {
    if (selectedModel) {
      const shareData = {
        title: `Check out this ${selectedModel.name} in AR!`,
        text: `I found a ${selectedModel.name} using FlavorSnap AR`,
        url: window.location.href,
      };

      if (navigator.share) {
        await navigator.share(shareData);
      } else {
        // Fallback for browsers that don't support share API
        alert('Share feature not supported on this browser');
      }
    }
  };

  return (
    <div className="w-full h-full bg-black rounded-lg overflow-hidden flex flex-col">
      {/* AR Canvas */}
      <div className="flex-1 relative">
        <canvas
          ref={canvasRef}
          className="w-full h-full object-cover"
          data-testid="ar-canvas"
        />
        
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <div className="text-white text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
              <p>Loading AR...</p>
            </div>
          </div>
        )}

        {/* Title Overlay */}
        {selectedModel && (
          <div className="absolute top-4 left-4 bg-black/70 text-white px-4 py-2 rounded-lg">
            <h3 className="font-bold">{selectedModel.name}</h3>
            <p className="text-sm text-gray-300">
              Confidence: {(selectedModel.metadata.confidence * 100).toFixed(1)}%
            </p>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="bg-gray-900 border-t border-gray-700 p-4 space-y-4">
        {/* Main Actions */}
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={handleCameraCapture}
            disabled={loading}
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white rounded-lg font-medium transition"
          >
            📷 Capture
          </button>
          <button
            onClick={handleRotateModel}
            disabled={!selectedModel || loading}
            className="px-4 py-2 bg-purple-500 hover:bg-purple-600 disabled:bg-gray-600 text-white rounded-lg font-medium transition"
          >
            🔄 Rotate
          </button>
          <button
            onClick={handleShareARScene}
            disabled={!selectedModel}
            className="px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-gray-600 text-white rounded-lg font-medium transition"
          >
            📤 Share
          </button>
          <button
            onClick={() => setModels([])}
            className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-medium transition"
          >
            🗑️ Clear
          </button>
        </div>

        {/* Scale Controls */}
        {selectedModel && (
          <div className="bg-gray-800 rounded-lg p-3 space-y-2">
            <p className="text-sm text-gray-300 font-medium">Scale Controls</p>
            <div className="space-y-2">
              {(['x', 'y', 'z'] as const).map((axis) => (
                <div key={axis} className="flex items-center gap-2">
                  <label className="text-gray-300 text-sm w-6">{axis.toUpperCase()}</label>
                  <input
                    type="range"
                    min="0.5"
                    max="2"
                    step="0.1"
                    value={selectedModel.scale[axis]}
                    onChange={(e) => handleScaleChange(axis, parseFloat(e.target.value))}
                    className="flex-1"
                  />
                  <span className="text-gray-300 text-sm w-8">
                    {selectedModel.scale[axis].toFixed(1)}x
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Models List */}
        {models.length > 0 && (
          <div className="bg-gray-800 rounded-lg p-3">
            <p className="text-sm text-gray-300 font-medium mb-2">
              Recognized Items ({models.length})
            </p>
            <div className="flex gap-2 overflow-x-auto">
              {models.map((model) => (
                <button
                  key={model.id}
                  onClick={() => handleRenderModel(model)}
                  className={`px-3 py-1 rounded text-sm font-medium whitespace-nowrap transition ${
                    selectedModel?.id === model.id
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {model.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
