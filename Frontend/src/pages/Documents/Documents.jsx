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
  const navigate = useNavigate();

  // Charger les documents au montage du composant
  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        const data = await bookService.getAllBooks();
        setDocuments(data);
      } catch (error) {
        console.error('Erreur lors du chargement des documents:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDocuments();
  }, []);

  // Filtrer les documents en fonction de la recherche
  const filteredDocuments = documents.filter(doc =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Gestionnaires d'événements
  const handleViewDocument = (docId) => {
    navigate(`/documents/${docId}`);
  };

  const handleAnalyzeDocument = async (docId) => {
    try {
      await bookService.analyzeBook(docId);
      // Rafraîchir la liste des documents après analyse
      const updatedDocs = await bookService.getAllBooks();
      setDocuments(updatedDocs);
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
            <h1 className="text-2xl font-bold text-gray-900">Mes Documents</h1>
            <p className="text-gray-500">Gérez et consultez tous vos documents</p>
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
        ) : filteredDocuments.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredDocuments.map((doc) => (
              <DocumentCard
                key={doc.id}
                title={doc.title}
                date={new Date(doc.created_at).toLocaleDateString()}
                sections={doc.chapters?.reduce((acc, chapter) => acc + (chapter.sections?.length || 0), 0) || 0}
                onView={() => handleViewDocument(doc.id)}
                onAnalyze={() => handleAnalyzeDocument(doc.id)}
                onDelete={() => handleDeleteDocument(doc.id)}
              />
            ))}
          </div>
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
