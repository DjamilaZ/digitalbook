from django.db import models
from django.utils import timezone


class QCM(models.Model):
    """Modèle représentant un QCM rattaché à un livre et un chapitre spécifique"""
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.CASCADE,
        related_name='qcms',
        verbose_name="Livre"
    )
    chapter = models.ForeignKey(
        'books.Chapter',
        on_delete=models.CASCADE,
        related_name='qcms',
        verbose_name="Chapitre"
    )
    title = models.CharField(max_length=255, verbose_name="Titre du QCM")
    description = models.TextField(blank=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de mise à jour")
    
    class Meta:
        verbose_name = "QCM"
        verbose_name_plural = "QCMs"
        ordering = ['chapter', 'title']
        # Un QCM doit être unique pour un chapitre donné
        unique_together = ['chapter', 'title']
    
    def __str__(self):
        return f"{self.book.title} - {self.chapter.title} - {self.title}"

class Question(models.Model):
    """Modèle représentant une question dans un QCM"""
    qcm = models.ForeignKey(
        QCM,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="QCM"
    )
    text = models.TextField(verbose_name="Texte de la question")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    
    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        ordering = ['order']
    
    def __str__(self):
        return f"{self.qcm.title} - Question {self.order}"

class Reponse(models.Model):
    """Modèle représentant une réponse à une question"""
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='reponses',
        verbose_name="Question"
    )
    text = models.CharField(max_length=500, verbose_name="Texte de la réponse")
    is_correct = models.BooleanField(default=False, verbose_name="Réponse correcte")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    
    class Meta:
        verbose_name = "Réponse"
        verbose_name_plural = "Réponses"
        ordering = ['order']
    
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{self.question} - {self.text} {status}"

# Create your models here.
