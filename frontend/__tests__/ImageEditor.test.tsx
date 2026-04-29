import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ImageEditor from '../components/ImageEditor';

// Mock the useCanvas hook
jest.mock('../hooks/useCanvas', () => ({
  useCanvas: () => ({
    canvasRef: { current: null },
    canUndo: false,
    canRedo: false,
    undo: jest.fn(),
    redo: jest.fn(),
    clearCanvas: jest.fn(),
    loadImage: jest.fn(),
    applyFilter: jest.fn(),
    adjustBrightness: jest.fn(),
    adjustContrast: jest.fn(),
    adjustSaturation: jest.fn(),
    rotate: jest.fn(),
    crop: jest.fn(),
    resize: jest.fn(),
    exportImage: jest.fn(),
    tool: 'brush',
    setTool: jest.fn(),
    brushSize: 5,
    setBrushSize: jest.fn(),
    brushColor: '#000000',
    setBrushColor: jest.fn(),
    startDrawing: jest.fn(),
    draw: jest.fn(),
    stopDrawing: jest.fn(),
  }),
}));

// Mock imageProcessing utilities
jest.mock('../utils/imageProcessing', () => ({
  loadImageFromFile: jest.fn(),
  exportImage: jest.fn(),
  downloadImage: jest.fn(),
}));

describe('ImageEditor Component', () => {
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
  });

  test('renders the image editor interface', () => {
    render(<ImageEditor />);

    expect(screen.getByText('Image Editor')).toBeInTheDocument();
    expect(screen.getByText('Upload Image')).toBeInTheDocument();
    expect(screen.getByText('Undo')).toBeInTheDocument();
    expect(screen.getByText('Redo')).toBeInTheDocument();
    expect(screen.getByText('Show Before/After')).toBeInTheDocument();
  });

  test('renders filter controls', () => {
    render(<ImageEditor />);

    expect(screen.getByText('Filters & Adjustments')).toBeInTheDocument();
    expect(screen.getByText('Quick Filters')).toBeInTheDocument();
    expect(screen.getAllByText('Grayscale')).toHaveLength(2); // One in filter controls, one might be elsewhere
  });

  test('renders drawing tools', () => {
    render(<ImageEditor />);

    expect(screen.getByText('Brush')).toBeInTheDocument();
    expect(screen.getByText('Eraser')).toBeInTheDocument();
    expect(screen.getByText('Size:')).toBeInTheDocument();
    expect(screen.getByText('Color:')).toBeInTheDocument();
  });

  test('renders transform tools', () => {
    render(<ImageEditor />);

    expect(screen.getByText('Rotate 90°')).toBeInTheDocument();
    expect(screen.getByText('Rotate -90°')).toBeInTheDocument();
    expect(screen.getByText('Crop Center')).toBeInTheDocument();
    expect(screen.getByText('Resize')).toBeInTheDocument();
  });

  test('renders export options', () => {
    render(<ImageEditor />);

    expect(screen.getByText('Export PNG')).toBeInTheDocument();
    expect(screen.getByText('Export JPEG')).toBeInTheDocument();
    expect(screen.getByText('Export WebP')).toBeInTheDocument();
  });

  test('canvas element is present', () => {
    render(<ImageEditor />);

    const canvas = document.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
  });
});