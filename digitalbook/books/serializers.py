from rest_framework import serializers
from django.db.models import Count
from .models import Book, Chapter, Section, Subsection, ReadingProgress

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
        fields = ['id', 'title', 'content', 'order', 'is_intro', 'images', 'tables', 'sections']
        read_only_fields = ['id']

class BookSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    pdf_file = serializers.FileField(required=False, allow_null=True, write_only=True)
    json_structure_file = serializers.FileField(required=False, allow_null=True, write_only=True)
    pdf_url = serializers.URLField(required=False, allow_null=True, read_only=True)
    language = serializers.CharField(read_only=True)
    processing_status = serializers.CharField(read_only=True)
    processing_progress = serializers.IntegerField(read_only=True)
    processing_error = serializers.CharField(read_only=True)
    processing_started_at = serializers.DateTimeField(read_only=True)
    processing_finished_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'url', 'created_at', 'created_by', 'chapters', 'language', 'published',
            'pdf_file', 'json_structure_file', 'pdf_url',
            'processing_status', 'processing_progress', 'processing_error',
            'processing_started_at', 'processing_finished_at'
        ]
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

class BookUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour la mise à jour du titre d'un livre"""
    class Meta:
        model = Book
        fields = ['title']
        
    def validate_title(self, value):
        """Valide que le titre n'est pas vide"""
        if not value or not value.strip():
            raise serializers.ValidationError("Le titre ne peut pas être vide.")
        return value.strip()

class BookListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des livres avec les champs demandés"""
    author = serializers.CharField(source='created_by', read_only=True, allow_null=True)
    chapters_count = serializers.SerializerMethodField()
    sections_count = serializers.SerializerMethodField()
    cover_image = serializers.ImageField(read_only=True, allow_null=True)
    language = serializers.CharField(read_only=True)
    
    class Meta:
        model = Book
        fields = [
            'id', 
            'title', 
            'pdf_url', 
            'cover_image',
            'chapters_count', 
            'sections_count', 
            'author', 
            'created_by', 
            'created_at',
            'language',
            'published',
        ]
        read_only_fields = ['id', 'created_at', 'created_by']
    
    def get_chapters_count(self, obj):
        """Retourne le nombre de chapitres pour ce livre"""
        return obj.chapters.count()
    
    def get_sections_count(self, obj):
        """Retourne le nombre total de sections pour ce livre"""
        return Section.objects.filter(chapter__book=obj).count()


class ReadingProgressSerializer(serializers.ModelSerializer):
    chapter_id = serializers.PrimaryKeyRelatedField(
        source='chapter', queryset=Chapter.objects.all(), required=False, allow_null=True
    )
    section_id = serializers.PrimaryKeyRelatedField(
        source='section', queryset=Section.objects.all(), required=False, allow_null=True
    )
    subsection_id = serializers.PrimaryKeyRelatedField(
        source='subsection', queryset=Subsection.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = ReadingProgress
        fields = [
            'book', 'chapter_id', 'section_id', 'subsection_id',
            'position_in_text', 'percentage', 'updated_at'
        ]
        read_only_fields = ['book', 'updated_at']