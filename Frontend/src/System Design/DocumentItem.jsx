import React from "react";
import { FileText, Clock } from "lucide-react";

const DocumentItem = ({ title, date, sections }) => {
  return (
    <div className="bg-white rounded-lg p-4 flex items-center justify-between shadow-sm hover:shadow-md transition">
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
      <button className="text-primary hover:text-primary">→</button>
    </div>
  );
};

export default DocumentItem;
