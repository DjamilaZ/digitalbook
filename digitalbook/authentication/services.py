from .models import UserSession

class AuthService:
    """Service d'authentification principal"""
    
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
        
        # Nettoyage minimal (rien à faire pour JWT côté serveur)
        return


# Instance globale du service
auth_service = AuthService()
