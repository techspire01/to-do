from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("tasks/add/", views.add_task, name="add_task"),
    path("tasks/<int:pk>/edit/", views.update_task, name="update_task"),
    path("tasks/<int:pk>/delete/", views.delete_task, name="delete_task"),
    path("tasks/<int:pk>/complete/", views.mark_complete, name="mark_complete"),
    path("tasks/<int:pk>/move/<str:direction>/", views.move_task, name="move_task"),
]
