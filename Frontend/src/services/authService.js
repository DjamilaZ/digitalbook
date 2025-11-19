import api from './api';
import axios from 'axios';

const BASE_URL = '/api/auth';

// Instance axios dédiée pour l'authentification
const authApi = axios.create({
  baseURL: BASE_URL,
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

// Storage preference key: 'local' or 'session'
const AUTH_PREF_KEY = 'auth_pref';

function getPreferredStorage() {
  const s = sessionStorage.getItem(AUTH_PREF_KEY);
  if (s === 'session') return 'session';
  const l = localStorage.getItem(AUTH_PREF_KEY);
  if (l === 'local') return 'local';
  return null;
}

function getStoreByPref(pref) {
  return pref === 'session' ? sessionStorage : localStorage;
}

function getActiveStore() {
  const pref = getPreferredStorage();
  if (pref) return getStoreByPref(pref);
  // Fallback: prefer session if it already has auth data
  if (
    sessionStorage.getItem('token') ||
    sessionStorage.getItem('user') ||
    sessionStorage.getItem('refresh_token') ||
    sessionStorage.getItem('session_token')
  ) {
    return sessionStorage;
  }
  return localStorage;
}

function getItemAny(key) {
  return sessionStorage.getItem(key) || localStorage.getItem(key);
}

function removeFromBoth(key) {
  try { sessionStorage.removeItem(key); } catch (_) {}
  try { localStorage.removeItem(key); } catch (_) {}
}

// Intercepteur pour ajouter le header CSRF aux requêtes non-sûres
authApi.interceptors.request.use(
  async (config) => {
    const method = (config.method || 'get').toLowerCase();
    const needsCsrf = ['post', 'put', 'patch', 'delete'].includes(method);
    if (needsCsrf) {
      config.withCredentials = true;
      let csrfToken = getCookie('csrftoken');
      if (!csrfToken) {
        try {
          await authApi.get('/csrf/', { withCredentials: true });
          csrfToken = getCookie('csrftoken');
        } catch (e) {
          // Ignorer: le backend refusera sans le header
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

class AuthService {
  // Login user
  async login(email, password, remember = false) {
    try {
      // Assurer que le cookie CSRF (csrftoken) est présent côté client
      await authApi.get('/csrf/');

      const response = await authApi.post('/login/', { email, password });

      const data = response?.data || {};
      const user = data.user;
      const accessToken = data.access_token ?? data.access;
      const refreshToken = data.refresh_token ?? data.refresh;
      const sessionToken = data.session_token;

      if (user) {
        // Choisir l'emplacement de stockage selon "Se souvenir de moi"
        const pref = remember ? 'local' : 'session';
        // Nettoyer les clés précédentes pour éviter les incohérences
        ['user', 'token', 'refresh_token', 'session_token', AUTH_PREF_KEY].forEach(removeFromBoth);
        // Enregistrer la préférence dans le store choisi
        getStoreByPref(pref).setItem(AUTH_PREF_KEY, pref);

        // Stocker les informations utilisateur et tokens
        this.setUserData(user, pref);
        if (accessToken) this.setToken(accessToken, pref);
        if (refreshToken) getStoreByPref(pref).setItem('refresh_token', refreshToken);
        if (sessionToken) getStoreByPref(pref).setItem('session_token', sessionToken);

        return data;
      }

      throw new Error('Réponse invalide du serveur');
    } catch (error) {
      console.error('Erreur de connexion:', error);
      throw error;
    }
  }

  // Stocker les données utilisateur
  setUserData(userData, preferStorage = null) {
    const store = preferStorage ? getStoreByPref(preferStorage) : getActiveStore();
    store.setItem('user', JSON.stringify(userData));
  }

  // Stocker le token
  setToken(token, preferStorage = null) {
    const store = preferStorage ? getStoreByPref(preferStorage) : getActiveStore();
    store.setItem('token', token);
  }

  // Récupérer les données utilisateur
  getUserData() {
    const active = getActiveStore();
    const userStr = active.getItem('user') || getItemAny('user');
    return userStr ? JSON.parse(userStr) : null;
  }

  // Récupérer le token
  getToken() {
    const active = getActiveStore();
    return active.getItem('token') || getItemAny('token');
  }

  // Vérifier si l'utilisateur est connecté
  isAuthenticated() {
    const token = this.getToken();
    const sessionToken = sessionStorage.getItem('session_token') || localStorage.getItem('session_token');
    const user = this.getUserData();
    // Considérer l'utilisateur authentifié si l'une des preuves est présente :
    // - access_token (JWT)
    // - session_token (session côté serveur)
    // - user stocké (sera validé par validateToken ensuite)
    return !!(token || sessionToken || user);
  }

  // Déconnexion
  async logout() {
    try {
      const sessionToken = localStorage.getItem('session_token');
      const sessionTokenSess = sessionStorage.getItem('session_token');
      // S'assurer que le cookie CSRF est présent
      let csrf = getCookie('csrftoken');
      if (!csrf) {
        try { await authApi.get('/csrf/', { withCredentials: true }); } catch (_) {}
      }
      try {
        await authApi.post('/logout/', (sessionToken || sessionTokenSess) ? { session_token: sessionToken || sessionTokenSess } : {});
      } catch (err) {
        // Si échec CSRF, tenter une fois de récupérer puis rejouer
        const status = err?.response?.status;
        const detail = err?.response?.data?.detail || '';
        if (status === 403 || /CSRF/i.test(detail)) {
          try {
            await authApi.get('/csrf/', { withCredentials: true });
            await authApi.post('/logout/', (sessionToken || sessionTokenSess) ? { session_token: sessionToken || sessionTokenSess } : {});
          } catch (e2) {
            throw err;
          }
        } else {
          throw err;
        }
      }
    } catch (error) {
      console.error('Erreur lors de la déconnexion:', error);
    } finally {
      // Nettoyer le localStorage même si la requête échoue
      ['user', 'token', 'refresh_token', 'session_token', AUTH_PREF_KEY].forEach((k) => {
        try { localStorage.removeItem(k); } catch (_) {}
        try { sessionStorage.removeItem(k); } catch (_) {}
      });
    }
  }

  // Récupérer le rôle de l'utilisateur
  getUserRole() {
    const user = this.getUserData();
    return user?.role?.name || user?.role_name || null;
  }

  // Vérifier si l'utilisateur est administrateur
  isAdmin() {
    const user = this.getUserData();
    const role = (user?.role?.name || user?.role_name || '').toString().toLowerCase();
    // Supporte différents indicateurs d'admin
    if (role === 'admin' || role === 'administrator') return true;
    if (user?.is_superuser === true || user?.is_staff === true) return true;
    return false;
  }

  // Vérifier si l'utilisateur est manager
  isManager() {
    const user = this.getUserData();
    const role = (user?.role?.name || user?.role_name || '').toString().toLowerCase();
    return role === 'manager';
  }

  // Récupérer le nom complet de l'utilisateur
  getUserName() {
    const user = this.getUserData();
    if (user?.first_name && user?.last_name) {
      return `${user.first_name} ${user.last_name}`;
    }
    return user?.username || user?.email || '';
  }

  // Demander un email de réinitialisation de mot de passe
  async requestPasswordReset(email) {
    try {
      const res = await api.post('/users/request-password-reset/', { email });
      return res.data;
    } catch (error) {
      console.error('Erreur lors de la demande de reset password:', error);
      throw error;
    }
  }

  // Réinitialiser le mot de passe avec un token
  async resetPassword(token, newPassword) {
    try {
      const res = await api.post('/users/reset-password/', { token, newPassword });
      return res.data;
    } catch (error) {
      console.error('Erreur lors du reset password:', error);
      throw error;
    }
  }

  // Changer le mot de passe (utilisateur connecté)
  async changePassword(oldPassword, newPassword) {
    try {
      const res = await api.post('/users/change-password/', { oldPassword, newPassword });
      return res.data;
    } catch (error) {
      console.error('Erreur lors du changement de mot de passe:', error);
      throw error;
    }
  }

  // Rafraîchir le token
  async refreshToken() {
    try {
      const refreshToken = sessionStorage.getItem('refresh_token') || localStorage.getItem('refresh_token');
      if (!refreshToken) {
        throw new Error('Pas de refresh token disponible');
      }

      // Endpoint backend: /api/auth/refresh/ (retourne { message, data: { access_token, refresh_token } })
      const response = await authApi.post('/refresh/', { refresh_token: refreshToken });

      const newAccess = response?.data?.data?.access_token ?? response?.data?.access_token;
      const newRefresh = response?.data?.data?.refresh_token ?? response?.data?.refresh_token;

      // Écrire de préférence dans le même store que la source du refresh token
      const targetStore = sessionStorage.getItem('refresh_token') ? sessionStorage : getActiveStore();
      if (newAccess) targetStore.setItem('token', newAccess);
      if (newRefresh) targetStore.setItem('refresh_token', newRefresh);
      if (newAccess) return newAccess;

      throw new Error('Réponse invalide du serveur');
    } catch (error) {
      console.error('Erreur lors du rafraîchissement du token:', error);
      // En cas d'échec, déconnecter l'utilisateur
      this.logout();
      throw error;
    }
  }

  // Récupérer le profil utilisateur
  async getUserProfile() {
    try {
      const response = await api.get('/auth/profile/');
      if (response.data) {
        this.setUserData(response.data);
        return response.data;
      }
      throw new Error('Réponse invalide du serveur');
    } catch (error) {
      console.error('Erreur lors de la récupération du profil:', error);
      throw error;
    }
  }

  // Vérifier si le token est valide
  async validateToken() {
    try {
      // Endpoint backend: GET /api/auth/validate-token/
      await api.get('/auth/validate-token/');
      return true;
    } catch (error) {
      console.error('Erreur lors de la validation du token:', error);
      return false;
    }
  }
}

export default new AuthService();
