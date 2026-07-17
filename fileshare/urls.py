from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_page),
    path('api/upload/', views.upload_file),
    path('download/<str:token>/', views.download_file),
]
