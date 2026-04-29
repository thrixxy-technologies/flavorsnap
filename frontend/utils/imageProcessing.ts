export interface ImageProcessingOptions {
  brightness?: number;
  contrast?: number;
  saturation?: number;
  hue?: number;
  blur?: number;
  sharpen?: number;
}

export const loadImageFromFile = (file: File): Promise<HTMLImageElement> => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
};

export const loadImageFromUrl = (url: string): Promise<HTMLImageElement> => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = url;
  });
};

export const createCanvasFromImage = (image: HTMLImageElement, maxWidth?: number, maxHeight?: number): HTMLCanvasElement => {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d')!;

  let { width, height } = image;

  if (maxWidth && width > maxWidth) {
    height = (height * maxWidth) / width;
    width = maxWidth;
  }

  if (maxHeight && height > maxHeight) {
    width = (width * maxHeight) / height;
    height = maxHeight;
  }

  canvas.width = width;
  canvas.height = height;
  ctx.drawImage(image, 0, 0, width, height);

  return canvas;
};

export const applyImageProcessing = (
  canvas: HTMLCanvasElement,
  options: ImageProcessingOptions
): HTMLCanvasElement => {
  const ctx = canvas.getContext('2d')!;
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const data = imageData.data;

  // Apply brightness
  if (options.brightness !== undefined && options.brightness !== 0) {
    for (let i = 0; i < data.length; i += 4) {
      data[i] = Math.min(255, Math.max(0, data[i] + options.brightness));
      data[i + 1] = Math.min(255, Math.max(0, data[i + 1] + options.brightness));
      data[i + 2] = Math.min(255, Math.max(0, data[i + 2] + options.brightness));
    }
  }

  // Apply contrast
  if (options.contrast !== undefined && options.contrast !== 0) {
    const factor = (259 * (options.contrast + 255)) / (255 * (259 - options.contrast));
    for (let i = 0; i < data.length; i += 4) {
      data[i] = Math.min(255, Math.max(0, factor * (data[i] - 128) + 128));
      data[i + 1] = Math.min(255, Math.max(0, factor * (data[i + 1] - 128) + 128));
      data[i + 2] = Math.min(255, Math.max(0, factor * (data[i + 2] - 128) + 128));
    }
  }

  // Apply saturation
  if (options.saturation !== undefined && options.saturation !== 0) {
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      const gray = 0.299 * r + 0.587 * g + 0.114 * b;
      data[i] = Math.min(255, Math.max(0, gray + (r - gray) * (1 + options.saturation)));
      data[i + 1] = Math.min(255, Math.max(0, gray + (g - gray) * (1 + options.saturation)));
      data[i + 2] = Math.min(255, Math.max(0, gray + (b - gray) * (1 + options.saturation)));
    }
  }

  // Apply hue adjustment
  if (options.hue !== undefined && options.hue !== 0) {
    const hue = options.hue / 180 * Math.PI;
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i] / 255;
      const g = data[i + 1] / 255;
      const b = data[i + 2] / 255;

      const max = Math.max(r, g, b);
      const min = Math.min(r, g, b);
      const delta = max - min;

      let h = 0;
      if (delta !== 0) {
        if (max === r) h = ((g - b) / delta) % 6;
        else if (max === g) h = (b - r) / delta + 2;
        else h = (r - g) / delta + 4;
        h /= 6;
      }

      h = (h + hue / (2 * Math.PI)) % 1;

      let c = (1 - Math.abs(2 * max - 1)) * delta;
      let x = c * (1 - Math.abs((h * 6) % 2 - 1));
      let m = max - c / 2;

      let r2, g2, b2;
      if (h < 1/6) { r2 = c; g2 = x; b2 = 0; }
      else if (h < 2/6) { r2 = x; g2 = c; b2 = 0; }
      else if (h < 3/6) { r2 = 0; g2 = c; b2 = x; }
      else if (h < 4/6) { r2 = 0; g2 = x; b2 = c; }
      else if (h < 5/6) { r2 = x; g2 = 0; b2 = c; }
      else { r2 = c; g2 = 0; b2 = x; }

      data[i] = Math.round((r2 + m) * 255);
      data[i + 1] = Math.round((g2 + m) * 255);
      data[i + 2] = Math.round((b2 + m) * 255);
    }
  }

  // Apply blur
  if (options.blur !== undefined && options.blur > 0) {
    applyGaussianBlur(data, canvas.width, canvas.height, options.blur);
  }

  // Apply sharpen
  if (options.sharpen !== undefined && options.sharpen > 0) {
    applySharpen(data, canvas.width, canvas.height, options.sharpen);
  }

  ctx.putImageData(imageData, 0, 0);
  return canvas;
};

const applyGaussianBlur = (data: Uint8ClampedArray, width: number, height: number, radius: number) => {
  const kernel = generateGaussianKernel(radius);
  applyConvolutionFilter(data, width, height, kernel);
};

const applySharpen = (data: Uint8ClampedArray, width: number, height: number, strength: number) => {
  const kernel = [
    [0, -strength, 0],
    [-strength, 1 + 4 * strength, -strength],
    [0, -strength, 0]
  ];
  applyConvolutionFilter(data, width, height, kernel);
};

const generateGaussianKernel = (sigma: number): number[][] => {
  const size = Math.ceil(sigma * 3) * 2 + 1;
  const kernel: number[][] = [];
  const center = Math.floor(size / 2);
  let sum = 0;

  for (let i = 0; i < size; i++) {
    kernel[i] = [];
    for (let j = 0; j < size; j++) {
      const x = i - center;
      const y = j - center;
      const value = Math.exp(-(x * x + y * y) / (2 * sigma * sigma));
      kernel[i][j] = value;
      sum += value;
    }
  }

  // Normalize
  for (let i = 0; i < size; i++) {
    for (let j = 0; j < size; j++) {
      kernel[i][j] /= sum;
    }
  }

  return kernel;
};

const applyConvolutionFilter = (data: Uint8ClampedArray, width: number, height: number, kernel: number[][]) => {
  const side = kernel.length;
  const halfSide = Math.floor(side / 2);
  const src = new Uint8ClampedArray(data);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let r = 0, g = 0, b = 0;
      for (let cy = 0; cy < side; cy++) {
        for (let cx = 0; cx < side; cx++) {
          const scy = y + cy - halfSide;
          const scx = x + cx - halfSide;
          if (scy >= 0 && scy < height && scx >= 0 && scx < width) {
            const srcOff = (scy * width + scx) * 4;
            const wt = kernel[cy][cx];
            r += src[srcOff] * wt;
            g += src[srcOff + 1] * wt;
            b += src[srcOff + 2] * wt;
          }
        }
      }
      const dstOff = (y * width + x) * 4;
      data[dstOff] = Math.min(255, Math.max(0, r));
      data[dstOff + 1] = Math.min(255, Math.max(0, g));
      data[dstOff + 2] = Math.min(255, Math.max(0, b));
    }
  }
};

export const resizeImage = (canvas: HTMLCanvasElement, newWidth: number, newHeight: number): HTMLCanvasElement => {
  const newCanvas = document.createElement('canvas');
  const newCtx = newCanvas.getContext('2d')!;

  newCanvas.width = newWidth;
  newCanvas.height = newHeight;
  newCtx.drawImage(canvas, 0, 0, newWidth, newHeight);

  return newCanvas;
};

export const cropImage = (canvas: HTMLCanvasElement, x: number, y: number, width: number, height: number): HTMLCanvasElement => {
  const newCanvas = document.createElement('canvas');
  const newCtx = newCanvas.getContext('2d')!;

  newCanvas.width = width;
  newCanvas.height = height;
  newCtx.drawImage(canvas, x, y, width, height, 0, 0, width, height);

  return newCanvas;
};

export const rotateImage = (canvas: HTMLCanvasElement, angle: number): HTMLCanvasElement => {
  const newCanvas = document.createElement('canvas');
  const newCtx = newCanvas.getContext('2d')!;

  const radians = (angle * Math.PI) / 180;
  const sin = Math.abs(Math.sin(radians));
  const cos = Math.abs(Math.cos(radians));

  newCanvas.width = Math.floor(canvas.height * sin + canvas.width * cos);
  newCanvas.height = Math.floor(canvas.height * cos + canvas.width * sin);

  newCtx.translate(newCanvas.width / 2, newCanvas.height / 2);
  newCtx.rotate(radians);
  newCtx.drawImage(canvas, -canvas.width / 2, -canvas.height / 2);

  return newCanvas;
};

export const exportImage = (
  canvas: HTMLCanvasElement,
  format: 'png' | 'jpeg' | 'webp' = 'png',
  quality?: number
): string => {
  return canvas.toDataURL(`image/${format}`, quality);
};

export const downloadImage = (dataUrl: string, filename: string) => {
  const link = document.createElement('a');
  link.href = dataUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};