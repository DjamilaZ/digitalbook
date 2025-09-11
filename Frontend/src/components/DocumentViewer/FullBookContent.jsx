import React, { useEffect, useRef } from 'react';
import { Pin } from 'lucide-react';

const FullBookContent = ({ bookData, selectedItem }) => {
  // Composant pour mettre en évidence les mots spéciaux
  const HighlightedText = ({ text }) => {
    const specialWords = ['remarque', 'note', 'rappelle'];
    
    const createHighlightedElements = (text) => {
      const elements = [];
      let lastIndex = 0;
      
      // Trouver toutes les occurrences des mots spéciaux
      specialWords.forEach(word => {
        const regex = new RegExp(`\\b${word}\\b`, 'gi');
        let match;
        
        while ((match = regex.exec(text)) !== null) {
          // Ajouter le texte avant le mot spécial
          if (match.index > lastIndex) {
            elements.push(
              <span key={`text-${lastIndex}-${match.index}`}>
                {text.substring(lastIndex, match.index)}
              </span>
            );
          }
          
          // Ajouter un saut de ligne avant le mot spécial
          if (match.index > 0 && text[match.index - 1] !== '\n') {
            elements.push(<br key={`br-${match.index}`} />);
          }
          
          // Ajouter le mot spécial mis en évidence
          elements.push(
            <span key={`highlight-${match.index}-${match[0]}`} className="inline-flex items-center gap-1 font-bold text-blue-600">
              <Pin size={14} className="text-blue-500" />
              <span className="italic">{match[0]}</span>
            </span>
          );
          
          lastIndex = match.index + match[0].length;
        }
      });
      
      // Ajouter le texte restant
      if (lastIndex < text.length) {
        elements.push(
          <span key={`text-${lastIndex}-end`}>
            {text.substring(lastIndex)}
          </span>
        );
      }
      
      return elements.length > 0 ? elements : [text];
    };
    
    return <>{createHighlightedElements(text)}</>;
  };

  const renderContent = (content) => {
    if (!content) return null;
    
    // Diviser le contenu en paragraphes
    return content.split('\n').map((paragraph, index) => {
      if (paragraph.trim()) {
        return (
          <p key={index} className="mb-4 text-gray-700 leading-relaxed">
            <HighlightedText text={paragraph} />
          </p>
        );
      }
      return null;
    }).filter(Boolean);
  };

  const renderImages = (images) => {
    if (!images || images.length === 0) return null;
    
    return (
      <div className="w-full my-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {images.map((image, index) => (
            <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
              <img 
                src={image.url} 
                alt={image.caption || `Illustration ${index + 1}`} 
                className="w-full h-auto object-cover"
              />
              <p className="text-sm text-gray-600 p-2 bg-gray-50">{image.caption || `Image ${index + 1}`}</p>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderTables = (tables) => {
    if (!tables || tables.length === 0) return null;
    
    return (
      <div className="w-full my-6">
        {tables.map((table, index) => (
          <div key={index} className="border border-gray-200 rounded-lg overflow-hidden mb-4">
            <div className="bg-gray-50 p-4 font-mono text-sm whitespace-pre-wrap">
              {table.content.split('\n').map((line, lineIndex) => (
                <div key={lineIndex} className="border-b border-gray-200 py-1 last:border-b-0">{line}</div>
              ))}
            </div>
            <p className="text-sm text-gray-600 p-2 bg-gray-100 font-medium">{table.caption || `Tableau ${index + 1}`}</p>
          </div>
        ))}
      </div>
    );
  };

  const contentRef = useRef(null);

  // Effet pour défiler vers l'élément sélectionné
  useEffect(() => {
    if (selectedItem && contentRef.current && bookData && bookData.chapters) {
      let elementId = '';
      
      if (selectedItem.type === 'chapter' && selectedItem.chapterIndex !== undefined) {
        const chapter = bookData.chapters[selectedItem.chapterIndex];
        if (chapter && chapter.id) {
          elementId = `chapter-${chapter.id}`;
        }
      } else if (selectedItem.type === 'section' && selectedItem.chapterIndex !== undefined && selectedItem.sectionIndex !== undefined) {
        const chapter = bookData.chapters[selectedItem.chapterIndex];
        if (chapter && chapter.sections && chapter.sections[selectedItem.sectionIndex]) {
          const section = chapter.sections[selectedItem.sectionIndex];
          if (section && section.id) {
            elementId = `section-${section.id}`;
          }
        }
      } else if (selectedItem.type === 'subsection' && selectedItem.chapterIndex !== undefined && selectedItem.sectionIndex !== undefined && selectedItem.subsectionIndex !== undefined) {
        const chapter = bookData.chapters[selectedItem.chapterIndex];
        if (chapter && chapter.sections && chapter.sections[selectedItem.sectionIndex]) {
          const section = chapter.sections[selectedItem.sectionIndex];
          if (section && section.subsections && section.subsections[selectedItem.subsectionIndex]) {
            const subsection = section.subsections[selectedItem.subsectionIndex];
            if (subsection && subsection.id) {
              elementId = `subsection-${subsection.id}`;
            }
          }
        }
      }
      
      if (elementId) {
        const element = document.getElementById(elementId);
        if (element) {
          // Attendre un peu que le contenu soit rendu
          setTimeout(() => {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }, 100);
        }
      }
    }
  }, [selectedItem, bookData]);

  return (
    <div className="w-full max-w-none px-6 py-8" ref={contentRef}>
      {/* Introduction du livre */}
      {bookData.title && (
        <div className="w-full mb-8">
          <h1 id="book-title" className="text-4xl font-bold text-gray-900 mb-4">{bookData.title}</h1>
          {bookData.description && (
            <div className="text-lg text-gray-700 leading-relaxed">
              {renderContent(bookData.description)}
            </div>
          )}
        </div>
      )}

      {/* Contenu des chapitres */}
      <div className="w-full space-y-8">
        {bookData.chapters.map((chapter, chapterIndex) => (
          <div key={chapter.id} className="w-full">
            {/* Titre du chapitre (H1) */}
            <h1 
              id={`chapter-${chapter.id}`}
              className={`text-3xl font-bold text-gray-900 mb-6 ${selectedItem?.type === 'chapter' && selectedItem?.chapterIndex === chapterIndex ? 'bg-blue-50 border-l-4 border-blue-500 pl-4 py-2 -ml-6' : ''}`}
            >
              Chapitre {chapter.order + 1}. {chapter.title}
            </h1>

            {/* Contenu du chapitre */}
            {chapter.content && (
              <div className="text-gray-800 leading-relaxed mb-6 space-y-4">
                {renderContent(chapter.content)}
              </div>
            )}

            {/* Images du chapitre */}
            {renderImages(chapter.images)}

            {/* Tableaux du chapitre */}
            {renderTables(chapter.tables)}

            {/* Sections du chapitre */}
            <div className="w-full space-y-6 ml-4">
              {chapter.sections.map((section, sectionIndex) => (
                <div key={section.id} className="w-full">
                  {/* Titre de la section (H2) */}
                  <h2 
                    id={`section-${section.id}`}
                    className={`text-2xl font-semibold text-gray-800 mb-4 ${selectedItem?.type === 'section' && selectedItem?.chapterIndex === chapterIndex && selectedItem?.sectionIndex === sectionIndex ? 'bg-green-50 border-l-4 border-green-500 pl-4 py-2 -ml-4' : ''}`}
                  >
                    {chapter.order + 1}.{section.order + 1} {section.title}
                  </h2>

                  {/* Contenu de la section */}
                  {section.content && (
                    <div className="text-gray-700 leading-relaxed mb-4 space-y-3">
                      {renderContent(section.content)}
                    </div>
                  )}

                  {/* Images de la section */}
                  {renderImages(section.images)}

                  {/* Tableaux de la section */}
                  {renderTables(section.tables)}

                  {/* Sous-sections de la section */}
                  <div className="w-full space-y-4 ml-4">
                    {section.subsections.map((subsection, subsectionIndex) => (
                      <div key={subsection.id} className="w-full">
                        {/* Titre de la sous-section (H3) */}
                        <h3 
                          id={`subsection-${subsection.id}`}
                          className={`text-xl font-medium text-gray-700 mb-3 ${selectedItem?.type === 'subsection' && selectedItem?.chapterIndex === chapterIndex && selectedItem?.sectionIndex === undefined && selectedItem?.subsectionIndex === subsectionIndex ? 'bg-yellow-50 border-l-4 border-yellow-500 pl-4 py-2 -ml-4' : ''}`}
                        >
                          {chapter.order + 1}.{section.order + 1}.{subsection.order + 1} {subsection.title}
                        </h3>

                        {/* Contenu de la sous-section */}
                        {subsection.content && (
                          <div className="text-gray-600 leading-relaxed mb-3 space-y-2">
                            {renderContent(subsection.content)}
                          </div>
                        )}

                        {/* Images de la sous-section */}
                        {renderImages(subsection.images)}

                        {/* Tableaux de la sous-section */}
                        {renderTables(subsection.tables)}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Sous-sections directes du chapitre (sans section parente) */}
            {chapter.subsections && chapter.subsections.length > 0 && (
              <div className="w-full space-y-4 ml-4">
                {chapter.subsections.map((subsection, subsectionIndex) => (
                  <div key={subsection.id} className="w-full">
                    {/* Titre de la sous-section (H3) */}
                    <h3 
                      id={`subsection-${subsection.id}`}
                      className="text-xl font-medium text-gray-700 mb-3"
                    >
                      {chapter.order + 1}.{subsection.order + 1} {subsection.title}
                    </h3>

                    {/* Contenu de la sous-section */}
                    {subsection.content && (
                      <div className="text-gray-600 leading-relaxed mb-3 space-y-2">
                        {renderContent(subsection.content)}
                      </div>
                    )}

                    {/* Images de la sous-section */}
                    {renderImages(subsection.images)}

                    {/* Tableaux de la sous-section */}
                    {renderTables(subsection.tables)}
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

export default FullBookContent;
