import api from './api';
import axios from 'axios';

const BASE_URL = 'http://localhost:8000/api/auth';

// Instance axios dédiée pour l'authentification
const authApi = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

class AuthService {
  // Login user
  async login(email, password) {
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
        // Stocker les informations utilisateur
        this.setUserData(user);

        // Stocker les tokens si présents
        if (accessToken) this.setToken(accessToken);
        if (refreshToken) localStorage.setItem('refresh_token', refreshToken);
        if (sessionToken) localStorage.setItem('session_token', sessionToken);

        return data;
      }

      throw new Error('Réponse invalide du serveur');
    } catch (error) {
      console.error('Erreur de connexion:', error);
      throw error;
    }
  }

  // Stocker les données utilisateur
  setUserData(userData) {
    localStorage.setItem('user', JSON.stringify(userData));
  }

  // Stocker le token
  setToken(token) {
    localStorage.setItem('token', token);
  }

  // Récupérer les données utilisateur
  getUserData() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }

  // Récupérer le token
  getToken() {
    return localStorage.getItem('token');
  }

  // Vérifier si l'utilisateur est connecté
  isAuthenticated() {
    const token = this.getToken();
    const sessionToken = localStorage.getItem('session_token');
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
      await authApi.post('/logout/', sessionToken ? { session_token: sessionToken } : {});
    } catch (error) {
      console.error('Erreur lors de la déconnexion:', error);
    } finally {
      // Nettoyer le localStorage même si la requête échoue
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('session_token');
    }
  }

  // Récupérer le rôle de l'utilisateur
  getUserRole() {
    const user = this.getUserData();
    return user?.role?.name || null;
  }

  // Récupérer le nom complet de l'utilisateur
  getUserName() {
    const user = this.getUserData();
    if (user?.first_name && user?.last_name) {
      return `${user.first_name} ${user.last_name}`;
    }
    return user?.username || user?.email || '';
  }

  // Rafraîchir le token
  async refreshToken() {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        throw new Error('Pas de refresh token disponible');
      }

      // Endpoint backend: /api/auth/refresh/ (retourne { message, data: { access_token, refresh_token } })
      const response = await authApi.post('/refresh/', { refresh_token: refreshToken });

      const newAccess = response?.data?.data?.access_token ?? response?.data?.access_token;
      const newRefresh = response?.data?.data?.refresh_token ?? response?.data?.refresh_token;

      if (newAccess) this.setToken(newAccess);
      if (newRefresh) localStorage.setItem('refresh_token', newRefresh);
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
