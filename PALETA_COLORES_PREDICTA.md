# Paleta de Colores Predicta - Sistema de Análisis Deportivo

## 🎨 **Paleta Principal**

### **Colores Base**
- **Azul Oscuro**: `#0A1F44` - Fondo principal, transmite confianza y seriedad
- **Azul Eléctrico**: `#007BFF` - Botones, acentos, links principales
- **Verde Lima**: `#5CFF5C` - Indicadores de éxito, predicciones ganadoras
- **Gris Medio**: `#B0B3B8` - Textos secundarios, elementos de apoyo
- **Blanco**: `#FFFFFF` - Fondos de tarjetas, texto sobre fondos oscuros

### **Colores Derivados**
- **Azul Oscuro Hover**: `#0D2A5A` - Estados hover del azul oscuro
- **Azul Eléctrico Hover**: `#0056B3` - Estados hover del azul eléctrico
- **Verde Lima Hover**: `#4AE64A` - Estados hover del verde lima
- **Gris Claro**: `#F8F9FA` - Fondos de secciones
- **Gris Oscuro**: `#6C757D` - Textos terciarios

## 🎯 **Aplicación por Módulos**

### **1. Sistema de Autenticación**
- **Archivo**: `static/css/cuentas/auth.css`
- **Uso**: Login, registro, formularios de autenticación
- **Características**: Gradientes suaves, efectos de hover elegantes

### **2. Panel de Administración**
- **Archivo**: `static/css/cuentas/admin.css`
- **Uso**: Gestión de usuarios, formularios administrativos
- **Características**: Interfaz profesional, botones de acción claros

### **3. Predicciones de IA**
- **Archivo**: `static/css/ai_predictions/ai-theme.css`
- **Uso**: Dashboard de IA, formularios de predicción, resultados
- **Características**: Enfoque en tecnología, indicadores de éxito

### **4. Cuotas y Apuestas**
- **Archivo**: `static/css/odds/odds-theme.css`
- **Uso**: Dashboard de cuotas, tarjetas de partidos, filtros
- **Características**: Dinamismo, indicadores en vivo, valores destacados

### **5. Datos de Fútbol**
- **Archivo**: `static/css/football_data/football-theme.css`
- **Uso**: Importación de datos, visualización de partidos, estadísticas
- **Características**: Organización clara, tarjetas informativas

## 🎨 **Tema Global**

### **Archivo Principal**
- **Archivo**: `static/css/predicta-theme.css`
- **Uso**: Variables CSS globales, estilos base, componentes comunes
- **Incluye**: Botones, tarjetas, formularios, tablas, alertas

### **Variables CSS Disponibles**
```css
:root {
    --azul-oscuro: #0A1F44;
    --azul-electrico: #007BFF;
    --verde-lima: #5CFF5C;
    --gris-medio: #B0B3B8;
    --blanco: #FFFFFF;
    
    --gradiente-principal: linear-gradient(135deg, var(--azul-oscuro) 0%, var(--azul-electrico) 100%);
    --gradiente-secundario: linear-gradient(135deg, var(--azul-electrico) 0%, var(--verde-lima) 100%);
    --gradiente-oscuro: linear-gradient(135deg, var(--azul-oscuro) 0%, #1A3A6B 100%);
    
    --sombra-suave: 0 4px 15px rgba(10, 31, 68, 0.1);
    --sombra-media: 0 8px 25px rgba(10, 31, 68, 0.15);
    --sombra-fuerte: 0 15px 35px rgba(10, 31, 68, 0.2);
    
    --borde-redondeado: 8px;
    --borde-redondeado-grande: 15px;
}
```

## 🚀 **Implementación**

### **1. Template Base**
El archivo `templates/base.html` incluye automáticamente:
```html
<link rel="stylesheet" href="{% static 'css/predicta-theme.css' %}">
```

### **2. Módulos Específicos**
Cada módulo incluye su CSS específico:
```html
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/ai_predictions/ai-theme.css' %}">
{% endblock %}
```

### **3. Uso en Componentes**
```html
<div class="card prediction-card">
    <div class="card-header">
        <h3>Predicción IA</h3>
    </div>
    <div class="card-body">
        <span class="success-indicator">Ganadora</span>
    </div>
</div>
```

## 🎯 **Características de Diseño**

### **Transmite Seriedad y Tecnología**
- **Azul oscuro** como base principal para confianza
- **Azul eléctrico** para elementos interactivos
- **Verde lima** para indicadores de éxito y predicciones ganadoras

### **Precisión y Análisis**
- Colores contrastantes para mejor legibilidad
- Colores planos para un diseño limpio y moderno
- Sombras consistentes para jerarquía

### **Experiencia de Usuario**
- Estados hover claros y consistentes
- Transiciones suaves (0.3s ease)
- Responsive design para todos los dispositivos

## 📱 **Responsive Design**

Todos los archivos CSS incluyen media queries para:
- **Desktop**: Diseño completo con todas las características
- **Tablet**: Ajustes de grid y espaciado
- **Mobile**: Layout vertical, botones más grandes

## 🔧 **Mantenimiento**

### **Actualización de Colores**
Para cambiar un color en todo el proyecto:
1. Modificar la variable en `predicta-theme.css`
2. Todos los módulos heredarán automáticamente el cambio

### **Nuevos Módulos**
Para agregar un nuevo módulo:
1. Crear archivo CSS específico en `static/css/[modulo]/`
2. Usar las variables CSS globales
3. Incluir en el template correspondiente

## ✨ **Efectos Especiales**

### **Animaciones**
- `fadeInUp`: Entrada suave de elementos
- `pulse`: Indicadores en vivo
- `hover`: Transformaciones y sombras

### **Colores Planos**
- **Principal**: Azul oscuro sólido
- **Secundario**: Azul eléctrico sólido
- **Éxito**: Verde lima sólido

### **Sombras**
- **Suave**: Para tarjetas y elementos ligeros
- **Media**: Para elementos interactivos
- **Fuerte**: Para modales y elementos destacados

Esta paleta de colores está diseñada específicamente para un sistema de análisis deportivo como Predicta, transmitiendo profesionalismo, tecnología y precisión en el análisis de datos.
