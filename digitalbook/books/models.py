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
    language = models.CharField(
        max_length=8,
        choices=[('fr', 'Français'), ('en', 'Anglais'), ('pt', 'Portugais')],
        null=True,
        blank=True,
        verbose_name="Langue détectée"
    )
    published = models.BooleanField(default=False, verbose_name="Publié")
    # Suivi de traitement en arrière-plan
    processing_status = models.CharField(
        max_length=32,
        choices=[
            ('queued', 'Queued'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('idle', 'Idle'),
        ],
        default='idle',
        verbose_name="Statut de traitement",
    )
    processing_progress = models.PositiveIntegerField(default=0, verbose_name="Progression (%)")
    processing_error = models.TextField(null=True, blank=True, verbose_name="Erreur de traitement")
    processing_started_at = models.DateTimeField(null=True, blank=True, verbose_name="Début de traitement")
    processing_finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Fin de traitement")
    
    class Meta:
        verbose_name = "Livre"
        verbose_name_plural = "Livres"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class Thematique(models.Model):
    """Modèle représentant une thématique qui peut contenir un ou plusieurs chapitres."""
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='thematiques',
        verbose_name="Livre",
        null=True,
        blank=True
    )
    title = models.CharField(max_length=255, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    
    class Meta:
        verbose_name = "Thématique"
        verbose_name_plural = "Thématiques"
        ordering = ['title']
    
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
    thematique = models.ForeignKey(
        Thematique,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chapters',
        verbose_name="Thématique"
    )
    title = models.CharField(max_length=255, verbose_name="Titre")
    content = models.TextField(verbose_name="Contenu", blank=True)
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    is_intro = models.BooleanField(default=False, verbose_name="Chapitre d'introduction")
    images = models.JSONField(default=list, blank=True, verbose_name="Images")
    tables = models.JSONField(default=list, blank=True, verbose_name="Tableaux")
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


class ReadingProgress(models.Model):
    """Suivi de la progression de lecture d'un utilisateur sur un livre."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_progress')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reading_progress')
    chapter = models.ForeignKey(Chapter, on_delete=models.SET_NULL, null=True, blank=True, related_name='reading_progress')
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='reading_progress')
    subsection = models.ForeignKey(Subsection, on_delete=models.SET_NULL, null=True, blank=True, related_name='reading_progress')
    position_in_text = models.PositiveIntegerField(default=0, verbose_name="Position (caractère/offset)")
    percentage = models.FloatField(default=0.0, verbose_name="Progression (%)")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière mise à jour")

    class Meta:
        unique_together = ('user', 'book')
        verbose_name = "Progression de lecture"
        verbose_name_plural = "Progressions de lecture"

    def __str__(self):
        return f"{self.user} - {self.book} ({self.percentage}%)"


class TranslationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    READY = 'ready', 'Ready'
    STALE = 'stale', 'Stale'


class ThematiqueTranslation(models.Model):
    thematique = models.ForeignKey(Thematique, on_delete=models.CASCADE, related_name='translations')
    lang = models.CharField(max_length=8)
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=TranslationStatus.choices, default=TranslationStatus.PENDING)
    source_hash = models.CharField(max_length=64, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('thematique', 'lang')


class ChapterTranslation(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='translations')
    lang = models.CharField(max_length=8)
    title = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=TranslationStatus.choices, default=TranslationStatus.PENDING)
    source_hash = models.CharField(max_length=64, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('chapter', 'lang')


class SectionTranslation(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='translations')
    lang = models.CharField(max_length=8)
    title = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    images = models.JSONField(default=list, blank=True)
    tables = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=TranslationStatus.choices, default=TranslationStatus.PENDING)
    source_hash = models.CharField(max_length=64, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('section', 'lang')


class SubsectionTranslation(models.Model):
    subsection = models.ForeignKey(Subsection, on_delete=models.CASCADE, related_name='translations')
    lang = models.CharField(max_length=8)
    title = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    images = models.JSONField(default=list, blank=True)
    tables = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=TranslationStatus.choices, default=TranslationStatus.PENDING)
    source_hash = models.CharField(max_length=64, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('subsection', 'lang')
