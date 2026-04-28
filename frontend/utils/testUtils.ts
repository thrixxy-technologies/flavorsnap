
import { render, RenderOptions } from '@testing-library/react';
import React, { ReactElement } from 'react';

// Custom render function that includes providers if needed
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { ...options });

// Mock data generators
export const mockFile = (overrides = {}) => ({
  id: 'test-id',
  name: 'test-file.jpg',
  type: 'file' as const,
  size: 1024,
  mimeType: 'image/jpeg',
  parentId: null,
  tags: ['test'],
  metadata: {},
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  ownerId: 'test-user',
  sharedWith: [],
  ...overrides,
});

export const mockFolder = (overrides = {}) => ({
  id: 'test-folder',
  name: 'Test Folder',
  type: 'folder' as const,
  parentId: null,
  tags: [],
  metadata: {},
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  ownerId: 'test-user',
  sharedWith: [],
  ...overrides,
});

// Accessibility test helper (requires jest-axe)
// export const checkAccessibility = async (ui: ReactElement) => {
//   const { container } = render(ui);
//   const results = await axe(container);
//   expect(results).toHaveNoViolations();
// };

export * from '@testing-library/react';
export { customRender as render };
