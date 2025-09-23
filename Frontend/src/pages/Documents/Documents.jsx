import React, { useState, useEffect } from 'react';
import { Search, Filter, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import DocumentCard from '../../components/DocumentCard';
import Button from '../../System Design/Button';
import bookService from '../../services/bookService';
import authService from '../../services/authService';

const Documents = () => {
  // État pour la recherche
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [nextPage, setNextPage] = useState(null);
  const [previousPage, setPreviousPage] = useState(null);
  const navigate = useNavigate();
  const isAdmin = authService.isAdmin();

  // Charger les documents avec pagination et recherche
  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        const data = await bookService.getAllBooks({ page: currentPage });
        console.log('Données reçues de l\'API:', data);
        console.log('Résultats (data.results):', data.results);
        // L'API retourne une réponse paginée avec structure { count, next, previous, results }
        setDocuments(data.results || []);
        setTotalCount(data.count || 0);
        setNextPage(data.next);
        setPreviousPage(data.previous);
        // Calculer le nombre total de pages
        const pageSize = 10; // Django REST Framework par défaut
        setTotalPages(Math.ceil((data.count || 0) / pageSize));
      } catch (error) {
        console.error('Erreur lors du chargement des documents:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDocuments();
  }, [currentPage]);

  const handleSearch = async () => {
    if (searchQuery.trim() === '') return;
    
    setIsLoading(true);
    setIsSearching(true);
    try {
      const data = await bookService.searchBooks(searchQuery, 1);
      setDocuments(data.results || []);
      setTotalCount(data.count || 0);
      setNextPage(data.next);
      setPreviousPage(data.previous);
      setCurrentPage(1);
      setTotalPages(Math.ceil((data.count || 0) / 10));
    } catch (error) {
      console.error('Erreur lors de la recherche:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Gérer la recherche avec debounce
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (searchQuery.trim() === '') {
        // Si la recherche est vide, recharger tous les documents
        setIsSearching(false);
        const fetchDocuments = async () => {
          setIsLoading(true);
          try {
            const data = await bookService.getAllBooks();
            setDocuments(data.results || []);
            setTotalCount(data.count || 0);
            setNextPage(data.next);
            setPreviousPage(data.previous);
            setCurrentPage(1);
            setTotalPages(Math.ceil((data.count || 0) / 10));
          } catch (error) {
            console.error('Erreur lors du chargement des documents:', error);
          } finally {
            setIsLoading(false);
          }
        };
        fetchDocuments();
      } else {
        // Sinon, effectuer la recherche
        handleSearch();
      }
    }, 300); // 300ms de debounce

    return () => clearTimeout(debounceTimer);
  }, [searchQuery]);

  // Gestionnaires de pagination
  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handleNextPage = () => {
    if (nextPage) {
      setCurrentPage(currentPage + 1);
    }
  };

  // Réinitialiser la recherche
  const handleResetSearch = () => {
    setSearchQuery('');
    setIsSearching(false);
    setCurrentPage(1);
  };

  const handlePreviousPage = () => {
    if (previousPage) {
      setCurrentPage(currentPage - 1);
    }
  };

  // Gestionnaires d'événements
  const handleViewDocument = (docId) => {
    navigate(`/documents/${docId}`);
  };


  const handleDeleteDocument = async (docId) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce document ?')) {
      try {
        await bookService.deleteBook(docId);
        // Mettre à jour la liste des documents après suppression
        setDocuments(documents.filter(doc => doc.id !== docId));
      } catch (error) {
        console.error('Erreur lors de la suppression du document:', error);
      }
    }
  };

  const handleDownloadDocument = async (docOrPdfUrl) => {
    try {
      // Récupérer l'URL du PDF à partir d'une chaîne ou d'un objet document
      let pdfUrl = '';
      if (typeof docOrPdfUrl === 'string') {
        pdfUrl = docOrPdfUrl || '';
      } else if (docOrPdfUrl && typeof docOrPdfUrl === 'object') {
        pdfUrl = docOrPdfUrl.pdf_url || docOrPdfUrl.pdf || '';
      }

      if (!pdfUrl) {
        alert('Le lien du PDF est introuvable');
        return;
      }

      // Construire l'URL complète du PDF
      const fullUrl = pdfUrl.startsWith('http') ? pdfUrl : `${pdfUrl}`;
      
      // Créer un lien temporaire pour le téléchargement
      const link = document.createElement('a');
      link.href = fullUrl;
      link.target = '_blank';
      link.download = (pdfUrl.split('/').pop() || 'document.pdf');
      
      // Ajouter le lien au document, cliquer dessus, puis le supprimer
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      console.log('Téléchargement du PDF initié:', fullUrl);
    } catch (error) {
      console.error('Erreur lors du téléchargement du document:', error);
      alert('Erreur lors du téléchargement du document. Veuillez réessayer.');
    }
  };

  const handleUploadNew = () => {
    navigate('/upload');
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        {/* En-tête avec titre et bouton */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Mes Documents</h1>
            <p className="text-gray-600 text-lg">Gérez et consultez tous vos documents</p>
          </div>
          {isAdmin && (
            <Button 
              variant="primary" 
              className="flex items-center gap-2"
              onClick={handleUploadNew}
            >
              <Plus size={18} />
              Nouveau document
            </Button>
          )}
        </div>

        {/* Barre de recherche et filtres */}
        <div className="mb-8">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="Rechercher un document..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <div className="absolute inset-y-0 right-0 flex items-center pr-3">
              {isSearching ? (
                <button 
                  onClick={handleResetSearch}
                  className="text-red-500 hover:text-red-700 transition-colors"
                  title="Réinitialiser la recherche"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              ) : (
                <button className="text-accent hover:text-accent">
                  <Filter className="h-5 w-5" />
                </button>
              )}
            </div>
          </div>
          
          {/* Indicateur de recherche active */}
          {isSearching && (
            <div className="mt-3 flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Résultats pour "{searchQuery}" : {totalCount} document{totalCount !== 1 ? 's' : ''} trouvé{totalCount !== 1 ? 's' : ''}
              </div>
              <button
                onClick={handleResetSearch}
                className="text-sm text-primary hover:text-primary-700 font-medium"
              >
                Voir tous les documents
              </button>
            </div>
          )}
          
          {/* Filtres rapides */}
          {/* <div className="flex gap-2 mt-4">
            <button className="px-3 py-1.5 text-sm font-medium bg-primary-100 text-primary rounded-md hover:bg-primary-200">
              Tous
            </button>
            <button className="px-3 py-1.5 text-sm font-medium bg-accent-100 text-accent rounded-md hover:bg-accent-200">
              Récents
            </button>
            <button className="px-3 py-1.5 text-sm font-medium bg-success-100 text-success rounded-md hover:bg-success-200">
              Favoris
            </button>
            <button className="px-3 py-1.5 text-sm font-medium bg-warning-100 text-warning rounded-md hover:bg-warning-200">
              Partagés
            </button>
          </div> */}
        </div>

        {/* Liste des documents */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
          </div>
        ) : documents.length > 0 ? (
          <>
            {/* Statistiques des documents */}
            {/* <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-primary-50 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-primary">{documents.length}</div>
                <div className="text-sm text-gray-600">Total documents</div>
              </div>
              <div className="bg-success-50 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-success">
                  {documents.reduce((sum, doc) => sum + (doc.chapters_count || 0), 0)}
                </div>
                <div className="text-sm text-gray-600">Chapitres totaux</div>
              </div>
              <div className="bg-accent-50 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-accent">
                  {Math.floor(documents.reduce((sum, doc) => sum + (doc.file_size || 0), 0) / 1024 / 1024)}
                </div>
                <div className="text-sm text-gray-600">MB utilisés</div>
              </div>
              <div className="bg-warning-50 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-warning">
                  {new Date().toLocaleDateString('fr-FR')}
                </div>
                <div className="text-sm text-gray-600">Dernière mise à jour</div>
              </div>
            </div> */}
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {documents.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  title={doc.title}
                  chapters_count={doc.chapters_count || 0}
                  document={doc}
                  date={doc.created_at ? new Date(doc.created_at).toLocaleDateString('fr-FR') : ''}
                  onView={() => handleViewDocument(doc.id)}
                  onDownload={() => handleDownloadDocument(doc.pdf_url)}
                  onDelete={() => handleDeleteDocument(doc.id)}
                  canDownload={isAdmin}
                />
              ))}
            </div>
            
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center space-x-2 mt-8">
                <Button
                  onClick={handlePreviousPage}
                  disabled={!previousPage}
                  variant="outline"
                  className="flex items-center space-x-2"
                >
                  <span>Précédent</span>
                </Button>
                
                <div className="flex items-center space-x-2">
                  {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                    let pageNum;
                    if (totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (currentPage <= 3) {
                      pageNum = i + 1;
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i;
                    } else {
                      pageNum = currentPage - 2 + i;
                    }
                    
                    return (
                      <Button
                        key={pageNum}
                        onClick={() => handlePageChange(pageNum)}
                        variant={currentPage === pageNum ? "default" : "outline"}
                        className="w-10 h-10"
                      >
                        {pageNum}
                      </Button>
                    );
                  })}
                </div>
                
                <Button
                  onClick={handleNextPage}
                  disabled={!nextPage}
                  variant="outline"
                  className="flex items-center space-x-2"
                >
                  <span>Suivant</span>
                </Button>
              </div>
            )}
            
            {/* Information sur la pagination */}
            {totalCount > 0 && (
              <div className="mt-4 text-center text-sm text-gray-600">
                Affichage de {documents.length} sur {totalCount} documents
                {totalPages > 1 && ` (Page ${currentPage} sur ${totalPages})`}
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-12">
            <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center text-gray-400 mb-4">
              <Search size={32} />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">Aucun document trouvé</h3>
            <p className="text-gray-500">Essayez de modifier vos critères de recherche</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Documents;
