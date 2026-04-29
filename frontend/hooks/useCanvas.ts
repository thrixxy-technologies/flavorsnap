import { useRef, useEffect, useState, useCallback } from 'react';

export interface CanvasHistory {
  data: ImageData;
  timestamp: number;
}

export interface UseCanvasOptions {
  width: number;
  height: number;
  backgroundColor?: string;
}

export const useCanvas = ({ width, height, backgroundColor = '#ffffff' }: UseCanvasOptions) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [history, setHistory] = useState<CanvasHistory[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [isDrawing, setIsDrawing] = useState(false);
  const [tool, setTool] = useState<'brush' | 'eraser' | 'line' | 'rectangle' | 'circle'>('brush');
  const [brushSize, setBrushSize] = useState(5);
  const [brushColor, setBrushColor] = useState('#000000');

  const getCanvas = useCallback(() => canvasRef.current, []);
  const getContext = useCallback(() => canvasRef.current?.getContext('2d'), []);

  const saveToHistory = useCallback(() => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push({ data: imageData, timestamp: Date.now() });
    setHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
  }, [getCanvas, getContext, history, historyIndex]);

  const undo = useCallback(() => {
    if (historyIndex > 0) {
      const ctx = getContext();
      if (!ctx) return;

      const prevState = history[historyIndex - 1];
      ctx.putImageData(prevState.data, 0, 0);
      setHistoryIndex(historyIndex - 1);
    }
  }, [getContext, history, historyIndex]);

  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const ctx = getContext();
      if (!ctx) return;

      const nextState = history[historyIndex + 1];
      ctx.putImageData(nextState.data, 0, 0);
      setHistoryIndex(historyIndex + 1);
    }
  }, [getContext, history, historyIndex]);

  const clearCanvas = useCallback(() => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    saveToHistory();
  }, [getCanvas, getContext, backgroundColor, saveToHistory]);

  const loadImage = useCallback((image: HTMLImageElement) => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    // Calculate scaling to fit the image within the canvas while maintaining aspect ratio
    const scale = Math.min(canvas.width / image.width, canvas.height / image.height);
    const x = (canvas.width - image.width * scale) / 2;
    const y = (canvas.height - image.height * scale) / 2;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, x, y, image.width * scale, image.height * scale);
    saveToHistory();
  }, [getCanvas, getContext, saveToHistory]);

  const getImageData = useCallback(() => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return null;

    return ctx.getImageData(0, 0, canvas.width, canvas.height);
  }, [getCanvas, getContext]);

  const putImageData = useCallback((imageData: ImageData) => {
    const ctx = getContext();
    if (!ctx) return;

    ctx.putImageData(imageData, 0, 0);
  }, [getContext]);

  const applyFilter = useCallback((filter: string) => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    switch (filter) {
      case 'grayscale':
        for (let i = 0; i < data.length; i += 4) {
          const gray = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
          data[i] = gray;
          data[i + 1] = gray;
          data[i + 2] = gray;
        }
        break;
      case 'sepia':
        for (let i = 0; i < data.length; i += 4) {
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];
          data[i] = Math.min(255, r * 0.393 + g * 0.769 + b * 0.189);
          data[i + 1] = Math.min(255, r * 0.349 + g * 0.686 + b * 0.168);
          data[i + 2] = Math.min(255, r * 0.272 + g * 0.534 + b * 0.131);
        }
        break;
      case 'invert':
        for (let i = 0; i < data.length; i += 4) {
          data[i] = 255 - data[i];
          data[i + 1] = 255 - data[i + 1];
          data[i + 2] = 255 - data[i + 2];
        }
        break;
      case 'blur':
        // Simple box blur implementation
        const kernel = [
          [1/9, 1/9, 1/9],
          [1/9, 1/9, 1/9],
          [1/9, 1/9, 1/9]
        ];
        applyConvolutionFilter(data, canvas.width, canvas.height, kernel);
        break;
      case 'sharpen':
        const sharpenKernel = [
          [0, -1, 0],
          [-1, 5, -1],
          [0, -1, 0]
        ];
        applyConvolutionFilter(data, canvas.width, canvas.height, sharpenKernel);
        break;
      case 'vintage':
        for (let i = 0; i < data.length; i += 4) {
          data[i] = Math.min(255, data[i] * 1.2);
          data[i + 1] = Math.min(255, data[i + 1] * 0.9);
          data[i + 2] = Math.min(255, data[i + 2] * 0.8);
        }
        break;
    }

    ctx.putImageData(imageData, 0, 0);
    saveToHistory();
  }, [getCanvas, getContext, saveToHistory]);

  const applyConvolutionFilter = (data: Uint8ClampedArray, width: number, height: number, kernel: number[][]) => {
    const side = Math.round(Math.sqrt(kernel.length));
    const halfSide = Math.floor(side / 2);
    const src = new Uint8ClampedArray(data);
    const sw = width;
    const sh = height;

    for (let y = 0; y < sh; y++) {
      for (let x = 0; x < sw; x++) {
        let r = 0, g = 0, b = 0;
        for (let cy = 0; cy < side; cy++) {
          for (let cx = 0; cx < side; cx++) {
            const scy = y + cy - halfSide;
            const scx = x + cx - halfSide;
            if (scy >= 0 && scy < sh && scx >= 0 && scx < sw) {
              const srcOff = (scy * sw + scx) * 4;
              const wt = kernel[cy][cx];
              r += src[srcOff] * wt;
              g += src[srcOff + 1] * wt;
              b += src[srcOff + 2] * wt;
            }
          }
        }
        const dstOff = (y * sw + x) * 4;
        data[dstOff] = Math.min(255, Math.max(0, r));
        data[dstOff + 1] = Math.min(255, Math.max(0, g));
        data[dstOff + 2] = Math.min(255, Math.max(0, b));
      }
    }
  };

  const adjustBrightness = useCallback((value: number) => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    for (let i = 0; i < data.length; i += 4) {
      data[i] = Math.min(255, Math.max(0, data[i] + value));
      data[i + 1] = Math.min(255, Math.max(0, data[i + 1] + value));
      data[i + 2] = Math.min(255, Math.max(0, data[i + 2] + value));
    }

    ctx.putImageData(imageData, 0, 0);
    saveToHistory();
  }, [getCanvas, getContext, saveToHistory]);

  const adjustContrast = useCallback((value: number) => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;
    const factor = (259 * (value + 255)) / (255 * (259 - value));

    for (let i = 0; i < data.length; i += 4) {
      data[i] = Math.min(255, Math.max(0, factor * (data[i] - 128) + 128));
      data[i + 1] = Math.min(255, Math.max(0, factor * (data[i + 1] - 128) + 128));
      data[i + 2] = Math.min(255, Math.max(0, factor * (data[i + 2] - 128) + 128));
    }

    ctx.putImageData(imageData, 0, 0);
    saveToHistory();
  }, [getCanvas, getContext, saveToHistory]);

  const adjustSaturation = useCallback((value: number) => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      const gray = 0.299 * r + 0.587 * g + 0.114 * b;
      data[i] = Math.min(255, Math.max(0, gray + (r - gray) * (1 + value)));
      data[i + 1] = Math.min(255, Math.max(0, gray + (g - gray) * (1 + value)));
      data[i + 2] = Math.min(255, Math.max(0, gray + (b - gray) * (1 + value)));
    }

    ctx.putImageData(imageData, 0, 0);
    saveToHistory();
  }, [getCanvas, getContext, saveToHistory]);

  const rotate = useCallback((angle: number) => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate((angle * Math.PI) / 180);
    ctx.translate(-canvas.width / 2, -canvas.height / 2);
    ctx.putImageData(imageData, 0, 0);
    ctx.restore();
    saveToHistory();
  }, [getCanvas, getContext, saveToHistory]);

  const crop = useCallback((x: number, y: number, width: number, height: number) => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    const imageData = ctx.getImageData(x, y, width, height);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.putImageData(imageData, 0, 0);
    saveToHistory();
  }, [getCanvas, getContext, saveToHistory]);

  const resize = useCallback((newWidth: number, newHeight: number) => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    canvas.width = newWidth;
    canvas.height = newHeight;
    ctx.putImageData(imageData, 0, 0);
    saveToHistory();
  }, [getCanvas, getContext, saveToHistory]);

  const exportImage = useCallback((format: 'png' | 'jpeg' | 'webp' = 'png', quality?: number) => {
    const canvas = getCanvas();
    if (!canvas) return null;

    return canvas.toDataURL(`image/${format}`, quality);
  }, [getCanvas]);

  // Drawing functionality
  const startDrawing = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    setIsDrawing(true);
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.beginPath();
    ctx.moveTo(x, y);
  }, [getCanvas, getContext]);

  const draw = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;

    const canvas = getCanvas();
    const ctx = getContext();
    if (!canvas || !ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.lineWidth = brushSize;
    ctx.lineCap = 'round';
    ctx.strokeStyle = tool === 'eraser' ? backgroundColor : brushColor;

    if (tool === 'brush' || tool === 'eraser') {
      ctx.lineTo(x, y);
      ctx.stroke();
    }
  }, [isDrawing, getCanvas, getContext, brushSize, brushColor, tool, backgroundColor]);

  const stopDrawing = useCallback(() => {
    setIsDrawing(false);
    saveToHistory();
  }, [saveToHistory]);

  useEffect(() => {
    const canvas = getCanvas();
    if (canvas) {
      canvas.width = width;
      canvas.height = height;
      clearCanvas();
    }
  }, [width, height, clearCanvas, getCanvas]);

  return {
    canvasRef,
    history,
    historyIndex,
    canUndo: historyIndex > 0,
    canRedo: historyIndex < history.length - 1,
    undo,
    redo,
    clearCanvas,
    loadImage,
    getImageData,
    putImageData,
    applyFilter,
    adjustBrightness,
    adjustContrast,
    adjustSaturation,
    rotate,
    crop,
    resize,
    exportImage,
    tool,
    setTool,
    brushSize,
    setBrushSize,
    brushColor,
    setBrushColor,
    startDrawing,
    draw,
    stopDrawing,
  };
};