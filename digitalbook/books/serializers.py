from rest_framework import serializers
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
    pdf_file = serializers.FileField(required=False, allow_null=True)
    
    class Meta:
        model = Book
        fields = ['id', 'title', 'url', 'created_at', 'created_by', 'chapters', 'pdf_file']
        read_only_fields = ['id', 'created_at', 'created_by', 'url']
        extra_kwargs = {
            'pdf_file': {'required': True}
        }
    
    def create(self, validated_data):
        # Crée le livre avec ou sans utilisateur
        book = Book.objects.create(
            title=validated_data['title'],
            pdf_file=validated_data.get('pdf_file')
        )
        return book