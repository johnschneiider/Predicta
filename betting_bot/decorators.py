"""
Decoradores personalizados para el proyecto Predicta
"""

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


def login_required_custom(view_func=None, redirect_field_name='next', login_url=None):
    """
    Decorador personalizado que requiere autenticación y redirige al login
    con mensaje informativo si el usuario no está autenticado.
    """
    if login_url is None:
        login_url = reverse('cuentas:login')
    
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.info(request, 'Debes iniciar sesión para acceder a esta página.')
                return redirect(login_url)
            return view_func(request, *args, **kwargs)
        return wrapper
    
    if view_func:
        return decorator(view_func)
    return decorator


def login_required_class_view(login_url=None):
    """
    Decorador para vistas basadas en clases que requiere autenticación
    """
    if login_url is None:
        login_url = reverse('cuentas:login')
    
    def decorator(cls):
        original_dispatch = cls.dispatch
        
        def dispatch(self, request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.info(request, 'Debes iniciar sesión para acceder a esta página.')
                return redirect(login_url)
            return original_dispatch(self, request, *args, **kwargs)
        
        cls.dispatch = dispatch
        return cls
    
    return decorator















