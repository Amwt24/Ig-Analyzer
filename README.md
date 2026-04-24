# IGNewScraper 📸

Un scraper modular de Instagram de alto rendimiento que utiliza **FastAPI** en el backend y **React (Vite)** en el frontend. El sistema emplea **Playwright** con técnicas de evasión de detección para extraer información pública de perfiles de forma segura y eficiente.

## 🚀 Arquitectura del Proyecto

El proyecto está dividido en dos componentes principales:

### 1. BackEnd (Python/FastAPI)
- **Tecnologías**: FastAPI, Playwright, Playwright-Stealth, MongoDB (Motor).
- **Funcionalidades**:
  - Scraping autónomo de perfiles de Instagram.
  - Gestión de sesiones y cookies para evitar bloqueos.
  - API RESTful para servir los datos al frontend.
  - Integración con base de datos NoSQL para persistencia (opcional).

### 2. FrontEnd (React/TypeScript)
- **Tecnologías**: React 19, Vite, TailwindCSS (o Vanilla CSS), Lucide React.
- **Funcionalidades**:
  - Interfaz moderna y reactiva.
  - Visualización de estadísticas de perfil (seguidores, seguidos, posts).
  - Galería de publicaciones recientes y visualización de comentarios.

---

## 🛠️ Instalación y Configuración

### Requisitos Previos
- Node.js (v18+)
- Python (3.9+)
- Navegador Chromium (instalado automáticamente por Playwright)

### Configuración del BackEnd
1. Entra en la carpeta del backend:
   ```bash
   cd BackEnd
   ```
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Configura el archivo `.env` en `BackEnd/`:
   ```env
   IG_USERNAME=tu_usuario
   IG_PASSWORD=tu_contraseña
   MONGODB_URI=tu_uri_de_mongodb
   IG_COOKIE_STRING="tus_cookies_aqui"
   ```
4. Ejecuta el servidor:
   ```bash
   uvicorn main:app --reload
   ```

### Configuración del FrontEnd
1. Entra en la carpeta del frontend:
   ```bash
   cd FrontEnd
   ```
2. Instala las dependencias:
   ```bash
   npm install
   ```
3. Ejecuta el entorno de desarrollo:
   ```bash
   npm run dev
   ```

---

## 🔍 Notas de Desarrollo

- **Evasión de detección**: El scraper utiliza `playwright-stealth` para minimizar las posibilidades de ser detectado como un bot por Instagram.
- **Sesiones**: El sistema intenta mantener una sesión activa en `session_state.json`. Si la sesión expira, utiliza las credenciales del `.env` para regenerarla automáticamente.
- **Limitaciones**: Respeta los límites de tasa (rate limiting) de Instagram para evitar baneos de IP.

---

## 📄 Licencia
Este proyecto es para fines educativos y de investigación. El uso de scrapers puede violar los términos de servicio de Instagram. Úsalo bajo tu propia responsabilidad.
