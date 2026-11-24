from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("resume/", views.resume, name="resume"),
    path("resume/download/", views.resume_download, name="resume_download"),
]
