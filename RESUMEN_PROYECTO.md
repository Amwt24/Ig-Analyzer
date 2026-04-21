# IGNewScraper - Estado del Proyecto

## Objetivo
Crear un scraper de Instagram utilizando Scrapy que permita extraer información pública de perfiles (nickname, seguidores, seguidos, biografía) y sus publicaciones (likes, comentarios, contenido) utilizando credenciales/cookies pre-autenticadas.

## Credenciales de Prueba
- **Usuario**: amwt820
- **Password**: Helados24*123

## Avances Realizados
1.  **Refactorización del Scraper (`ScraperIG`)**:
    - Se incluyó la carga de variables de entorno mediante `.env` (oculto en git) y `python-dotenv` para administrar las cookies.
    - Se añadió manejo de códigos HTTP (ej. 429) en el manejador del Spider para no fallar silenciosamente.
2.  **Decisión Arquitectónica (PIVOTE)**:
    - Se comprobó que, pese a tener cookies válidas, los modelos de Instagram limitan el raspado HTTP puro lanzando código 429 (Baneo de IP / Detección Anti-Bot).
    - **Nueva Estrategia**: Se ha decidido abandonar `web_profile_info` / `Scrapy` a favor de una **API de terceros (ej. RapidAPI)** para abstraer el problema de las IPs y el Fingerprinting.

## Problemas Detectados y Resueltos
- [Resuelto] Scrapy fallaba en silencio: solucionado activando lectura del HTTP 429 en la respuesta.
- [Evitado] Instagram bloqueaba activamente las IPs y demandaba desafíos JS: se sorteará utilizando una API especializada en Instagram.

## Próximos Pasos (Arquitectura Final)
1. **BackEnd**: Crear un servidor (NodeJS/Express o FastAPI) que maneje un endpoint intermedio para consultar con la API seleccionada y proteja nuestra API Key.
2. **FrontEnd**: Desarrollar la interfaz gráfica donde el usuario podrá introducir el nombre de la cuenta (ej. `andersliinky`) a buscar y donde se visualizará el perfil extraído y el listado de posts.
3. **Integración**: Conectar el FrontEnd con el BackEnd y probar llamadas reales a la API de terceros.
