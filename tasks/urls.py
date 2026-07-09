from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('project/<int:project_pk>/create/', views.task_create, name='task_create'),
    path('<int:pk>/', views.task_detail, name='task_detail'),
    path('<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('<int:pk>/status/', views.task_status_update, name='task_status_update'),
    path('<int:pk>/accept/', views.task_accept, name='task_accept'),
    path('<int:pk>/submit/', views.task_submit, name='task_submit'),
    path('<int:pk>/approve/', views.task_approve, name='task_approve'),
    path('<int:pk>/reject/', views.task_reject, name='task_reject'),
    path('comment/<int:pk>/delete/', views.comment_delete, name='comment_delete'),
]
