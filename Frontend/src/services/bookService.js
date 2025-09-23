import api from './api';

const bookService = {
  // Récupérer tous les livres
  getAllBooks: async (params = {}) => {
    try {
      const response = await api.get('/books/', { params });
      console.log('Réponse axios complète:', response);
      console.log('Données de la réponse:', response.data);
      return response.data;
    } catch (error) {
      console.error('Erreur lors de la récupération des livres:', error);
      throw error;
    }
  },

  // Rechercher des livres
  searchBooks: async (query, page = 1) => {
    try {
      const params = {
        q: query,
        page: page
      };
      const response = await api.get('/books/search/', { params });
      return response.data;
    } catch (error) {
      console.error('Erreur lors de la recherche des livres:', error);
      throw error;
    }
  },

  // Récupérer un livre par son ID
  getBookById: async (id) => {
    try {
      const response = await api.get(`/books/${id}/`);
      return response.data;
    } catch (error) {
      console.error(`Erreur lors de la récupération du livre ${id}:`, error);
      throw error;
    }
  },

  // Créer un nouveau livre
  createBook: async (bookData) => {
    try {
      let formData;
      
      // Si bookData est déjà un FormData, l'utiliser directement
      if (bookData instanceof FormData) {
        formData = bookData;
      } else {
        // Sinon, créer un objet FormData pour envoyer les données du formulaire
        formData = new FormData();
        
        // Ajouter le titre s'il est défini
        if (bookData.title) {
          formData.append('title', bookData.title);
        }
        
        // Ajouter le fichier PDF s'il est défini
        if (bookData.pdf_file) {
          formData.append('pdf_file', bookData.pdf_file);
        }
        
        // Ajouter le fichier JSON de structure s'il est défini
        if (bookData.json_structure_file) {
          formData.append('json_structure_file', bookData.json_structure_file);
        }
      }
      
      // Utiliser api pour les requêtes avec des fichiers
      const response = await api.post('/books/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    } catch (error) {
      console.error('Erreur lors de la création du livre:', error);
      throw error;
    }
  },

  // Mettre à jour un livre
  updateBook: async (id, bookData) => {
    try {
      const response = await api.patch(`/books/${id}/`, bookData);
      return response.data;
    } catch (error) {
      console.error(`Erreur lors de la mise à jour du livre ${id}:`, error);
      throw error;
    }
  },

  // Supprimer un livre
  deleteBook: async (id) => {
    try {
      const response = await api.delete(`/books/${id}/`);
      return response.data;
    } catch (error) {
      console.error(`Erreur lors de la suppression du livre ${id}:`, error);
      throw error;
    }
  },

  // Récupérer les livres récents (créés dans les 7 derniers jours)
  getRecentBooks: async () => {
    try {
      const response = await api.get('/books/recent/');
      return response.data;
    } catch (error) {
      console.error('Erreur lors de la récupération des livres récents:', error);
      throw error;
    }
  },

  // Analyser un livre (si vous avez un endpoint spécifique pour l'analyse)
  analyzeBook: async (id) => {
    try {
      const response = await api.post(`/books/${id}/analyze/`);
      return response.data;
    } catch (error) {
      console.error(`Erreur lors de l'analyse du livre ${id}:`, error);
      throw error;
    }
  },
};

export default bookService;
