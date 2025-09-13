import React from 'react';
import { FileText, Download, Trash2, Eye, Clock, BookOpen } from "lucide-react";

const DocumentCard = ({ 
  title, 
  date, 
  chapters_count, 
  onView, 
  onDownload, 
  onDelete 
}) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <div className="p-5 border-b">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-primary rounded-lg flex items-center justify-center text-white flex-shrink-0">
              <FileText size={24} />
            </div>
            <div>
              <h3 className="font-medium text-gray-900">{title}</h3>
              <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                <Clock size={14} />
                <span>{date}</span>
                <span>•</span>
                <span>{chapters_count} chapitres</span>
              </div>
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
          <button 
            onClick={onDownload}
            className="px-3 py-1.5 text-sm font-medium text-accent hover:bg-accent-50 rounded-md flex items-center gap-1.5"
          >
            <Download size={16} />
            Télécharger PDF
          </button>
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
