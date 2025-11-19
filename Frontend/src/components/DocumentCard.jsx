import React from 'react';
import { FileText, Download, Trash2, Eye, Clock, BookOpen, CheckCircle2, CircleOff } from "lucide-react";

const DocumentCard = ({ 
  title, 
  date, 
  chapters_count, 
  document,
  onView, 
  onDownload, 
  onDelete,
  canDownload = true,
  published,
  canTogglePublished = false,
  onTogglePublished,
  canDelete = false,
}) => {
  // Construire l'URL complète de l'image de couverture (interop dev/prod)
  let coverImageUrl = null;
  if (document.cover_image) {
    try {
      const href = document.cover_image;
      const path = href.startsWith('http') ? new URL(href).pathname : href;
      const adjustedPath = path.replace('/books/covers/', '/covers/');
      const isDev = window.location.port === '3000';
      const origin = isDev
        ? `${window.location.protocol}//${window.location.hostname}:8017`
        : `${window.location.protocol}//${window.location.host}`;
      coverImageUrl = adjustedPath.startsWith('/media/')
        ? `${origin}${adjustedPath}`
        : `${origin}/media/${adjustedPath.replace(/^\/?/, '')}`;
    } catch (_) {
      coverImageUrl = document.cover_image;
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      {/* Image de couverture */}
      <div className="h-48 bg-gray-100 relative overflow-hidden">
        {/* Toggle Publié / Non publié en overlay sur la cover */}
        <div className="absolute top-2 right-2 z-10">
          {canTogglePublished ? (
            <button
              type="button"
              onClick={onTogglePublished}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border shadow-sm transition-colors ${published ? 'bg-green-500 border-green-600 text-white' : 'bg-gray-200 border-gray-400 text-gray-700'} cursor-pointer hover:opacity-90`}
            >
              <span
                className={`inline-flex items-center justify-center w-8 h-4 rounded-full mr-1 transition-colors ${published ? 'bg-green-200' : 'bg-gray-400'}`}
              >
                <span
                  className={`block w-3 h-3 bg-white rounded-full shadow transform transition-transform ${published ? 'translate-x-2' : '-translate-x-2'}`}
                />
              </span>
              {published ? (
                <span className="flex items-center gap-1">
                  <CheckCircle2 size={14} />
                  <span>Publié</span>
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <CircleOff size={14} />
                  <span>Non publié</span>
                </span>
              )}
            </button>
          ) : (
            <div
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border shadow-sm ${published ? 'bg-green-50 border-green-200 text-green-700' : 'bg-gray-100 border-gray-200 text-gray-600'}`}
            >
              {published ? (
                <>
                  <CheckCircle2 size={14} />
                  <span>Publié</span>
                </>
              ) : (
                <>
                  <CircleOff size={14} />
                  <span>Non publié</span>
                </>
              )}
            </div>
          )}
        </div>

        {coverImageUrl ? (
          <img 
            src={coverImageUrl} 
            alt={`Couverture de ${title}`}
            className="w-full h-full object-cover"
            onError={(e) => {
              console.log('DocumentCard - Image failed to load:', coverImageUrl);
              console.log('DocumentCard - Error event:', e);
              e.target.style.display = 'none';
              e.target.nextSibling.style.display = 'flex';
            }}
          />
        ) : null}
        <div className="w-full h-full bg-primary flex items-center justify-center text-white" 
             style={{ display: coverImageUrl ? 'none' : 'flex' }}>
          <FileText size={48} />
        </div>
      </div>
      
      <div className="p-5 border-b">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="font-medium text-gray-900 text-lg">{title}</h3>
            <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
              <Clock size={14} />
              <span>{date}</span>
              <span>•</span>
              <span>{chapters_count} chapitres</span>
            </div>
          </div>
          {/* <button className="text-gray-400 hover:text-gray-600">
            <MoreVertical size={18} />
          </button> */}
        </div>
      </div>
      
      <div className="p-4 bg-gray-50 flex justify-between items-center">
        <div className="flex gap-2">
          <button 
            onClick={onView}
            className="px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary-50 rounded-md flex items-center gap-1.5"
          >
            <BookOpen size={16} />
           Lire
          </button>
          {canDownload && (
            <button 
              onClick={onDownload}
              className="px-3 py-1.5 text-sm font-medium text-accent hover:bg-accent-50 rounded-md flex items-center gap-1.5"
            >
              <Download size={16} />
              Télécharger PDF
            </button>
          )}
        </div>
        {canDelete && (
          <button 
            type="button"
            onClick={onDelete}
            className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1"
          >
            <Trash2 size={16} />
            Supprimer
          </button>
        )}
      </div>
    </div>
  );
};

export default DocumentCard;
