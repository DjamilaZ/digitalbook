import React from 'react';
import { FileText, Download, Trash2, Eye, Clock, BookOpen } from "lucide-react";

const DocumentCard = ({ 
  title, 
  date, 
  chapters_count, 
  document,
  onView, 
  onDownload, 
  onDelete,
  canDownload = true,
}) => {
  // Construire l'URL complète de l'image de couverture
  const coverImageUrl = document.cover_image 
    ? (document.cover_image.startsWith('http') 
        ? document.cover_image.replace('/books/covers/', '/covers/')  // Corriger le chemin
        : `http://localhost:8000${document.cover_image}`)
    : null;

  // Débogage
  console.log('DocumentCard - document.cover_image:', document.cover_image);
  console.log('DocumentCard - coverImageUrl:', coverImageUrl);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      {/* Image de couverture */}
      <div className="h-48 bg-gray-100 relative overflow-hidden">
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
        {/* <button 
          onClick={onDelete}
          className="text-primary hover:text-primary"
        >
          Supprimer
        </button> */}
      </div>
    </div>
  );
};

export default DocumentCard;
