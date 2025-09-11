from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Book(models.Model):
    """Modèle représentant un livre."""
    title = models.CharField(max_length=255, verbose_name="Titre")
    url = models.SlugField(max_length=255, unique=True, verbose_name="URL")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Date de création")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='books',
        verbose_name="Créé par"
    )
    cover_image = models.ImageField(upload_to='books/covers/', null=True, blank=True, verbose_name="Image de couverture")
    pdf_url = models.URLField(max_length=1000, null=True, blank=True, verbose_name="URL du PDF")
    
    class Meta:
        verbose_name = "Livre"
        verbose_name_plural = "Livres"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class Chapter(models.Model):
    """Modèle représentant un chapitre d'un livre."""
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='chapters',
        verbose_name="Livre"
    )
    title = models.CharField(max_length=255, verbose_name="Titre")
    content = models.TextField(verbose_name="Contenu", blank=True)
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    
    class Meta:
        verbose_name = "Chapitre"
        verbose_name_plural = "Chapitres"
        ordering = ['order']
    
    def __str__(self):
        return f"{self.book.title} - {self.title}"

class Section(models.Model):
    """Modèle représentant une section d'un chapitre."""
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name='sections',
        verbose_name="Chapitre"
    )
    title = models.CharField(max_length=255, verbose_name="Titre")
    content = models.TextField(verbose_name="Contenu", blank=True)
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    images = models.JSONField(default=list, blank=True, verbose_name="Images")
    tables = models.JSONField(default=list, blank=True, verbose_name="Tableaux")
    
    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        ordering = ['order']
    
    def __str__(self):
        return f"{self.chapter} - {self.title}"

class Subsection(models.Model):
    """Modèle représentant une sous-section d'une section."""
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='subsections',
        verbose_name="Section"
    )
    title = models.CharField(max_length=255, verbose_name="Titre")
    content = models.TextField(verbose_name="Contenu", blank=True)
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    images = models.JSONField(default=list, blank=True, verbose_name="Images")
    tables = models.JSONField(default=list, blank=True, verbose_name="Tableaux")
    
    class Meta:
        verbose_name = "Sous-section"
        verbose_name_plural = "Sous-sections"
        ordering = ['order']
    
    def __str__(self):
        return f"{self.section} - {self.title}"
