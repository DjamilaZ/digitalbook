import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

// Utility to read a cookie value by name from document.cookie
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return undefined;
}

// Intercepteur pour ajouter le token JWT à chaque requête
api.interceptors.request.use(
  async (config) => {
    // 1) Joindre le token JWT si présent
    const token = sessionStorage.getItem('token') || localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 2) S'assurer d'envoyer le header CSRF pour les requêtes non sûres
    const method = (config.method || 'get').toLowerCase();
    const needsCsrf = ['post', 'put', 'patch', 'delete'].includes(method);
    if (needsCsrf) {
      // Toujours envoyer les cookies
      config.withCredentials = true;

      let csrfToken = getCookie('csrftoken');
      // Si pas de cookie CSRF, tenter de le récupérer depuis le backend
      if (!csrfToken) {
        try {
          // Appel idempotent qui pose le cookie csrftoken côté client
          await api.get('/auth/csrf/', { withCredentials: true });
          csrfToken = getCookie('csrftoken');
        } catch (e) {
          // On ignore l'erreur ici; le backend refusera sans le header
        }
      }

      if (csrfToken && !config.headers['X-CSRFToken']) {
        config.headers['X-CSRFToken'] = csrfToken;
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Intercepteur pour gérer les erreurs d'authentification
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token invalide ou expiré
      try { localStorage.removeItem('token'); } catch (e) {}
      try { localStorage.removeItem('user'); } catch (e) {}
      try { localStorage.removeItem('auth_pref'); } catch (e) {}
      try { sessionStorage.removeItem('token'); } catch (e) {}
      try { sessionStorage.removeItem('user'); } catch (e) {}
      try { sessionStorage.removeItem('auth_pref'); } catch (e) {}
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
