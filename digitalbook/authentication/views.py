from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import login
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
import logging

from .models import CustomUser, UserSession
from .serializers import (
    LoginSerializer, UserSerializer, AuthResponseSerializer,
    RefreshTokenSerializer, LogoutSerializer, UserSessionSerializer,
    ErrorResponseSerializer, SuccessResponseSerializer,
    RequestPasswordResetSerializer, ResetPasswordSerializer, ChangePasswordSerializer,
)
from .services import auth_service

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def get_csrf_token(request):
    """Retourne un token CSRF et s'assure qu'il est posé en cookie (csrftoken)."""
    token = get_token(request)
    return Response({ 'csrfToken': token })


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(generics.GenericAPIView):
    """Vue pour la connexion des utilisateurs"""
    permission_classes = [AllowAny]
    authentication_classes = []  # Ne pas appliquer SessionAuthentication (évite la vérification CSRF DRF)
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        """Authentifie l'utilisateur via l'API externe"""
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                ErrorResponseSerializer({
                    'error': 'Données invalides',
                    'status_code': status.HTTP_400_BAD_REQUEST,
                    'details': {'validation': str(e)}
                }).data,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        login_source = serializer.validated_data.get('login_source', 'web')
        
        # Authentification via le service
        auth_result = auth_service.authenticate_user(email, password)
        
        if not auth_result['success']:
            error_status = auth_result.get('status_code', status.HTTP_401_UNAUTHORIZED)
            return Response(
                ErrorResponseSerializer({
                    'error': auth_result['error'],
                    'status_code': error_status
                }).data,
                status=error_status
            )
        
        user = auth_result['user']
        access_token = auth_result['access_token']
        refresh_token = auth_result['refresh_token']
        created = auth_result['created']
        
        # Créer une session locale
        session_token = auth_service.create_user_session(user, request)
        
        # Connecter l'utilisateur avec Django (optionnel)
        login(request, user)
        
        # Préparer la réponse
        response_data = {
            'message': 'login successfully...',
            'user': user,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'session_token': session_token,
            'created': created
        }
        
        response_serializer = AuthResponseSerializer(response_data)
        
        logger.info(f"Connexion réussie pour l'utilisateur: {email}")
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)


# Password reset request (AllowAny) -> proxifie l'API externe
@method_decorator(csrf_exempt, name='dispatch')
class RequestPasswordResetView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = RequestPasswordResetSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                ErrorResponseSerializer({
                    'error': 'Données invalides',
                    'status_code': status.HTTP_400_BAD_REQUEST,
                    'details': {'validation': str(e)}
                }).data,
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email']
        result = auth_service.external_api.request_password_reset(email)
        if not result['success']:
            return Response(
                ErrorResponseSerializer({
                    'error': result['error'] or 'Erreur lors de la demande de réinitialisation',
                    'status_code': result.get('status_code', 400)
                }).data,
                status=result.get('status_code', status.HTTP_400_BAD_REQUEST)
            )
        message = result['data'].get('message', 'Password reset email sent')
        return Response(SuccessResponseSerializer({ 'message': message }).data, status=status.HTTP_200_OK)


# Password reset with token (AllowAny) -> proxifie l'API externe
@method_decorator(csrf_exempt, name='dispatch')
class ResetPasswordView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                ErrorResponseSerializer({
                    'error': 'Données invalides',
                    'status_code': status.HTTP_400_BAD_REQUEST,
                    'details': {'validation': str(e)}
                }).data,
                status=status.HTTP_400_BAD_REQUEST
            )

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['newPassword']
        result = auth_service.external_api.reset_password(token, new_password)
        if not result['success']:
            return Response(
                ErrorResponseSerializer({
                    'error': result['error'] or 'Erreur lors de la réinitialisation du mot de passe',
                    'status_code': result.get('status_code', 400)
                }).data,
                status=result.get('status_code', status.HTTP_400_BAD_REQUEST)
            )
        message = result['data'].get('message', 'Password reset successful')
        return Response(SuccessResponseSerializer({ 'message': message }).data, status=status.HTTP_200_OK)


# Change password (IsAuthenticated) -> proxifie l'API externe
class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                ErrorResponseSerializer({
                    'error': 'Données invalides',
                    'status_code': status.HTTP_400_BAD_REQUEST,
                    'details': {'validation': str(e)}
                }).data,
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        access_token = getattr(user, 'access_token', None)
        if not access_token:
            return Response(
                ErrorResponseSerializer({
                    'error': 'Utilisateur non authentifié auprès de l\'API externe',
                    'status_code': status.HTTP_401_UNAUTHORIZED
                }).data,
                status=status.HTTP_401_UNAUTHORIZED
            )

        old_password = serializer.validated_data['oldPassword']
        new_password = serializer.validated_data['newPassword']
        result = auth_service.external_api.change_password(access_token, old_password, new_password)
        if not result['success']:
            return Response(
                ErrorResponseSerializer({
                    'error': result['error'] or 'Erreur lors du changement de mot de passe',
                    'status_code': result.get('status_code', 400)
                }).data,
                status=result.get('status_code', status.HTTP_400_BAD_REQUEST)
            )
        message = result['data'].get('message', 'Password changed successfully')
        return Response(SuccessResponseSerializer({ 'message': message }).data, status=status.HTTP_200_OK)


class RefreshTokenView(generics.GenericAPIView):
    """Vue pour rafraîchir le token d'accès"""
    permission_classes = [IsAuthenticated]
    serializer_class = RefreshTokenSerializer

    def post(self, request, *args, **kwargs):
        """Rafraîchit le token d'accès via l'API externe"""
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                ErrorResponseSerializer({
                    'error': 'Données invalides',
                    'status_code': status.HTTP_400_BAD_REQUEST,
                    'details': {'validation': str(e)}
                }).data,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        refresh_token = serializer.validated_data['refresh_token']
        
        # Utiliser le refresh token fourni ou celui de l'utilisateur
        if not refresh_token:
            refresh_token = user.refresh_token
        
        if not refresh_token:
            return Response(
                ErrorResponseSerializer({
                    'error': 'Pas de refresh token disponible',
                    'status_code': status.HTTP_400_BAD_REQUEST
                }).data,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Rafraîchir le token via le service
        refresh_result = auth_service.refresh_user_token(user)
        
        if not refresh_result['success']:
            return Response(
                ErrorResponseSerializer({
                    'error': refresh_result['error'],
                    'status_code': status.HTTP_401_UNAUTHORIZED
                }).data,
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        response_data = {
            'message': 'Token rafraîchi avec succès',
            'data': {
                'access_token': refresh_result['access_token'],
                'refresh_token': refresh_result['refresh_token']
            }
        }
        
        response_serializer = SuccessResponseSerializer(response_data)
        
        logger.info(f"Token rafraîchi pour l'utilisateur: {user.email}")
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class LogoutView(generics.GenericAPIView):
    """Vue pour la déconnexion des utilisateurs"""
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        """Déconnecte l'utilisateur"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid()
        
        user = request.user
        session_token = serializer.validated_data.get('session_token')
        
        # Déconnecter l'utilisateur via le service
        auth_service.logout_user(user, session_token)
        
        # Invalider la session Django
        from django.contrib.auth import logout
        logout(request)
        
        response_data = {
            'message': 'Déconnexion réussie'
        }
        
        response_serializer = SuccessResponseSerializer(response_data)
        
        logger.info(f"Déconnexion réussie pour l'utilisateur: {user.email}")
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveAPIView):
    """Vue pour obtenir le profil utilisateur"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserSessionsView(generics.ListAPIView):
    """Vue pour lister les sessions utilisateur"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-last_activity')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def validate_token(request):
    """Valide la session utilisateur (authentification par session)."""
    user = request.user
    response_data = {
        'message': 'Session valide',
        'data': {
            'user_id': user.id,
            'email': user.email,
            'session_auth': True,
        }
    }
    response_serializer = SuccessResponseSerializer(response_data)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_session(request, session_token):
    """Révoque une session spécifique"""
    try:
        session = UserSession.objects.get(
            user=request.user,
            session_token=session_token,
            is_active=True
        )
        
        session.is_active = False
        session.save()
        
        response_data = {
            'message': 'Session révoquée avec succès'
        }
        
        response_serializer = SuccessResponseSerializer(response_data)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            ErrorResponseSerializer({
                'error': 'Session non trouvée',
                'status_code': status.HTTP_404_NOT_FOUND
            }).data,
            status=status.HTTP_404_NOT_FOUND
        )
