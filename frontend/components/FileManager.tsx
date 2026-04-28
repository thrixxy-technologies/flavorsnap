
import React, { useState, useRef } from 'react';
import { useFileManagement } from '../hooks/useFileManagement';
import { FileItem, formatFileSize } from '../utils/fileOperations';
import { FilePreview } from './FilePreview';

export const FileManager: React.FC = () => {
  const {
    files,
    currentFolderId,
    setCurrentFolderId,
    searchQuery,
    setSearchQuery,
    storageStats,
    createFolder,
    uploadFiles,
    deleteFile,
    moveFile,
    tagFile
  } = useFileManagement();

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      uploadFiles(droppedFiles);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFiles(Array.from(e.target.files));
    }
  };

  const breadcrumbs = [
    { id: null, name: 'My Files' },
    // Mock breadcrumbs for now - in real app would track path
  ];

  return (
    <div className="flex flex-col h-full bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans">
      {/* Top Header */}
      <header className="flex items-center justify-between p-6 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            FlavorSnap Drive
          </h1>
          <div className="h-6 w-px bg-slate-200 dark:bg-slate-800 mx-2" />
          <nav className="flex items-center gap-2">
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={crumb.id || 'root'}>
                {index > 0 && <span className="text-slate-400">/</span>}
                <button 
                  onClick={() => setCurrentFolderId(crumb.id)}
                  className={`px-2 py-1 rounded-md transition-colors ${currentFolderId === crumb.id ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-semibold' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}`}
                >
                  {crumb.name}
                </button>
              </React.Fragment>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input 
              type="text" 
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 bg-slate-100 dark:bg-slate-800 border-none rounded-xl w-64 focus:ring-2 focus:ring-blue-500 transition-all outline-none"
            />
          </div>
          <button 
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold transition-all shadow-lg shadow-blue-500/25 active:scale-95"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Upload
          </button>
          <input 
            type="file" 
            multiple 
            className="hidden" 
            ref={fileInputRef}
            onChange={handleFileSelect}
          />
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 p-6 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 hidden md:flex flex-col gap-8">
          <div className="space-y-2">
            <button className="flex items-center gap-3 w-full px-4 py-3 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl font-semibold transition-all">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              All Files
            </button>
            <button className="flex items-center gap-3 w-full px-4 py-3 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-xl font-medium transition-all">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Recent
            </button>
            <button className="flex items-center gap-3 w-full px-4 py-3 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-xl font-medium transition-all">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.783-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
              Starred
            </button>
            <button className="flex items-center gap-3 w-full px-4 py-3 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-xl font-medium transition-all">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Trash
            </button>
          </div>

          <div className="mt-auto p-4 bg-slate-50 dark:bg-slate-800/50 rounded-2xl border border-slate-200 dark:border-slate-800">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Storage Usage</h4>
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden mb-2">
              <div 
                className="h-full bg-blue-600 transition-all duration-1000" 
                style={{ width: `${(storageStats.used / storageStats.limit) * 100}%` }}
              />
            </div>
            <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
              {formatFileSize(storageStats.used)} used of {formatFileSize(storageStats.limit)}
            </p>
          </div>
        </aside>

        {/* Main Content */}
        <main 
          className={`flex-1 p-6 overflow-auto transition-colors ${isDragging ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-4">
              <h2 className="text-xl font-bold text-slate-800 dark:text-white">
                {currentFolderId ? 'Folder' : 'Quick Access'}
              </h2>
              <span className="px-2 py-1 bg-slate-100 dark:bg-slate-800 text-slate-500 rounded-md text-sm font-bold">
                {files.length} items
              </span>
            </div>
            
            <div className="flex bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-1 shadow-sm">
              <button 
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded-md transition-all ${viewMode === 'grid' ? 'bg-slate-100 dark:bg-slate-800 text-blue-600' : 'text-slate-400'}`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
              </button>
              <button 
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-md transition-all ${viewMode === 'list' ? 'bg-slate-100 dark:bg-slate-800 text-blue-600' : 'text-slate-400'}`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            </div>
          </div>

          {files.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center">
              <div className="w-32 h-32 bg-slate-100 dark:bg-slate-900 rounded-full flex items-center justify-center mb-6">
                <svg className="w-16 h-16 text-slate-300 dark:text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No files yet</h3>
              <p className="text-slate-500 dark:text-slate-400 max-w-xs mx-auto">
                Drag and drop files here or use the upload button to get started.
              </p>
            </div>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
              {files.map((file) => (
                <div 
                  key={file.id}
                  onClick={() => setSelectedFile(file)}
                  className="group relative bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-blue-500/50 dark:hover:border-blue-500/50 hover:shadow-xl hover:shadow-blue-500/5 transition-all cursor-pointer overflow-hidden"
                >
                  <div className="aspect-square rounded-xl bg-slate-50 dark:bg-slate-950 flex items-center justify-center mb-4 group-hover:scale-105 transition-transform duration-300">
                    {file.type === 'folder' ? (
                      <svg className="w-16 h-16 text-amber-400 fill-amber-400/10" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                      </svg>
                    ) : file.mimeType?.startsWith('image/') ? (
                      <img 
                        src={`/api/files/${file.id}/thumbnail`} 
                        alt={file.name}
                        className="w-full h-full object-cover rounded-lg"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                          e.currentTarget.parentElement?.classList.add('bg-blue-50');
                        }}
                      />
                    ) : (
                      <svg className="w-12 h-12 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    )}
                  </div>
                  <h3 className="font-semibold text-sm text-slate-800 dark:text-white truncate mb-1">{file.name}</h3>
                  <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    <span>{file.type === 'folder' ? 'Folder' : formatFileSize(file.size || 0)}</span>
                    <span>{new Date(file.updatedAt).toLocaleDateString()}</span>
                  </div>
                  
                  {/* Action overlay */}
                  <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                    <button 
                      onClick={(e) => { e.stopPropagation(); deleteFile(file.id); }}
                      className="p-1.5 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50">
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Name</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Size</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Updated</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {files.map((file) => (
                    <tr 
                      key={file.id}
                      onClick={() => setSelectedFile(file)}
                      className="hover:bg-blue-50/30 dark:hover:bg-blue-900/10 cursor-pointer transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          {file.type === 'folder' ? (
                            <svg className="w-5 h-5 text-amber-400" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                            </svg>
                          ) : (
                            <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                          )}
                          <span className="font-semibold text-slate-800 dark:text-white">{file.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-500 text-sm">{file.type === 'folder' ? '--' : formatFileSize(file.size || 0)}</td>
                      <td className="px-6 py-4 text-slate-500 text-sm">{new Date(file.updatedAt).toLocaleDateString()}</td>
                      <td className="px-6 py-4">
                        <button 
                          onClick={(e) => { e.stopPropagation(); deleteFile(file.id); }}
                          className="text-red-400 hover:text-red-600 transition-colors"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </main>
      </div>

      {selectedFile && (
        <FilePreview 
          file={selectedFile} 
          onClose={() => setSelectedFile(null)} 
        />
      )}
    </div>
  );
};
