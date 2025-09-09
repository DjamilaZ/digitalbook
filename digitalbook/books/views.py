# books/views.py
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Book, Chapter, Section, Subsection
from .serializers import BookSerializer, ChapterSerializer, SectionSerializer, SubsectionSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    # permission_classes = [IsAuthenticated]
    lookup_field = 'url'
    lookup_url_kwarg = 'url'

    def get_queryset(self):
        queryset = Book.objects.all()
        # Temporairement désactivé pour le débogage
        # if self.request.user.is_authenticated:
        #     queryset = queryset.filter(created_by=self.request.user)
        return queryset

    def perform_create(self, serializer):
        # Temporairement désactivé pour le débogage
        # serializer.save(created_by=self.request.user)
        serializer.save()

    def create(self, request, *args, **kwargs):
        # Gestion spéciale pour l'upload de fichiers
        if 'pdf_file' in request.FILES:
            request.data._mutable = True
            request.data['pdf_file'] = request.FILES['pdf_file']
            request.data._mutable = False
        return super().create(request, *args, **kwargs)

class ChapterViewSet(viewsets.ModelViewSet):
    serializer_class = ChapterSerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Chapter.objects.filter(book__created_by=self.request.user)

    def perform_create(self, serializer):
        book = get_object_or_404(Book, url=self.kwargs['book_url'], created_by=self.request.user)
        serializer.save(book=book)

class SectionViewSet(viewsets.ModelViewSet):
    serializer_class = SectionSerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Section.objects.filter(chapter__book__created_by=self.request.user)

    def perform_create(self, serializer):
        chapter = get_object_or_404(
            Chapter, 
            id=self.kwargs['chapter_id'],
            book__created_by=self.request.user
        )
        serializer.save(chapter=chapter)

class SubsectionViewSet(viewsets.ModelViewSet):
    serializer_class = SubsectionSerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subsection.objects.filter(section__chapter__book__created_by=self.request.user)

    def perform_create(self, serializer):
        section = get_object_or_404(
            Section, 
            id=self.kwargs['section_id'],
            chapter__book__created_by=self.request.user
        )
        serializer.save(section=section)