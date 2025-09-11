import React, { useState, useEffect } from 'react';
import { Search, Filter, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import DocumentCard from '../../components/DocumentCard';
import Button from '../../System Design/Button';
import bookService from '../../services/bookService';

const Documents = () => {
  // État pour la recherche
  const [searchQuery, setSearchQuery] = useState('');
  
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [nextPage, setNextPage] = useState(null);
  const [previousPage, setPreviousPage] = useState(null);
  const navigate = useNavigate();

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

  // Gérer la recherche avec debounce
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (searchQuery.trim() === '') {
        // Si la recherche est vide, recharger tous les documents
        setCurrentPage(1);
        const fetchDocuments = async () => {
          try {
            const data = await bookService.getAllBooks({ page: 1 });
            setDocuments(data.results || []);
            setTotalCount(data.count || 0);
            setNextPage(data.next);
            setPreviousPage(data.previous);
            setTotalPages(Math.ceil((data.count || 0) / 10));
          } catch (error) {
            console.error('Erreur lors du chargement des documents:', error);
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

  const handleSearch = async () => {
    if (searchQuery.trim() === '') return;
    
    setIsLoading(true);
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

  // Gestionnaires de pagination
  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handleNextPage = () => {
    if (nextPage) {
      setCurrentPage(currentPage + 1);
    }
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

  const handleAnalyzeDocument = async (docId) => {
    try {
      await bookService.analyzeBook(docId);
      // Rafraîchir la liste des documents après analyse
      const updatedDocs = await bookService.getAllBooks();
      setDocuments(updatedDocs.results || []);
    } catch (error) {
      console.error('Erreur lors de l\'analyse du document:', error);
    }
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
          <Button 
            variant="primary" 
            className="flex items-center gap-2"
            onClick={handleUploadNew}
          >
            <Plus size={18} />
            Nouveau document
          </Button>
        </div>

        {/* Barre de recherche et filtres */}
        <div className="mb-8">
          <div className="relative max-w-xl">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Rechercher un document..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <div className="absolute inset-y-0 right-0 flex items-center pr-3">
              <button className="text-gray-400 hover:text-gray-500">
                <Filter className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Liste des documents */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : documents.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {documents.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  title={doc.title}
                  sections={doc.sections}
                  document={doc}
                  onView={() => handleViewDocument(doc.id)}
                  onAnalyze={() => handleAnalyzeDocument(doc.id)}
                />
              ))}
            </div>
            
            {/* Contrôles de pagination */}
            {totalPages > 1 && (
              <div className="mt-8 flex justify-center items-center space-x-4">
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
