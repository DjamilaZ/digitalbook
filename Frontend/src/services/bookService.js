import api, { fileApi } from './api';

const bookService = {
  // Récupérer tous les livres
  getAllBooks: async () => {
    try {
      return await api.get('/books/');
    } catch (error) {
      console.error('Erreur lors de la récupération des livres:', error);
      throw error;
    }
  },

  // Récupérer un livre par son ID
  getBookById: async (id) => {
    try {
      return await api.get(`/books/${id}/`);
    } catch (error) {
      console.error(`Erreur lors de la récupération du livre ${id}:`, error);
      throw error;
    }
  },

  // Créer un nouveau livre
  createBook: async (bookData) => {
    try {
      // Créer un objet FormData pour envoyer les données du formulaire
      const formData = new FormData();
      
      // Ajouter le titre s'il est défini
      if (bookData.title) {
        formData.append('title', bookData.title);
      }
      
      // Ajouter le fichier PDF s'il est défini
      if (bookData.pdf_file) {
        formData.append('pdf_file', bookData.pdf_file);
      }
      
      // Utiliser fileApi pour les requêtes avec des fichiers
      return await fileApi.post('/books/', formData);
    } catch (error) {
      console.error('Erreur lors de la création du livre:', error);
      throw error;
    }
  },

  // Mettre à jour un livre
  updateBook: async (id, bookData) => {
    try {
      return await api.patch(`/books/${id}/`, bookData);
    } catch (error) {
      console.error(`Erreur lors de la mise à jour du livre ${id}:`, error);
      throw error;
    }
  },

  // Supprimer un livre
  deleteBook: async (id) => {
    try {
      return await api.delete(`/books/${id}/`);
    } catch (error) {
      console.error(`Erreur lors de la suppression du livre ${id}:`, error);
      throw error;
    }
  },

  // Analyser un livre (si vous avez un endpoint spécifique pour l'analyse)
  analyzeBook: async (id) => {
    try {
      return await api.post(`/books/${id}/analyze/`);
    } catch (error) {
      console.error(`Erreur lors de l'analyse du livre ${id}:`, error);
      throw error;
    }
  },
};

export default bookService;
