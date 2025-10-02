# 🤖 Bot de Apuestas Deportivas Django

Un bot automatizado en Django que utiliza **The Odds API** y **Betfair Exchange API** para detectar y ejecutar oportunidades de arbitraje en apuestas deportivas.

## 📋 Características

- **Integración con The Odds API**: Obtiene cuotas en tiempo real de múltiples casas de apuestas
- **Integración con Betfair Exchange API**: Coloca apuestas automáticamente usando `betfairlightweight`
- **Detección de arbitraje**: Compara cuotas entre fuentes para encontrar oportunidades
- **Base de datos SQLite**: Registra todas las operaciones y estadísticas
- **Interfaz de administración Django**: Panel de control completo
- **Comandos de gestión**: Herramientas para sincronizar datos y ejecutar el bot
- **Manejo de errores robusto**: Gestión de timeouts, fallos de conexión y autenticación
- **Configuración flexible**: Parámetros personalizables para estrategias

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone <tu-repositorio>
cd betting_bot
```

### 2. Crear entorno virtual
```bash
python -m venv venv
venv\Scripts\activate  # En Windows
# source venv/bin/activate  # En Linux/Mac
```

### 3. Instalar dependencias
```bash
pip install django requests betfairlightweight python-dotenv
```

### 4. Configurar credenciales
Copia el archivo `env_example.txt` como `.env` y completa tus credenciales:

```bash
cp env_example.txt .env
```

Edita el archivo `.env`:
```env
# Django Configuration
SECRET_KEY=tu-clave-secreta-de-django

# The Odds API Configuration
ODDS_API_KEY=tu_clave_de_odds_api_aqui

# Betfair API Configuration
BETFAIR_APP_KEY=tu_app_key_de_betfair_aqui
BETFAIR_USERNAME=tu_usuario_de_betfair_aqui
BETFAIR_PASSWORD=tu_contraseña_de_betfair_aqui
BETFAIR_SANDBOX=True

# Bot Configuration
SPORT_KEY=soccer_epl
REGIONS=uk,us,eu
MARKETS=h2h
ODDS_FORMAT=decimal

# Betting Configuration
MIN_STAKE=1.0
MAX_STAKE=10.0
MIN_EDGE=0.05

# Execution Configuration
EXECUTION_INTERVAL=10
```

### 5. Configurar base de datos
```bash
python manage.py migrate
```

### 6. Crear superusuario (opcional)
```bash
python manage.py createsuperuser
```

## 🔑 Obtener Credenciales

### The Odds API
1. Visita [the-odds-api.com](https://the-odds-api.com)
2. Regístrate para obtener una API key gratuita
3. Copia tu API key en el archivo `.env`

### Betfair Exchange API
1. Visita [betfair.com](https://betfair.com) y crea una cuenta
2. Solicita acceso a la API en [developer.betfair.com](https://developer.betfair.com)
3. Obtén tu App Key y configura tus credenciales
4. **Importante**: Para pruebas, el bot está configurado en modo sandbox por defecto

## 🏃‍♂️ Uso

### 1. Probar las APIs
```bash
python manage.py test_apis
```

### 2. Sincronizar datos
```bash
# Sincronizar deportes y cuotas de The Odds API
python manage.py sync_odds --sync-sports

# Sincronizar datos de Betfair
python manage.py sync_betfair --all
```

### 3. Ejecutar el bot
```bash
# Ejecutar bot con configuración por defecto
python manage.py run_bot

# Ejecutar con parámetros personalizados
python manage.py run_bot --strategy conservative --interval 30 --cycles 100

# Modo de prueba (no coloca apuestas reales)
python manage.py run_bot --dry-run
```

### 4. Interfaz web
```bash
python manage.py runserver
```
Visita http://127.0.0.1:8000/admin/ (usuario: admin, contraseña: admin123)

## 📊 Estructura del Proyecto

```
betting_bot/
├── betting_bot/          # Configuración del proyecto Django
├── odds/                 # Aplicación para The Odds API
│   ├── models.py         # Modelos de base de datos
│   ├── services.py       # Lógica de negocio
│   └── admin.py          # Interfaz de administración
├── betfair/              # Aplicación para Betfair API
│   ├── models.py         # Modelos de base de datos
│   ├── services.py       # Lógica de negocio
│   └── admin.py          # Interfaz de administración
├── betting/              # Aplicación principal del bot
│   ├── models.py         # Modelos de base de datos
│   ├── services.py       # Lógica de arbitraje
│   ├── admin.py          # Interfaz de administración
│   └── management/       # Comandos de Django
│       └── commands/
│           ├── sync_odds.py      # Sincronizar cuotas
│           ├── sync_betfair.py   # Sincronizar Betfair
│           ├── run_bot.py        # Ejecutar bot
│           └── test_apis.py      # Probar APIs
├── manage.py             # Script de gestión Django
├── env_example.txt       # Ejemplo de configuración
└── README.md            # Este archivo
```

## 🧠 Lógica del Bot

El bot ejecuta los siguientes pasos en cada ciclo:

1. **Obtener cuotas**: Consulta The Odds API para obtener cuotas actuales
2. **Obtener mercados**: Consulta Betfair para obtener mercados disponibles
3. **Buscar coincidencias**: Encuentra eventos que coincidan entre ambas fuentes
4. **Calcular arbitraje**: Analiza oportunidades donde Betfair tenga mejores cuotas
5. **Tomar decisiones**: Coloca apuestas solo en oportunidades de alta confianza
6. **Registrar datos**: Guarda todas las operaciones en la base de datos

## 📈 Estrategia de Arbitraje

El bot utiliza una estrategia de arbitraje simple:

- **Edge mínimo**: Solo actúa si Betfair ofrece al menos 5% mejor cuota
- **Confianza**: Evalúa la confiabilidad basada en liquidez y número de casas
- **Stake óptimo**: Calcula el tamaño de apuesta usando Kelly Criterion simplificado
- **Filtros de seguridad**: Verifica saldo disponible y límites de apuesta

## 🗄️ Base de Datos

La base de datos incluye las siguientes tablas principales:

### Odds App
- `Sport`: Deportes disponibles
- `Bookmaker`: Casas de apuestas
- `Match`: Partidos/matches
- `Odds`: Cuotas históricas
- `AverageOdds`: Cuotas promedio calculadas

### Betfair App
- `BetfairEventType`: Tipos de eventos (deportes)
- `BetfairEvent`: Eventos específicos
- `BetfairMarket`: Mercados de apuestas
- `BetfairRunner`: Opciones de apuesta
- `BetfairOrder`: Órdenes de apuesta
- `BetfairAccount`: Información de cuenta

### Betting App
- `ArbitrageOpportunity`: Oportunidades detectadas
- `BettingStrategy`: Estrategias de apuestas
- `BotSession`: Sesiones del bot
- `BotCycle`: Ciclos de ejecución
- `BotConfiguration`: Configuración del bot
- `Alert`: Alertas del sistema

## ⚠️ Advertencias Importantes

1. **Solo para fines educativos**: Este bot es para aprendizaje y experimentación
2. **Usa sandbox**: Siempre prueba primero en modo sandbox de Betfair
3. **Gestiona el riesgo**: Configura stakes pequeños y límites de pérdida
4. **Cumple regulaciones**: Asegúrate de cumplir las leyes locales de apuestas
5. **Monitorea constantemente**: Supervisa el bot y sus operaciones

## 🔧 Comandos Disponibles

### Gestión de datos
```bash
# Sincronizar cuotas
python manage.py sync_odds [--sport soccer_epl] [--sync-sports]

# Sincronizar Betfair
python manage.py sync_betfair [--event-types] [--events] [--markets] [--all]
```

### Ejecución del bot
```bash
# Ejecutar bot
python manage.py run_bot [--strategy default] [--interval 10] [--cycles 100] [--dry-run]
```

### Pruebas
```bash
# Probar APIs
python manage.py test_apis [--odds] [--betfair]
```

## 🐛 Solución de Problemas

### Error de autenticación en Betfair
- Verifica tus credenciales en `.env`
- Asegúrate de usar el App Key correcto
- Comprueba que tu cuenta tenga permisos de API

### No se obtienen cuotas
- Verifica tu API key de The Odds API
- Comprueba tu límite de requests mensual
- Revisa la conectividad a internet

### Base de datos bloqueada
- Cierra otras conexiones a la base de datos
- Reinicia el bot si es necesario

## 📝 Logs y Monitoreo

El bot proporciona logging detallado:
- ✅ Operaciones exitosas
- ⚠️ Advertencias y filtros
- ❌ Errores y fallos
- 📊 Estadísticas periódicas

Los logs se guardan en `logs/betting_bot.log`

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es para fines educativos únicamente. Úsalo bajo tu propia responsabilidad.

---

**⚠️ Disclaimer**: Las apuestas deportivas conllevan riesgo de pérdida de dinero. Este bot es únicamente para fines educativos y experimentales. Los usuarios son responsables de cumplir todas las leyes y regulaciones aplicables.

## 🎯 Próximos Pasos

1. **Configura tus credenciales** en el archivo `.env`
2. **Prueba las APIs** con `python manage.py test_apis`
3. **Sincroniza los datos** con los comandos de sync
4. **Ejecuta el bot** en modo sandbox primero
5. **Monitorea los resultados** en el panel de administración
6. **Personaliza la estrategia** según tus necesidades

¡Disfruta explorando el mundo del arbitraje deportivo! 🚀
