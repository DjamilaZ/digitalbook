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
            'full_name', 'role_name', 'role_display',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_role_display(self, obj):
        return obj.get_role_display()


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'role_name', 'is_active', 'is_staff', 'is_superuser',
            'created_at', 'password'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not validated_data.get('username'):
            validated_data['username'] = validated_data.get('email')
        # Enforce defaults and privilege restrictions
        request = self.context.get('request')
        # is_active à True automatiquement
        validated_data['is_active'] = True
        # Un non-superuser ne peut pas définir is_staff/superuser
        if not (request and getattr(request.user, 'is_superuser', False)):
            validated_data.pop('is_staff', None)
            validated_data.pop('is_superuser', None)
        user = CustomUser.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=['password'])
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        request = self.context.get('request')
        # Un non-superuser ne peut pas modifier ces flags sensibles
        if not (request and getattr(request.user, 'is_superuser', False)):
            validated_data.pop('is_active', None)
            validated_data.pop('is_staff', None)
            validated_data.pop('is_superuser', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'first_name', 'last_name', 'username']

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un utilisateur avec cet email existe déjà")
        return value

    def create(self, validated_data):
        username = validated_data.get('username') or validated_data['email']
        user = CustomUser.objects.create_user(
            username=username,
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        return user


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


class RequestPasswordResetSerializer(serializers.Serializer):
    """Sérialiseur pour demander la réinitialisation de mot de passe"""
    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    """Sérialiseur pour réinitialiser le mot de passe avec un token"""
    token = serializers.CharField(required=True)
    newPassword = serializers.CharField(required=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Sérialiseur pour changer le mot de passe (utilisateur authentifié)"""
    oldPassword = serializers.CharField(required=True)
    newPassword = serializers.CharField(required=True)
