from rest_framework import serializers
from .models import QCM, Question, Reponse


class ReponseSerializer(serializers.ModelSerializer):
    """Serializer pour les réponses"""
    class Meta:
        model = Reponse
        fields = ['id', 'text', 'is_correct', 'order']
        read_only_fields = ['id']


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer pour les questions avec leurs réponses"""
    reponses = ReponseSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'order', 'reponses']
        read_only_fields = ['id']


class QCMSerializer(serializers.ModelSerializer):
    """Serializer pour les QCM avec leurs questions et réponses"""
    questions = QuestionSerializer(many=True, read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    chapter_title = serializers.CharField(source='chapter.title', read_only=True)
    questions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = QCM
        fields = [
            'id', 'title', 'description', 'book', 'chapter', 'book_title', 'chapter_title',
            'questions', 'questions_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_questions_count(self, obj):
        """Retourne le nombre de questions pour ce QCM"""
        return obj.questions.count()


class QCMListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des QCM (sans les questions détaillées)"""
    book_title = serializers.CharField(source='book.title', read_only=True)
    chapter_title = serializers.CharField(source='chapter.title', read_only=True)
    questions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = QCM
        fields = [
            'id', 'title', 'description', 'book_title', 'chapter_title',
            'questions_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_questions_count(self, obj):
        """Retourne le nombre de questions pour ce QCM"""
        return obj.questions.count()


class QCMCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de QCM"""
    class Meta:
        model = QCM
        fields = ['title', 'description', 'book', 'chapter']
    
    def validate(self, data):
        """Valide que le chapitre appartient bien au livre"""
        if data['chapter'].book != data['book']:
            raise serializers.ValidationError(
                "Le chapitre doit appartenir au livre spécifié"
            )
        return data


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de questions"""
    class Meta:
        model = Question
        fields = ['text', 'order', 'qcm']


class ReponseCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de réponses"""
    class Meta:
        model = Reponse
        fields = ['text', 'is_correct', 'order', 'question']
