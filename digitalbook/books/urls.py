# books/urls.py
from django.urls import path, include
from rest_framework_nested import routers
from . import views

router = routers.DefaultRouter()
router.register(r'books', views.BookViewSet, basename='book')

# Nested routers for chapters, sections, and subsections
books_router = routers.NestedSimpleRouter(router, r'books', lookup='book')
books_router.register(r'chapters', views.ChapterViewSet, basename='book-chapter')

chapters_router = routers.NestedSimpleRouter(books_router, r'chapters', lookup='chapter')
chapters_router.register(r'sections', views.SectionViewSet, basename='chapter-section')

sections_router = routers.NestedSimpleRouter(chapters_router, r'sections', lookup='section')
sections_router.register(r'subsections', views.SubsectionViewSet, basename='section-subsection')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(books_router.urls)),
    path('', include(chapters_router.urls)),
    path('', include(sections_router.urls)),
]