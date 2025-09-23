import React from "react";
import { FileText, Clock } from "lucide-react";

const DocumentItem = ({ title, date, sections, onClick }) => {
  const handleKeyDown = (e) => {
    if (!onClick) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <div
      className="bg-white rounded-lg p-4 flex items-center justify-between shadow-sm hover:shadow-md transition cursor-pointer"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-white">
          <FileText size={20} />
        </div>
        <div>
          <h4 className="font-medium">{title}</h4>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Clock size={14} />
            <span>{date}</span>
            <span>•</span>
            <span>{sections} sections</span>
          </div>
        </div>
      </div>
      <button
        type="button"
        className="text-primary hover:text-primary"
        onClick={(e) => { e.stopPropagation(); onClick && onClick(); }}
        aria-label="Ouvrir le document"
      >
        →
      </button>
    </div>
  );
};

export default DocumentItem;
