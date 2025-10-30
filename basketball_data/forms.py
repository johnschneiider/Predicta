"""
Formularios para basketball_data
"""

from django import forms
from .models import NBATeam, NBAPrediction


class PredictionForm(forms.Form):
    """Formulario para predicción de puntos totales"""
    
    home_team = forms.ModelChoiceField(
        queryset=NBATeam.objects.all().order_by('full_name'),
        empty_label="Selecciona equipo local",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'home_team'
        }),
        label="Equipo Local"
    )
    
    away_team = forms.ModelChoiceField(
        queryset=NBATeam.objects.all().order_by('full_name'),
        empty_label="Selecciona equipo visitante",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'away_team'
        }),
        label="Equipo Visitante"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        home_team = cleaned_data.get('home_team')
        away_team = cleaned_data.get('away_team')
        
        if home_team and away_team and home_team == away_team:
            raise forms.ValidationError("Los equipos local y visitante deben ser diferentes.")
        
        return cleaned_data
