import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Menu, X, BookOpen, FileText, Loader2, ArrowLeft, Download, RefreshCw, Languages } from 'lucide-react';

import Button from '../../System Design/Button';
import api from '../../services/api';
import authService from '../../services/authService';
import Sidebar from '../../components/DocumentViewer/Sidebar';
import ContentDisplay from '../../components/DocumentViewer/ContentDisplay';
import FullBookContent from '../../components/DocumentViewer/FullBookContent';
import './DocumentViewer.css';

const DocumentViewer = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [bookData, setBookData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('full'); // 'simple' ou 'full' - démarrer en vue complète
  const [selectedItem, setSelectedItem] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const isAdmin = authService.isAdmin();
  const isManager = authService.isManager();
  const [regenLoading, setRegenLoading] = useState(false);
  const [regenError, setRegenError] = useState(null);
  // Traduction désactivée temporairement
  // const [translateLoading, setTranslateLoading] = useState(false);
  // const [translateMessage, setTranslateMessage] = useState(null);

  // const handleTranslateBook = async () => {
  //   try {
  //     setTranslateMessage(null);
  //     setTranslateLoading(true);
  //     await api.post(`/books/${id}/finalize/`, {
  //       target_langs: ['en', 'pt'],
  //     });
  //     setTranslateMessage("Traduction lancée. Le contenu sera disponible progressivement en anglais et portugais.");
  //   } catch (error) {
  //     console.error('Erreur lors du lancement de la traduction du livre:', error);
  //     const msg = error?.response?.data?.error || error?.message || 'Erreur lors du lancement de la traduction';
  //     setTranslateMessage(msg);
  //   } finally {
  //     setTranslateLoading(false);
  //   }
  // };

  const reloadBookData = async () => {
    if (!id) return;
    try {
      // Appeler l'API avec l'URL du livre (l'ID est utilisé comme URL)
      const structure = await api.get(`/books/${id}/export_structure/`);
      setBookData(structure.data);

      // Si rien n'est sélectionné, sélectionner automatiquement le premier chapitre
      if (!selectedItem && structure.data?.chapters?.length > 0) {
        setSelectedItem({
          type: 'chapter',
          data: structure.data.chapters[0],
          index: 0,
        });
      }
    } catch (error) {
      console.error('Erreur lors de la mise à jour des données du livre:', error);
    }
  };

  useEffect(() => {
    const fetchBookData = async () => {
      try {
        setLoading(true);
        await reloadBookData();
      } catch (error) {
        setError('Impossible de charger les données du livre');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchBookData();
    }
  }, [id]);

  const handleSelectContent = (content) => {
    // Passer automatiquement en vue complète lors de la sélection
    setViewMode('full');
    setSelectedItem(content);
    
    // Si c'est la couverture, faire défiler vers l'image
    if (content.type === 'cover') {
      setTimeout(() => {
        const coverImage = document.getElementById('cover-image');
        if (coverImage) {
          coverImage.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    }
  };

  // Regénérer le QCM pour un chapitre donné (utilisé par FullBookContent)
  const regenerateQCMForChapter = async (chapterId) => {
    try {
      setRegenError(null);
      if (!chapterId) return;
      setRegenLoading(true);
      await api.post('/qcms/regenerate-chapter/', { chapter_id: chapterId });
      // Recharger la structure
      const structure = await api.get(`/books/${id}/export_structure/`);
      setBookData(structure.data);
      // Conserver la sélection courante sur le chapitre régénéré
      const updatedChapter = structure.data?.chapters?.find(c => c.id === chapterId);
      if (updatedChapter) {
        setSelectedItem({ type: 'chapter', data: updatedChapter, index: 0 });
      }
    } catch (e) {
      console.error('Erreur lors de la régénération du QCM (par chapitre):', e);
      setRegenError(e?.response?.data?.error || e?.message || 'Erreur lors de la régénération du QCM');
    } finally {
      setRegenLoading(false);
    }
  };

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const handleRegenerateQCM = async () => {
    try {
      setRegenError(null);
      if (!selectedItem || selectedItem.type !== 'chapter') {
        return;
      }
      setRegenLoading(true);
      const chapterId = selectedItem.data?.id;
      if (!chapterId) return;
      await api.post('/qcms/regenerate-chapter/', { chapter_id: chapterId });
      // Recharger la structure
      const structure = await api.get(`/books/${id}/export_structure/`);
      setBookData(structure.data);
      // Conserver la sélection courante avec les données à jour
      const updatedChapter = structure.data?.chapters?.find(c => c.id === chapterId);
      if (updatedChapter) {
        setSelectedItem({ type: 'chapter', data: updatedChapter, index: selectedItem.index });
      }
    } catch (e) {
      console.error('Erreur lors de la régénération du QCM:', e);
      setRegenError(e?.response?.data?.error || e?.message || 'Erreur lors de la régénération du QCM');
    } finally {
      setRegenLoading(false);
    }
  };

  const handleDownloadDocument = async () => {
    try {
      if (!bookData?.book?.pdf_url) {
        console.error('URL du PDF non disponible');
        return;
      }
      
      // Construire l'URL complète du PDF
      const fullUrl = `${bookData.book.pdf_url}`;
      
      // Créer un lien temporaire pour le téléchargement
      const link = document.createElement('a');
      link.href = fullUrl;
      link.target = '_blank';
      link.download = bookData.book.pdf_url.split('/').pop() || 'document.pdf';
      
      // Ajouter le lien au document, cliquer dessus, puis le supprimer
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Erreur lors du téléchargement du document:', error);
    }
  };


  if (loading) {
    return (
      <div className="w-full flex flex-col bg-gray-50 min-h-screen items-center justify-center">
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-gray-600 mt-2">Chargement du document...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full flex flex-col bg-gray-50 min-h-screen items-center justify-center">
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <FileText className="h-16 w-16" />
          <p className="text-red-600 text-lg mb-4">{error}</p>
          <Button onClick={() => navigate('/documents')}>
            Retour aux documents
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col bg-gray-50 min-h-screen">
      {/* Header - Fixe lors du défilement */}
      <div className="bg-white border-b border-gray-200 px-5 py-4 flex items-center justify-between shadow-sm z-100 w-full sticky top-0">
        <div className="flex items-center gap-5 w-full">
          <Button
            variant="outline"
            onClick={() => navigate('/documents')}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 bg-white rounded-md cursor-pointer transition-all duration-200 text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-400 hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Retour
          </Button>
          
          <div className="flex flex-col gap-1 flex-1">
            {bookData?.book && (
              <>
                <h1 className="text-xl font-semibold text-gray-900 leading-tight">{bookData.book.title}</h1>
                <p className="text-xs text-gray-600">
                  Créé le {new Date(bookData.book.created_at).toLocaleDateString()}
                </p>
              </>
            )}
          </div>
        </div>
        
        {/* <button 
          onClick={toggleViewMode}
          className="view-mode-toggle-btn"
          title={viewMode === 'simple' ? "Vue complète" : "Vue simple"}
        >
          {viewMode === 'simple' ? <FileText size={20} /> : <List size={20} />}
        </button> */}
        {isAdmin && (
          <div className="flex items-center gap-2 mr-2">
            {/* Bouton Traduire désactivé temporairement */}
            {/* <button 
              onClick={handleTranslateBook}
              disabled={translateLoading}
              className={`border-none rounded-md px-3 py-2 cursor-pointer transition-all duration-300 text-sm flex items-center gap-2 ${translateLoading ? 'bg-gray-300 text-gray-600' : 'bg-primary text-white hover:bg-primary hover:-translate-y-0.5'}`}
              title="Lancer la traduction du livre"
            >
              {translateLoading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Languages size={16} />
              )}
              <span>Traduire</span>
            </button> */}
            <button 
              onClick={handleDownloadDocument}
              className="bg-success text-white border-none rounded-md px-2 py-2 cursor-pointer transition-all duration-300 hover:bg-success hover:-translate-y-0.5"
              title="Voir le PDF d'origine"
            >
              <Download size={20} />
            </button>
          </div>
        )}
        <button 
          onClick={toggleSidebar}
          className="bg-primary text-white border-none rounded-md px-2 py-2 cursor-pointer transition-all duration-300 hover:bg-primary hover:-translate-y-0.5"
          title={sidebarOpen ? "Masquer le sommaire" : "Afficher le sommaire"}
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Main Content - Layout avec sommaire à gauche et contenu à droite */}
      <div className="flex w-full flex-1">
        {/* Sidebar - toujours visible à gauche et fixe lors du défilement */}
        {sidebarOpen && (
          <div className="w-80 bg-white border-r border-gray-200 flex-shrink-0 sticky top-20 h-screen overflow-y-auto">
            <Sidebar 
              bookData={bookData} 
              onSelectContent={handleSelectContent}
              selectedItem={selectedItem}
            />
          </div>
        )}
        
        {/* Content Area - contenu à droite qui défile */}
        <div className="flex-1 w-full overflow-y-auto">
          {/* Image de couverture et en-tête dans le contenu principal */}
          {bookData?.book && (() => {
            let coverImageUrl = null;
            if (bookData.book.cover_image) {
              try {
                const href = bookData.book.cover_image;
                const path = href.startsWith('http') ? new URL(href).pathname : href;
                const isDev = window.location.port === '3000';
                const origin = isDev
                  ? `${window.location.protocol}//${window.location.hostname}:8017`
                  : `${window.location.protocol}//${window.location.host}`;
                coverImageUrl = path.startsWith('/media/')
                  ? `${origin}${path}`
                  : `${origin}/media/${path.replace(/^\/?/, '')}`;
              } catch (_) {
                coverImageUrl = bookData.book.cover_image;
              }
            }

            return (
              <div className="w-full bg-white">
                {/* En-tête avec titre et informations */}
                <div className="max-w-4xl mx-auto p-6 border-b border-gray-200">
                  <div className="flex flex-col md:flex-row gap-6 items-start">
                    <div className="flex-1">
                      <h1 className="text-3xl font-bold text-gray-900 mb-4">{bookData.book.title}</h1>
                      <div className="text-gray-600 space-y-2">
                        <p>Créé le {new Date(bookData.book.created_at).toLocaleDateString('fr-FR', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}</p>
                        <p>{bookData.chapters?.length || 0} chapitre{bookData.chapters?.length !== 1 ? 's' : ''}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Image de couverture pleine largeur comme un PDF */}
                {coverImageUrl && (
                  <div className="w-full bg-gray-50 py-8">
                    <div className="max-w-4xl mx-auto px-6">
                      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
                        <img
                          id="cover-image"
                          src={coverImageUrl}
                          alt={`Couverture de ${bookData.book.title}`}
                          className="w-full h-auto object-contain"
                          onError={(e) => {
                            console.log('DocumentViewer - Cover image failed to load:', coverImageUrl);
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'flex';
                          }}
                          onLoad={() => {
                            console.log('DocumentViewer - Cover image loaded successfully:', coverImageUrl);
                          }}
                        />
                        <div
                          className="w-full h-96 bg-primary flex items-center justify-center text-white"
                          style={{ display: 'none' }}
                        >
                          <FileText size={64} />
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

          {/* Contenu du livre (chapitres) */}
          {viewMode === 'full' ? (
            <FullBookContent
              bookData={bookData}
              selectedItem={selectedItem}
              isAdmin={isAdmin}
              canEditStructure={isAdmin || isManager}
              onRegenerateChapter={regenerateQCMForChapter}
              regenLoading={regenLoading}
              onBookContentChanged={reloadBookData}
            />
          ) : selectedItem ? (
            <ContentDisplay selectedItem={selectedItem} bookData={bookData} />
          ) : (
            <div className="flex flex-col items-center justify-center p-12 text-center">
              <BookOpen size={48} className="text-gray-400 mb-4" />
              <h2 className="text-2xl font-semibold text-gray-800 mb-2">Bienvenue dans le Document Viewer</h2>
              <p className="text-gray-600 mb-4">
                Sélectionnez un chapitre, une section ou une sous-section dans le sommaire pour afficher son contenu.
              </p>
              <p className="text-sm text-gray-500">
                Ou cliquez sur <FileText size={16} /> pour afficher tout le livre avec la hiérarchie complète.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DocumentViewer;