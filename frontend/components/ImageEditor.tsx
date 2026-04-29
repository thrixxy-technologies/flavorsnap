import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useCanvas } from '../hooks/useCanvas';
import FilterControls from './FilterControls';
import { loadImageFromFile, exportImage, downloadImage } from '../utils/imageProcessing';

const ImageEditor: React.FC = () => {
  const [originalImage, setOriginalImage] = useState<HTMLImageElement | null>(null);
  const [brightness, setBrightness] = useState(0);
  const [contrast, setContrast] = useState(0);
  const [saturation, setSaturation] = useState(0);
  const [showBeforeAfter, setShowBeforeAfter] = useState(false);
  const [beforeImageData, setBeforeImageData] = useState<ImageData | null>(null);
  const beforeCanvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    canvasRef,
    canUndo,
    canRedo,
    undo,
    redo,
    clearCanvas,
    loadImage,
    applyFilter,
    adjustBrightness,
    adjustContrast,
    adjustSaturation,
    rotate,
    crop,
    resize,
    exportImage: exportCanvasImage,
    tool,
    setTool,
    brushSize,
    setBrushSize,
    brushColor,
    setBrushColor,
    startDrawing,
    draw,
    stopDrawing,
  } = useCanvas({ width: 800, height: 600 });

  useEffect(() => {
    if (beforeCanvasRef.current && beforeImageData) {
      const ctx = beforeCanvasRef.current.getContext('2d');
      if (ctx) {
        ctx.putImageData(beforeImageData, 0, 0);
      }
    }
  }, [beforeImageData]);

  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const image = await loadImageFromFile(file);
      setOriginalImage(image);
      loadImage(image);
      setBeforeImageData(null);
      setBrightness(0);
      setContrast(0);
      setSaturation(0);
    } catch (error) {
      console.error('Error loading image:', error);
      alert('Error loading image. Please try again.');
    }
  }, [loadImage]);

  const handleApplyFilter = useCallback((filter: string) => {
    if (!beforeImageData && originalImage) {
      // Store the original image data for before/after comparison
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d')!;
      canvas.width = canvasRef.current!.width;
      canvas.height = canvasRef.current!.height;
      ctx.drawImage(originalImage, 0, 0, canvas.width, canvas.height);
      setBeforeImageData(ctx.getImageData(0, 0, canvas.width, canvas.height));
    }
    applyFilter(filter);
  }, [applyFilter, beforeImageData, originalImage, canvasRef]);

  const handleAdjustBrightness = useCallback((value: number) => {
    if (!beforeImageData && originalImage) {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d')!;
      canvas.width = canvasRef.current!.width;
      canvas.height = canvasRef.current!.height;
      ctx.drawImage(originalImage, 0, 0, canvas.width, canvas.height);
      setBeforeImageData(ctx.getImageData(0, 0, canvas.width, canvas.height));
    }
    adjustBrightness(value - brightness);
    setBrightness(value);
  }, [adjustBrightness, brightness, beforeImageData, originalImage, canvasRef]);

  const handleAdjustContrast = useCallback((value: number) => {
    if (!beforeImageData && originalImage) {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d')!;
      canvas.width = canvasRef.current!.width;
      canvas.height = canvasRef.current!.height;
      ctx.drawImage(originalImage, 0, 0, canvas.width, canvas.height);
      setBeforeImageData(ctx.getImageData(0, 0, canvas.width, canvas.height));
    }
    adjustContrast(value - contrast);
    setContrast(value);
  }, [adjustContrast, contrast, beforeImageData, originalImage, canvasRef]);

  const handleAdjustSaturation = useCallback((value: number) => {
    if (!beforeImageData && originalImage) {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d')!;
      canvas.width = canvasRef.current!.width;
      canvas.height = canvasRef.current!.height;
      ctx.drawImage(originalImage, 0, 0, canvas.width, canvas.height);
      setBeforeImageData(ctx.getImageData(0, 0, canvas.width, canvas.height));
    }
    adjustSaturation(value - saturation);
    setSaturation(value);
  }, [adjustSaturation, saturation, beforeImageData, originalImage, canvasRef]);

  const handleRotate = useCallback((angle: number) => {
    if (!beforeImageData && originalImage) {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d')!;
      canvas.width = canvasRef.current!.width;
      canvas.height = canvasRef.current!.height;
      ctx.drawImage(originalImage, 0, 0, canvas.width, canvas.height);
      setBeforeImageData(ctx.getImageData(0, 0, canvas.width, canvas.height));
    }
    rotate(angle);
  }, [rotate, beforeImageData, originalImage, canvasRef]);

  const handleCrop = useCallback(() => {
    // For simplicity, crop to center 80% of the image
    const canvas = canvasRef.current;
    if (!canvas) return;

    const width = canvas.width * 0.8;
    const height = canvas.height * 0.8;
    const x = (canvas.width - width) / 2;
    const y = (canvas.height - height) / 2;

    if (!beforeImageData && originalImage) {
      const tempCanvas = document.createElement('canvas');
      const ctx = tempCanvas.getContext('2d')!;
      tempCanvas.width = canvas.width;
      tempCanvas.height = canvas.height;
      ctx.drawImage(originalImage, 0, 0, tempCanvas.width, tempCanvas.height);
      setBeforeImageData(ctx.getImageData(0, 0, tempCanvas.width, tempCanvas.height));
    }
    crop(x, y, width, height);
  }, [crop, beforeImageData, originalImage, canvasRef]);

  const handleResize = useCallback(() => {
    const newWidth = prompt('Enter new width:', '800');
    const newHeight = prompt('Enter new height:', '600');
    if (newWidth && newHeight) {
      if (!beforeImageData && originalImage) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d')!;
        canvas.width = canvasRef.current!.width;
        canvas.height = canvasRef.current!.height;
        ctx.drawImage(originalImage, 0, 0, canvas.width, canvas.height);
        setBeforeImageData(ctx.getImageData(0, 0, canvas.width, canvas.height));
      }
      resize(parseInt(newWidth), parseInt(newHeight));
    }
  }, [resize, beforeImageData, originalImage, canvasRef]);

  const handleExport = useCallback((format: 'png' | 'jpeg' | 'webp' = 'png') => {
    const dataUrl = exportCanvasImage(format);
    if (dataUrl) {
      const filename = `edited-image.${format}`;
      downloadImage(dataUrl, filename);
    }
  }, [exportCanvasImage]);

  const toggleBeforeAfter = useCallback(() => {
    if (!showBeforeAfter && !beforeImageData && originalImage) {
      // Initialize before image data when first toggling on
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d')!;
      canvas.width = canvasRef.current!.width;
      canvas.height = canvasRef.current!.height;
      ctx.drawImage(originalImage, 0, 0, canvas.width, canvas.height);
      setBeforeImageData(ctx.getImageData(0, 0, canvas.width, canvas.height));
    }
    setShowBeforeAfter(!showBeforeAfter);
  }, [showBeforeAfter, beforeImageData, originalImage, canvasRef]);

  return (
    <div className="flex flex-col lg:flex-row gap-6 p-6 bg-gray-50 min-h-screen">
      {/* Main Canvas Area */}
      <div className="flex-1">
        <div className="bg-white rounded-lg shadow-md p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Image Editor</h2>
            <div className="flex gap-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              >
                Upload Image
              </button>
              <button
                onClick={undo}
                disabled={!canUndo}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Undo
              </button>
              <button
                onClick={redo}
                disabled={!canRedo}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Redo
              </button>
              <button
                onClick={toggleBeforeAfter}
                className={`px-4 py-2 rounded transition-colors ${
                  showBeforeAfter ? 'bg-green-500 text-white hover:bg-green-600' : 'bg-gray-500 text-white hover:bg-gray-600'
                }`}
              >
                {showBeforeAfter ? 'Hide' : 'Show'} Before/After
              </button>
            </div>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
          />

          <div className="flex gap-4">
            {/* Canvas */}
            <div className="flex-1">
              <canvas
                ref={canvasRef}
                onMouseDown={startDrawing}
                onMouseMove={draw}
                onMouseUp={stopDrawing}
                onMouseLeave={stopDrawing}
                className="border border-gray-300 rounded cursor-crosshair max-w-full h-auto"
                style={{ maxHeight: '600px' }}
              />
            </div>

            {/* Before/After View */}
            {showBeforeAfter && beforeImageData && (
              <div className="flex-1">
                <h3 className="text-lg font-medium mb-2">Before</h3>
                <canvas
                  ref={beforeCanvasRef}
                  width={canvasRef.current?.width || 800}
                  height={canvasRef.current?.height || 600}
                  className="border border-gray-300 rounded max-w-full h-auto"
                  style={{ maxHeight: '600px' }}
                />
              </div>
            )}
          </div>

          {/* Drawing Tools */}
          <div className="mt-4 flex flex-wrap gap-4 items-center">
            <div className="flex gap-2">
              <button
                onClick={() => setTool('brush')}
                className={`px-3 py-2 rounded ${tool === 'brush' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
              >
                Brush
              </button>
              <button
                onClick={() => setTool('eraser')}
                className={`px-3 py-2 rounded ${tool === 'eraser' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
              >
                Eraser
              </button>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm">Size:</label>
              <input
                type="range"
                min="1"
                max="50"
                value={brushSize}
                onChange={(e) => setBrushSize(Number(e.target.value))}
                className="w-20"
              />
              <span className="text-sm">{brushSize}px</span>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm">Color:</label>
              <input
                type="color"
                value={brushColor}
                onChange={(e) => setBrushColor(e.target.value)}
                className="w-8 h-8 rounded border"
              />
            </div>
          </div>

          {/* Transform Tools */}
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              onClick={() => handleRotate(90)}
              className="px-3 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
            >
              Rotate 90°
            </button>
            <button
              onClick={() => handleRotate(-90)}
              className="px-3 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
            >
              Rotate -90°
            </button>
            <button
              onClick={handleCrop}
              className="px-3 py-2 bg-orange-500 text-white rounded hover:bg-orange-600"
            >
              Crop Center
            </button>
            <button
              onClick={handleResize}
              className="px-3 py-2 bg-orange-500 text-white rounded hover:bg-orange-600"
            >
              Resize
            </button>
          </div>

          {/* Export Options */}
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => handleExport('png')}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Export PNG
            </button>
            <button
              onClick={() => handleExport('jpeg')}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Export JPEG
            </button>
            <button
              onClick={() => handleExport('webp')}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Export WebP
            </button>
          </div>
        </div>
      </div>

      {/* Controls Sidebar */}
      <div className="w-full lg:w-80">
        <FilterControls
          onApplyFilter={handleApplyFilter}
          onAdjustBrightness={handleAdjustBrightness}
          onAdjustContrast={handleAdjustContrast}
          onAdjustSaturation={handleAdjustSaturation}
          brightness={brightness}
          contrast={contrast}
          saturation={saturation}
        />
      </div>
    </div>
  );
};

export default ImageEditor;