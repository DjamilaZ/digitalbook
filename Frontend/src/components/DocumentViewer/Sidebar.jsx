import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, BookOpen, FileText, Brain, Folder } from 'lucide-react';
import './Sidebar.css';

const Sidebar = ({ bookData, onSelectContent, selectedItem }) => {
  const [expandedChapters, setExpandedChapters] = useState({});
  const [expandedSections, setExpandedSections] = useState({});
  const [expandedThematiques, setExpandedThematiques] = useState({});

  // Détecter s'il y a des thématiques réelles (pas seulement le groupe "sans-thematique")
  const hasRealThematiques = useMemo(() => {
    if (!bookData?.chapters) return false;
    return bookData.chapters.some(chapter => chapter.thematique);
  }, [bookData?.chapters]);

  // Fonction pour nettoyer les titres qui contiennent déjà une numérotation
  const cleanTitle = (title, order = null, prefix = '') => {
    if (!title) return '';
    
    // Si un ordre est fourni, vérifier si le titre commence déjà par la numérotation
    if (order !== null) {
      const expectedPrefix = `${order}.`;
      const regex = new RegExp(`^${order}\.\s*`);
      
      if (regex.test(title)) {
        // Le titre contient déjà la numérotation, la retirer
        return title.replace(regex, '');
      }
    }
    
    // Vérifier si le titre commence par un pattern de numérotation général (ex: "1.", "2.1", etc.)
    const generalNumberingRegex = /^(\d+\.?\s*)+/;
    if (generalNumberingRegex.test(title)) {
      // Retirer la numérotation existante
      return title.replace(generalNumberingRegex, '');
    }
    
    return title;
  };

  const isNoFolderChapter = (chapter) => {
    if (!chapter) return false;
    return !!chapter.is_intro;
  };

  const getDisplayChapterNumber = (chapter) => {
    if (!bookData?.chapters) return chapter?.order ?? 0;
    const countIntroBefore = bookData.chapters.filter(c => (c.order < chapter.order) && isNoFolderChapter(c)).length;
    const n = (chapter?.order ?? 0) - countIntroBefore;
    return n;
  };

  // Regrouper les chapitres par thématique
  const chaptersByThematique = useMemo(() => {
    if (!bookData?.chapters) return {};
    
    const grouped = {};
    
    // Chapitres sans thématique
    const chaptersWithoutThematique = bookData.chapters.filter(chapter => !chapter.thematique);
    if (chaptersWithoutThematique.length > 0) {
      grouped['sans-thematique'] = {
        thematique: null,
        chapters: chaptersWithoutThematique
      };
    }
    
    // Chapitres avec thématique
    const chaptersWithThematique = bookData.chapters.filter(chapter => chapter.thematique);
    chaptersWithThematique.forEach(chapter => {
      const thematiqueId = chapter.thematique.id;
      if (!grouped[thematiqueId]) {
        grouped[thematiqueId] = {
          thematique: chapter.thematique,
          chapters: []
        };
      }
      grouped[thematiqueId].chapters.push(chapter);
    });
    
    return grouped;
  }, [bookData?.chapters]);

  const toggleThematique = (thematiqueId, event) => {
    event.stopPropagation();
    setExpandedThematiques(prev => ({
      ...prev,
      [thematiqueId]: !prev[thematiqueId]
    }));
  };

  const toggleChapter = (chapterIndex, event) => {
    event.stopPropagation();
    setExpandedChapters(prev => ({
      ...prev,
      [chapterIndex]: !prev[chapterIndex]
    }));
  };

  const toggleSection = (chapterIndex, sectionIndex, event) => {
    event.stopPropagation();
    const key = `${chapterIndex}-${sectionIndex}`;
    setExpandedSections(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const handleItemClick = (type, chapterIndex, sectionIndex = null, subsectionIndex = null, qcmIndex = null) => {
    onSelectContent({ type, chapterIndex, sectionIndex, subsectionIndex, qcmIndex });
    
    // Mettre à jour les états d'expansion
    if (type === 'cover') {
      // Pas besoin d'expansion pour la couverture
      return;
    } else if (type === 'chapter') {
      if (!expandedChapters[chapterIndex]) {
        setExpandedChapters(prev => ({
          ...prev,
          [chapterIndex]: true
        }));
      }
      
      // Développer aussi la thématique du chapitre
      const chapter = bookData?.chapters[chapterIndex];
      if (chapter?.thematique) {
        const thematiqueId = chapter.thematique.id;
        if (!expandedThematiques[thematiqueId]) {
          setExpandedThematiques(prev => ({
            ...prev,
            [thematiqueId]: true
          }));
        }
      }
    } else if (type === 'section') {
      if (!expandedChapters[chapterIndex]) {
        setExpandedChapters(prev => ({
          ...prev,
          [chapterIndex]: true
        }));
      }
      if (!expandedSections[`${chapterIndex}-${sectionIndex}`]) {
        setExpandedSections(prev => ({
          ...prev,
          [`${chapterIndex}-${sectionIndex}`]: true
        }));
      }
      
      // Développer aussi la thématique du chapitre
      const chapter = bookData?.chapters[chapterIndex];
      if (chapter?.thematique) {
        const thematiqueId = chapter.thematique.id;
        if (!expandedThematiques[thematiqueId]) {
          setExpandedThematiques(prev => ({
            ...prev,
            [thematiqueId]: true
          }));
        }
      }
    } else if (type === 'subsection') {
      if (!expandedChapters[chapterIndex]) {
        setExpandedChapters(prev => ({
          ...prev,
          [chapterIndex]: true
        }));
      }
      if (!expandedSections[`${chapterIndex}-${sectionIndex}`]) {
        setExpandedSections(prev => ({
          ...prev,
          [`${chapterIndex}-${sectionIndex}`]: true
        }));
      }
      
      // Développer aussi la thématique du chapitre
      const chapter = bookData?.chapters[chapterIndex];
      if (chapter?.thematique) {
        const thematiqueId = chapter.thematique.id;
        if (!expandedThematiques[thematiqueId]) {
          setExpandedThematiques(prev => ({
            ...prev,
            [thematiqueId]: true
          }));
        }
      }
    } else if (type === 'qcm') {
      if (!expandedChapters[chapterIndex]) {
        setExpandedChapters(prev => ({
          ...prev,
          [chapterIndex]: true
        }));
      }
      
      // Développer aussi la thématique du chapitre
      const chapter = bookData?.chapters[chapterIndex];
      if (chapter?.thematique) {
        const thematiqueId = chapter.thematique.id;
        if (!expandedThematiques[thematiqueId]) {
          setExpandedThematiques(prev => ({
            ...prev,
            [thematiqueId]: true
          }));
        }
      }
    }
  };

  const isSelected = (type, chapterIndex, sectionIndex = null, subsectionIndex = null, qcmIndex = null) => {
    if (!selectedItem) return false;
    
    if (type === 'cover' && selectedItem.type === 'cover') {
      return true;
    } else if (type === 'chapter' && selectedItem.type === 'chapter') {
      return selectedItem.chapterIndex === chapterIndex;
    } else if (type === 'section' && selectedItem.type === 'section') {
      return selectedItem.chapterIndex === chapterIndex && selectedItem.sectionIndex === sectionIndex;
    } else if (type === 'subsection' && selectedItem.type === 'subsection') {
      return selectedItem.chapterIndex === chapterIndex && 
             selectedItem.sectionIndex === sectionIndex && 
             selectedItem.subsectionIndex === subsectionIndex;
    } else if (type === 'qcm' && selectedItem.type === 'qcm') {
      return selectedItem.chapterIndex === chapterIndex && selectedItem.qcmIndex === qcmIndex;
    }
    
    return false;
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Sommaire</h2>
      </div>
      
      <div className="sidebar-content">
        {/* Lien vers l'image de couverture */}
        <div className="cover-item">
          <div 
            className={`cover-header ${isSelected('cover') ? 'selected' : ''}`}
            onClick={() => handleItemClick('cover')}
          >
            <FileText size={18} className="cover-icon" />
            <span className="cover-title">
              Couverture
            </span>
          </div>
        </div>
        
        {/* Afficher les thématiques et leurs chapitres */}
        {Object.entries(chaptersByThematique).map(([thematiqueId, groupe]) => {
          const thematique = groupe.thematique;
          const isExpanded = expandedThematiques[thematiqueId];
          
          return (
            <div key={thematiqueId} className="thematique-item">
              {/* Si pas de thématiques réelles, afficher les chapitres comme des thématiques */}
              {!hasRealThematiques ? (
                // Afficher chaque chapitre comme une thématique
                groupe.chapters.map((chapter, chapterIndex) => {
                  const originalChapterIndex = bookData.chapters.findIndex(c => c.id === chapter.id);
                  const isChapterExpanded = expandedChapters[originalChapterIndex];
                  
                  return (
                    <div key={chapter.id} className="thematique-item">
                      <div 
                        className={`thematique-header ${isSelected('chapter', originalChapterIndex) ? 'selected' : ''} ${isChapterExpanded ? 'expanded' : ''}`}
                        onClick={(e) => {
                          toggleChapter(originalChapterIndex, e);
                          handleItemClick('chapter', originalChapterIndex);
                        }}
                      >
                        <button 
                          className="toggle-button"
                          aria-label={isChapterExpanded ? "Réduire le chapitre" : "Développer le chapitre"}
                        >
                          {isChapterExpanded ? (
                            <ChevronDown size={20} className="toggle-icon-expanded" />
                          ) : (
                            <ChevronRight size={20} className="toggle-icon-collapsed" />
                          )}
                        </button>
                        {!isNoFolderChapter(chapter) && (
                          <Folder size={18} className="thematique-icon" />
                        )}
                        <span className="thematique-title">
                          {isNoFolderChapter(chapter)
                            ? cleanTitle(chapter.title, chapter.order)
                            : `${getDisplayChapterNumber(chapter)}. ${cleanTitle(chapter.title, chapter.order)}`}
                        </span>
                        <span className="thematique-count">
                          ({chapter.sections.length})
                        </span>
                      </div>
                      
                      {isChapterExpanded && (
                        <div className="thematique-content">
                          {/* Sections affichées comme des chapitres */}
                          {chapter.sections.length > 0 && (
                            <div className="sections-list">
                              {chapter.sections.map((section, sectionIndex) => {
                                const isSectionExpanded = expandedSections[`${originalChapterIndex}-${sectionIndex}`];
                                
                                return (
                                  <div key={sectionIndex} className="chapter-item">
                                    <div 
                                      className={`chapter-header ${isSelected('section', originalChapterIndex, sectionIndex) ? 'selected' : ''}`}
                                      onClick={() => handleItemClick('section', originalChapterIndex, sectionIndex)}
                                    >
                                      {section.subsections.length > 0 && (
                                        <button 
                                          className="toggle-button"
                                          onClick={(e) => toggleSection(originalChapterIndex, sectionIndex, e)}
                                          aria-label={isSectionExpanded ? "Réduire la section" : "Développer la section"}
                                        >
                                          {isSectionExpanded ? (
                                            <ChevronDown size={20} className="toggle-icon-expanded" />
                                          ) : (
                                            <ChevronRight size={20} className="toggle-icon-collapsed" />
                                          )}
                                        </button>
                                      )}
                                      <span className="chapter-title">
                                        {isNoFolderChapter(chapter)
                                          ? `${section.order} ${cleanTitle(section.title, section.order)}`
                                          : `${getDisplayChapterNumber(chapter)}.${section.order} ${cleanTitle(section.title, section.order)}`}
                                      </span>
                                    </div>
                                    
                                    {isSectionExpanded && section.subsections.length > 0 && (
                                      <div className="sections-list">
                                        {/* Sous-sections affichées comme des sections */}
                                        {section.subsections.map((subsection, subsectionIndex) => (
                                          <div key={subsectionIndex} className="section-item">
                                            <div 
                                              className={`section-header ${isSelected('subsection', originalChapterIndex, sectionIndex, subsectionIndex) ? 'selected' : ''}`}
                                              onClick={() => handleItemClick('subsection', originalChapterIndex, sectionIndex, subsectionIndex)}
                                            >
                                              <span className="section-title">
                                                {isNoFolderChapter(chapter)
                                                  ? `${section.order}.${subsection.order} ${cleanTitle(subsection.title, subsection.order)}`
                                                  : `${getDisplayChapterNumber(chapter)}.${section.order}.${subsection.order} ${cleanTitle(subsection.title, subsection.order)}`}
                                              </span>
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          )}
                          
                          {/* QCMs du chapitre */}
                          {chapter.qcm && chapter.qcm.length > 0 && (
                            <div className="qcm-list">
                              {chapter.qcm.map((qcm, qcmIndex) => (
                                <div 
                                  key={qcmIndex}
                                  className={`qcm-item ${isSelected('qcm', originalChapterIndex, null, null, qcmIndex) ? 'selected' : ''}`}
                                  onClick={() => handleItemClick('qcm', originalChapterIndex, null, null, qcmIndex)}
                                >
                                  <Brain size={16} className="qcm-icon" />
                                  <span className="qcm-title">
                                    🧠 Quiz {qcmIndex + 1}: {qcm.title || `Questionnaire ${qcmIndex + 1}`}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                // Structure normale avec thématiques
                <>
                  <div 
                    className={`thematique-header ${isExpanded ? 'expanded' : ''}`}
                    onClick={(e) => toggleThematique(thematiqueId, e)}
                  >
                    <button 
                      className="toggle-button"
                      aria-label={isExpanded ? "Réduire la thématique" : "Développer la thématique"}
                    >
                      {isExpanded ? (
                        <ChevronDown size={20} className="toggle-icon-expanded" />
                      ) : (
                        <ChevronRight size={20} className="toggle-icon-collapsed" />
                      )}
                    </button>
                    <Folder size={18} className="thematique-icon" />
                    <span className="thematique-title">
                      {thematique ? thematique.title : 'Autres chapitres'}
                    </span>
                    <span className="thematique-count">
                      ({groupe.chapters.length})
                    </span>
                  </div>
                  
                  {isExpanded && (
                    <div className="thematique-content">
                      {groupe.chapters.map((chapter, chapterIndex) => {
                        // Trouver l'index original du chapitre dans bookData.chapters
                        const originalChapterIndex = bookData.chapters.findIndex(c => c.id === chapter.id);
                        
                        return (
                          <div key={chapter.id} className="chapter-item">
                            <div 
                              className={`chapter-header ${isSelected('chapter', originalChapterIndex) ? 'selected' : ''}`}
                              onClick={() => handleItemClick('chapter', originalChapterIndex)}
                            >
                              {chapter.sections.length > 0 && (
                                <button 
                                  className="toggle-button"
                                  onClick={(e) => toggleChapter(originalChapterIndex, e)}
                                  aria-label={expandedChapters[originalChapterIndex] ? "Réduire le chapitre" : "Développer le chapitre"}
                                >
                                  {expandedChapters[originalChapterIndex] ? (
                                    <ChevronDown size={20} className="toggle-icon-expanded" />
                                  ) : (
                                    <ChevronRight size={20} className="toggle-icon-collapsed" />
                                  )}
                                </button>
                              )}
                              <span className="chapter-title">
                                {isNoFolderChapter(chapter.title)
                                  ? cleanTitle(chapter.title, chapter.order)
                                  : `${getDisplayChapterNumber(chapter)}. ${cleanTitle(chapter.title, chapter.order)}`}
                              </span>
                            </div>
                            
                            {expandedChapters[originalChapterIndex] && (
                              <>
                                {chapter.sections.length > 0 && (
                                  <div className="sections-list">
                                    {chapter.sections.map((section, sectionIndex) => (
                                      <div key={sectionIndex} className="section-item">
                                        <div 
                                          className={`section-header ${isSelected('section', originalChapterIndex, sectionIndex) ? 'selected' : ''}`}
                                          onClick={() => handleItemClick('section', originalChapterIndex, sectionIndex)}
                                        >
                                          {section.subsections.length > 0 && (
                                            <button 
                                              className="toggle-button"
                                              onClick={(e) => toggleSection(originalChapterIndex, sectionIndex, e)}
                                              aria-label={expandedSections[`${originalChapterIndex}-${sectionIndex}`] ? "Réduire la section" : "Développer la section"}
                                            >
                                              {expandedSections[`${originalChapterIndex}-${sectionIndex}`] ? (
                                                <ChevronDown size={18} className="toggle-icon-expanded" />
                                              ) : (
                                                <ChevronRight size={18} className="toggle-icon-collapsed" />
                                              )}
                                            </button>
                                          )}
                                          <span className="section-title">
                                            {isNoFolderChapter(chapter.title)
                                              ? `${section.order} ${cleanTitle(section.title, section.order)}`
                                              : `${getDisplayChapterNumber(chapter)}.${section.order} ${cleanTitle(section.title, section.order)}`}
                                          </span>
                                        </div>
                                        
                                        {expandedSections[`${originalChapterIndex}-${sectionIndex}`] && section.subsections.length > 0 && (
                                          <div className="subsections-list">
                                            {section.subsections.map((subsection, subsectionIndex) => (
                                              <div 
                                                key={subsectionIndex}
                                                className={`subsection-item ${isSelected('subsection', originalChapterIndex, sectionIndex, subsectionIndex) ? 'selected' : ''}`}
                                                onClick={() => handleItemClick('subsection', originalChapterIndex, sectionIndex, subsectionIndex)}
                                              >
                                                <span className="subsection-title">
                                                  {isNoFolderChapter(chapter.title)
                                                    ? `${section.order}.${subsection.order} ${cleanTitle(subsection.title, subsection.order)}`
                                                    : `${getDisplayChapterNumber(chapter)}.${section.order}.${subsection.order} ${cleanTitle(subsection.title, subsection.order)}`}
                                                </span>
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                )}
                                
                                {/* QCMs du chapitre - Affichés à la fin du chapitre */}
                                {chapter.qcm && chapter.qcm.length > 0 && (
                                  <div className="qcm-list">
                                    {chapter.qcm.map((qcm, qcmIndex) => (
                                      <div 
                                        key={qcmIndex}
                                        className={`qcm-item ${isSelected('qcm', originalChapterIndex, null, null, qcmIndex) ? 'selected' : ''}`}
                                        onClick={() => handleItemClick('qcm', originalChapterIndex, null, null, qcmIndex)}
                                      >
                                        <Brain size={16} className="qcm-icon" />
                                        <span className="qcm-title">
                                          🧠 Quiz {qcmIndex + 1}: {qcm.title || `Questionnaire ${qcmIndex + 1}`}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Sidebar;
