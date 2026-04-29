
import React from 'react';
import { FileItem, formatFileSize } from '../utils/fileOperations';

interface FilePreviewProps {
  file: FileItem;
  onClose: () => void;
}

export const FilePreview: React.FC<FilePreviewProps> = ({ file, onClose }) => {
  const isImage = file.mimeType?.startsWith('image/');
  const isPDF = file.mimeType === 'application/pdf';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-4xl overflow-hidden animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
              <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-white truncate max-w-md">{file.name}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">{formatFileSize(file.size || 0)} • {file.mimeType || 'Unknown type'}</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="relative aspect-video flex items-center justify-center bg-slate-50 dark:bg-slate-950 overflow-auto p-8">
          {isImage ? (
            <img 
              src={`/api/files/${file.id}/content`} 
              alt={file.name}
              className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
              onError={(e) => {
                e.currentTarget.src = 'https://via.placeholder.com/800x450?text=Preview+Not+Available';
              }}
            />
          ) : isPDF ? (
            <iframe 
              src={`/api/files/${file.id}/content`} 
              className="w-full h-full rounded-lg border-0"
              title={file.name}
            />
          ) : (
            <div className="text-center">
              <div className="w-20 h-20 bg-slate-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg className="w-10 h-10 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-slate-600 dark:text-slate-400 font-medium">No preview available for this file type</p>
              <button className="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-all shadow-lg shadow-blue-500/20">
                Download File
              </button>
            </div>
          )}
        </div>

        <div className="p-6 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
          <div className="grid grid-cols-2 gap-8">
            <div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-3">Metadata</h4>
              <dl className="space-y-2">
                <div className="flex justify-between">
                  <dt className="text-sm text-slate-500 dark:text-slate-400">Created</dt>
                  <dd className="text-sm text-slate-900 dark:text-white font-medium">{new Date(file.createdAt).toLocaleDateString()}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-slate-500 dark:text-slate-400">Last Modified</dt>
                  <dd className="text-sm text-slate-900 dark:text-white font-medium">{new Date(file.updatedAt).toLocaleDateString()}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-slate-500 dark:text-slate-400">Owner</dt>
                  <dd className="text-sm text-slate-900 dark:text-white font-medium">You</dd>
                </div>
              </dl>
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-3">Tags</h4>
              <div className="flex flex-wrap gap-2">
                {file.tags.length > 0 ? file.tags.map(tag => (
                  <span key={tag} className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-semibold rounded-full">
                    {tag}
                  </span>
                )) : (
                  <span className="text-sm text-slate-400 italic">No tags added</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
