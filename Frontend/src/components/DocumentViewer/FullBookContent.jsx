import React, { useEffect, useRef, useMemo, useState } from 'react';
import { Pin, RefreshCw } from 'lucide-react';
import QCMComponent from './QCMComponent';
import api from '../../services/api';

const FullBookContent = ({
  bookData,
  selectedItem,
  isAdmin,
  canEditStructure = false,
  onRegenerateChapter,
  regenLoading,
  onBookContentChanged,
}) => {
  const [displayTitle, setDisplayTitle] = useState(bookData?.title || bookData?.book?.title || '');
  const [editMode, setEditMode] = useState(false);
  const [pendingTitle, setPendingTitle] = useState(displayTitle);
  const bookId = useMemo(() => (bookData?.book?.id || bookData?.id || null), [bookData]);
  const progressTimerRef = useRef(null);
  const saveCheckTimerRef = useRef(null);
  const lastScrollTsRef = useRef(0);
  const anchorRef = useRef({ type: null, id: null });
  const anchorChangedTsRef = useRef(0);
  const pendingPayloadRef = useRef(null);
  const [progressPct, setProgressPct] = useState(0);
  const [editStates, setEditStates] = useState({
    chapters: {},
    sections: {},
    subsections: {},
  });

  const [createStates, setCreateStates] = useState({
    chapter: { open: false, title: '', content: '', position: 'first', afterId: '' },
    // section: { [chapterId]: { open, title, content, position, afterId } }
    section: {},
    // subsection: { [sectionId]: { open, title, content, position, afterId } }
    subsection: {},
  });

  const [dragState, setDragState] = useState({ type: null, id: null });

  const CHARS_PER_MIN = 1000;
  const MIN_READ_MS = 5000;
  const MAX_READ_MS = 180000;
  const READ_RATIO = 0.8;

  const textLen = (s) => (typeof s === 'string' ? s.length : 0);
  const getAnchorLen = (type, id) => {
    let len = 0;
    const chapters = Array.isArray(bookData?.chapters) ? bookData.chapters : [];
    for (const ch of chapters) {
      if (type === 'chapter' && ch?.id === id) {
        const override = editStates.chapters[ch.id]?.contentOverride;
        len = textLen(override ?? ch?.content);
        break;
      }
      if (type === 'section' && Array.isArray(ch?.sections)) {
        for (const sec of ch.sections) {
          if (sec?.id === id) {
            const override = editStates.sections[sec.id]?.contentOverride;
            len = textLen(override ?? sec?.content);
            break;
          }
        }
        if (len) break;
      }
      if (type === 'subsection' && Array.isArray(ch?.sections)) {
        for (const sec of ch.sections) {
          if (Array.isArray(sec?.subsections)) {
            for (const sub of sec.subsections) {
              if (sub?.id === id) {
                const override = editStates.subsections[sub.id]?.contentOverride;
                len = textLen(override ?? sub?.content);
                break;
              }
            }
            if (len) break;
          }
        }
        if (len) break;
      }
    }
    return len;
  };
  const estimateReadMs = (type, id) => {
    const chars = getAnchorLen(type, id);
    const cps = CHARS_PER_MIN / 60;
    let ms = Math.ceil((chars / cps) * 1000);
    if (ms < MIN_READ_MS) ms = MIN_READ_MS;
    if (ms > MAX_READ_MS) ms = MAX_READ_MS;
    return ms;
  };

  useEffect(() => {
    setDisplayTitle(bookData?.title || bookData?.book?.title || '');
    setPendingTitle(bookData?.title || bookData?.book?.title || '');
  }, [bookData?.title, bookData?.book?.title]);
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
      const regex = new RegExp(`^${order}\.\s*`);
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
    if (!content || typeof content !== 'string') return null;

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
              className="mb-4 text-gray-700 leading-relaxed text-justify"
            >
              <HighlightedText text={trimmed} />
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
                className="mb-2 last:mb-0 leading-relaxed text-justify"
              >
                <HighlightedText text={line} />
              </p>
            ))}
          </div>
        );
      }
    });

    return elements;
  };

  const renderImages = (images) => {
    if (!images || images.length === 0) return null;
    
    // URL de base du backend Django pour les fichiers médias
    const backendBaseUrl = '';
    
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
                    console.error("Erreur de chargement de l'image:", fullImageUrl);
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
            {(() => {
              // Afficher une image si le tableau est un snapshot
              const url = table?.url || '';
              const isSnapshot = table?.is_snapshot === true || /\.(png|jpe?g|gif|webp)$/i.test(url);
              if (isSnapshot && url) {
                return (
                  <>
                    <div className="bg-white p-4 flex justify-center items-center">
                      <img src={url} alt={table.title || table.caption || `Tableau ${index + 1}`} className="max-w-full h-auto" />
                    </div>
                    <p className="text-sm text-gray-600 p-2 bg-gray-100 font-medium">{table.caption || table.title || `Tableau ${index + 1}`}</p>
                  </>
                );
              }

              // Sinon, parser le contenu texte en vrai tableau HTML
              const c = table?.content;
              let rawLines = [];
              if (typeof c === 'string') {
                rawLines = c.split('\n');
              } else if (Array.isArray(c)) {
                rawLines = c.flatMap((item) => (typeof item === 'string' ? item.split('\n') : []));
              }
              // Nettoyage
              let lines = rawLines.map(l => (l ?? '').trim()).filter(l => l.length > 0);
              const hasPipe = lines.some(l => l.includes('|'));
              if (hasPipe) {
                lines = lines.filter(l => l.includes('|'));
              }
              const rows = lines.map(l => l.split('|').map(cell => cell.trim()));
              const colCount = table?.columns || (rows[0]?.length || 0);
              const useHeader = colCount > 1 && rows.length > 0 && rows[0].length === colCount;

              return rows.length > 0 ? (
                <div className="bg-white p-4 overflow-x-auto">
                  <table className="min-w-full border border-gray-200 text-sm">
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
                  <p className="text-sm text-gray-600 mt-2">{table.caption || table.title || `Tableau ${index + 1}`}</p>
                </div>
              ) : (
                <div className="bg-gray-50 p-4 text-gray-500">Aucun contenu de tableau</div>
              );
            })()}
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

  useEffect(() => {
    if (!bookId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get(`/books/${bookId}/reading-progress/`);
        if (cancelled) return;
        const data = res?.data || {};
        if (typeof data.percentage === 'number') setProgressPct(data.percentage);
        const targetId = data.subsection_id
          ? `subsection-${data.subsection_id}`
          : data.section_id
          ? `section-${data.section_id}`
          : data.chapter_id
          ? `chapter-${data.chapter_id}`
          : null;
        if (targetId) {
          const el = document.getElementById(targetId);
          if (el) {
            setTimeout(() => {
              el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 150);
          }
        }
      } catch (_) {}
    })();
    return () => {
      cancelled = true;
    };
  }, [bookId]);

  const startEdit = (type, ids, initial) => {
    if (!canEditStructure) return;
    setEditStates((prev) => {
      const copy = { ...prev, [type]: { ...prev[type] } };
      const existing = copy[type][ids.id] || {};
      const effectiveContent =
        typeof existing.contentOverride === 'string'
          ? existing.contentOverride
          : typeof existing.content === 'string'
          ? existing.content
          : (initial.content || '');

      const baseImages =
        Array.isArray(existing.imagesOverride)
          ? existing.imagesOverride
          : initial.images;
      const baseTables =
        Array.isArray(existing.tablesOverride)
          ? existing.tablesOverride
          : initial.tables;

      const imagesText =
        typeof existing.imagesText === 'string'
          ? existing.imagesText
          : baseImages
          ? JSON.stringify(baseImages, null, 2)
          : '[]';
      const tablesText =
        typeof existing.tablesText === 'string'
          ? existing.tablesText
          : baseTables
          ? JSON.stringify(baseTables, null, 2)
          : '[]';

      const effectiveIsIntro =
        typeof existing.is_intro_override === 'boolean'
          ? existing.is_intro_override
          : typeof existing.is_intro === 'boolean'
          ? existing.is_intro
          : !!initial.is_intro;

      copy[type][ids.id] = {
        ...existing,
        editing: true,
        content: effectiveContent,
        imagesText,
        tablesText,
        is_intro: effectiveIsIntro,
      };
      return copy;
    });
  };

  const cancelEdit = (type, id) => {
    setEditStates((prev) => {
      const copy = { ...prev, [type]: { ...prev[type] } };
      copy[type][id] = { editing: false };
      return copy;
    });
  };

  const onChangeEditField = (type, id, field, value) => {
    setEditStates((prev) => {
      const copy = { ...prev, [type]: { ...prev[type] } };
      copy[type][id] = { ...(copy[type][id] || {}), [field]: value };
      return copy;
    });
  };

  const saveChapter = async (chapter) => {
    const st = editStates.chapters[chapter.id];
    if (!st) return;
    try {
      let images = [];
      let tables = [];
      try { images = JSON.parse(st.imagesText || '[]'); } catch (_) {}
      try { tables = JSON.parse(st.tablesText || '[]'); } catch (_) {}
      const is_intro = !!st.is_intro;
      await api.patch(`/books/${bookId}/chapters/${chapter.id}/`, { content: st.content, images, tables, is_intro });
      setEditStates((prev) => {
        const copy = { ...prev, chapters: { ...prev.chapters } };
        copy.chapters[chapter.id] = {
          editing: false,
          contentOverride: st.content,
          imagesOverride: images,
          tablesOverride: tables,
          is_intro_override: is_intro,
        };
        return copy;
      });
      if (typeof onBookContentChanged === 'function') {
        await onBookContentChanged();
      }
    } catch (e) {
      console.error('Erreur sauvegarde chapitre', e);
    }
  };

  const saveSection = async (chapter, section) => {
    const st = editStates.sections[section.id];
    if (!st) return;
    try {
      let images = [];
      let tables = [];
      try { images = JSON.parse(st.imagesText || '[]'); } catch (_) {}
      try { tables = JSON.parse(st.tablesText || '[]'); } catch (_) {}
      await api.patch(`/books/${bookId}/chapters/${chapter.id}/sections/${section.id}/`, {
        content: st.content,
        images,
        tables,
      });
      setEditStates((prev) => {
        const copy = { ...prev, sections: { ...prev.sections } };
        copy.sections[section.id] = {
          editing: false,
          contentOverride: st.content,
          imagesOverride: images,
          tablesOverride: tables,
        };
        return copy;
      });
      if (typeof onBookContentChanged === 'function') {
        await onBookContentChanged();
      }
    } catch (e) {
      console.error('Erreur sauvegarde section', e);
    }
  };

  const saveSubsection = async (chapter, section, subsection) => {
    const st = editStates.subsections[subsection.id];
    if (!st) return;
    try {
      let images = [];
      let tables = [];
      try { images = JSON.parse(st.imagesText || '[]'); } catch (_) {}
      try { tables = JSON.parse(st.tablesText || '[]'); } catch (_) {}
      await api.patch(`/books/${bookId}/chapters/${chapter.id}/sections/${section.id}/subsections/${subsection.id}/`, {
        content: st.content,
        images,
        tables,
      });
      setEditStates((prev) => {
        const copy = { ...prev, subsections: { ...prev.subsections } };
        copy.subsections[subsection.id] = {
          editing: false,
          contentOverride: st.content,
          imagesOverride: images,
          tablesOverride: tables,
        };
        return copy;
      });
      if (typeof onBookContentChanged === 'function') {
        await onBookContentChanged();
      }
    } catch (e) {
      console.error('Erreur sauvegarde sous-section', e);
    }
  };

  // Création de nouveaux chapitres / sections / sous-sections
  const startCreateChapter = () => {
    if (!canEditStructure) return;
    setCreateStates((prev) => ({
      ...prev,
      chapter: { open: true, title: '', content: '', position: 'first', afterId: '' },
    }));
  };

  const cancelCreateChapter = () => {
    setCreateStates((prev) => ({
      ...prev,
      chapter: { open: false, title: '', content: '', position: 'first', afterId: '' },
    }));
  };

  const saveCreateChapter = async () => {
    if (!bookId) return;
    const { title, content, position, afterId } = createStates.chapter;
    if (!title || !title.trim()) return;
    try {
      const payload = {
        title: title.trim(),
        content: content || '',
      };
      if (position) payload.position = position;
      if (position === 'after' && afterId) payload.after_id = afterId;
      await api.post(`/books/${bookId}/chapters/`, payload);
      cancelCreateChapter();
      if (typeof onBookContentChanged === 'function') {
        await onBookContentChanged();
      }
    } catch (e) {
      console.error('Erreur lors de la création du chapitre', e);
    }
  };

  const startCreateSection = (chapterId) => {
    if (!canEditStructure) return;
    setCreateStates((prev) => ({
      ...prev,
      section: {
        ...prev.section,
        [chapterId]: { open: true, title: '', content: '', position: 'first', afterId: '' },
      },
    }));
  };

  const cancelCreateSection = (chapterId) => {
    setCreateStates((prev) => ({
      ...prev,
      section: {
        ...prev.section,
        [chapterId]: { open: false, title: '', content: '', position: 'first', afterId: '' },
      },
    }));
  };

  const saveCreateSection = async (chapterId) => {
    if (!bookId) return;
    const st = createStates.section[chapterId];
    if (!st || !st.title || !st.title.trim()) return;
    try {
      const payload = {
        title: st.title.trim(),
        content: st.content || '',
      };
      if (st.position) payload.position = st.position;
      if (st.position === 'after' && st.afterId) payload.after_id = st.afterId;
      await api.post(`/books/${bookId}/chapters/${chapterId}/sections/`, payload);
      cancelCreateSection(chapterId);
      if (typeof onBookContentChanged === 'function') {
        await onBookContentChanged();
      }
    } catch (e) {
      console.error('Erreur lors de la création de la section', e);
    }
  };

  const startCreateSubsection = (sectionId) => {
    if (!canEditStructure) return;
    setCreateStates((prev) => ({
      ...prev,
      subsection: {
        ...prev.subsection,
        [sectionId]: { open: true, title: '', content: '', position: 'first', afterId: '' },
      },
    }));
  };

  const cancelCreateSubsection = (sectionId) => {
    setCreateStates((prev) => ({
      ...prev,
      subsection: {
        ...prev.subsection,
        [sectionId]: { open: false, title: '', content: '', position: 'first', afterId: '' },
      },
    }));
  };

  const saveCreateSubsection = async (chapterId, sectionId) => {
    if (!bookId) return;
    const st = createStates.subsection[sectionId];
    if (!st || !st.title || !st.title.trim()) return;
    try {
      const payload = {
        title: st.title.trim(),
        content: st.content || '',
      };
      if (st.position) payload.position = st.position;
      if (st.position === 'after' && st.afterId) payload.after_id = st.afterId;
      await api.post(`/books/${bookId}/chapters/${chapterId}/sections/${sectionId}/subsections/`, payload);
      cancelCreateSubsection(sectionId);
      if (typeof onBookContentChanged === 'function') {
        await onBookContentChanged();
      }
    } catch (e) {
      console.error('Erreur lors de la création de la sous-section', e);
    }
  };

  const saveProgress = (payload) => {
    if (!bookId) return;
    api.patch(`/books/${bookId}/reading-progress/`, payload).catch(() => {});
  };

  const IDLE_MS = 2500;   // temps sans scroll avant de considérer la position stable
  const DWELL_MS = 6000;  // temps minimum passé sur la même ancre (chapitre/section/sous-section)

  const scheduleSaveCheck = () => {
    if (saveCheckTimerRef.current) clearTimeout(saveCheckTimerRef.current);
    saveCheckTimerRef.current = setTimeout(() => {
      const now = Date.now();
      const idleOk = now - (lastScrollTsRef.current || 0) >= IDLE_MS;
      const a = anchorRef.current || { type: null, id: null };
      let dwellNeeded = DWELL_MS;
      if (a.type && a.id) {
        const est = estimateReadMs(a.type, a.id);
        dwellNeeded = Math.floor(READ_RATIO * est);
      }
      const dwellOk = now - (anchorChangedTsRef.current || 0) >= dwellNeeded;
      if (idleOk && dwellOk && pendingPayloadRef.current) {
        saveProgress(pendingPayloadRef.current);
      } else {
        // Replanifier jusqu'à ce que les conditions soient remplies
        scheduleSaveCheck();
      }
    }, 400);
  };

  const computeAndSaveProgress = () => {
    if (!bookId) return;
    const now = Date.now();
    const doc = document.documentElement;
    const scrollTop = window.pageYOffset || doc.scrollTop || 0;
    const scrollHeight = doc.scrollHeight || 1;
    const clientHeight = doc.clientHeight || 1;
    const pct = Math.max(0, Math.min(100, (scrollTop / Math.max(1, scrollHeight - clientHeight)) * 100));
    setProgressPct(pct);

    const threshold = 120;
    let currentId = null;
    let currentType = null;

    const pick = (selector, type) => {
      const nodes = Array.from(document.querySelectorAll(selector));
      for (let i = 0; i < nodes.length; i++) {
        const r = nodes[i].getBoundingClientRect();
        if (r.top <= threshold) currentId = parseInt(nodes[i].id.split('-').pop(), 10) || null;
      }
      if (currentId != null) currentType = type;
    };

    pick('[id^="subsection-"]', 'subsection');
    if (currentId == null) pick('[id^="section-"]', 'section');
    if (currentId == null) pick('[id^="chapter-"]', 'chapter');

    const payload = { percentage: pct, position_in_text: Math.floor(scrollTop) };
    if (currentType === 'subsection') payload.subsection_id = currentId;
    else if (currentType === 'section') payload.section_id = currentId;
    else if (currentType === 'chapter') payload.chapter_id = currentId;

    // Mettre à jour l'ancre courante et le timestamp de changement
    const prev = anchorRef.current || { type: null, id: null };
    if (prev.type !== currentType || prev.id !== currentId) {
      anchorRef.current = { type: currentType, id: currentId };
      anchorChangedTsRef.current = now;
    }

    // Mémoriser la dernière activité de scroll et le payload à sauvegarder
    lastScrollTsRef.current = now;
    pendingPayloadRef.current = payload;
    scheduleSaveCheck();
  };

  useEffect(() => {
    const handler = () => computeAndSaveProgress();
    window.addEventListener('scroll', handler, { passive: true });
    return () => {
      window.removeEventListener('scroll', handler);
      if (progressTimerRef.current) clearTimeout(progressTimerRef.current);
      if (saveCheckTimerRef.current) clearTimeout(saveCheckTimerRef.current);
    };
  }, [bookId]);

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

  // Gestion du drag & drop pour réordonner les chapitres
  const handleChapterDragOver = (e) => {
    if (!canEditStructure || dragState.type !== 'chapter') return;
    e.preventDefault();
  };

  const handleChapterDrop = async (e, targetChapterId) => {
    if (!canEditStructure || !bookId) return;
    if (dragState.type !== 'chapter' || !dragState.id) return;
    e.preventDefault();

    const draggedId = dragState.id;
    if (draggedId === targetChapterId) {
      setDragState({ type: null, id: null });
      return;
    }

    const chaptersAll = Array.isArray(bookData?.chapters) ? bookData.chapters : [];
    if (!chaptersAll.length) return;

    const sorted = [...chaptersAll].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
    const fromIndex = sorted.findIndex((ch) => ch.id === draggedId);
    const toIndex = sorted.findIndex((ch) => ch.id === targetChapterId);
    if (fromIndex === -1 || toIndex === -1 || fromIndex === toIndex) {
      setDragState({ type: null, id: null });
      return;
    }

    const updated = [...sorted];
    const [moved] = updated.splice(fromIndex, 1);
    updated.splice(toIndex, 0, moved);

    try {
      await Promise.all(
        updated.map((ch, idx) =>
          api.patch(`/books/${bookId}/chapters/${ch.id}/`, { order: idx })
        )
      );
      if (typeof onBookContentChanged === 'function') {
        await onBookContentChanged();
      }
    } catch (err) {
      console.error('Erreur lors du réordonnancement des chapitres', err);
    } finally {
      setDragState({ type: null, id: null });
    }
  };

  return (
    <div className="w-full max-w-none px-6 py-8" ref={contentRef}>
      {/* Introduction du livre - Fixe lors du défilement */}
      {displayTitle && (
        <div className="w-full mb-8 sticky top-0 bg-white z-10 py-4 border-b border-gray-200">
          <div className="flex items-start justify-between gap-3">
            {!editMode ? (
              <h1 id="book-title" className="text-4xl font-bold text-gray-900 mb-4">{displayTitle}</h1>
            ) : (
              <div className="flex flex-col gap-2 w-full max-w-2xl">
                <input
                  type="text"
                  value={pendingTitle}
                  onChange={(e) => setPendingTitle(e.target.value)}
                  className="border border-gray-300 rounded px-3 py-2 text-2xl font-bold"
                />
                <div className="flex items-center gap-2">
                  <button
                    className="px-3 py-1 bg-blue-600 text-white rounded text-sm"
                    onClick={async () => {
                      try {
                        if (!bookId) return;
                        await api.patch(`/books/${bookId}/`, { title: pendingTitle });
                        setDisplayTitle(pendingTitle);
                        setEditMode(false);
                      } catch (e) {
                        console.error('Erreur lors de la mise à jour du titre', e);
                      }
                    }}
                  >
                    Enregistrer
                  </button>
                  <button
                    className="px-3 py-1 bg-gray-200 text-gray-800 rounded text-sm"
                    onClick={() => { setPendingTitle(displayTitle); setEditMode(false); }}
                  >
                    Annuler
                  </button>
                </div>
              </div>
            )}
            {isAdmin && !editMode && (
              <button
                className="h-9 mt-1 px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded text-sm border border-gray-300"
                onClick={() => setEditMode(true)}
                title="Modifier le titre du livre"
              >
                Modifier
              </button>
            )}
          </div>
          {/* Pourcentage de lecture */}
          <div className="flex items-center gap-3 mt-1">
            <div className="text-sm text-gray-600 font-medium">Progression: {Math.round(progressPct)}%</div>
            <div className="flex-1 h-2 bg-gray-200 rounded">
              <div className="h-2 bg-blue-500 rounded" style={{ width: `${Math.round(progressPct)}%` }} />
            </div>
          </div>
          {bookData.description && (
            <div className="text-lg text-gray-700 leading-relaxed">
              {renderContent(bookData.description)}
            </div>
          )}

          {canEditStructure && (
            <div className="mt-4">
              <button
                type="button"
                onClick={startCreateChapter}
                className="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md border border-dashed border-blue-400 text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors"
              >
                + Ajouter un chapitre
              </button>
            </div>
          )}

          {canEditStructure && createStates.chapter.open && (
            <div className="mt-4 max-w-2xl border border-gray-200 rounded-lg p-4 bg-gray-50 shadow-sm">
              <h2 className="text-sm font-semibold text-gray-800 mb-3">Nouveau chapitre</h2>
              <label className="block text-xs font-medium text-gray-600 mb-1">Titre</label>
              <input
                type="text"
                value={createStates.chapter.title}
                onChange={(e) =>
                  setCreateStates((prev) => ({
                    ...prev,
                    chapter: { ...prev.chapter, title: e.target.value },
                  }))
                }
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm mb-3"
                placeholder="Titre du chapitre"
              />
              <label className="block text-xs font-medium text-gray-600 mb-1">Contenu (optionnel)</label>
              <textarea
                value={createStates.chapter.content}
                onChange={(e) =>
                  setCreateStates((prev) => ({
                    ...prev,
                    chapter: { ...prev.chapter, content: e.target.value },
                  }))
                }
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm min-h-[80px]"
                placeholder="Résumé ou introduction du chapitre"
              />
              {/* Position du chapitre */}
              <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Position</label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                    value={createStates.chapter.position}
                    onChange={(e) =>
                      setCreateStates((prev) => ({
                        ...prev,
                        chapter: { ...prev.chapter, position: e.target.value, afterId: '' },
                      }))
                    }
                  >
                    <option value="first">Au début du livre</option>
                    <option value="last">À la fin du livre</option>
                    <option value="after">Après un autre chapitre</option>
                  </select>
                </div>
                {createStates.chapter.position === 'after' && Array.isArray(bookData?.chapters) && (
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Après le chapitre</label>
                    <select
                      className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                      value={createStates.chapter.afterId}
                      onChange={(e) =>
                        setCreateStates((prev) => ({
                          ...prev,
                          chapter: { ...prev.chapter, afterId: e.target.value },
                        }))
                      }
                    >
                      <option value="">-- Choisir un chapitre --</option>
                      {bookData.chapters.map((ch) => (
                        <option key={ch.id} value={ch.id}>
                          {cleanTitle(ch.title, ch.order) || `Chapitre ${ch.order}`}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
              <div className="mt-3 flex items-center gap-2">
                <button
                  type="button"
                  onClick={saveCreateChapter}
                  className="px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Enregistrer le chapitre
                </button>
                <button
                  type="button"
                  onClick={cancelCreateChapter}
                  className="px-3 py-1.5 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
                >
                  Annuler
                </button>
              </div>
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
                const isIntroChapter = (ch) => {
                  if (!ch) return false;
                  return !!ch.is_intro;
                };
                const isIntro = isIntroChapter(chapter);
                const displayChapterNumber = (chapter?.order ?? 0) - (bookData?.chapters?.filter(c => (c.order < chapter.order) && isIntroChapter(c)).length || 0);
                return (
                  <div
                    key={chapter.id}
                    className="w-full"
                    draggable={canEditStructure}
                    onDragStart={() => {
                      if (!canEditStructure) return;
                      setDragState({ type: 'chapter', id: chapter.id });
                    }}
                    onDragOver={handleChapterDragOver}
                    onDrop={(e) => handleChapterDrop(e, chapter.id)}
                  >
                    {/* Titre du chapitre (H1) + actions admin */}
                    <div className="flex items-center justify-between gap-3 mb-6">
                      <h1 
                        id={`chapter-${chapter.id}`}
                        className={`text-3xl font-bold text-gray-900 ${selectedItem?.type === 'chapter' && selectedItem?.chapterIndex === chapterIndexOriginal ? 'bg-blue-50 border-l-4 border-blue-500 pl-4 py-2 -ml-6' : ''}`}
                      >
                        {isIntro
                          ? cleanTitle(chapter.title, chapter.order)
                          : <>Chapitre {displayChapterNumber}. {cleanTitle(chapter.title, chapter.order)}</>}
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
                      {canEditStructure && (
                        <button
                          type="button"
                          onClick={() => startEdit('chapters', { id: chapter.id }, { content: chapter.content, is_intro: chapter.is_intro })}
                          className="border border-gray-300 text-gray-800 rounded-md px-3 py-2 text-sm hover:bg-gray-50"
                        >
                          Modifier contenu
                        </button>
                      )}
                    </div>

                    {/* Contenu du chapitre */}
                    {editStates.chapters[chapter.id]?.editing ? (
                      <div className="mb-6 border border-gray-200 rounded p-3 bg-gray-50">
                        <label className="block text-sm font-medium text-gray-700 mb-1">Contenu (texte)</label>
                        <textarea
                          className="w-full border border-gray-300 rounded p-2 text-sm min-h-[120px]"
                          value={editStates.chapters[chapter.id]?.content || ''}
                          onChange={(e) => onChangeEditField('chapters', chapter.id, 'content', e.target.value)}
                        />
                        <div className="mt-3 flex items-center gap-2">
                          <input
                            id={`chapter-${chapter.id}-is-intro`}
                            type="checkbox"
                            className="h-4 w-4"
                            checked={!!editStates.chapters[chapter.id]?.is_intro}
                            onChange={(e) => onChangeEditField('chapters', chapter.id, 'is_intro', e.target.checked)}
                          />
                          <label htmlFor={`chapter-${chapter.id}-is-intro`} className="text-sm text-gray-700">
                            Chapitre d'introduction (sans numéro ni icône de dossier)
                          </label>
                        </div>
                        {/* Images du chapitre: upload + liste visuelle (JSON caché) */}
                        <div className="mt-2 flex items-center gap-2">
                          <input
                            type="file"
                            accept="image/*"
                            onChange={async (e) => {
                              const file = e.target.files?.[0];
                              if (!file) return;
                              const form = new FormData();
                              form.append('file', file);
                              try {
                                const res = await api.post('/uploads/images/', form, { headers: { 'Content-Type': 'multipart/form-data' } });
                                const payload = res?.data;
                                const arr = (() => { try { return JSON.parse(editStates.chapters[chapter.id]?.imagesText || '[]'); } catch { return []; } })();
                                arr.push(payload);
                                onChangeEditField('chapters', chapter.id, 'imagesText', JSON.stringify(arr, null, 2));
                              } catch (err) {
                                console.error('Upload image chapitre échoué', err);
                              } finally {
                                e.target.value = '';
                              }
                            }}
                          />
                          <span className="text-xs text-gray-500">Uploader et ajouter automatiquement à la liste</span>
                        </div>
                        {(() => {
                          let arr = [];
                          try { arr = JSON.parse(editStates.chapters[chapter.id]?.imagesText || '[]'); } catch {}
                          if (!Array.isArray(arr) || arr.length === 0) return null;
                          return (
                            <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-3">
                              {arr.map((img, idx) => {
                                const url = typeof img === 'string' ? img : img?.url;
                                const caption = typeof img === 'object' ? img?.caption : undefined;
                                return (
                                  <div key={idx} className="border rounded p-2 flex flex-col gap-2 bg-white">
                                    {url ? (
                                      <img src={url} alt={caption || `Image ${idx+1}`} className="w-full h-28 object-cover rounded" />
                                    ) : (
                                      <div className="text-xs text-gray-500">Entrée d'image invalide</div>
                                    )}
                                    {caption ? <div className="text-xs text-gray-600 truncate">{caption}</div> : null}
                                    <button
                                      type="button"
                                      className="self-start px-2 py-1 text-xs bg-red-600 text-white rounded"
                                      onClick={() => {
                                        const next = arr.filter((_, i) => i !== idx);
                                        onChangeEditField('chapters', chapter.id, 'imagesText', JSON.stringify(next, null, 2));
                                      }}
                                    >Supprimer</button>
                                  </div>
                                );
                              })}
                            </div>
                          );
                        })()}
                        {/* Tableaux du chapitre: builder lignes/colonnes + grille */}
                        {(() => {
                          let tbls = [];
                          try { tbls = JSON.parse(editStates.chapters[chapter.id]?.tablesText || '[]'); } catch {}
                          if (!Array.isArray(tbls)) tbls = [];

                          const ensureShape = (t) => {
                            const clone = { ...(t || {}) };
                            let rows = Number.isInteger(clone.rows) ? clone.rows : null;
                            let columns = Number.isInteger(clone.columns) ? clone.columns : null;
                            let grid = Array.isArray(clone.grid) ? clone.grid.map((r) => Array.isArray(r) ? [...r] : []) : null;

                            if (!rows || !columns || !grid || grid.length === 0) {
                              const c = clone.content;
                              let rawLines = [];
                              if (typeof c === 'string') {
                                rawLines = c.split('\n');
                              } else if (Array.isArray(c)) {
                                rawLines = c.flatMap((item) => (typeof item === 'string' ? item.split('\n') : []));
                              }
                              let lines = rawLines.map((l) => (l ?? '').trim()).filter((l) => l.length > 0);
                              const hasPipe = lines.some((l) => l.includes('|'));
                              if (hasPipe) {
                                lines = lines.filter((l) => l.includes('|'));
                              }
                              const parsedRows = lines.map((l) => l.split('|').map((cell) => cell.trim()));
                              const colCount = parsedRows.length > 0 ? Math.max(...parsedRows.map((r) => r.length)) : 2;
                              const rowCount = parsedRows.length > 0 ? parsedRows.length : 2;
                              rows = rowCount;
                              columns = colCount;
                              grid = Array.from({ length: rows }, (_, ri) =>
                                Array.from({ length: columns }, (_, ci) => parsedRows[ri]?.[ci] ?? '')
                              );
                            }

                            if (grid.length !== rows) {
                              grid = Array.from({ length: rows }, (_, ri) => grid[ri] || []);
                            }
                            grid = grid.map((row) => {
                              if (!Array.isArray(row)) return Array.from({ length: columns }, () => '');
                              if (row.length < columns) {
                                return [...row, ...Array.from({ length: columns - row.length }, () => '')];
                              }
                              return row.slice(0, columns);
                            });

                            const content = grid.map((r) => r.join(' | ')).join('\n');
                            return { ...clone, rows, columns, grid, content };
                          };

                          const update = (updater) => {
                            const normalized = tbls.map((t) => ensureShape(t));
                            const next = updater(normalized).map((t) => {
                              const withShape = ensureShape(t);
                              return {
                                ...withShape,
                                content: withShape.grid.map((r) => r.join(' | ')).join('\n'),
                              };
                            });
                            onChangeEditField('chapters', chapter.id, 'tablesText', JSON.stringify(next, null, 2));
                          };

                          return (
                            <div className="mt-3 space-y-3">
                              {tbls.map((t, idx) => {
                                const shaped = ensureShape(t);
                                return (
                                  <div key={idx} className="border rounded p-2 bg-white">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-2">
                                      <div className="md:col-span-1">
                                        <label className="text-xs text-gray-600">Intitulé du tableau</label>
                                        <input
                                          className="w-full border border-gray-300 rounded p-1 text-sm"
                                          value={shaped.title || ''}
                                          onChange={(e) =>
                                            update((arr) => {
                                              arr[idx] = { ...shaped, title: e.target.value };
                                              return arr;
                                            })
                                          }
                                        />
                                      </div>
                                      <div>
                                        <label className="text-xs text-gray-600">Colonnes</label>
                                        <input
                                          type="number"
                                          min={1}
                                          max={12}
                                          className="w-full border border-gray-300 rounded p-1 text-sm"
                                          value={shaped.columns || 1}
                                          onChange={(e) => {
                                            const nextCols = Math.max(1, Math.min(12, parseInt(e.target.value || '1', 10)));
                                            update((arr) => {
                                              const current = ensureShape(arr[idx] || shaped);
                                              const newGrid = current.grid.map((row) => {
                                                if (row.length < nextCols) {
                                                  return [...row, ...Array.from({ length: nextCols - row.length }, () => '')];
                                                }
                                                return row.slice(0, nextCols);
                                              });
                                              arr[idx] = { ...current, columns: nextCols, grid: newGrid };
                                              return arr;
                                            });
                                          }}
                                        />
                                      </div>
                                      <div>
                                        <label className="text-xs text-gray-600">Lignes</label>
                                        <input
                                          type="number"
                                          min={1}
                                          max={30}
                                          className="w-full border border-gray-300 rounded p-1 text-sm"
                                          value={shaped.rows || 1}
                                          onChange={(e) => {
                                            const nextRows = Math.max(1, Math.min(30, parseInt(e.target.value || '1', 10)));
                                            update((arr) => {
                                              const current = ensureShape(arr[idx] || shaped);
                                              let newGrid = current.grid;
                                              if (newGrid.length < nextRows) {
                                                newGrid = [
                                                  ...newGrid,
                                                  ...Array.from({ length: nextRows - newGrid.length }, () =>
                                                    Array.from({ length: current.columns || 1 }, () => '')
                                                  ),
                                                ];
                                              } else if (newGrid.length > nextRows) {
                                                newGrid = newGrid.slice(0, nextRows);
                                              }
                                              arr[idx] = { ...current, rows: nextRows, grid: newGrid };
                                              return arr;
                                            });
                                          }}
                                        />
                                      </div>
                                    </div>

                                    <div className="overflow-x-auto">
                                      <table className="min-w-full border border-gray-200 text-xs">
                                        <tbody>
                                          {shaped.grid.map((row, ri) => (
                                            <tr key={ri} className={ri === 0 ? 'bg-gray-50' : ri % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                              {row.map((cell, ci) => (
                                                <td key={ci} className="border border-gray-200 p-1 align-top">
                                                  <input
                                                    className="w-full border border-gray-200 rounded px-1 py-0.5 text-[11px] bg-white"
                                                    value={cell}
                                                    onChange={(e) =>
                                                      update((arr) => {
                                                        const current = ensureShape(arr[idx] || shaped);
                                                        const g = current.grid.map((r) => [...r]);
                                                        g[ri][ci] = e.target.value;
                                                        arr[idx] = { ...current, grid: g };
                                                        return arr;
                                                      })
                                                    }
                                                  />
                                                </td>
                                              ))}
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>

                                    <div className="mt-2 flex items-center gap-2">
                                      <button
                                        type="button"
                                        className="px-2 py-1 text-xs bg-red-600 text-white rounded"
                                        onClick={() => update((arr) => arr.filter((_, i) => i !== idx))}
                                      >
                                        Supprimer
                                      </button>
                                    </div>
                                  </div>
                                );
                              })}
                              <button
                                type="button"
                                className="px-3 py-1 text-sm bg-gray-100 border rounded"
                                onClick={() =>
                                  update((arr) => [
                                    ...arr,
                                    {
                                      title: '',
                                      rows: 2,
                                      columns: 2,
                                      grid: [
                                        ['', ''],
                                        ['', ''],
                                      ],
                                      content: '|',
                                    },
                                  ])
                                }
                              >
                                Ajouter un tableau
                              </button>
                            </div>
                          );
                        })()}
                        <div className="mt-2 flex items-center gap-2">
                          <button
                            className="px-3 py-1 bg-blue-600 text-white rounded text-sm"
                            onClick={() => saveChapter(chapter)}
                          >
                            Enregistrer
                          </button>
                          <button
                            className="px-3 py-1 bg-gray-200 text-gray-800 rounded text-sm"
                            onClick={() => cancelEdit('chapters', chapter.id)}
                          >
                            Annuler
                          </button>
                        </div>
                      </div>
                    ) : (
                      (editStates.chapters[chapter.id]?.contentOverride || chapter.content) && (
                        <div className="text-gray-800 leading-relaxed mb-6 space-y-4">
                          {renderContent(editStates.chapters[chapter.id]?.contentOverride || chapter.content)}
                        </div>
                      )
                    )}

                    {/* Images du chapitre */}
                    {renderImages(editStates.chapters[chapter.id]?.imagesOverride ?? chapter.images)}

                    {/* Tableaux du chapitre */}
                    {renderTables(editStates.chapters[chapter.id]?.tablesOverride ?? chapter.tables)}

                    {/* Sections du chapitre */}
                    <div className="w-full space-y-6 ml-4">
                      {canEditStructure && (
                        <div className="mb-4 flex items-center justify-between">
                          <button
                            type="button"
                            onClick={() => startCreateSection(chapter.id)}
                            className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md border border-dashed border-emerald-400 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 transition-colors"
                          >
                            + Ajouter une section
                          </button>
                        </div>
                      )}

                      {canEditStructure && createStates.section[chapter.id]?.open && (
                        <div className="mb-4 border border-gray-200 rounded-lg p-3 bg-gray-50">
                          <h3 className="text-xs font-semibold text-gray-800 mb-2">Nouvelle section</h3>
                          <label className="block text-xs font-medium text-gray-600 mb-1">Titre</label>
                          <input
                            type="text"
                            value={createStates.section[chapter.id]?.title || ''}
                            onChange={(e) =>
                              setCreateStates((prev) => ({
                                ...prev,
                                section: {
                                  ...prev.section,
                                  [chapter.id]: {
                                    ...(prev.section[chapter.id] || {}),
                                    title: e.target.value,
                                  },
                                },
                              }))
                            }
                            className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm mb-2"
                            placeholder="Titre de la section"
                          />
                          <label className="block text-xs font-medium text-gray-600 mb-1">Contenu (optionnel)</label>
                          <textarea
                            value={createStates.section[chapter.id]?.content || ''}
                            onChange={(e) =>
                              setCreateStates((prev) => ({
                                ...prev,
                                section: {
                                  ...prev.section,
                                  [chapter.id]: {
                                    ...(prev.section[chapter.id] || {}),
                                    content: e.target.value,
                                  },
                                },
                              }))
                            }
                            className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm min-h-[60px]"
                            placeholder="Contenu de la section"
                          />
                          {/* Position de la section */}
                          <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">Position</label>
                              <select
                                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
                                value={createStates.section[chapter.id]?.position || 'first'}
                                onChange={(e) =>
                                  setCreateStates((prev) => ({
                                    ...prev,
                                    section: {
                                      ...prev.section,
                                      [chapter.id]: {
                                        ...(prev.section[chapter.id] || {}),
                                        position: e.target.value,
                                        afterId: '',
                                      },
                                    },
                                  }))
                                }
                              >
                                <option value="first">Au début du chapitre</option>
                                <option value="last">À la fin du chapitre</option>
                                <option value="after">Après une autre section</option>
                              </select>
                            </div>
                            {createStates.section[chapter.id]?.position === 'after' && Array.isArray(chapter.sections) && chapter.sections.length > 0 && (
                              <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">Après la section</label>
                                <select
                                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
                                  value={createStates.section[chapter.id]?.afterId || ''}
                                  onChange={(e) =>
                                    setCreateStates((prev) => ({
                                      ...prev,
                                      section: {
                                        ...prev.section,
                                        [chapter.id]: {
                                          ...(prev.section[chapter.id] || {}),
                                          afterId: e.target.value,
                                        },
                                      },
                                    }))
                                  }
                                >
                                  <option value="">-- Choisir une section --</option>
                                  {chapter.sections.map((sec) => (
                                    <option key={sec.id} value={sec.id}>
                                      {cleanTitle(sec.title, sec.order) || `Section ${sec.order}`}
                                    </option>
                                  ))}
                                </select>
                              </div>
                            )}
                          </div>
                          <div className="mt-2 flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => saveCreateSection(chapter.id)}
                              className="px-3 py-1.5 text-xs font-medium bg-emerald-600 text-white rounded hover:bg-emerald-700"
                            >
                              Enregistrer la section
                            </button>
                            <button
                              type="button"
                              onClick={() => cancelCreateSection(chapter.id)}
                              className="px-3 py-1.5 text-xs font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
                            >
                              Annuler
                            </button>
                          </div>
                        </div>
                      )}

                      {chapter.sections.map((section, sectionIndex) => (
                        <div key={section.id} className="w-full">
                          {/* Titre de la section (H2) */}
                          <div className="flex items-start justify-between gap-3">
                            <h2 
                            id={`section-${section.id}`}
                            className={`text-2xl font-semibold text-gray-800 mb-4 ${selectedItem?.type === 'section' && selectedItem?.chapterIndex === chapterIndexOriginal && selectedItem?.sectionIndex === sectionIndex ? 'bg-green-50 border-l-4 border-green-500 pl-4 py-2 -ml-4' : ''}`}
                            >
                              {isIntro
                                ? `${section.order} ${cleanTitle(section.title, section.order)}`
                                : `${displayChapterNumber}.${section.order} ${cleanTitle(section.title, section.order)}`}
                            </h2>
                            {canEditStructure && (
                              <button
                                type="button"
                                onClick={() => startEdit('sections', { id: section.id }, { content: section.content, images: section.images, tables: section.tables })}
                                className="mt-1 border border-gray-300 text-gray-800 rounded-md px-3 py-1 text-sm hover:bg-gray-50"
                              >
                                Modifier
                              </button>
                            )}
                          </div>

                          {/* Contenu de la section */}
                          {editStates.sections[section.id]?.editing ? (
                            <div className="mb-4 border border-gray-200 rounded p-3 bg-gray-50">
                              <label className="block text-sm font-medium text-gray-700 mb-1">Contenu (texte)</label>
                              <textarea
                                className="w-full border border-gray-300 rounded p-2 text-sm min-h-[100px]"
                                value={editStates.sections[section.id]?.content || ''}
                                onChange={(e) => onChangeEditField('sections', section.id, 'content', e.target.value)}
                              />
                              {/* Images: upload + liste visuelle (JSON caché) */}
                              <div className="mt-2 flex items-center gap-2">
                                <input
                                  type="file"
                                  accept="image/*"
                                  onChange={async (e) => {
                                    const file = e.target.files?.[0];
                                    if (!file) return;
                                    const form = new FormData();
                                    form.append('file', file);
                                    try {
                                      const res = await api.post('/uploads/images/', form, { headers: { 'Content-Type': 'multipart/form-data' } });
                                      const payload = res?.data;
                                      const arr = (() => { try { return JSON.parse(editStates.sections[section.id]?.imagesText || '[]'); } catch { return []; } })();
                                      arr.push(payload);
                                      onChangeEditField('sections', section.id, 'imagesText', JSON.stringify(arr, null, 2));
                                    } catch (err) {
                                      console.error('Upload image section échoué', err);
                                    } finally {
                                      e.target.value = '';
                                    }
                                  }}
                                />
                                <span className="text-xs text-gray-500">Uploader et ajouter automatiquement à la liste</span>
                              </div>
                              {(() => {
                                let arr = [];
                                try { arr = JSON.parse(editStates.sections[section.id]?.imagesText || '[]'); } catch {}
                                if (!Array.isArray(arr) || arr.length === 0) return null;
                                return (
                                  <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-3">
                                    {arr.map((img, idx) => {
                                      const url = typeof img === 'string' ? img : img?.url;
                                      const caption = typeof img === 'object' ? img?.caption : undefined;
                                      return (
                                        <div key={idx} className="border rounded p-2 flex flex-col gap-2 bg-white">
                                          {url ? (
                                            <img src={url} alt={caption || `Image ${idx+1}`} className="w-full h-28 object-cover rounded" />
                                          ) : (
                                            <div className="text-xs text-gray-500">Entrée d'image invalide</div>
                                          )}
                                          {caption ? <div className="text-xs text-gray-600 truncate">{caption}</div> : null}
                                          <button
                                            type="button"
                                            className="self-start px-2 py-1 text-xs bg-red-600 text-white rounded"
                                            onClick={() => {
                                              const next = arr.filter((_, i) => i !== idx);
                                              onChangeEditField('sections', section.id, 'imagesText', JSON.stringify(next, null, 2));
                                            }}
                                          >Supprimer</button>
                                        </div>
                                      );
                                    })}
                                  </div>
                                );
                              })()}
                              {/* Tableaux: builder avec lignes/colonnes + grille (JSON caché) */}
                              {(() => {
                                let tbls = [];
                                try { tbls = JSON.parse(editStates.sections[section.id]?.tablesText || '[]'); } catch {}
                                if (!Array.isArray(tbls)) tbls = [];

                                const ensureShape = (t) => {
                                  const clone = { ...(t || {}) };
                                  let rows = Number.isInteger(clone.rows) ? clone.rows : null;
                                  let columns = Number.isInteger(clone.columns) ? clone.columns : null;
                                  let grid = Array.isArray(clone.grid) ? clone.grid.map((r) => Array.isArray(r) ? [...r] : []) : null;

                                  if (!rows || !columns || !grid || grid.length === 0) {
                                    // Essayer de déduire depuis content texte
                                    const c = clone.content;
                                    let rawLines = [];
                                    if (typeof c === 'string') {
                                      rawLines = c.split('\n');
                                    } else if (Array.isArray(c)) {
                                      rawLines = c.flatMap((item) => (typeof item === 'string' ? item.split('\n') : []));
                                    }
                                    let lines = rawLines.map((l) => (l ?? '').trim()).filter((l) => l.length > 0);
                                    const hasPipe = lines.some((l) => l.includes('|'));
                                    if (hasPipe) {
                                      lines = lines.filter((l) => l.includes('|'));
                                    }
                                    const parsedRows = lines.map((l) => l.split('|').map((cell) => cell.trim()));
                                    const colCount = parsedRows.length > 0 ? Math.max(...parsedRows.map((r) => r.length)) : 2;
                                    const rowCount = parsedRows.length > 0 ? parsedRows.length : 2;
                                    rows = rowCount;
                                    columns = colCount;
                                    grid = Array.from({ length: rows }, (_, ri) =>
                                      Array.from({ length: columns }, (_, ci) => parsedRows[ri]?.[ci] ?? '')
                                    );
                                  }

                                  // S'assurer que grid correspond bien à rows/columns
                                  if (grid.length !== rows) {
                                    grid = Array.from({ length: rows }, (_, ri) => grid[ri] || []);
                                  }
                                  grid = grid.map((row) => {
                                    if (!Array.isArray(row)) return Array.from({ length: columns }, () => '');
                                    if (row.length < columns) {
                                      return [...row, ...Array.from({ length: columns - row.length }, () => '')];
                                    }
                                    return row.slice(0, columns);
                                  });

                                  const content = grid.map((r) => r.join(' | ')).join('\n');
                                  return { ...clone, rows, columns, grid, content };
                                };

                                const update = (updater) => {
                                  const normalized = tbls.map((t) => ensureShape(t));
                                  const next = updater(normalized).map((t) => {
                                    const withShape = ensureShape(t);
                                    return {
                                      ...withShape,
                                      content: withShape.grid.map((r) => r.join(' | ')).join('\n'),
                                    };
                                  });
                                  onChangeEditField('sections', section.id, 'tablesText', JSON.stringify(next, null, 2));
                                };

                                return (
                                  <div className="mt-2 space-y-3">
                                    {tbls.map((t, idx) => {
                                      const shaped = ensureShape(t);
                                      return (
                                        <div key={idx} className="border rounded p-2 bg-white">
                                          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-2">
                                            <div className="md:col-span-1">
                                              <label className="text-xs text-gray-600">Intitulé du tableau</label>
                                              <input
                                                className="w-full border border-gray-300 rounded p-1 text-sm"
                                                value={shaped.title || ''}
                                                onChange={(e) =>
                                                  update((arr) => {
                                                    arr[idx] = { ...shaped, title: e.target.value };
                                                    return arr;
                                                  })
                                                }
                                              />
                                            </div>
                                            <div>
                                              <label className="text-xs text-gray-600">Colonnes</label>
                                              <input
                                                type="number"
                                                min={1}
                                                max={12}
                                                className="w-full border border-gray-300 rounded p-1 text-sm"
                                                value={shaped.columns || 1}
                                                onChange={(e) => {
                                                  const nextCols = Math.max(1, Math.min(12, parseInt(e.target.value || '1', 10)));
                                                  update((arr) => {
                                                    const current = ensureShape(arr[idx] || shaped);
                                                    const newGrid = current.grid.map((row) => {
                                                      if (row.length < nextCols) {
                                                        return [...row, ...Array.from({ length: nextCols - row.length }, () => '')];
                                                      }
                                                      return row.slice(0, nextCols);
                                                    });
                                                    arr[idx] = { ...current, columns: nextCols, grid: newGrid };
                                                    return arr;
                                                  });
                                                }}
                                              />
                                            </div>
                                            <div>
                                              <label className="text-xs text-gray-600">Lignes</label>
                                              <input
                                                type="number"
                                                min={1}
                                                max={30}
                                                className="w-full border border-gray-300 rounded p-1 text-sm"
                                                value={shaped.rows || 1}
                                                onChange={(e) => {
                                                  const nextRows = Math.max(1, Math.min(30, parseInt(e.target.value || '1', 10)));
                                                  update((arr) => {
                                                    const current = ensureShape(arr[idx] || shaped);
                                                    let newGrid = current.grid;
                                                    if (newGrid.length < nextRows) {
                                                      newGrid = [
                                                        ...newGrid,
                                                        ...Array.from({ length: nextRows - newGrid.length }, () =>
                                                          Array.from({ length: current.columns || 1 }, () => '')
                                                        ),
                                                      ];
                                                    } else if (newGrid.length > nextRows) {
                                                      newGrid = newGrid.slice(0, nextRows);
                                                    }
                                                    arr[idx] = { ...current, rows: nextRows, grid: newGrid };
                                                    return arr;
                                                  });
                                                }}
                                              />
                                            </div>
                                          </div>

                                          {/* Grille éditable */}
                                          <div className="overflow-x-auto">
                                            <table className="min-w-full border border-gray-200 text-xs">
                                              <tbody>
                                                {shaped.grid.map((row, ri) => (
                                                  <tr key={ri} className={ri === 0 ? 'bg-gray-50' : ri % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                                    {row.map((cell, ci) => (
                                                      <td key={ci} className="border border-gray-200 p-1 align-top">
                                                        <input
                                                          className="w-full border border-gray-200 rounded px-1 py-0.5 text-[11px] bg-white"
                                                          value={cell}
                                                          onChange={(e) =>
                                                            update((arr) => {
                                                              const current = ensureShape(arr[idx] || shaped);
                                                              const g = current.grid.map((r) => [...r]);
                                                              g[ri][ci] = e.target.value;
                                                              arr[idx] = { ...current, grid: g };
                                                              return arr;
                                                            })
                                                          }
                                                        />
                                                      </td>
                                                    ))}
                                                  </tr>
                                                ))}
                                              </tbody>
                                            </table>
                                          </div>

                                          <div className="mt-2 flex items-center gap-2">
                                            <button
                                              type="button"
                                              className="px-2 py-1 text-xs bg-red-600 text-white rounded"
                                              onClick={() => update((arr) => arr.filter((_, i) => i !== idx))}
                                            >
                                              Supprimer
                                            </button>
                                          </div>
                                        </div>
                                      );
                                    })}
                                    <button
                                      type="button"
                                      className="px-3 py-1 text-sm bg-gray-100 border rounded"
                                      onClick={() =>
                                        update((arr) => [
                                          ...arr,
                                          {
                                            title: '',
                                            rows: 2,
                                            columns: 2,
                                            grid: [
                                              ['', ''],
                                              ['', ''],
                                            ],
                                            content: '|',
                                          },
                                        ])
                                      }
                                    >
                                      Ajouter un tableau
                                    </button>
                                  </div>
                                );
                              })()}
                              <div className="mt-2 flex items-center gap-2">
                                <button className="px-3 py-1 bg-blue-600 text-white rounded text-sm" onClick={() => saveSection(chapter, section)}>Enregistrer</button>
                                <button className="px-3 py-1 bg-gray-200 text-gray-800 rounded text-sm" onClick={() => cancelEdit('sections', section.id)}>Annuler</button>
                              </div>
                            </div>
                          ) : (
                            (editStates.sections[section.id]?.contentOverride || section.content) && (
                              <div className="text-gray-700 leading-relaxed mb-4 space-y-3">
                                {renderContent(editStates.sections[section.id]?.contentOverride || section.content)}
                              </div>
                            )
                          )}

                          {/* Images de la section */}
                          {renderImages(editStates.sections[section.id]?.imagesOverride ?? section.images)}

                          {/* Tableaux de la section */}
                          {renderTables(editStates.sections[section.id]?.tablesOverride ?? section.tables)}

                          {/* Sous-sections de la section */}
                          <div className="w-full space-y-4 ml-4">
                            {canEditStructure && (
                              <div className="mb-2 flex items-center justify-between">
                                <button
                                  type="button"
                                  onClick={() => startCreateSubsection(section.id)}
                                  className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md border border-dashed border-indigo-400 text-indigo-700 bg-indigo-50 hover:bg-indigo-100 transition-colors"
                                >
                                  + Ajouter une sous-section
                                </button>
                              </div>
                            )}

                            {canEditStructure && createStates.subsection[section.id]?.open && (
                              <div className="mb-3 border border-gray-200 rounded p-3 bg-gray-50">
                                <h4 className="text-xs font-semibold text-gray-800 mb-2">Nouvelle sous-section</h4>
                                <label className="block text-xs font-medium text-gray-600 mb-1">Titre</label>
                                <input
                                  type="text"
                                  value={createStates.subsection[section.id]?.title || ''}
                                  onChange={(e) =>
                                    setCreateStates((prev) => ({
                                      ...prev,
                                      subsection: {
                                        ...prev.subsection,
                                        [section.id]: {
                                          ...(prev.subsection[section.id] || {}),
                                          title: e.target.value,
                                        },
                                      },
                                    }))
                                  }
                                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm mb-2"
                                  placeholder="Titre de la sous-section"
                                />
                                <label className="block text-xs font-medium text-gray-600 mb-1">Contenu (optionnel)</label>
                                <textarea
                                  value={createStates.subsection[section.id]?.content || ''}
                                  onChange={(e) =>
                                    setCreateStates((prev) => ({
                                      ...prev,
                                      subsection: {
                                        ...prev.subsection,
                                        [section.id]: {
                                          ...(prev.subsection[section.id] || {}),
                                          content: e.target.value,
                                        },
                                      },
                                    }))
                                  }
                                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm min-h-[60px]"
                                  placeholder="Contenu de la sous-section"
                                />
                                {/* Position de la sous-section */}
                                <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">Position</label>
                                    <select
                                      className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
                                      value={createStates.subsection[section.id]?.position || 'first'}
                                      onChange={(e) =>
                                        setCreateStates((prev) => ({
                                          ...prev,
                                          subsection: {
                                            ...prev.subsection,
                                            [section.id]: {
                                              ...(prev.subsection[section.id] || {}),
                                              position: e.target.value,
                                              afterId: '',
                                            },
                                          },
                                        }))
                                      }
                                    >
                                      <option value="first">Au début de la section</option>
                                      <option value="last">À la fin de la section</option>
                                      <option value="after">Après une autre sous-section</option>
                                    </select>
                                  </div>
                                  {createStates.subsection[section.id]?.position === 'after' && Array.isArray(section.subsections) && section.subsections.length > 0 && (
                                    <div>
                                      <label className="block text-xs font-medium text-gray-600 mb-1">Après la sous-section</label>
                                      <select
                                        className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
                                        value={createStates.subsection[section.id]?.afterId || ''}
                                        onChange={(e) =>
                                          setCreateStates((prev) => ({
                                            ...prev,
                                            subsection: {
                                              ...prev.subsection,
                                              [section.id]: {
                                                ...(prev.subsection[section.id] || {}),
                                                afterId: e.target.value,
                                              },
                                            },
                                          }))
                                        }
                                      >
                                        <option value="">-- Choisir une sous-section --</option>
                                        {section.subsections.map((sub) => (
                                          <option key={sub.id} value={sub.id}>
                                            {cleanTitle(sub.title, sub.order) || `Sous-section ${sub.order}`}
                                          </option>
                                        ))}
                                      </select>
                                    </div>
                                  )}
                                </div>
                                <div className="mt-2 flex items-center gap-2">
                                  <button
                                    type="button"
                                    onClick={() => saveCreateSubsection(chapter.id, section.id)}
                                    className="px-3 py-1.5 text-xs font-medium bg-indigo-600 text-white rounded hover:bg-indigo-700"
                                  >
                                    Enregistrer la sous-section
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => cancelCreateSubsection(section.id)}
                                    className="px-3 py-1.5 text-xs font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
                                  >
                                    Annuler
                                  </button>
                                </div>
                              </div>
                            )}

                            {section.subsections.map((subsection, subsectionIndex) => (
                              <div key={subsection.id} className="w-full">
                                {/* Titre de la sous-section (H3) */}
                                <div className="flex items-start justify-between gap-3">
                                  <h3 
                                  id={`subsection-${subsection.id}`}
                                  className={`text-xl font-medium text-gray-700 mb-3 ${selectedItem?.type === 'subsection' && selectedItem?.chapterIndex === chapterIndexOriginal && selectedItem?.sectionIndex === sectionIndex && selectedItem?.subsectionIndex === subsectionIndex ? 'bg-yellow-50 border-l-4 border-yellow-500 pl-4 py-2 -ml-4' : ''}`}
                                  >
                                    {isIntro
                                      ? `${section.order}.${subsection.order} ${cleanTitle(subsection.title, subsection.order)}`
                                      : `${displayChapterNumber}.${section.order}.${subsection.order} ${cleanTitle(subsection.title, subsection.order)}`}
                                  </h3>
                                  {canEditStructure && (
                                    <button
                                      type="button"
                                      onClick={() => startEdit('subsections', { id: subsection.id }, { content: subsection.content, images: subsection.images, tables: subsection.tables })}
                                      className="mt-1 border border-gray-300 text-gray-800 rounded-md px-3 py-1 text-sm hover:bg-gray-50"
                                    >
                                      Modifier
                                    </button>
                                  )}
                                </div>

                                {/* Contenu de la sous-section */}
                                {editStates.subsections[subsection.id]?.editing ? (
                                  <div className="mb-3 border border-gray-200 rounded p-3 bg-gray-50">
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Contenu (texte)</label>
                                    <textarea
                                      className="w-full border border-gray-300 rounded p-2 text-sm min-h-[90px]"
                                      value={editStates.subsections[subsection.id]?.content || ''}
                                      onChange={(e) => onChangeEditField('subsections', subsection.id, 'content', e.target.value)}
                                    />
                                    {/* Images: upload + liste visuelle (JSON caché) */}
                                    <div className="mt-2 flex items-center gap-2">
                                      <input
                                        type="file"
                                        accept="image/*"
                                        onChange={async (e) => {
                                          const file = e.target.files?.[0];
                                          if (!file) return;
                                          const form = new FormData();
                                          form.append('file', file);
                                          try {
                                            const res = await api.post('/uploads/images/', form, { headers: { 'Content-Type': 'multipart/form-data' } });
                                            const payload = res?.data;
                                            const arr = (() => { try { return JSON.parse(editStates.subsections[subsection.id]?.imagesText || '[]'); } catch { return []; } })();
                                            arr.push(payload);
                                            onChangeEditField('subsections', subsection.id, 'imagesText', JSON.stringify(arr, null, 2));
                                          } catch (err) {
                                            console.error('Upload image sous-section échoué', err);
                                          } finally {
                                            e.target.value = '';
                                          }
                                        }}
                                      />
                                      <span className="text-xs text-gray-500">Uploader et ajouter automatiquement à la liste</span>
                                    </div>
                                    {(() => {
                                      let arr = [];
                                      try { arr = JSON.parse(editStates.subsections[subsection.id]?.imagesText || '[]'); } catch {}
                                      if (!Array.isArray(arr) || arr.length === 0) return null;
                                      return (
                                        <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-3">
                                          {arr.map((img, idx) => {
                                            const url = typeof img === 'string' ? img : img?.url;
                                            const caption = typeof img === 'object' ? img?.caption : undefined;
                                            return (
                                              <div key={idx} className="border rounded p-2 flex flex-col gap-2 bg-white">
                                                {url ? (
                                                  <img src={url} alt={caption || `Image ${idx+1}`} className="w-full h-28 object-cover rounded" />
                                                ) : (
                                                  <div className="text-xs text-gray-500">Entrée d'image invalide</div>
                                                )}
                                                {caption ? <div className="text-xs text-gray-600 truncate">{caption}</div> : null}
                                                <button
                                                  type="button"
                                                  className="self-start px-2 py-1 text-xs bg-red-600 text-white rounded"
                                                  onClick={() => {
                                                    const next = arr.filter((_, i) => i !== idx);
                                                    onChangeEditField('subsections', subsection.id, 'imagesText', JSON.stringify(next, null, 2));
                                                  }}
                                                >Supprimer</button>
                                              </div>
                                            );
                                          })}
                                        </div>
                                      );
                                    })()}
                                    {/* Tableaux: UI structurée (JSON caché) */}
                                    {(() => {
                                      let tbls = [];
                                      try { tbls = JSON.parse(editStates.subsections[subsection.id]?.tablesText || '[]'); } catch {}
                                      if (!Array.isArray(tbls)) tbls = [];

                                      const ensureShape = (t) => {
                                        const clone = { ...(t || {}) };
                                        let rows = Number.isInteger(clone.rows) ? clone.rows : null;
                                        let columns = Number.isInteger(clone.columns) ? clone.columns : null;
                                        let grid = Array.isArray(clone.grid) ? clone.grid.map((r) => Array.isArray(r) ? [...r] : []) : null;

                                        if (!rows || !columns || !grid || grid.length === 0) {
                                          const c = clone.content;
                                          let rawLines = [];
                                          if (typeof c === 'string') {
                                            rawLines = c.split('\n');
                                          } else if (Array.isArray(c)) {
                                            rawLines = c.flatMap((item) => (typeof item === 'string' ? item.split('\n') : []));
                                          }
                                          let lines = rawLines.map((l) => (l ?? '').trim()).filter((l) => l.length > 0);
                                          const hasPipe = lines.some((l) => l.includes('|'));
                                          if (hasPipe) {
                                            lines = lines.filter((l) => l.includes('|'));
                                          }
                                          const parsedRows = lines.map((l) => l.split('|').map((cell) => cell.trim()));
                                          const colCount = parsedRows.length > 0 ? Math.max(...parsedRows.map((r) => r.length)) : 2;
                                          const rowCount = parsedRows.length > 0 ? parsedRows.length : 2;
                                          rows = rowCount;
                                          columns = colCount;
                                          grid = Array.from({ length: rows }, (_, ri) =>
                                            Array.from({ length: columns }, (_, ci) => parsedRows[ri]?.[ci] ?? '')
                                          );
                                        }

                                        if (grid.length !== rows) {
                                          grid = Array.from({ length: rows }, (_, ri) => grid[ri] || []);
                                        }
                                        grid = grid.map((row) => {
                                          if (!Array.isArray(row)) return Array.from({ length: columns }, () => '');
                                          if (row.length < columns) {
                                            return [...row, ...Array.from({ length: columns - row.length }, () => '')];
                                          }
                                          return row.slice(0, columns);
                                        });

                                        const content = grid.map((r) => r.join(' | ')).join('\n');
                                        return { ...clone, rows, columns, grid, content };
                                      };

                                      const update = (updater) => {
                                        const normalized = tbls.map((t) => ensureShape(t));
                                        const next = updater(normalized).map((t) => {
                                          const withShape = ensureShape(t);
                                          return {
                                            ...withShape,
                                            content: withShape.grid.map((r) => r.join(' | ')).join('\n'),
                                          };
                                        });
                                        onChangeEditField('subsections', subsection.id, 'tablesText', JSON.stringify(next, null, 2));
                                      };

                                      return (
                                        <div className="mt-2 space-y-3">
                                          {tbls.map((t, idx) => {
                                            const shaped = ensureShape(t);
                                            return (
                                              <div key={idx} className="border rounded p-2 bg-white">
                                                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-2">
                                                  <div className="md:col-span-1">
                                                    <label className="text-xs text-gray-600">Intitulé du tableau</label>
                                                    <input
                                                      className="w-full border border-gray-300 rounded p-1 text-sm"
                                                      value={shaped.title || ''}
                                                      onChange={(e) =>
                                                        update((arr) => {
                                                          arr[idx] = { ...shaped, title: e.target.value };
                                                          return arr;
                                                        })
                                                      }
                                                    />
                                                  </div>
                                                  <div>
                                                    <label className="text-xs text-gray-600">Colonnes</label>
                                                    <input
                                                      type="number"
                                                      min={1}
                                                      max={12}
                                                      className="w-full border border-gray-300 rounded p-1 text-sm"
                                                      value={shaped.columns || 1}
                                                      onChange={(e) => {
                                                        const nextCols = Math.max(1, Math.min(12, parseInt(e.target.value || '1', 10)));
                                                        update((arr) => {
                                                          const current = ensureShape(arr[idx] || shaped);
                                                          const newGrid = current.grid.map((row) => {
                                                            if (row.length < nextCols) {
                                                              return [...row, ...Array.from({ length: nextCols - row.length }, () => '')];
                                                            }
                                                            return row.slice(0, nextCols);
                                                          });
                                                          arr[idx] = { ...current, columns: nextCols, grid: newGrid };
                                                          return arr;
                                                        });
                                                      }}
                                                    />
                                                  </div>
                                                  <div>
                                                    <label className="text-xs text-gray-600">Lignes</label>
                                                    <input
                                                      type="number"
                                                      min={1}
                                                      max={30}
                                                      className="w-full border border-gray-300 rounded p-1 text-sm"
                                                      value={shaped.rows || 1}
                                                      onChange={(e) => {
                                                        const nextRows = Math.max(1, Math.min(30, parseInt(e.target.value || '1', 10)));
                                                        update((arr) => {
                                                          const current = ensureShape(arr[idx] || shaped);
                                                          let newGrid = current.grid;
                                                          if (newGrid.length < nextRows) {
                                                            newGrid = [
                                                              ...newGrid,
                                                              ...Array.from({ length: nextRows - newGrid.length }, () =>
                                                                Array.from({ length: current.columns || 1 }, () => '')
                                                              ),
                                                            ];
                                                          } else if (newGrid.length > nextRows) {
                                                            newGrid = newGrid.slice(0, nextRows);
                                                          }
                                                          arr[idx] = { ...current, rows: nextRows, grid: newGrid };
                                                          return arr;
                                                        });
                                                      }}
                                                    />
                                                  </div>
                                                </div>

                                                <div className="overflow-x-auto">
                                                  <table className="min-w-full border border-gray-200 text-xs">
                                                    <tbody>
                                                      {shaped.grid.map((row, ri) => (
                                                        <tr key={ri} className={ri === 0 ? 'bg-gray-50' : ri % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                                          {row.map((cell, ci) => (
                                                            <td key={ci} className="border border-gray-200 p-1 align-top">
                                                              <input
                                                                className="w-full border border-gray-200 rounded px-1 py-0.5 text-[11px] bg-white"
                                                                value={cell}
                                                                onChange={(e) =>
                                                                  update((arr) => {
                                                                    const current = ensureShape(arr[idx] || shaped);
                                                                    const g = current.grid.map((r) => [...r]);
                                                                    g[ri][ci] = e.target.value;
                                                                    arr[idx] = { ...current, grid: g };
                                                                    return arr;
                                                                  })
                                                                }
                                                              />
                                                            </td>
                                                          ))}
                                                        </tr>
                                                      ))}
                                                    </tbody>
                                                  </table>
                                                </div>

                                                <div className="mt-2 flex items-center gap-2">
                                                  <button
                                                    type="button"
                                                    className="px-2 py-1 text-xs bg-red-600 text-white rounded"
                                                    onClick={() => update((arr) => arr.filter((_, i) => i !== idx))}
                                                  >
                                                    Supprimer
                                                  </button>
                                                </div>
                                              </div>
                                            );
                                          })}
                                          <button
                                            type="button"
                                            className="px-3 py-1 text-sm bg-gray-100 border rounded"
                                            onClick={() =>
                                              update((arr) => [
                                                ...arr,
                                                {
                                                  title: '',
                                                  rows: 2,
                                                  columns: 2,
                                                  grid: [
                                                    ['', ''],
                                                    ['', ''],
                                                  ],
                                                  content: '|',
                                                },
                                              ])
                                            }
                                          >
                                            Ajouter un tableau
                                          </button>
                                        </div>
                                      );
                                    })()}
                                    <div className="mt-2 flex items-center gap-2">
                                      <button className="px-3 py-1 bg-blue-600 text-white rounded text-sm" onClick={() => saveSubsection(chapter, section, subsection)}>Enregistrer</button>
                                      <button className="px-3 py-1 bg-gray-200 text-gray-800 rounded text-sm" onClick={() => cancelEdit('subsections', subsection.id)}>Annuler</button>
                                    </div>
                                  </div>
                                ) : (
                                  (editStates.subsections[subsection.id]?.contentOverride || subsection.content) && (
                                    <div className="text-gray-600 leading-relaxed mb-3 space-y-2">
                                      {renderContent(editStates.subsections[subsection.id]?.contentOverride || subsection.content)}
                                    </div>
                                  )
                                )}

                                {/* Images de la sous-section */}
                                {renderImages(editStates.subsections[subsection.id]?.imagesOverride ?? subsection.images)}

                                {/* Tableaux de la sous-section */}
                                {renderTables(editStates.subsections[subsection.id]?.tablesOverride ?? subsection.tables)}
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
                              {isIntro
                                ? `${subsection.order} ${cleanTitle(subsection.title, subsection.order)}`
                                : `${displayChapterNumber}.${subsection.order} ${cleanTitle(subsection.title, subsection.order)}`}
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