import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ImageUpload } from './ImageUpload';

// Mock next-i18next
jest.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback || key,
  }),
}));

describe('ImageUpload Accessibility', () => {
  const mockOnImageSelect = jest.fn();
  const mockOnError = jest.fn();

  beforeEach(() => {
    mockOnImageSelect.mockClear();
    mockOnError.mockClear();
  });

  test('has proper ARIA attributes', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    
    expect(dropZone).toHaveAttribute('role', 'button');
    expect(dropZone).toHaveAttribute('tabIndex', '0');
    expect(dropZone).toHaveAttribute('aria-label', 'Image upload area');
    expect(dropZone).toHaveAttribute('aria-disabled', 'false');
    expect(dropZone).toHaveAttribute('aria-pressed', 'false');
    expect(dropZone).toHaveAttribute('aria-busy', 'false');
  });

  test('disabled state is properly announced', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} disabled />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    
    expect(dropZone).toHaveAttribute('aria-disabled', 'true');
    expect(dropZone).toHaveAttribute('tabIndex', '-1');
  });

  test('loading state is properly announced', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} loading />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    
    expect(dropZone).toHaveAttribute('aria-busy', 'true');
    expect(dropZone).toHaveAttribute('aria-disabled', 'true');
  });

  test('supports keyboard navigation', async () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    
    // Test Enter key
    fireEvent.keyDown(dropZone, { key: 'Enter' });
    expect(dropZone).toHaveFocus();
    
    // Test Space key
    fireEvent.keyDown(dropZone, { key: ' ' });
    expect(dropZone).toHaveFocus();
    
    // Test Escape key
    fireEvent.keyDown(dropZone, { key: 'Escape' });
    expect(dropZone).not.toHaveFocus();
  });

  test('provides screen reader feedback for drag state', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    
    // Simulate drag enter
    fireEvent.dragEnter(dropZone);
    expect(dropZone).toHaveAttribute('aria-pressed', 'true');
    
    // Check for drag overlay
    expect(screen.getByText('Drop image here to upload')).toBeInTheDocument();
  });

  test('progress bar has proper accessibility attributes', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} uploadProgress={50} />);
    
    const progressBar = screen.getByRole('progressbar');
    
    expect(progressBar).toHaveAttribute('aria-valuenow', '50');
    expect(progressBar).toHaveAttribute('aria-valuemin', '0');
    expect(progressBar).toHaveAttribute('aria-valuemax', '100');
    expect(progressBar).toHaveAttribute('aria-label');
  });

  test('progress bar announces changes to screen readers', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} uploadProgress={75} />);
    
    const liveRegion = screen.getByText('Upload progress: 75%');
    expect(liveRegion).toHaveAttribute('aria-live', 'polite');
    expect(liveRegion).toHaveAttribute('aria-atomic', 'true');
  });

  test('drop zone references progress bar when active', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} uploadProgress={25} />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    expect(dropZone).toHaveAttribute('aria-describedby', 'upload-progress');
  });

  test('file type hint has proper accessibility role', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const fileTypeHint = screen.getByRole('note');
    expect(fileTypeHint).toBeInTheDocument();
    expect(fileTypeHint).toHaveAttribute('aria-label');
  });

  test('mobile hint is hidden from screen readers', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const mobileHint = screen.getByText('tap_to_upload');
    expect(mobileHint).toHaveAttribute('aria-hidden', 'true');
  });

  test('drag overlay has live region for announcements', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    fireEvent.dragEnter(dropZone);
    
    const dragOverlay = screen.getByText('Drop image here to upload').parentElement;
    expect(dragOverlay).toHaveAttribute('aria-live', 'polite');
    expect(dragOverlay).toHaveAttribute('aria-atomic', 'true');
  });

  test('keyboard navigation is disabled when component is disabled', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} disabled />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    
    // Keyboard events should not trigger actions when disabled
    fireEvent.keyDown(dropZone, { key: 'Enter' });
    expect(mockOnImageSelect).not.toHaveBeenCalled();
    
    fireEvent.keyDown(dropZone, { key: ' ' });
    expect(mockOnImageSelect).not.toHaveBeenCalled();
  });

  test('keyboard navigation is disabled when component is loading', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} loading />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    
    // Keyboard events should not trigger actions when loading
    fireEvent.keyDown(dropZone, { key: 'Enter' });
    expect(mockOnImageSelect).not.toHaveBeenCalled();
    
    fireEvent.keyDown(dropZone, { key: ' ' });
    expect(mockOnImageSelect).not.toHaveBeenCalled();
  });

  test('calls onImageSelect when valid file is dropped', async () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    const validFile = new File(['content'], 'valid.jpg', { type: 'image/jpeg' });
    
    fireEvent.drop(dropZone, { dataTransfer: { files: [validFile] } });
    
    await waitFor(() => {
      expect(mockOnImageSelect).toHaveBeenCalledWith(validFile, expect.any(String));
    });
  });

  test('calls onError when invalid file is dropped', async () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} onError={mockOnError} />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    const invalidFile = new File(['content'], 'invalid.txt', { type: 'text/plain' });
    
    fireEvent.drop(dropZone, { dataTransfer: { files: [invalidFile] } });
    
    await waitFor(() => {
      expect(mockOnError).toHaveBeenCalledWith({
        message: 'Invalid file type. Please upload an image.',
        code: 'INVALID_FILE_TYPE'
      });
    });
  });

  test('focus is properly managed', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    
    // Component should be focusable
    dropZone.focus();
    expect(dropZone).toHaveFocus();
    
    // Escape should blur focus
    fireEvent.keyDown(dropZone, { key: 'Escape' });
    expect(dropZone).not.toHaveFocus();
  });

  test('input element is properly hidden from tab order', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const fileInput = screen.getByLabelText('select_image_file');
    expect(fileInput).toHaveAttribute('tabIndex', '-1');
  });
});

describe('ImageUpload Functionality', () => {
  const mockOnImageSelect = jest.fn();

  beforeEach(() => {
    mockOnImageSelect.mockClear();
  });

  test('handles click events properly', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    fireEvent.click(dropZone);
    
    // Should trigger file input click (we can't directly test this but we can ensure no errors)
    expect(dropZone).toBeInTheDocument();
  });

  test('handles touch events', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const dropZone = screen.getByTestId('image-upload-drop-zone');
    
    fireEvent.touchStart(dropZone);
    fireEvent.touchEnd(dropZone);
    
    expect(dropZone).toBeInTheDocument();
  });

  test('handles file input changes', async () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const fileInput = screen.getByLabelText('select_image_file');
    const validFile = new File(['content'], 'valid.jpg', { type: 'image/jpeg' });
    
    fireEvent.change(fileInput, { target: { files: [validFile] } });
    
    await waitFor(() => {
      expect(mockOnImageSelect).toHaveBeenCalledWith(validFile, expect.any(String));
    });
  });

  test('resets input value after file selection', () => {
    render(<ImageUpload onImageSelect={mockOnImageSelect} />);
    
    const fileInput = screen.getByLabelText('select_image_file');
    const validFile = new File(['content'], 'valid.jpg', { type: 'image/jpeg' });
    
    fireEvent.change(fileInput, { target: { files: [validFile] } });
    
    // Input value should be reset to allow selecting the same file again
    expect(fileInput).toHaveAttribute('value', '');
  });
});
