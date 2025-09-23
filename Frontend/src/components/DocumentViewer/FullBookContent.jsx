import React, { useEffect, useRef, useMemo } from 'react';
import { Pin, RefreshCw } from 'lucide-react';
import QCMComponent from './QCMComponent';

const FullBookContent = ({ bookData, selectedItem, isAdmin, onRegenerateChapter, regenLoading }) => {
  // Composant pour mettre en évidence les mots spéciaux
  const HighlightedText = ({ text }) => {
    const specialWords = ['remarque', 'note', 'rappelle'];
    const redBoldWords = ["N'oubliez pas"];
    
    const createHighlightedElements = (text) => {
      const elements = [];
      let lastIndex = 0;
      
      // Trouver toutes les occurrences des mots spéciaux en bleu
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
          
          // Ajouter le mot spécial mis en évidence en bleu
          elements.push(
            <span key={`highlight-${match.index}-${match[0]}`} className="inline-flex items-center gap-1 font-bold text-blue-600">
              <Pin size={14} className="text-blue-500" />
              <span className="italic">{match[0]}</span>
            </span>
          );
          
          lastIndex = match.index + match[0].length;
        }
      });
      
      // Trouver toutes les occurrences des mots spéciaux en rouge et gras
      redBoldWords.forEach(word => {
        const regex = new RegExp(word, 'gi');
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
          
          // Ajouter le mot spécial mis en évidence en rouge et gras
          elements.push(
            <span key={`redbold-${match.index}-${match[0]}`} className="inline-flex items-center gap-1 font-bold text-red-600">
              <Pin size={14} className="text-red-500" />
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

  // Nettoyer les titres qui contiennent déjà une numérotation (même logique que Sidebar)
  const cleanTitle = (title, order = null) => {
    if (!title) return '';
    if (order !== null) {
      const regex = new RegExp(`^${order + 1}\\.\\s*`);
      if (regex.test(title)) {
        return title.replace(regex, '');
      }
    }
    const generalNumberingRegex = /^(\d+\.?\s*)+/;
    if (generalNumberingRegex.test(title)) {
      return title.replace(generalNumberingRegex, '');
    }
    return title;
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
    
    // URL de base du backend Django pour les fichiers médias
    const backendBaseUrl = 'http://localhost:8000';
    
    return (
      <div className="w-full my-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {images.map((image, index) => {
            // Gérer les deux formats: chaîne de caractères ou objet avec url
            const imagePath = typeof image === 'string' ? image : image.url;
            const imageCaption = typeof image === 'string' ? `Image ${index + 1}` : (image.caption || `Illustration ${index + 1}`);
            
            // Construire l'URL complète pour l'image
            let fullImageUrl;
            if (imagePath.startsWith('http')) {
              // Si c'est déjà une URL complète, l'utiliser telle quelle
              fullImageUrl = imagePath;
            } else if (imagePath.startsWith('/media/')) {
              // Si c'est un chemin média, ajouter l'URL du backend
              fullImageUrl = `${backendBaseUrl}${imagePath}`;
            } else if (imagePath.startsWith('/')) {
              // Si c'est un chemin absolu, l'ajouter à l'URL du backend
              fullImageUrl = `${backendBaseUrl}${imagePath}`;
            } else {
              // Si c'est un chemin relatif, le traiter comme chemin média
              fullImageUrl = `${backendBaseUrl}/media/${imagePath}`;
            }
            
            return (
              <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                <img 
                  src={fullImageUrl} 
                  alt={imageCaption} 
                  className="w-full h-auto object-cover"
                  onError={(e) => {
                    console.error('Erreur de chargement de l\'image:', fullImageUrl);
                    // Cacher l'image en cas d'erreur
                    e.target.style.display = 'none';
                    // Afficher un message d'erreur à la place
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'p-4 bg-red-50 border border-red-200 rounded text-red-600 text-sm';
                    errorDiv.textContent = `Image non trouvée: ${imageCaption}`;
                    e.target.parentNode.appendChild(errorDiv);
                  }}
                />
                <p className="text-sm text-gray-600 p-2 bg-gray-50">{imageCaption}</p>
              </div>
            );
          })}
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
      console.log('🎯 Défilement vers:', selectedItem);
      
      let elementId = '';
      
      if (selectedItem.type === 'chapter' && selectedItem.chapterIndex !== undefined) {
        const chapter = bookData.chapters[selectedItem.chapterIndex];
        if (chapter && chapter.id) {
          elementId = `chapter-${chapter.id}`;
          console.log('📍 ID chapitre:', elementId, 'Chapitre:', chapter.title);
        }
      } else if (selectedItem.type === 'section' && selectedItem.chapterIndex !== undefined && selectedItem.sectionIndex !== undefined) {
        const chapter = bookData.chapters[selectedItem.chapterIndex];
        if (chapter && chapter.sections && chapter.sections[selectedItem.sectionIndex]) {
          const section = chapter.sections[selectedItem.sectionIndex];
          if (section && section.id) {
            elementId = `section-${section.id}`;
            console.log('📍 ID section:', elementId, 'Section:', section.title);
            console.log('📍 Chapter index:', selectedItem.chapterIndex, 'Section index:', selectedItem.sectionIndex);
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
              console.log('📍 ID sous-section:', elementId, 'Sous-section:', subsection.title);
            }
          }
        }
      } else if (selectedItem.type === 'qcm' && selectedItem.chapterIndex !== undefined && selectedItem.qcmIndex !== undefined) {
        const chapter = bookData.chapters[selectedItem.chapterIndex];
        if (chapter && chapter.id) {
          elementId = `chapter-${chapter.id}-qcm-${selectedItem.qcmIndex}`;
          console.log('📍 ID QCM:', elementId, 'Chapitre:', chapter.title, 'QCM Index:', selectedItem.qcmIndex);
        }
      }
      
      if (elementId) {
        console.log('🔍 Recherche de l\'élément avec ID:', elementId);
        const element = document.getElementById(elementId);
        if (element) {
          console.log('✅ Élément trouvé:', element.tagName, element.textContent);
          // Attendre un peu que le contenu soit rendu
          setTimeout(() => {
            // Calculer précisément la hauteur du header fixe
            const mainHeader = document.querySelector('.sticky.top-0');
            const bookTitleHeader = document.querySelector('.sticky.top-0.bg-white.z-10');
            
            let totalHeaderHeight = 0;
            
            // Header principal (navigation)
            if (mainHeader) {
              totalHeaderHeight += mainHeader.offsetHeight;
              console.log('📐 Header principal:', mainHeader.offsetHeight);
            }
            
            // Header du titre du livre (s'il existe)
            if (bookTitleHeader && bookTitleHeader !== mainHeader) {
              totalHeaderHeight += bookTitleHeader.offsetHeight;
              console.log('📐 Header titre livre:', bookTitleHeader.offsetHeight);
            }
            
            console.log('📐 Hauteur totale des headers:', totalHeaderHeight);
            
            // Calculer la position de l'élément dans le conteneur de défilement
            console.log('🔍 Début de la recherche du conteneur de défilement');
            
            // D'abord chercher le conteneur le plus proche
            let scrollContainer = element.closest('.overflow-y-auto');
            console.log('🔍 closest(.overflow-y-auto):', !!scrollContainer);
            
            // Si aucun conteneur trouvé, chercher dans les parents plus largement
            if (!scrollContainer) {
              console.log('🔍 Recherche dans les parents...');
              let parent = element.parentElement;
              let level = 0;
              while (parent && !scrollContainer && level < 10) {
                console.log(`🔍 Parent niveau ${level}:`, parent.tagName, parent.className);
                if (parent.classList.contains('overflow-y-auto')) {
                  scrollContainer = parent;
                  console.log('✅ Conteneur trouvé dans les parents!');
                }
                parent = parent.parentElement;
                level++;
              }
            }
            
            // Si toujours pas trouvé, chercher globalement
            if (!scrollContainer) {
              console.log('🔍 Recherche globale...');
              scrollContainer = document.querySelector('.overflow-y-auto');
              console.log('🔍 querySelector(.overflow-y-auto):', !!scrollContainer);
            }
            
            // Alternative: chercher par d'autres sélecteurs courants
            if (!scrollContainer) {
              console.log('🔍 Recherche avec sélecteurs alternatifs...');
              const selectors = [
                '.overflow-y-auto',
                '[class*="overflow-y"]',
                '.overflow-auto',
                '[class*="overflow"]'
              ];
              
              for (const selector of selectors) {
                const container = document.querySelector(selector);
                if (container) {
                  console.log(`✅ Conteneur trouvé avec selector: ${selector}`);
                  scrollContainer = container;
                  break;
                }
              }
            }
            
            // Dernière tentative: chercher le conteneur principal du contenu
            if (!scrollContainer) {
              console.log('🔍 Recherche du conteneur principal...');
              // Chercher le conteneur qui contient le FullBookContent
              const contentContainer = document.querySelector('.flex-1.w-full.overflow-y-auto');
              if (contentContainer) {
                scrollContainer = contentContainer;
                console.log('✅ Conteneur principal trouvé!');
              }
            }
            
            console.log('🔍 Scroll container trouvé:', !!scrollContainer);
            
            if (scrollContainer) {
              console.log('📐 Scroll container:', scrollContainer.tagName, scrollContainer.className);
              
              // S'assurer que le conteneur peut défiler
              if (scrollContainer.scrollHeight > scrollContainer.clientHeight) {
                console.log('✅ Conteneur peut défiler');
                
                // Position absolue de l'élément dans le conteneur
                const containerRect = scrollContainer.getBoundingClientRect();
                const elementRect = element.getBoundingClientRect();
                const scrollTop = scrollContainer.scrollTop;
                
                console.log('📐 Container rect:', { top: containerRect.top, left: containerRect.left, width: containerRect.width, height: containerRect.height });
                console.log('📐 Element rect:', { top: elementRect.top, left: elementRect.left, width: elementRect.width, height: elementRect.height });
                console.log('📐 Current scroll top:', scrollTop);
                
                // Position de l'élément par rapport au début du contenu
                const elementOffsetTop = elementRect.top - containerRect.top + scrollTop;
                
                // Position finale avec compensation du header et marge supplémentaire
                const marginOffset = 80; // Marge confortable sous le header
                const finalScrollPosition = Math.max(0, elementOffsetTop - totalHeaderHeight - marginOffset);
                
                console.log('📐 Element offset top:', elementOffsetTop);
                console.log('📐 Total header height:', totalHeaderHeight);
                console.log('📐 Margin offset:', marginOffset);
                console.log('📐 Final scroll position:', finalScrollPosition);
                
                // Défiler vers la position calculée
                scrollContainer.scrollTo({
                  top: finalScrollPosition,
                  behavior: 'smooth'
                });
                
                // Vérifier que le défilement a bien eu lieu
                setTimeout(() => {
                  console.log('📐 Scroll position après défilement:', scrollContainer.scrollTop);
                }, 300);
              } else {
                console.log('⚠️ Conteneur ne peut pas défiler, utilisation de window.scrollTo()');
                
                // Utiliser window.scrollTo() comme fallback
                const elementRect = element.getBoundingClientRect();
                const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
                
                console.log('📐 Element rect (window):', { top: elementRect.top, left: elementRect.left });
                console.log('📐 Current window scroll:', currentScroll);
                
                // Calculer la position absolue de l'élément par rapport à la page
                const elementPageTop = elementRect.top + currentScroll;
                
                // Position finale avec compensation du header
                const marginOffset = 80;
                const finalWindowScrollPosition = Math.max(0, elementPageTop - totalHeaderHeight - marginOffset);
                
                console.log('📐 Element page top:', elementPageTop);
                console.log('📐 Final window scroll position:', finalWindowScrollPosition);
                
                // Défiler la fenêtre entière
                window.scrollTo({
                  top: finalWindowScrollPosition,
                  behavior: 'smooth'
                });
                
                // Vérifier que le défilement a bien eu lieu
                setTimeout(() => {
                  console.log('📐 Window scroll position après défilement:', window.pageYOffset || document.documentElement.scrollTop);
                }, 300);
              }
            } else {
              console.log('❌ Aucun conteneur de défilement trouvé');
              // Lister tous les éléments avec overflow-y-auto pour le débogage
              const allScrollContainers = document.querySelectorAll('.overflow-y-auto');
              console.log('📋 Tous les conteneurs de défilement trouvés:', allScrollContainers.length);
              allScrollContainers.forEach((container, index) => {
                console.log(`📋 Container ${index}:`, container.tagName, container.className);
              });
              
              // Utiliser scrollIntoView comme dernier recours
              element.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
                inline: 'nearest'
              });
            }
          }, 150);
        } else {
          console.log('❌ Élément non trouvé avec ID:', elementId);
          // Lister tous les IDs disponibles pour le débogage
          const allElements = document.querySelectorAll('[id^="chapter-"], [id^="section-"], [id^="subsection-"]');
          console.log('📋 IDs disponibles:', Array.from(allElements).map(el => el.id));
        }
      }
    }
  }, [selectedItem, bookData]);

  // Regrouper les chapitres par thématique pour l'affichage "full content"
  const hasRealThematiques = useMemo(() => {
    return Array.isArray(bookData?.chapters) && bookData.chapters.some(ch => ch.thematique);
  }, [bookData?.chapters]);

  const groupedChapters = useMemo(() => {
    if (!Array.isArray(bookData?.chapters)) return [];
    const map = new Map(); // préserve l'ordre d'apparition
    const WITHOUT = 'sans-thematique';
    for (const ch of bookData.chapters) {
      const key = ch.thematique ? String(ch.thematique.id) : WITHOUT;
      if (!map.has(key)) {
        map.set(key, { key, thematique: ch.thematique || null, chapters: [] });
      }
      map.get(key).chapters.push(ch);
    }
    return Array.from(map.values());
  }, [bookData?.chapters]);

  return (
    <div className="w-full max-w-none px-6 py-8" ref={contentRef}>
      {/* Introduction du livre - Fixe lors du défilement */}
      {bookData.title && (
        <div className="w-full mb-8 sticky top-0 bg-white z-10 py-4 border-b border-gray-200">
          <h1 id="book-title" className="text-4xl font-bold text-gray-900 mb-4">{bookData.title}</h1>
          {bookData.description && (
            <div className="text-lg text-gray-700 leading-relaxed">
              {renderContent(bookData.description)}
            </div>
          )}
        </div>
      )}

      {/* Contenu des chapitres, groupés par thématique */}
      <div className="w-full space-y-12">
        {groupedChapters.map((group) => (
          <div key={group.key} className="w-full">
            {group.thematique ? (
              <div className="mb-6 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                <div className="flex items-center gap-2 text-purple-800">
                  <span className="font-semibold text-purple-900">Thématique:</span>
                  <span className="text-purple-700">{group.thematique.title}</span>
                </div>
                {group.thematique.description && (
                  <p className="text-sm text-purple-600 mt-1 italic">
                    {group.thematique.description}
                  </p>
                )}
              </div>
            ) : null}

            <div className="w-full space-y-10">
              {group.chapters.map((chapter) => {
                const chapterIndexOriginal = bookData.chapters.findIndex(c => c.id === chapter.id);
                return (
                  <div key={chapter.id} className="w-full">
                    {/* Titre du chapitre (H1) + actions admin */}
                    <div className="flex items-center justify-between gap-3 mb-6">
                      <h1 
                        id={`chapter-${chapter.id}`}
                        className={`text-3xl font-bold text-gray-900 ${selectedItem?.type === 'chapter' && selectedItem?.chapterIndex === chapterIndexOriginal ? 'bg-blue-50 border-l-4 border-blue-500 pl-4 py-2 -ml-6' : ''}`}
                      >
                        Chapitre {chapter.order + 1}. {cleanTitle(chapter.title, chapter.order)}
                      </h1>
                      {isAdmin && onRegenerateChapter && Array.isArray(chapter.sections) && chapter.sections.length > 0 && (
                        <button
                          type="button"
                          onClick={() => onRegenerateChapter(chapter.id)}
                          disabled={regenLoading}
                          className={`border-none rounded-md px-3 py-2 cursor-pointer transition-all duration-300 text-sm flex items-center gap-2 ${regenLoading ? 'bg-gray-300 text-gray-600' : 'bg-warning text-white hover:bg-warning hover:-translate-y-0.5'}`}
                          title="Régénérer le QCM (5 questions)"
                        >
                          <RefreshCw size={16} />
                          Régénérer QCM
                        </button>
                      )}
                    </div>

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
                            className={`text-2xl font-semibold text-gray-800 mb-4 ${selectedItem?.type === 'section' && selectedItem?.chapterIndex === chapterIndexOriginal && selectedItem?.sectionIndex === sectionIndex ? 'bg-green-50 border-l-4 border-green-500 pl-4 py-2 -ml-4' : ''}`}
                          >
                            {chapter.order + 1}.{section.order + 1} {cleanTitle(section.title, section.order)}
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
                                  className={`text-xl font-medium text-gray-700 mb-3 ${selectedItem?.type === 'subsection' && selectedItem?.chapterIndex === chapterIndexOriginal && selectedItem?.sectionIndex === sectionIndex && selectedItem?.subsectionIndex === subsectionIndex ? 'bg-yellow-50 border-l-4 border-yellow-500 pl-4 py-2 -ml-4' : ''}`}
                                >
                                  {chapter.order + 1}.{section.order + 1}.{subsection.order + 1} {cleanTitle(subsection.title, subsection.order)}
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
                              {chapter.order + 1}.{subsection.order + 1} {cleanTitle(subsection.title, subsection.order)}
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

                    {/* QCMs du chapitre - Affichés à la fin */}
                    {chapter.qcm && chapter.qcm.length > 0 && (
                      <div className="w-full mt-8">
                        <div className="border-t-2 border-blue-200 pt-6">
                          <h2 className="text-2xl font-bold text-blue-900 mb-6 flex items-center gap-2">
                            🧠 Quiz - Testez vos connaissances
                          </h2>
                          <div className="space-y-6">
                            {chapter.qcm.map((qcm, qcmIndex) => (
                              <div key={qcm.id} id={`chapter-${chapter.id}-qcm-${qcmIndex}`} className="qcm-section">
                                <QCMComponent key={qcm.id} qcm={qcm} />
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FullBookContent;