# DOCUMENTO TÉCNICO COMPLETO DEL FRONTEND

**Formato:** Checklist de Validación de Entrega  
**Producto:** Plataforma de Bienestar con Coach Digital Activo  
**Stack:** Angular + Tailwind  
**Rol:** UX + Frontend  
**Propósito:** Confirmar que el Front cumple visión, UX, técnica y ejecución

---

## CHECKLIST DE VALIDACIÓN — READY TO SHIP

> **Este documento es normativo.**  
> Si un punto no se cumple, el Front **NO** está terminado, aunque “funcione”.

---

## 1. CHECKLIST GLOBAL (APLICA A TODO EL FRONT)

### 1.1 Principios del Coach

- [ ] Todas las pantallas muestran estado actual
- [ ] Todas las pantallas muestran meta activa
- [ ] Todas las pantallas indican siguiente acción clara
- [ ] El lenguaje es directo, firme y alentador
- [ ] No hay pantallas “informativas pasivas”

---

### 1.2 Separación de responsabilidades

- [ ] Front no calcula dinero, descuentos, comisiones ni estados
- [ ] Todo valor económico viene del backend
- [ ] No existen valores “hardcodeados” de negocio
- [ ] El Front solo renderiza y guía

---

### 1.3 UX y consistencia

- [ ] El usuario entiende qué hacer en < 3 segundos
- [ ] No hay más de un CTA principal por pantalla
- [ ] El CTA principal está visible sin scroll (mobile)
- [ ] No hay ambigüedad visual (colores, estados)

---

## 2. ARQUITECTURA ANGULAR

### 2.1 Estructura del proyecto

- [ ] Módulos separados correctamente:
  - public
  - store
  - dashboard
  - admin
  - shared
  - core
- [ ] Lazy loading por módulo
- [ ] No hay componentes gigantes (>300 líneas)

---

### 2.2 Core

- [ ] Interceptor JWT activo
- [ ] Guards por rol funcionando
- [ ] Manejo centralizado de sesión (session-context)
- [ ] Persistencia correcta de:
  - userId
  - referrerUserId
  - landingSlug

---

## 3. LANDING PÚBLICA POR REFERIDO

**Ruta:** `/r/:refCode/:landingSlug`

### Validaciones

- [ ] Se resuelve refCode
- [ ] Se guarda referrerUserId
- [ ] Se renderiza contenido dinámico de la landing
- [ ] Hero visible y dominante
- [ ] CTA único: “Empieza hoy”
- [ ] Registro embebido funcional
- [ ] Sin header / footer / navegación externa
- [ ] Copy alineado al tono del coach

---

## 4. REGISTRO / LOGIN

### Validaciones

- [ ] Formularios reactivos
- [ ] Validaciones visibles
- [ ] Mensajes firmes post-submit
- [ ] Redirección correcta según rol
- [ ] El referido se conserva tras registro

---

## 5. DASHBOARD — TABLERO DE ENTRENAMIENTO

### 5.1 Estructura base

- [ ] Coach Header sticky
- [ ] Meta activa en primer bloque
- [ ] Barra de progreso visible
- [ ] Mensaje claro de falta o logro
- [ ] CTA principal único
- [ ] Métricas clave visibles
- [ ] Secciones de misiones y logros

---

### 5.2 Coach Header

- [ ] Mensaje contextual según estado
- [ ] No genérico
- [ ] No decorativo

---

### 5.3 Meta Activa

- [ ] Solo una meta activa
- [ ] Progreso real (backend)
- [ ] Texto: “Te faltan $X” o “Cumpliste”
- [ ] Colores semánticos correctos

---

### 5.4 Siguiente Acción

- [ ] Botón claro y dominante
- [ ] Acción ejecutable
- [ ] Texto directo (“Haz esto ahora”)

---

## 6. GAMIFICACIÓN (METAS, LOGROS, MISIONES)

### 6.1 Metas

- [ ] Metas alineadas al modelo de negocio
- [ ] Medidores claros:
  - compras
  - visitas
  - registros
  - ventas
- [ ] Reset mensual donde aplica
- [ ] Nunca ocultas

---

### 6.2 Logros

- [ ] Logros desbloqueados correctamente
- [ ] Persisten históricamente
- [ ] No se pierden por inactividad
- [ ] Visualización clara (badges)

---

### 6.3 Misiones

- [ ] Checklist visible
- [ ] Progreso por paso
- [ ] CTA por misión
- [ ] Misiones no bloqueantes

---

## 7. TIENDA Y CHECKOUT

### 7.1 Catálogo y carrito

- [ ] Catálogo renderiza correctamente
- [ ] Carrito reactivo
- [ ] Subtotal visible
- [ ] No cálculo de descuento en Front

---

### 7.2 Cotización

- [ ] Se consume `/checkout/quote`
- [ ] Se muestra descuento (si aplica)
- [ ] Mensaje claro si no hay descuento
- [ ] Snapshot respetado

---

### 7.3 Checkout

- [ ] Orden creada correctamente
- [ ] Redirección a pasarela
- [ ] Manejo de estados de error
- [ ] Confirmación post-pago clara

---

## 8. ÓRDENES

- [ ] Listado correcto por mes
- [ ] Estado claro
- [ ] Montos correctos
- [ ] Mensaje contextual (“Tu historial no miente”)

---

## 9. COMISIONES

- [ ] Total mensual correcto
- [ ] Desglose por nivel
- [ ] Gráficas sobrias
- [ ] Lenguaje de consecuencia, no promesa

---

## 10. RED (NIVEL 1)

- [ ] Lista de referidos directos
- [ ] Estado activo/inactivo visible
- [ ] Volumen visible
- [ ] Mensaje de liderazgo claro

---

## 11. LANDINGS — PANEL PROMOTOR

- [ ] Lista de landings disponibles
- [ ] Preview funcional
- [ ] Copiar link correcto
- [ ] El link incluye refCode + landingSlug

---

## 12. ADMIN — LANDINGS (MARKETING)

- [ ] CRUD completo de landings
- [ ] Preview en vivo
- [ ] Activar / desactivar sin deploy
- [ ] Marketing no toca código

---

## 13. ESTADOS Y ERRORES

- [ ] Loading visible
- [ ] Errores claros
- [ ] Sin mensajes técnicos al usuario
- [ ] No pantallas en blanco

---

## 14. RESPONSIVE & ACCESIBILIDAD

- [ ] Mobile-first validado
- [ ] Tablet y desktop correctos
- [ ] Botones accesibles
- [ ] Contraste adecuado

---

## 15. PERFORMANCE

- [ ] Lazy loading real
- [ ] Componentes reutilizables
- [ ] No llamadas API innecesarias
- [ ] Render rápido del dashboard

---

## 16. DEFINICIÓN FINAL DE “READY”

El Front está **LISTO** solo si:

- [ ] Todas las pantallas cumplen el rol de coach
- [ ] El usuario nunca está perdido
- [ ] Siempre hay una meta y una acción
- [ ] El Front no toma decisiones de negocio
- [ ] El checklist completo está marcado

**Si falta un solo punto → NO ESTÁ LISTO.**

---

## CIERRE

Este documento no es sugerencia.  
Es el contrato de calidad del Frontend.
