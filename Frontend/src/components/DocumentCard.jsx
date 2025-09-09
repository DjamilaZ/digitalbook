import React from 'react';
import { FileText, Clock, MoreVertical, BookOpen, FileSearch } from 'lucide-react';

const DocumentCard = ({ 
  title, 
  date, 
  sections, 
  onView, 
  onAnalyze, 
  onDelete 
}) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <div className="p-5 border-b">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 flex-shrink-0">
              <FileText size={24} />
            </div>
            <div>
              <h3 className="font-medium text-gray-900">{title}</h3>
              <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                <Clock size={14} />
                <span>{date}</span>
                <span>•</span>
                <span>{sections} sections</span>
              </div>
            </div>
          </div>
          <button className="text-gray-400 hover:text-gray-600">
            <MoreVertical size={18} />
          </button>
        </div>
      </div>
      
      <div className="p-4 bg-gray-50 flex justify-between items-center">
        <div className="flex gap-2">
          <button 
            onClick={onView}
            className="px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-md flex items-center gap-1.5"
          >
            <BookOpen size={16} />
            Voir
          </button>
          <button 
            onClick={onAnalyze}
            className="px-3 py-1.5 text-sm font-medium text-purple-600 hover:bg-purple-50 rounded-md flex items-center gap-1.5"
          >
            <FileSearch size={16} />
            Analyser
          </button>
        </div>
        <button 
          onClick={onDelete}
          className="text-sm text-red-600 hover:text-red-800"
        >
          Supprimer
        </button>
      </div>
    </div>
  );
};

export default DocumentCard;
