# Referencia de API — Smart Security System

## Base URL
```
https://tu-proyecto.vercel.app
```

## Autenticación
Todos los endpoints requieren el header:
```
X-API-Key: <tu_api_key>
```

---

## Endpoints

### POST /api/register
Registra un nuevo usuario con datos biométricos.

**Request**
```json
{
  "nombre":   "Ana García",
  "email":    "ana@empresa.com",
  "encoding": [0.123, -0.456, ...]
}
```

**Response 201**
```json
{
  "usuario_id": 5,
  "mensaje": "Usuario registrado correctamente"
}
```

**Errores**
| Código | Causa |
|--------|-------|
| 400 | Campos faltantes o encoding con tamaño incorrecto |
| 409 | Email ya registrado |
| 403 | API Key inválida |

---

### POST /api/login
Registra el resultado de un intento de autenticación.

**Request**
```json
{
  "usuario_id": 5,
  "estado":     "permitido",
  "confianza":  0.94,
  "metodo":     "facial"
}
```

**Response 200 — acceso concedido**
```json
{
  "acceso": true,
  "mensaje": "Bienvenido"
}
```

**Response 200 — acceso denegado**
```json
{
  "acceso": false,
  "mensaje": "Acceso denegado",
  "intentos_fallidos": 2
}
```

**Response 423 — usuario bloqueado**
```json
{
  "error": "Usuario bloqueado temporalmente",
  "bloqueado_hasta": "2025-06-01T15:30:00Z"
}
```

---

### GET /api/usuarios
Retorna todos los usuarios activos con sus embeddings.

**Query params** (opcionales)
| Param | Tipo | Descripción |
|-------|------|-------------|
| — | — | Sin parámetros por ahora |

**Response 200**
```json
[
  {
    "id": 1,
    "nombre": "Ana García",
    "email": "ana@empresa.com",
    "encoding": [0.123, -0.456, ...],
    "creado_en": "2025-01-15T10:30:00Z"
  }
]
```

---

### GET /api/logs
Historial paginado de accesos.

**Query params**
| Param | Default | Descripción |
|-------|---------|-------------|
| limit | 50 | Máx 500 |
| offset | 0 | Para paginación |
| estado | — | `permitido`, `denegado`, `error` |
| usuario_id | — | Filtrar por usuario |

**Response 200**
```json
{
  "total":  320,
  "limit":  50,
  "offset": 0,
  "logs": [
    {
      "id": 123,
      "usuario_id": 5,
      "usuario_nombre": "Ana García",
      "estado": "permitido",
      "metodo": "facial",
      "detalle": "Reconocimiento exitoso con liveness",
      "confianza": "0.9412",
      "fecha": "2025-06-01T14:22:33Z"
    }
  ]
}
```

---

### POST /api/logs
Registra manualmente un evento de acceso.

**Request**
```json
{
  "usuario_id": 5,
  "estado":    "denegado",
  "metodo":    "facial",
  "detalle":   "Liveness detection fallida",
  "confianza": 0.0
}
```

**Response 201**
```json
{
  "log_id": 124,
  "fecha":   "2025-06-01T14:25:00Z",
  "mensaje": "Log registrado"
}
```

---

## Códigos de estado HTTP utilizados

| Código | Significado |
|--------|-------------|
| 200 | OK |
| 201 | Creado |
| 400 | Bad Request — datos inválidos |
| 401 | Unauthorized — API Key ausente |
| 403 | Forbidden — API Key inválida |
| 405 | Method Not Allowed |
| 409 | Conflict — recurso duplicado |
| 423 | Locked — usuario bloqueado |
| 500 | Internal Server Error |
