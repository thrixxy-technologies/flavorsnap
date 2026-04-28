
export interface FileItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  size?: number;
  mimeType?: string;
  parentId: string | null;
  tags: string[];
  metadata: Record<string, any>;
  createdAt: string;
  updatedAt: string;
  ownerId: string;
  sharedWith: string[];
}

export interface StorageStats {
  total: number;
  used: number;
  limit: number;
}

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const filterFiles = (files: FileItem[], query: string, tags: string[]): FileItem[] => {
  return files.filter(file => {
    const matchesQuery = file.name.toLowerCase().includes(query.toLowerCase());
    const matchesTags = tags.length === 0 || tags.every(tag => file.tags.includes(tag));
    return matchesQuery && matchesTags;
  });
};

export const sortFiles = (files: FileItem[], sortBy: 'name' | 'size' | 'date', order: 'asc' | 'desc'): FileItem[] => {
  return [...files].sort((a, b) => {
    let comparison = 0;
    if (sortBy === 'name') {
      comparison = a.name.localeCompare(b.name);
    } else if (sortBy === 'size') {
      comparison = (a.size || 0) - (b.size || 0);
    } else if (sortBy === 'date') {
      comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
    }
    return order === 'asc' ? comparison : -comparison;
  });
};

export const validateFileName = (name: string): boolean => {
  return /^[a-zA-Z0-9._-\s]+$/.test(name) && name.length > 0 && name.length <= 255;
};
