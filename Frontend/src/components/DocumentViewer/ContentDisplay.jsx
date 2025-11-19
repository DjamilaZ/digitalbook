import React, { useEffect, useRef } from 'react';
import './ContentDisplay.css';

const ContentDisplay = ({ selectedItem, bookData }) => {
  const contentRef = useRef(null);

  // Effet pour défiler vers le titre de l'élément sélectionné
  useEffect(() => {
    if (selectedItem && contentRef.current) {
      setTimeout(() => {
        // Calculer la position du header fixe pour ajuster le défilement
        const header = document.querySelector('[class*="sticky top-20"]');
        const headerHeight = header ? header.offsetHeight : 80;
        
        // Position du titre par rapport au haut de la page
        const titleElement = contentRef.current.querySelector('.content-title');
        if (titleElement) {
          const titlePosition = titleElement.getBoundingClientRect().top + window.pageYOffset;
          
          // Défiler vers le titre avec un décalage pour le header
          window.scrollTo({
            top: titlePosition - headerHeight - 20, // 20px de marge supplémentaire
            behavior: 'smooth'
          });
        }
      }, 150);
    }
  }, [selectedItem]);

  if (!selectedItem) {
    return (
      <div className="content-display">
        <div className="empty-state">
          <div className="empty-icon">📄</div>
          <h3>Sélectionnez un élément dans le sommaire</h3>
          <p>Cliquez sur un chapitre, une section ou une sous-section pour afficher son contenu ici.</p>
        </div>
      </div>
    );
  }

  const { type, data } = selectedItem;
  
  // Vérifier si les données existent
  if (!data) {
    return (
      <div className="content-display">
        <div className="empty-state">
          <div className="empty-icon">⚠️</div>
          <h3>Données non disponibles</h3>
          <p>Les données pour cet élément ne sont pas disponibles.</p>
        </div>
      </div>
    );
  }

  const renderContent = () => {
    if (!data.content || typeof data.content !== 'string' || data.content.trim() === '') {
      return (
        <div className="no-content">
          <p>Cet élément ne contient pas de texte.</p>
        </div>
      );
    }

    const content = data.content;

    const blocks = [];
    const articleRegex = /<article>([\s\S]*?)<\/article>/gi;
    let lastIndex = 0;
    let match;

    while ((match = articleRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        blocks.push({ type: 'text', text: content.slice(lastIndex, match.index) });
      }
      blocks.push({ type: 'article', text: (match[1] || '').trim() });
      lastIndex = articleRegex.lastIndex;
    }
    if (lastIndex < content.length) {
      blocks.push({ type: 'text', text: content.slice(lastIndex) });
    }

    const elements = [];

    blocks.forEach((block, blockIndex) => {
      if (block.type === 'text') {
        const lines = block.text.split(/\n+/);
        lines.forEach((line, lineIndex) => {
          const trimmed = line.trim();
          if (!trimmed) return;
          elements.push(
            <p
              key={`p-${blockIndex}-${lineIndex}`}
              className="content-paragraph"
              style={{ textAlign: 'justify' }}
            >
              {trimmed}
            </p>
          );
        });
      } else if (block.type === 'article') {
        const lines = block.text.split(/\n+/).map((l) => l.trim()).filter(Boolean);
        if (!lines.length) return;
        elements.push(
          <div
            key={`article-${blockIndex}`}
            className="my-4 border border-yellow-400 bg-yellow-50 rounded-md px-4 py-3 text-sm text-gray-800"
          >
            {lines.map((line, i) => (
              <p
                key={i}
                className="content-paragraph mb-2"
                style={{ textAlign: 'justify' }}
              >
                {line}
              </p>
            ))}
          </div>
        );
      }
    });

    return elements;
  };

  const isIntroChapter = (chapter) => {
    if (!chapter) return false;
    return !!chapter.is_intro;
  };

  const getDisplayChapterNumber = (chapter) => {
    if (!chapter) return 0;
    if (!bookData?.chapters) return chapter?.order ?? 0;
    const countIntroBefore = bookData.chapters.filter(c => (c.order < chapter.order) && isIntroChapter(c)).length;
    return (chapter?.order ?? 0) - countIntroBefore;
  };

  const getBreadcrumb = () => {
    const breadcrumb = [];
    
    if (selectedItem.type === 'chapter') {
      if (data && data.order !== undefined && data.title) {
        if (isIntroChapter(data)) {
          breadcrumb.push(`${data.title}`);
        } else {
          breadcrumb.push(`Chapitre ${getDisplayChapterNumber(data)}: ${data.title}`);
        }
      }
    } else if (selectedItem.type === 'section') {
      const chapter = selectedItem.chapterData;
      if (chapter && chapter.order !== undefined && chapter.title) {
        if (isIntroChapter(chapter)) {
          breadcrumb.push(`${chapter.title}`);
        } else {
          breadcrumb.push(`Chapitre ${getDisplayChapterNumber(chapter)}: ${chapter.title}`);
        }
      }
      if (data && data.order !== undefined && data.title) {
        if (chapter && isIntroChapter(chapter)) {
          breadcrumb.push(`Section ${data.order}: ${data.title}`);
        } else {
          breadcrumb.push(`Section ${getDisplayChapterNumber(chapter)}.${data.order}: ${data.title}`);
        }
      }
    } else if (selectedItem.type === 'subsection') {
      const chapter = selectedItem.chapterData;
      const section = selectedItem.sectionData;
      if (chapter && chapter.order !== undefined && chapter.title) {
        if (isIntroChapter(chapter)) {
          breadcrumb.push(`${chapter.title}`);
        } else {
          breadcrumb.push(`Chapitre ${getDisplayChapterNumber(chapter)}: ${chapter.title}`);
        }
      }
      if (section && section.order !== undefined && section.title) {
        if (chapter && isIntroChapter(chapter)) {
          breadcrumb.push(`Section ${section.order}: ${section.title}`);
        } else {
          breadcrumb.push(`Section ${getDisplayChapterNumber(chapter)}.${section.order}: ${section.title}`);
        }
      }
      if (data && data.order !== undefined && data.title) {
        if (chapter && isIntroChapter(chapter)) {
          breadcrumb.push(`Sous-section ${section?.order}.${data.order}: ${data.title}`);
        } else {
          breadcrumb.push(`Sous-section ${getDisplayChapterNumber(chapter)}.${section?.order}.${data.order}: ${data.title}`);
        }
      }
    }
    
    return breadcrumb;
  };

  const getTypeIcon = () => {
    switch (type) {
      case 'chapter':
        return '📚';
      case 'section':
        return '📑';
      case 'subsection':
        return '📄';
      default:
        return '📄';
    }
  };

  return (
    <div className="content-display" ref={contentRef}>
      <div className="content-header">
        <div className="breadcrumb">
          {getBreadcrumb().map((item, index) => (
            <React.Fragment key={index}>
              <span className="breadcrumb-item">{item}</span>
              {index < getBreadcrumb().length - 1 && (
                <span className="breadcrumb-separator">›</span>
              )}
            </React.Fragment>
          ))}
        </div>
        
        <div className="content-title">
          <span className="type-icon">{getTypeIcon()}</span>
          <h1>{data.title || 'Titre non disponible'}</h1>
          <span className="content-number">(ID: {data.id || 'N/A'})</span>
        </div>
      </div>

      <div className="content-body">
        <div className="content-text">
          {renderContent()}
        </div>

        {/* Afficher les images si elles existent */}
        {Array.isArray(data.images) && data.images.length > 0 && (
          <div className="content-images">
            <h3>Images</h3>
            <div className="images-grid">
              {data.images.map((image, index) => (
                <div key={index} className="image-item">
                  <img 
                    src={image.url || ''} 
                    alt={image.caption || `Illustration ${index + 1}`} 
                    className="content-image"
                  />
                  <p className="image-caption">{image.caption || `Image ${index + 1}`}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Afficher les tableaux s'ils existent */}
        {data.tables && data.tables.length > 0 && (
          <div className="content-tables">
            <h3>Tableaux</h3>
            {data.tables.map((table, index) => (
              <div key={index} className="table-item">
                {(() => {
                  // 1) Snapshot image table
                  const url = table?.url || '';
                  const isSnapshot = table?.is_snapshot === true || /\.(png|jpe?g|gif|webp)$/i.test(url);
                  if (isSnapshot && url) {
                    return (
                      <>
                        <div className="bg-white p-3 flex justify-center items-center border border-gray-200 rounded">
                          <img src={url} alt={table.title || table.caption || `Tableau ${index + 1}`} className="max-w-full h-auto" />
                        </div>
                        <p className="table-caption">{table.caption || table.title || `Tableau ${index + 1}`}</p>
                      </>
                    );
                  }

                  // 2) Text content table -> parse pipe-delimited rows
                  const c = table?.content;
                  let rawLines = [];
                  if (typeof c === 'string') {
                    rawLines = c.split('\n');
                  } else if (Array.isArray(c)) {
                    rawLines = c.flatMap((item) => (typeof item === 'string' ? item.split('\n') : []));
                  }
                  let lines = rawLines.map(l => (l ?? '').trim()).filter(l => l.length > 0);
                  const hasPipe = lines.some(l => l.includes('|'));
                  if (hasPipe) {
                    lines = lines.filter(l => l.includes('|'));
                  }
                  const rows = lines.map(l => l.split('|').map(cell => cell.trim()));
                  const colCount = table?.columns || (rows[0]?.length || 0);
                  const useHeader = colCount > 1 && rows.length > 0 && rows[0].length === colCount;

                  return rows.length > 0 ? (
                    <div className="bg-white p-3 overflow-x-auto border border-gray-200 rounded">
                      <table className="min-w-full text-sm">
                        {useHeader && (
                          <thead className="bg-gray-50">
                            <tr>
                              {rows[0].map((h, i) => (
                                <th key={i} className="px-3 py-2 text-left font-semibold text-gray-700 border-b border-gray-200">{h}</th>
                              ))}
                            </tr>
                          </thead>
                        )}
                        <tbody>
                          {(useHeader ? rows.slice(1) : rows).map((r, ri) => (
                            <tr key={ri} className={ri % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                              {r.map((cell, ci) => (
                                <td key={ci} className="px-3 py-2 align-top border-b border-gray-200 whitespace-pre-wrap">{cell}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <p className="table-caption mt-2">{table.caption || table.title || `Tableau ${index + 1}`}</p>
                    </div>
                  ) : (
                    <div className="table-line text-gray-500">Aucun contenu de tableau</div>
                  );
                })()}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ContentDisplay;
