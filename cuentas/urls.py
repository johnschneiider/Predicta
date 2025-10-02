from django.urls import path
from . import views

app_name = 'cuentas'

urlpatterns = [
    path('login/', views.VistaLogin.as_view(), name='login'),
    path('registro/', views.VistaRegistro.as_view(), name='registro'),
    path('dashboard/', views.VistaDashboard.as_view(), name='dashboard'),
    path('logout/', views.vista_logout, name='logout'),
]