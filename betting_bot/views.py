from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def landing_page(request):
    """Página de aterrizaje moderna con paleta de colores azules"""
    return render(request, 'landing_page.html')
