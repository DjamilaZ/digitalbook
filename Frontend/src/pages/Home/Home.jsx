import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../../System Design/Button";
import FeatureCard from "../../System Design/FeatureCard";
import DocumentItem from "../../System Design/DocumentItem";
import { Search, FileText, BookOpen } from "lucide-react";
import bookService from "../../services/bookService";
import authService from "../../services/authService";

const Home = () => {
  const navigate = useNavigate();
  const [recentDocuments, setRecentDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const isAdmin = authService.isAdmin();

  // Charger les documents récents
  useEffect(() => {
    const fetchRecentDocuments = async () => {
      try {
        setIsLoading(true);
        const response = await bookService.getRecentBooks();
        setRecentDocuments(response.results || []);
        setError(null);
      } catch (err) {
        console.error('Erreur lors du chargement des documents récents:', err);
        setError('Impossible de charger les documents récents');
        setRecentDocuments([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchRecentDocuments();
  }, []);

  // Gestionnaires d'événements
  const handleUploadNew = () => {
    navigate('/upload');
  };

  const handleViewLibrary = () => {
    navigate('/documents');
  };

  const handleViewDocument = (docId) => {
    console.log(docId);
    navigate(`/documents/${docId}`);
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto">
      {/* Hero */}
      <div className="bg-primary-50 rounded-xl p-10 text-center">
        <h1 className="text-3xl font-bold mb-4">
          Lisez vos Book <span className="text-primary">intelligemment</span>
        </h1>
        <p className="text-gray-600 mb-6">
          Transformez vos documents PDF en expérience de lecture interactive avec sommaire automatique et navigation fluide.
        </p>
        <div className="flex justify-center gap-4">
          {isAdmin && (
            <Button variant="primary" onClick={handleUploadNew}>Télécharger un PDF</Button>
          )}
          <Button variant="accent" onClick={handleViewLibrary}>Voir ma bibliothèque</Button>
        </div>
      </div>

      {/* Features */}
      <h2 className="text-xl font-bold mt-12 mb-6 text-center">
        Une expérience de lecture révolutionnaire
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <FeatureCard icon={<Search size={24} />} title="Analyse Automatique" description="Notre IA extrait automatiquement le sommaire et structure le contenu." />
        <FeatureCard icon={<BookOpen size={24} />} title="Navigation Intelligente" description="Naviguez facilement grâce au sommaire interactif et liens rapides." />
        <FeatureCard icon={<FileText size={24} />} title="Interface Moderne" description="Design épuré et ergonomique, optimisé pour tous vos appareils." />
      </div>
      
      {/* Statistiques */}
      <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-success-50 border border-success-200 rounded-xl p-6 text-center">
          <div className="text-3xl font-bold text-success mb-2">100%</div>
          <div className="text-sm text-success-700">Analyse automatique</div>
        </div>
        <div className="bg-accent-50 border border-accent-200 rounded-xl p-6 text-center">
          <div className="text-3xl font-bold text-accent mb-2">24/7</div>
          <div className="text-sm text-accent-700">Disponibilité</div>
        </div>
        <div className="bg-warning-50 border border-warning-200 rounded-xl p-6 text-center">
          <div className="text-3xl font-bold text-warning mb-2">∞</div>
          <div className="text-sm text-warning-700">Documents stockés</div>
        </div>
      </div>

      {/* Documents récents */}
      <div className="mt-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Documents Récents</h2>
          <button 
            className="text-primary hover:text-primary text-sm"
            onClick={handleViewLibrary}
          >
            Voir tout →
          </button>
        </div>
        
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
          </div>
        ) : error ? (
          <div className="text-center py-8 text-gray-500">
            <p>{error}</p>
          </div>
        ) : recentDocuments.length > 0 ? (
          <div className="flex flex-col gap-4">
            {recentDocuments.map((doc) => (
              <DocumentItem 
                key={doc.id}
                title={doc.title}
                date={new Date(doc.created_at).toLocaleDateString('fr-FR')}
                sections={doc.sections_count || 0}
                onClick={() => handleViewDocument(doc.id)}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>Aucun document récent trouvé</p>
            {isAdmin ? (
              <Button 
                variant="outline" 
                className="mt-4"
                onClick={handleUploadNew}
              >
                Télécharger votre premier document
              </Button>
            ) : (
              <Button 
                variant="accent" 
                className="mt-4"
                onClick={handleViewLibrary}
              >
                Voir ma bibliothèque
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Home;
