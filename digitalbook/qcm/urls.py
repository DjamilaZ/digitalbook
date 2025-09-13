from django.urls import path, include
from rest_framework_nested import routers
from . import views

router = routers.DefaultRouter()
router.register(r'qcms', views.QCMViewSet, basename='qcm')

# Nested routers for questions and responses
qcms_router = routers.NestedSimpleRouter(router, r'qcms', lookup='qcm')
qcms_router.register(r'questions', views.QuestionViewSet, basename='qcm-question')

questions_router = routers.NestedSimpleRouter(qcms_router, r'questions', lookup='question')
questions_router.register(r'reponses', views.ReponseViewSet, basename='question-reponse')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(qcms_router.urls)),
    path('', include(questions_router.urls)),
]
