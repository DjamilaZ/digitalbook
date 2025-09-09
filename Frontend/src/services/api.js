import axios from 'axios';

// Fonction pour créer une instance d'API avec des en-têtes personnalisés
const createApiInstance = (contentType = 'application/json') => {
  const instance = axios.create({
    baseURL: '/api',
    headers: {
      'Content-Type': contentType,
      'Accept': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    },
    timeout: 30000, // 30 secondes de timeout
    withCredentials: true,
    xsrfCookieName: 'csrftoken',
    xsrfHeaderName: 'X-CSRFToken',
    validateStatus: function (status) {
      return status >= 200 && status < 300;
    }
  });
  
  // Intercepteur pour ajouter le token CSRF et gérer le cache
  instance.interceptors.request.use(config => {
    // Récupérer le token CSRF depuis les cookies
    const csrfToken = document.cookie.split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];
    
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    }
    
    // Ajouter un timestamp pour éviter le cache pour les requêtes GET
    if (config.method?.toLowerCase() === 'get') {
      config.params = config.params || {};
      config.params._t = new Date().getTime();
    }
    
    // Pour les requêtes avec des fichiers, supprimer le Content-Type pour laisser le navigateur le définir
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }
    
    return config;
  });
  
  // Intercepteur de réponse
  instance.interceptors.response.use(
    (response) => {
      // Retourne directement les données de la réponse
      return response.data;
    },
    (error) => {
      // Gestion des erreurs
      if (error.response) {
        // La requête a été faite et le serveur a répondu avec un code d'erreur
        console.error('Erreur de réponse:', {
          status: error.response.status,
          statusText: error.response.statusText,
          url: error.config.url,
          data: error.response.data
        });
      } else if (error.request) {
        // La requête a été faite mais aucune réponse n'a été reçue
        console.error('Aucune réponse du serveur:', error.request);
      } else {
        // Une erreur s'est produite lors de la configuration de la requête
        console.error('Erreur de configuration de la requête:', error.message);
      }
      
      return Promise.reject(error);
    }
  );
  
  return instance;
};

// Instance par défaut pour les requêtes JSON
const api = createApiInstance();

// Instance spécifique pour les requêtes avec des fichiers
const fileApi = createApiInstance('multipart/form-data');

export { api as default, fileApi };
