# Predicta - AI Football Prediction System

Sistema de predicción de fútbol basado en inteligencia artificial que utiliza múltiples modelos estadísticos para generar predicciones precisas sobre partidos de fútbol.

## 🚀 Características Principales

### 🤖 Modelos de Predicción
- **Ensemble Average**: Modelo oficial que combina múltiples algoritmos estadísticos
- **Simple Poisson**: Basado en distribución de Poisson para eventos raros
- **Simple Average**: Promedio histórico con ajustes contextuales

### 📊 Tipos de Predicciones
- **Remates (Shots)**: Total, Local, Visitante
- **Goles (Goals)**: Total, Local, Visitante  
- **Córners (Corners)**: Total, Local, Visitante
- **Ambos Marcan**: Probabilidad de que ambos equipos anoten

### 🎯 Funcionalidades
- **Predicciones en Tiempo Real**: Generación instantánea de predicciones
- **Análisis Estadístico Avanzado**: Múltiples algoritmos de machine learning
- **Interfaz Web Intuitiva**: Dashboard moderno y fácil de usar
- **Historial de Predicciones**: Seguimiento de predicciones anteriores
- **Validación de Modelos**: Sistema de evaluación de rendimiento

## 🛠️ Tecnologías Utilizadas

- **Backend**: Django 4.x
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **IA/ML**: Scikit-learn, NumPy, Pandas
- **APIs**: Betfair API, Odds API

## 📦 Instalación

### Requisitos Previos
- Python 3.8+
- pip
- Git

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/johnschneiider/Predicta.git
cd Predicta
```

2. **Crear entorno virtual**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar base de datos**
```bash
python manage.py migrate
python manage.py createsuperuser
```

5. **Cargar datos de ejemplo**
```bash
python manage.py create_sample_leagues
python manage.py create_sample_data
```

6. **Ejecutar servidor**
```bash
python manage.py runserver
```

7. **Acceder a la aplicación**
```
http://127.0.0.1:8000/
```

## 📁 Estructura del Proyecto

```
Predicta/
├── ai_predictions/          # Módulo principal de predicciones
│   ├── models.py           # Modelos de datos
│   ├── views.py            # Vistas y lógica de negocio
│   ├── simple_models.py    # Modelos de predicción simples
│   ├── advanced_models.py  # Modelos avanzados de ML
│   └── templates/          # Plantillas HTML
├── football_data/          # Gestión de datos de fútbol
├── betting/                # Sistema de apuestas
├── odds/                   # Gestión de cuotas
├── cuentas/                # Sistema de usuarios
└── betting_bot/            # Configuración principal
```

## 🎮 Uso del Sistema

### 1. Crear Predicción
1. Ve a "Nueva Predicción"
2. Selecciona equipos y liga
3. El sistema generará predicciones automáticamente
4. Revisa los resultados en la tabla

### 2. Ver Historial
1. Accede a "Historial de Predicciones"
2. Filtra por fecha o equipos
3. Analiza el rendimiento de las predicciones

### 3. Dashboard
1. Ve el resumen general del sistema
2. Estadísticas de rendimiento
3. Gráficos de tendencias

## 🔧 Configuración Avanzada

### Variables de Entorno
Crea un archivo `.env` con:
```
SECRET_KEY=tu_clave_secreta
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
BETFAIR_USERNAME=tu_usuario
BETFAIR_PASSWORD=tu_contraseña
```

### Configuración de Producción
1. Cambiar `DEBUG=False` en settings.py
2. Configurar base de datos PostgreSQL
3. Configurar servidor web (Nginx + Gunicorn)
4. Configurar SSL/HTTPS

## 📈 Modelos de Predicción

### Ensemble Average (Modelo Oficial)
- **Descripción**: Combina Simple Poisson y Simple Average
- **Ventaja**: Reduce el sesgo individual de cada modelo
- **Precisión**: Mayor confiabilidad estadística

### Simple Poisson
- **Algoritmo**: Distribución de Poisson
- **Uso**: Eventos raros (goles, remates)
- **Fortaleza**: Bueno para eventos de baja frecuencia

### Simple Average
- **Algoritmo**: Promedios históricos con ajustes
- **Uso**: Tendencias generales
- **Fortaleza**: Estable y confiable

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 👨‍💻 Autor

**John Schneider**
- GitHub: [@johnschneiider](https://github.com/johnschneiider)
- Proyecto: [Predicta](https://github.com/johnschneiider/Predicta)

## 🙏 Agradecimientos

- Django Framework
- Scikit-learn
- Bootstrap
- Betfair API
- Comunidad de desarrolladores de Python

---

**Predicta** - Predicciones de fútbol con inteligencia artificial 🚀⚽