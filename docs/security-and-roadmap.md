# Guía de Seguridad y Mejoras Futuras

## Buenas prácticas implementadas

### Variables de entorno
- Todas las credenciales (DATABASE_URL, API_KEY) se leen exclusivamente desde variables de entorno.
- Los archivos `.env` están listados en `.gitignore` y nunca se suben al repositorio.
- Se provee `.env.example` sin valores reales como documentación.

### Autenticación entre servicios
- El sistema local se autentica con el backend usando una API Key en el header `X-API-Key`.
- La comparación de la API Key se realiza en tiempo constante (`timingSafeEqual`) para evitar ataques de timing.
- Las API Keys se generan con `openssl rand -hex 32` (256 bits de entropía).

### Protección contra suplantación
- Liveness detection de doble factor: parpadeo (EAR) + movimiento de cabeza (yaw angle).
- Sin liveness, el reconocimiento facial no se evalúa. No importa qué tan buena sea la foto.

### Bloqueo por intentos fallidos
- Después de `MAX_FAILED_ATTEMPTS` intentos fallidos consecutivos, el usuario queda bloqueado `LOCKOUT_MINUTES` minutos.
- Se genera una alerta automática en la tabla `alertas`.
- El contador se resetea al primer acceso exitoso.

### Base de datos
- Uso de consultas parametrizadas en todos los endpoints (`$1`, `$2`, ...). Nunca interpolación de strings.
- Transacciones explícitas (`BEGIN / COMMIT / ROLLBACK`) en operaciones compuestas.
- Conexión SSL obligatoria con Neon (`sslmode=require`).
- Pool de conexiones con límite bajo (max: 5) para respetar los límites serverless de Neon.

### Embeddings
- Los vectores faciales se almacenan como JSONB, nunca como texto plano ni binario sin estructura.
- El modelo `dlib_face_recognition_resnet_model_v1` genera embeddings de 128 dimensiones.
- La tolerancia de comparación (default: 0.50) es configurable por variable de entorno.

### Código
- Arquitectura modular: cada clase tiene una única responsabilidad.
- Sin credenciales hardcodeadas en ningún archivo de código fuente.
- Logging estructurado: los logs nunca imprimen valores de API Keys ni encodings completos.

---

## Mejoras futuras recomendadas

### Dashboard web (prioridad alta)
Construir un panel en Next.js/React con:
- Mapa de calor de accesos por hora/día.
- Listado de alertas activas con resolución manual.
- Gestión de usuarios (alta, baja, actualización biométrica).
- Gráficos de tendencias de intentos fallidos.

### Notificaciones en tiempo real (prioridad alta)
- Integrar Webhooks o WebSockets (Pusher/Ably) para alertas instantáneas.
- Envío de emails transaccionales (Resend o SendGrid) al detectar intrusos.
- Integración con Slack/Telegram para alertas del equipo de seguridad.

### Mejoras de IA
- Reemplazar dlib por InsightFace (ArcFace) para mayor precisión en condiciones adversas.
- Anti-spoofing con modelos de profundidad (depth maps) usando cámaras IR o estéreo.
- Detección de máscaras faciales y condiciones de baja iluminación con clasificador ligero.
- Reconocimiento de múltiples rostros simultáneos para control de acceso grupal.

### Escalabilidad del backend
- Migrar a Edge Functions de Vercel para latencia sub-10ms globalmente.
- Caché de embeddings con Redis (Upstash) para evitar consultas BD en cada autenticación.
- Rate limiting por IP con middleware en Vercel (o Cloudflare Workers en frontal).
- Versionado de API: `/api/v1/register`, `/api/v2/register`.

### Seguridad avanzada
- Rotación automática de API Keys con expiración configurable.
- Cifrado de embeddings en reposo usando pgcrypto (extensión de PostgreSQL).
- Logs de auditoría inmutables con hash encadenado (como un mini blockchain de accesos).
- Integración con un Identity Provider (Auth0, Keycloak) para autenticación de administradores.

### Infraestructura
- Contenedorización del sistema local con Docker para despliegue reproducible.
- Orquestación multi-cámara con un proceso supervisor (supervisord o systemd).
- Backup automático de la BD con pg_dump programado (cron en Neon o GitHub Actions).
- Monitoreo con Sentry (errores) + Datadog o Grafana (métricas de rendimiento).

### Cumplimiento normativo
- Implementar derecho al olvido: endpoint `DELETE /api/usuarios/:id` que elimina todos los datos biométricos.
- Política de retención de logs configurable (ej. borrar logs > 90 días automáticamente).
- Consentimiento explícito de registro biométrico almacenado en BD con timestamp.
- Documentación de tratamiento de datos para cumplir GDPR/Ley 1581 (Colombia).
