from django.contrib import admin
from .models import QCM, Question, Reponse


@admin.register(QCM)
class QCMAdmin(admin.ModelAdmin):
    list_display = ('title', 'book', 'chapter', 'question_count', 'created_at')
    list_filter = ('book', 'created_at')
    search_fields = ('title', 'book__title', 'chapter__title')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Informations générales', {
            'fields': ('title', 'book', 'chapter', 'description', 'created_at', 'updated_at')
        }),
    )
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Nombre de questions'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'qcm', 'order', 'created_at')
    list_filter = ('qcm', 'created_at')
    search_fields = ('text', 'qcm__title')
    ordering = ('qcm', 'order')
    fieldsets = (
        ('Question', {
            'fields': ('qcm', 'text', 'order', 'created_at')
        }),
    )


@admin.register(Reponse)
class ReponseAdmin(admin.ModelAdmin):
    list_display = ('text', 'question', 'is_correct', 'order')
    list_filter = ('question__qcm', 'is_correct')
    search_fields = ('text', 'question__text')
    ordering = ('question', 'order')
    fieldsets = (
        ('Réponse', {
            'fields': ('question', 'text', 'is_correct', 'order')
        }),
    )
