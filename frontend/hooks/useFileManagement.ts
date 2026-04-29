
import { useState, useCallback, useMemo } from 'react';
import { FileItem, StorageStats, filterFiles, sortFiles } from '../utils/fileOperations';

export const useFileManagement = (initialFiles: FileItem[] = []) => {
  const [files, setFiles] = useState<FileItem[]>(initialFiles);
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<'name' | 'size' | 'date'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  const filteredAndSortedFiles = useMemo(() => {
    const folderFiles = files.filter(f => f.parentId === currentFolderId);
    const filtered = filterFiles(folderFiles, searchQuery, selectedTags);
    return sortFiles(filtered, sortBy, sortOrder);
  }, [files, currentFolderId, searchQuery, selectedTags, sortBy, sortOrder]);

  const createFolder = useCallback((name: string) => {
    const newFolder: FileItem = {
      id: Math.random().toString(36).substr(2, 9),
      name,
      type: 'folder',
      parentId: currentFolderId,
      tags: [],
      metadata: {},
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ownerId: 'current-user',
      sharedWith: [],
    };
    setFiles(prev => [...prev, newFolder]);
  }, [currentFolderId]);

  const deleteFile = useCallback((id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  }, []);

  const moveFile = useCallback((id: string, newParentId: string | null) => {
    setFiles(prev => prev.map(f => 
      f.id === id ? { ...f, parentId: newParentId, updatedAt: new Date().toISOString() } : f
    ));
  }, []);

  const tagFile = useCallback((id: string, tags: string[]) => {
    setFiles(prev => prev.map(f => 
      f.id === id ? { ...f, tags: Array.from(new Set([...f.tags, ...tags])), updatedAt: new Date().toISOString() } : f
    ));
  }, []);

  const uploadFiles = useCallback((newFiles: File[]) => {
    const items: FileItem[] = newFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      type: 'file',
      size: file.size,
      mimeType: file.type,
      parentId: currentFolderId,
      tags: [],
      metadata: {},
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ownerId: 'current-user',
      sharedWith: [],
    }));
    setFiles(prev => [...prev, ...items]);
  }, [currentFolderId]);

  const storageStats: StorageStats = useMemo(() => {
    const used = files.reduce((acc, f) => acc + (f.size || 0), 0);
    return {
      used,
      total: 10 * 1024 * 1024 * 1024, // 10 GB
      limit: 10 * 1024 * 1024 * 1024,
    };
  }, [files]);

  return {
    files: filteredAndSortedFiles,
    allFiles: files,
    currentFolderId,
    setCurrentFolderId,
    searchQuery,
    setSearchQuery,
    selectedTags,
    setSelectedTags,
    sortBy,
    setSortBy,
    sortOrder,
    setSortOrder,
    createFolder,
    deleteFile,
    moveFile,
    tagFile,
    uploadFiles,
    storageStats,
  };
};
