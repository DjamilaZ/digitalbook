from django.contrib import admin
from .models import Book, Chapter, Section, Subsection, Thematique

class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1
    show_change_link = True

class SectionInline(admin.TabularInline):
    model = Section
    extra = 1
    show_change_link = True

class SubsectionInline(admin.TabularInline):
    model = Subsection
    extra = 1

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at')
    list_filter = ('created_at', 'created_by')
    search_fields = ('title', 'url')
    prepopulated_fields = {'url': ('title',)}
    inlines = [ChapterInline]

@admin.register(Thematique)
class ThematiqueAdmin(admin.ModelAdmin):
    list_display = ('title', 'book', 'created_at')
    list_filter = ('book', 'created_at')
    search_fields = ('title', 'description', 'book__title')

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'book', 'thematique', 'order')
    list_filter = ('book', 'thematique')
    search_fields = ('title', 'book__title', 'thematique__title')
    inlines = [SectionInline]

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'chapter', 'order')
    list_filter = ('chapter__book', 'chapter')
    search_fields = ('title', 'content')
    inlines = [SubsectionInline]

@admin.register(Subsection)
class SubsectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'order')
    list_filter = ('section__chapter__book', 'section__chapter')
    search_fields = ('title', 'content')
