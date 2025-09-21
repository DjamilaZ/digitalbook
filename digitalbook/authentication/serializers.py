from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser, UserSession


class LoginSerializer(serializers.Serializer):
    """Sérialiseur pour la connexion"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    login_source = serializers.CharField(default='web', required=False)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError("Email et mot de passe sont requis")
        
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les données utilisateur"""
    full_name = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'role_id', 'role_name', 'role_display',
            'is_external_user', 'last_login_api', 'created_at'
        ]
        read_only_fields = ['id', 'is_external_user', 'last_login_api', 'created_at']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_role_display(self, obj):
        return obj.get_role_display()


class AuthResponseSerializer(serializers.Serializer):
    """Sérialiseur pour la réponse d'authentification"""
    message = serializers.CharField()
    user = UserSerializer()
    access_token = serializers.CharField(allow_null=True)
    refresh_token = serializers.CharField(allow_null=True)
    session_token = serializers.CharField()
    created = serializers.BooleanField()


class RefreshTokenSerializer(serializers.Serializer):
    """Sérialiseur pour le rafraîchissement du token"""
    refresh_token = serializers.CharField(required=True)


class LogoutSerializer(serializers.Serializer):
    """Sérialiseur pour la déconnexion"""
    session_token = serializers.CharField(required=False)


class UserSessionSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les sessions utilisateur"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'session_token', 'is_active', 'ip_address',
            'user_agent', 'created_at', 'last_activity',
            'user_email', 'user_name'
        ]
        read_only_fields = ['id', 'user_email', 'user_name', 'created_at', 'last_activity']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name()


class ErrorResponseSerializer(serializers.Serializer):
    """Sérialiseur pour les réponses d'erreur"""
    error = serializers.CharField()
    status_code = serializers.IntegerField()
    details = serializers.DictField(child=serializers.CharField(), required=False)


class SuccessResponseSerializer(serializers.Serializer):
    """Sérialiseur pour les réponses de succès"""
    message = serializers.CharField()
    data = serializers.DictField(required=False)
