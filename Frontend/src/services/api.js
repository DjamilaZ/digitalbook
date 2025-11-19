import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

// Separate instance for token refresh to avoid interceptor recursion
const refreshApi = axios.create({
  baseURL: '/api/auth',
  withCredentials: true,
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
  async (error) => {
    const originalRequest = error.config || {};
    if (error.response?.status === 401 && !originalRequest._retry) {
      const storedRefresh = sessionStorage.getItem('refresh_token') || localStorage.getItem('refresh_token');
      if (!storedRefresh) {
        // No refresh token, redirect to login
        window.location.href = '/login';
        return Promise.reject(error);
      }
      originalRequest._retry = true;
      try {
        const res = await refreshApi.post('/refresh/', { refresh_token: storedRefresh });
        const newAccess = res?.data?.data?.access_token || res?.data?.access_token;
        const newRefresh = res?.data?.data?.refresh_token || res?.data?.refresh_token;
        const targetStore = sessionStorage.getItem('refresh_token') ? sessionStorage : localStorage;
        if (newAccess) targetStore.setItem('token', newAccess);
        if (newRefresh) targetStore.setItem('refresh_token', newRefresh);
        // Set header and retry
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers['Authorization'] = `Bearer ${newAccess}`;
        return api(originalRequest);
      } catch (e) {
        // On failure, clear and redirect
        try { localStorage.removeItem('token'); } catch (_) {}
        try { localStorage.removeItem('user'); } catch (_) {}
        try { localStorage.removeItem('auth_pref'); } catch (_) {}
        try { localStorage.removeItem('refresh_token'); } catch (_) {}
        try { sessionStorage.removeItem('token'); } catch (_) {}
        try { sessionStorage.removeItem('user'); } catch (_) {}
        try { sessionStorage.removeItem('auth_pref'); } catch (_) {}
        try { sessionStorage.removeItem('refresh_token'); } catch (_) {}
        window.location.href = '/login';
        return Promise.reject(e);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
