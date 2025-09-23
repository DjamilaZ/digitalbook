from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Identique à SessionAuthentication mais sans enforcement CSRF.
    À utiliser avec parcimonie, uniquement sur des vues API spécifiques.
    """
    def enforce_csrf(self, request):
        return
