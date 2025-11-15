# Tipografía Predicta - Sistema de Fuentes

## 🎨 **Fuentes Implementadas**

### **Montserrat Bold - Títulos**
- **Uso**: Todos los títulos (h1, h2, h3, h4, h5, h6)
- **Pesos**: 400, 500, 600, 700, 800, 900
- **Características**: 
  - Fuente sans-serif moderna y elegante
  - Excelente legibilidad en pantallas
  - Transmite profesionalismo y tecnología
  - Ideal para títulos y encabezados

### **Inter Regular - Texto**
- **Uso**: Párrafos, texto general, elementos de interfaz
- **Pesos**: 400, 500, 600, 700
- **Características**:
  - Fuente optimizada para interfaces digitales
  - Alta legibilidad en todos los tamaños
  - Diseñada específicamente para pantallas
  - Perfecta para texto corrido y elementos de UI

## 🔧 **Implementación Técnica**

### **Variables CSS Globales**
```css
:root {
    --fuente-titulo: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --fuente-texto: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
```

### **Jerarquía de Títulos**
```css
h1 {
    font-family: var(--fuente-titulo);
    font-size: 2.5rem;
    font-weight: 800;
}

h2 {
    font-family: var(--fuente-titulo);
    font-size: 2rem;
    font-weight: 700;
}

h3 {
    font-family: var(--fuente-titulo);
    font-size: 1.75rem;
    font-weight: 600;
}

h4 {
    font-family: var(--fuente-titulo);
    font-size: 1.5rem;
    font-weight: 600;
}

h5 {
    font-family: var(--fuente-titulo);
    font-size: 1.25rem;
    font-weight: 600;
}

h6 {
    font-family: var(--fuente-titulo);
    font-size: 1.1rem;
    font-weight: 600;
}
```

### **Texto General**
```css
p, span, div, a, li, td, th {
    font-family: var(--fuente-texto);
    font-weight: 400;
}

strong, b {
    font-family: var(--fuente-texto);
    font-weight: 600;
}
```

## 📱 **Carga de Fuentes**

### **Google Fonts CDN**
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Montserrat:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
```

### **CSS Import (Alternativo)**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Montserrat:wght@400;500;600;700;800;900&display=swap');
```

## 🎯 **Aplicación por Módulos**

### **1. Tema Global**
- **Archivo**: `static/css/predicta-theme.css`
- **Variables**: `--fuente-titulo`, `--fuente-texto`
- **Aplicación**: Todos los elementos base del sistema

### **2. Autenticación**
- **Archivo**: `static/css/cuentas/auth.css`
- **Títulos**: Montserrat Bold para `.auth-title`
- **Texto**: Inter Regular para todo el contenido

### **3. Administración**
- **Archivo**: `static/css/cuentas/admin.css`
- **Títulos**: Montserrat Bold para `.admin-header h1`
- **Texto**: Inter Regular para formularios y tablas

### **4. Predicciones de IA**
- **Archivo**: `static/css/ai_predictions/ai-theme.css`
- **Variables**: `--ai-fuente-titulo`, `--ai-fuente-texto`
- **Títulos**: Montserrat Bold para headers de IA
- **Texto**: Inter Regular para contenido técnico

### **5. Cuotas y Apuestas**
- **Archivo**: `static/css/odds/odds-theme.css`
- **Variables**: `--odds-fuente-titulo`, `--odds-fuente-texto`
- **Títulos**: Montserrat Bold para headers de cuotas
- **Texto**: Inter Regular para datos numéricos

### **6. Datos de Fútbol**
- **Archivo**: `static/css/football_data/football-theme.css`
- **Variables**: `--football-fuente-titulo`, `--football-fuente-texto`
- **Títulos**: Montserrat Bold para headers de datos
- **Texto**: Inter Regular para estadísticas

## ✨ **Beneficios de la Nueva Tipografía**

### **Consistencia Visual**
- ✅ Jerarquía clara entre títulos y texto
- ✅ Identidad visual unificada en todo el sistema
- ✅ Transmite profesionalismo y modernidad

### **Legibilidad Optimizada**
- ✅ Inter diseñada específicamente para pantallas
- ✅ Montserrat excelente para títulos impactantes
- ✅ Mejor experiencia de lectura en todos los dispositivos

### **Rendimiento**
- ✅ Fuentes cargadas desde Google Fonts CDN
- ✅ Preconexión para carga rápida
- ✅ Fallbacks a fuentes del sistema

### **Mantenibilidad**
- ✅ Variables CSS centralizadas
- ✅ Fácil cambio de fuentes en el futuro
- ✅ Consistencia automática en nuevos módulos

## 🔄 **Fallbacks de Fuentes**

### **Montserrat (Títulos)**
```css
font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

### **Inter (Texto)**
```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

## 📊 **Pesos de Fuente Utilizados**

### **Montserrat**
- **800**: Títulos principales (h1)
- **700**: Títulos secundarios (h2)
- **600**: Títulos terciarios (h3, h4, h5, h6)

### **Inter**
- **400**: Texto normal (p, span, div)
- **600**: Texto en negrita (strong, b)

Esta tipografía está perfectamente integrada con la paleta de colores Predicta, creando una identidad visual cohesiva y profesional para el sistema de análisis deportivo.















