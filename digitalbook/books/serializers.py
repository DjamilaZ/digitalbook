from rest_framework import serializers
from django.db.models import Count
from .models import Book, Chapter, Section, Subsection

class SubsectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subsection
        fields = ['id', 'title', 'content', 'order', 'images', 'tables']
        read_only_fields = ['id']

class SectionSerializer(serializers.ModelSerializer):
    subsections = SubsectionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Section
        fields = ['id', 'title', 'content', 'order', 'images', 'tables', 'subsections']
        read_only_fields = ['id']

class ChapterSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Chapter
        fields = ['id', 'title', 'order', 'sections']
        read_only_fields = ['id']

class BookSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    pdf_file = serializers.FileField(required=False, allow_null=True, write_only=True)
    pdf_url = serializers.URLField(required=False, allow_null=True, read_only=True)
    
    class Meta:
        model = Book
        fields = ['id', 'title', 'url', 'created_at', 'created_by', 'chapters', 'pdf_file', 'pdf_url']
        read_only_fields = ['id', 'created_at', 'created_by', 'url']
        extra_kwargs = {
            'pdf_file': {'required': True}
        }
    
    def create(self, validated_data):
        # Crée le livre avec ou sans utilisateur
        pdf_file = validated_data.pop('pdf_file', None)
        book = Book.objects.create(
            title=validated_data['title']
        )
        return book

class BookListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des livres avec les champs demandés"""
    author = serializers.CharField(source='created_by', read_only=True, allow_null=True)
    chapters_count = serializers.SerializerMethodField()
    sections_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Book
        fields = [
            'id', 
            'title', 
            'pdf_url', 
            'chapters_count', 
            'sections_count', 
            'author', 
            'created_by', 
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'created_by']
    
    def get_chapters_count(self, obj):
        """Retourne le nombre de chapitres pour ce livre"""
        return obj.chapters.count()
    
    def get_sections_count(self, obj):
        """Retourne le nombre total de sections pour ce livre"""
        return Section.objects.filter(chapter__book=obj).count()