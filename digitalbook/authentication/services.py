import requests
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import CustomUser, UserSession

logger = logging.getLogger(__name__)


class ExternalAPIService:
    """Service pour communiquer avec l'API externe d'authentification"""
    
    def __init__(self):
        self.base_url = 'https://total-cms.worldws.pro/api'
        self.timeout = 30
        
    def _make_request(self, method, endpoint, data=None, headers=None):
        """Méthode générique pour faire des requêtes à l'API externe"""
        url = f"{self.base_url}{endpoint}"
        
        default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'DigitalBook/1.0'
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            logger.info(f"Requête {method} vers {url}")
            logger.debug(f"Données: {data}")
            logger.debug(f"Headers: {default_headers}")
            
            response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=default_headers,
                timeout=self.timeout
            )
            
            logger.info(f"Réponse status: {response.status_code}")
            logger.debug(f"Réponse data: {response.text}")
            
            # Essayer de parser la réponse JSON
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {'raw_response': response.text}
            
            return response.status_code, response_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur de requête vers {url}: {str(e)}")
            raise Exception(f"Impossible de contacter l'API externe: {str(e)}")
    
    def login(self, email, password, login_source='web'):
        """Authentifie l'utilisateur via l'API externe"""
        endpoint = '/users/login'
        data = {
            'email': email,
            'password': password,
            'loginSource': login_source
        }
        
        status_code, response_data = self._make_request('POST', endpoint, data)
        
        if status_code == 200:
            return {
                'success': True,
                'data': response_data
            }
        else:
            error_message = response_data.get('message', 'Erreur lors de la connexion')
            return {
                'success': False,
                'error': error_message,
                'status_code': status_code
            }
    
    def refresh_token(self, refresh_token):
        """Rafraîchit le token d'accès"""
        endpoint = '/users/refresh'
        data = {
            'refreshToken': refresh_token
        }
        
        status_code, response_data = self._make_request('POST', endpoint, data)
        
        if status_code == 200:
            return {
                'success': True,
                'data': response_data
            }
        else:
            return {
                'success': False,
                'error': response_data.get('message', 'Erreur lors du rafraîchissement du token'),
                'status_code': status_code
            }

    def request_password_reset(self, email: str):
        """Demande l'envoi d'un email de réinitialisation de mot de passe"""
        endpoint = '/users/request-password-reset'
        data = { 'email': email }
        status_code, response_data = self._make_request('POST', endpoint, data)
        return {
            'success': status_code == 200,
            'data': response_data,
            'status_code': status_code,
            'error': None if status_code == 200 else response_data.get('message', 'Erreur lors de la demande de réinitialisation')
        }

    def reset_password(self, token: str, new_password: str):
        """Réinitialise le mot de passe à partir d'un token reçu par email"""
        endpoint = '/users/reset-password'
        data = { 'token': token, 'newPassword': new_password }
        status_code, response_data = self._make_request('POST', endpoint, data)
        return {
            'success': status_code == 200,
            'data': response_data,
            'status_code': status_code,
            'error': None if status_code == 200 else response_data.get('message', 'Erreur lors de la réinitialisation du mot de passe')
        }

    def change_password(self, access_token: str, old_password: str, new_password: str):
        """Change le mot de passe de l'utilisateur authentifié"""
        endpoint = '/users/change-password'
        headers = { 'Authorization': f'Bearer {access_token}' }
        data = { 'oldPassword': old_password, 'newPassword': new_password }
        status_code, response_data = self._make_request('POST', endpoint, data, headers=headers)
        return {
            'success': status_code == 200,
            'data': response_data,
            'status_code': status_code,
            'error': None if status_code == 200 else response_data.get('message', 'Erreur lors du changement de mot de passe')
        }
    
    def get_user_info(self, access_token):
        """Récupère les informations utilisateur avec le token d'accès"""
        endpoint = '/users/me'
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        status_code, response_data = self._make_request('GET', endpoint, headers=headers)
        
        if status_code == 200:
            return {
                'success': True,
                'data': response_data
            }
        else:
            return {
                'success': False,
                'error': response_data.get('message', 'Erreur lors de la récupération des informations utilisateur'),
                'status_code': status_code
            }


class AuthService:
    """Service d'authentification principal"""
    
    def __init__(self):
        self.external_api = ExternalAPIService()
    
    def authenticate_user(self, email, password):
        """Authentifie un utilisateur et crée/met à jour le compte local"""
        try:
            # Appel à l'API externe
            auth_result = self.external_api.login(email, password)
            
            if not auth_result['success']:
                return {
                    'success': False,
                    'error': auth_result['error'],
                    'status_code': auth_result.get('status_code', 400)
                }
            
            # Extraction des données de la réponse
            response_data = auth_result['data']
            user_data = response_data.get('user', {})
            access_token = response_data.get('token')
            refresh_token = response_data.get('refreshToken')
            
            if not user_data or not user_data.get('email'):
                return {
                    'success': False,
                    'error': 'Réponse invalide de l\'API externe',
                    'status_code': 500
                }
            
            # Création ou mise à jour de l'utilisateur local
            user, created = CustomUser.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'username': user_data.get('username', user_data['email']),
                    'is_external_user': True,
                    'is_active': True,
                }
            )
            
            # Mise à jour des données utilisateur
            user.update_from_external_data(user_data)
            
            # Mise à jour des tokens
            if access_token:
                # Par défaut, le token expire en 24 heures (à ajuster selon l'API)
                user.update_tokens(access_token, refresh_token, expires_in=86400)
            
            logger.info(f"Utilisateur {user.email} authentifié avec succès (créé: {created})")
            
            return {
                'success': True,
                'user': user,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'created': created
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'authentification: {str(e)}")
            return {
                'success': False,
                'error': 'Erreur interne du serveur',
                'status_code': 500
            }
    
    def refresh_user_token(self, user):
        """Rafraîchit le token d'un utilisateur"""
        if not user.refresh_token:
            return {
                'success': False,
                'error': 'Pas de refresh token disponible'
            }
        
        try:
            refresh_result = self.external_api.refresh_token(user.refresh_token)
            
            if not refresh_result['success']:
                return {
                    'success': False,
                    'error': refresh_result['error']
                }
            
            response_data = refresh_result['data']
            access_token = response_data.get('token')
            refresh_token = response_data.get('refreshToken')
            
            # Mise à jour des tokens
            user.update_tokens(access_token, refresh_token, expires_in=86400)
            
            return {
                'success': True,
                'access_token': access_token,
                'refresh_token': refresh_token
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement du token: {str(e)}")
            return {
                'success': False,
                'error': 'Erreur lors du rafraîchissement du token'
            }
    
    def create_user_session(self, user, request):
        """Crée une session utilisateur"""
        import uuid
        
        session_token = str(uuid.uuid4())
        
        session = UserSession.objects.create(
            user=user,
            session_token=session_token,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return session_token
    
    def _get_client_ip(self, request):
        """Récupère l'IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def logout_user(self, user, session_token=None):
        """Déconnecte un utilisateur"""
        if session_token:
            # Désactiver la session spécifique
            try:
                session = UserSession.objects.get(
                    user=user,
                    session_token=session_token,
                    is_active=True
                )
                session.is_active = False
                session.save()
            except UserSession.DoesNotExist:
                pass
        
        # Supprimer les tokens locaux
        user.access_token = None
        user.refresh_token = None
        user.token_expires_at = None
        user.save()
        
        logger.info(f"Utilisateur {user.email} déconnecté")


# Instance globale du service
auth_service = AuthService()
