"""
Formularios para la aplicación football_data
"""

from django import forms
from django.forms.widgets import FileInput
from .models import League




class ExcelUploadForm(forms.Form):
    """Formulario para cargar archivos Excel/CSV"""
    
    file = forms.FileField(
        label='Archivo de Datos',
        required=True,
        help_text='Selecciona un archivo Excel (.xlsx, .xls) o CSV (.csv)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls,.csv',
            'id': 'dataFiles'
        })
    )
    
    # Opciones de ligas predefinidas
    LEAGUE_CHOICES = [
        ('', 'Seleccionar liga...'),
        ('Premier League', 'Premier League (Inglaterra)'),
        ('Championship', 'Championship (Inglaterra)'),
        ('League One', 'League One (Inglaterra)'),
        ('League Two', 'League Two (Inglaterra)'),
        ('La Liga', 'La Liga (España)'),
        ('Segunda División', 'Segunda División (España)'),
        ('Bundesliga', 'Bundesliga (Alemania)'),
        ('2. Bundesliga', '2. Bundesliga (Alemania)'),
        ('Ligue 1', 'Ligue 1 (Francia)'),
        ('Ligue 2', 'Ligue 2 (Francia)'),
        ('Serie A', 'Serie A (Italia)'),
        ('Serie B', 'Serie B (Italia)'),
        ('Eredivisie', 'Eredivisie (Países Bajos)'),
        ('Jupiler Pro League', 'Jupiler Pro League (Bélgica)'),
        ('Primeira Liga', 'Primeira Liga (Portugal)'),
        ('Süper Lig', 'Süper Lig (Turquía)'),
        ('Super League', 'Super League (Suiza)'),
        ('Scottish Premiership', 'Scottish Premiership (Escocia)'),
        ('Scottish Championship', 'Scottish Championship (Escocia)'),
        ('Other', 'Otra liga...'),
    ]
    
    league = forms.ChoiceField(
        label='Liga',
        choices=LEAGUE_CHOICES,
        required=True,
        help_text='Selecciona la liga correspondiente a los datos',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'leagueSelect'
        })
    )
    
    league_name = forms.CharField(
        label='Nombre Personalizado de Liga',
        max_length=100,
        required=False,
        help_text='Solo si seleccionaste "Otra liga..."',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Liga MX, MLS, Brasileirão...',
            'id': 'leagueName'
        })
    )
    
    season = forms.CharField(
        label='Temporada',
        max_length=20,
        required=False,
        help_text='Si se deja vacío, se detectará automáticamente',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 2023-24, 2022-23...',
            'id': 'season'
        })
    )
    
    def clean_file(self):
        """Validar el archivo Excel/CSV"""
        file = self.cleaned_data.get('file')
        
        if not file:
            raise forms.ValidationError(
                '⚠️ Debe seleccionar al menos un archivo para importar',
                code='no_file'
            )
                
        # Validar extensión
        if not file.name.lower().endswith(('.xlsx', '.xls', '.csv')):
            raise forms.ValidationError(
                f'❌ El archivo "{file.name}" no es válido. Solo se permiten archivos Excel (.xlsx, .xls) o CSV (.csv)',
                code='invalid_extension'
            )
        
        # Validar tamaño (máximo 10MB)
        if file.size > 10 * 1024 * 1024:
            size_mb = round(file.size / (1024 * 1024), 1)
            raise forms.ValidationError(
                f'⚠️ El archivo "{file.name}" es demasiado grande ({size_mb}MB). El tamaño máximo permitido es 10MB',
                code='file_too_large'
            )
        
        # Validar que el archivo no esté vacío
        if file.size == 0:
            raise forms.ValidationError(
                f'❌ El archivo "{file.name}" está vacío. Por favor selecciona un archivo con datos',
                code='empty_file'
            )
        
        return file
    
    def clean_league(self):
        """Validar selección de liga"""
        league = self.cleaned_data.get('league')
        league_name = self.cleaned_data.get('league_name', '').strip()
        
        if not league or league == '':
            raise forms.ValidationError(
                '⚠️ Debe seleccionar una liga de la lista',
                code='no_league_selected'
            )
        
        if league == 'Other' and not league_name:
            raise forms.ValidationError(
                '⚠️ Debe especificar el nombre de la liga personalizada cuando selecciona "Otra liga..."',
                code='custom_league_required'
            )
        
        return league
    
    def clean_league_name(self):
        """Limpiar nombre de la liga"""
        league = self.cleaned_data.get('league')
        league_name = self.cleaned_data.get('league_name', '').strip()
        
        if league == 'Other':
            if not league_name:
                raise forms.ValidationError(
                    '⚠️ Debe escribir el nombre de la liga personalizada',
                    code='custom_league_name_required'
                )
            
            # Validar que el nombre no sea muy corto
            if len(league_name) < 3:
                raise forms.ValidationError(
                    '⚠️ El nombre de la liga debe tener al menos 3 caracteres',
                    code='league_name_too_short'
                )
            
            # Validar que el nombre no sea muy largo
            if len(league_name) > 50:
                raise forms.ValidationError(
                    '⚠️ El nombre de la liga no puede tener más de 50 caracteres',
                    code='league_name_too_long'
                )
            
            return league_name
        else:
            return league  # Usar la liga seleccionada de la lista
    
    def clean_season(self):
        """Limpiar temporada"""
        season = self.cleaned_data.get('season', '').strip()
        return season if season else None


class LeagueFilterForm(forms.Form):
    """Formulario para filtrar ligas"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar liga...',
            'id': 'leagueSearch'
        })
    )
    
    country = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'País...',
            'id': 'countryFilter'
        })
    )


class MatchFilterForm(forms.Form):
    """Formulario para filtrar partidos"""
    
    league = forms.ModelChoiceField(
        queryset=League.objects.all(),
        required=False,
        empty_label="Todas las ligas",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'leagueFilter'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar equipos...',
            'id': 'matchSearch'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'dateFrom'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'dateTo'
        })
    )
    
    result = forms.ChoiceField(
        choices=[
            ('', 'Todos los resultados'),
            ('H', 'Victoria Local'),
            ('D', 'Empate'),
            ('A', 'Victoria Visitante'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'resultFilter'
        })
    )
