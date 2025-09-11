import React, { useState } from 'react';
import './Sidebar.css';

const Sidebar = ({ bookData, onSelectContent, selectedItem }) => {
  const [expandedChapters, setExpandedChapters] = useState({});
  const [expandedSections, setExpandedSections] = useState({});

  const toggleChapter = (chapterIndex) => {
    setExpandedChapters(prev => ({
      ...prev,
      [chapterIndex]: !prev[chapterIndex]
    }));
  };

  const toggleSection = (chapterIndex, sectionIndex) => {
    const key = `${chapterIndex}-${sectionIndex}`;
    setExpandedSections(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const handleItemClick = (type, chapterIndex, sectionIndex = null, subsectionIndex = null) => {
    onSelectContent({ type, chapterIndex, sectionIndex, subsectionIndex });
    
    // Mettre à jour les états d'expansion
    if (type === 'chapter') {
      if (!expandedChapters[chapterIndex]) {
        toggleChapter(chapterIndex);
      }
    } else if (type === 'section') {
      if (!expandedChapters[chapterIndex]) {
        toggleChapter(chapterIndex);
      }
      if (!expandedSections[`${chapterIndex}-${sectionIndex}`]) {
        toggleSection(chapterIndex, sectionIndex);
      }
    } else if (type === 'subsection') {
      if (!expandedChapters[chapterIndex]) {
        toggleChapter(chapterIndex);
      }
      if (!expandedSections[`${chapterIndex}-${sectionIndex}`]) {
        toggleSection(chapterIndex, sectionIndex);
      }
    }
  };

  const isSelected = (type, chapterIndex, sectionIndex = null, subsectionIndex = null) => {
    if (!selectedItem) return false;
    
    if (type === 'chapter' && selectedItem.type === 'chapter') {
      return selectedItem.chapterIndex === chapterIndex;
    } else if (type === 'section' && selectedItem.type === 'section') {
      return selectedItem.chapterIndex === chapterIndex && selectedItem.sectionIndex === sectionIndex;
    } else if (type === 'subsection' && selectedItem.type === 'subsection') {
      return selectedItem.chapterIndex === chapterIndex && 
             selectedItem.sectionIndex === sectionIndex && 
             selectedItem.subsectionIndex === subsectionIndex;
    }
    
    return false;
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Sommaire</h2>
      </div>
      
      <div className="sidebar-content">
        {bookData.chapters.map((chapter, chapterIndex) => (
          <div key={chapterIndex} className="chapter-item">
            <div 
              className={`chapter-header ${isSelected('chapter', chapterIndex) ? 'selected' : ''}`}
              onClick={() => handleItemClick('chapter', chapterIndex)}
            >
              {chapter.sections.length > 0 && (
                <span className="toggle-icon">
                  {expandedChapters[chapterIndex] ? '▼' : '►'}
                </span>
              )}
              <span className="chapter-title">
                {chapter.order + 1}. {chapter.title}
              </span>
            </div>
            
            {expandedChapters[chapterIndex] && chapter.sections.length > 0 && (
              <div className="sections-list">
                {chapter.sections.map((section, sectionIndex) => (
                  <div key={sectionIndex} className="section-item">
                    <div 
                      className={`section-header ${isSelected('section', chapterIndex, sectionIndex) ? 'selected' : ''}`}
                      onClick={() => handleItemClick('section', chapterIndex, sectionIndex)}
                    >
                      {section.subsections.length > 0 && (
                        <span className="toggle-icon">
                          {expandedSections[`${chapterIndex}-${sectionIndex}`] ? '▼' : '►'}
                        </span>
                      )}
                      <span className="section-title">
                        {chapter.order + 1}.{section.order + 1} {section.title}
                      </span>
                    </div>
                    
                    {expandedSections[`${chapterIndex}-${sectionIndex}`] && section.subsections.length > 0 && (
                      <div className="subsections-list">
                        {section.subsections.map((subsection, subsectionIndex) => (
                          <div 
                            key={subsectionIndex}
                            className={`subsection-item ${isSelected('subsection', chapterIndex, sectionIndex, subsectionIndex) ? 'selected' : ''}`}
                            onClick={() => handleItemClick('subsection', chapterIndex, sectionIndex, subsectionIndex)}
                          >
                            <span className="subsection-title">
                              {chapter.order + 1}.{section.order + 1}.{subsection.order + 1} {subsection.title}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default Sidebar;
