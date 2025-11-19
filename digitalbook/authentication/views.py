from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, BasePermission, SAFE_METHODS
from rest_framework.response import Response
from django.contrib.auth import login
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
import logging
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings
from django.core.mail import send_mail

from .models import CustomUser, UserSession
from .serializers import (
    LoginSerializer, UserSerializer, AuthResponseSerializer,
    RefreshTokenSerializer, LogoutSerializer, UserSessionSerializer,
    ErrorResponseSerializer, SuccessResponseSerializer,
    RequestPasswordResetSerializer, ResetPasswordSerializer, ChangePasswordSerializer,
    RegisterSerializer, AdminUserSerializer,
)
from .services import auth_service
from .custom_auth import CsrfExemptSessionAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class IsAdminOrManagerReadOnly(BasePermission):
    """Autorise les admins pour tout. Autorise les managers en lecture seule."""
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        role = getattr(user, 'role_name', '') or ''
        role = str(role).lower()
        # Admins: accès complet
        if user.is_superuser or user.is_staff or role == 'admin':
            return True
        # Managers: seulement lecture
        if role == 'manager':
            return request.method in SAFE_METHODS
        return False

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
        """Authentifie l'utilisateur localement (sans API externe)"""
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

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                ErrorResponseSerializer({
                    'error': 'Identifiants invalides',
                    'status_code': status.HTTP_401_UNAUTHORIZED
                }).data,
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.check_password(password):
            return Response(
                ErrorResponseSerializer({
                    'error': 'Identifiants invalides',
                    'status_code': status.HTTP_401_UNAUTHORIZED
                }).data,
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Créer une session locale
        session_token = auth_service.create_user_session(user, request)

        # Connecter l'utilisateur avec Django (session)
        login(request, user)

        # Émettre des tokens JWT (access/refresh)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response_data = {
            'message': 'login successfully...',
            'user': user,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'session_token': session_token,
            'created': False
        }
        response_serializer = AuthResponseSerializer(response_data)
        logger.info(f"Connexion réussie pour l'utilisateur: {email}")
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.GenericAPIView):
    """Inscription locale d'un utilisateur, avec auto-login."""
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = RegisterSerializer

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

        user = serializer.save()

        # Auto login + session
        session_token = auth_service.create_user_session(user, request)
        login(request, user)

        response_data = {
            'message': 'register successfully...',
            'user': user,
            'access_token': None,
            'refresh_token': None,
            'session_token': session_token,
            'created': True
        }
        response_serializer = AuthResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


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
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # Ne pas divulguer si l'email existe; répondre succès générique
            return Response(SuccessResponseSerializer({ 'message': 'Si un compte existe, un lien a été généré.' }).data, status=status.HTTP_200_OK)

        signer = TimestampSigner(salt='password-reset')
        token = signer.sign(str(user.id))

        # Construire le lien de réinitialisation côté Frontend
        frontend_base = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:3000')
        reset_link = f"{frontend_base}/reset-password?token={token}"

        # Envoyer l'email (texte simple + lien)
        subject = "Réinitialisation de votre mot de passe"
        message = (
            "Bonjour,\n\n"
            "Vous avez demandé à réinitialiser votre mot de passe. "
            f"Veuillez cliquer sur le lien suivant pour continuer: {reset_link}\n\n"
            "Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email.\n"
        )
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@digitalbook.local')
        try:
            send_mail(subject, message, from_email, [user.email], fail_silently=False)
        except Exception:
            # En cas d'erreur d'envoi, ne pas exposer de détails en prod
            pass

        resp_data = {'message': 'Lien de réinitialisation envoyé par email'}
        if getattr(settings, 'DEBUG', False):
            resp_data = {
                'message': 'Lien de réinitialisation généré',
                'data': { 'reset_token': token, 'reset_link': reset_link }
            }
        return Response(SuccessResponseSerializer(resp_data).data, status=status.HTTP_200_OK)


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

        try:
            signer = TimestampSigner(salt='password-reset')
            # Expire après 24h
            unsigned = signer.unsign(token, max_age=60*60*24)
            user_id = int(unsigned)
            user = CustomUser.objects.get(id=user_id)
        except (BadSignature, SignatureExpired, ValueError, CustomUser.DoesNotExist):
            return Response(
                ErrorResponseSerializer({
                    'error': 'Token invalide ou expiré',
                    'status_code': status.HTTP_400_BAD_REQUEST
                }).data,
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save(update_fields=['password'])

        return Response(SuccessResponseSerializer({ 'message': 'Password reset successfully' }).data, status=status.HTTP_200_OK)


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
        old_password = serializer.validated_data['oldPassword']
        new_password = serializer.validated_data['newPassword']

        if not user.check_password(old_password):
            return Response(
                ErrorResponseSerializer({
                    'error': 'Ancien mot de passe incorrect',
                    'status_code': status.HTTP_400_BAD_REQUEST
                }).data,
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save(update_fields=['password'])

        return Response(SuccessResponseSerializer({ 'message': 'Password changed successfully' }).data, status=status.HTTP_200_OK)


class RefreshTokenView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = RefreshTokenSerializer

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

        token_str = serializer.validated_data['refresh_token']
        try:
            refresh = RefreshToken(token_str)
            user_id = refresh.get('user_id')
            user = CustomUser.objects.get(id=user_id)

            # Blacklist l'ancien refresh si blacklist activé
            try:
                refresh.blacklist()
            except Exception:
                pass

            new_refresh = RefreshToken.for_user(user)
            new_access = str(new_refresh.access_token)

            response_data = {
                'message': 'Token rafraîchi avec succès',
                'data': {
                    'access_token': new_access,
                    'refresh_token': str(new_refresh)
                }
            }
            response_serializer = SuccessResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except CustomUser.DoesNotExist:
            return Response(
                ErrorResponseSerializer({
                    'error': 'Utilisateur inconnu',
                    'status_code': status.HTTP_401_UNAUTHORIZED
                }).data,
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception:
            return Response(
                ErrorResponseSerializer({
                    'error': 'Refresh token invalide',
                    'status_code': status.HTTP_401_UNAUTHORIZED
                }).data,
                status=status.HTTP_401_UNAUTHORIZED
            )


class AdminUserViewSet(viewsets.ModelViewSet):
    """CRUD Admin sur les utilisateurs"""
    permission_classes = [IsAdminOrManagerReadOnly]
    queryset = CustomUser.objects.all().order_by('-created_at')
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        req = getattr(self, 'request', None)
        # Un non-superuser ne peut pas voir les superadmins
        if not (req and getattr(req.user, 'is_superuser', False)):
            qs = qs.exclude(is_superuser=True)
        # Un manager ne voit que managers et employés (et pas les admins)
        if req and getattr(req, 'user', None):
            role = str(getattr(req.user, 'role_name', '') or '').lower()
            if role == 'manager' and not req.user.is_superuser:
                qs = qs.filter(role_name__in=['manager', 'employe'])
        # Masquer l'utilisateur connecté lui-même
        if req and getattr(req, 'user', None) and getattr(req.user, 'is_authenticated', False):
            qs = qs.exclude(id=req.user.id)
        email = self.request.query_params.get('email')
        role = self.request.query_params.get('role') or self.request.query_params.get('role_name')
        active = self.request.query_params.get('is_active')
        if email:
            qs = qs.filter(email__icontains=email)
        if role:
            qs = qs.filter(role_name=role)
        if active is not None:
            if active.lower() in ('true', '1'):
                qs = qs.filter(is_active=True)
            elif active.lower() in ('false', '0'):
                qs = qs.filter(is_active=False)
        return qs

@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(generics.GenericAPIView):
    """Vue pour la déconnexion des utilisateurs"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, CsrfExemptSessionAuthentication]
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
