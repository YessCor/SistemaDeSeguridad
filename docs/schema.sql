-- ============================================================
-- Schema: Sistema de Seguridad Inteligente
-- Base de datos: PostgreSQL (Neon serverless)
-- Version: 1.0.0
-- ============================================================

-- ============================================================
-- EXTENSIONES
-- ============================================================

-- Habilitar UUID para IDs únicos (opcional)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Habilitar pg_trgm para búsqueda difusa (opcional)
-- CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- ENUM TYPES
-- ============================================================

-- Estado de acceso
CREATE TYPE acceso_estado AS ENUM (
    'permitido',
    'denegado',
    'error'
);

-- Tipo de método de autenticación
CREATE TYPE metodo_tipo AS ENUM (
    'facial',
    'huella',
    'tarjeta',
    'password',
    'multi_factor'
);

-- Tipo de alerta
CREATE TYPE alerta_tipo AS ENUM (
    'intentos_excedidos',
    'liveness_fallo',
    'rostro_desconocido',
    'acceso_no_autorizado',
    'error_sistema',
    'bloqueo_cuenta',
    'intento_sospechoso',
    'otro'
);

-- ============================================================
-- TABLAS PRINCIPALES
-- ============================================================

-- Tabla: usuarios
-- Almacena los usuarios registrados en el sistema
CREATE TABLE IF NOT EXISTS usuarios (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(120) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    activo      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla: biometria
-- Almacena los embeddings faciales (JSONB) por usuario
-- NOTA: Los embeddings son arrays de 128 floats generados por dlib
CREATE TABLE IF NOT EXISTS biometria (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    encoding        JSONB NOT NULL,          -- Array de 128 floats
    modelo          VARCHAR(50) DEFAULT 'dlib_face_recognition_resnet_model_v1',
    calidad         NUMERIC(5,4) DEFAULT 1.0, -- Score de calidad de la captura (0-1)
    activo          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla: logs
-- Registro de todos los intentos de acceso
CREATE TABLE IF NOT EXISTS logs (
    id          SERIAL PRIMARY KEY,
    usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    estado      VARCHAR(20) NOT NULL CHECK (estado IN ('permitido','denegado','error')),
    metodo      VARCHAR(30) NOT NULL DEFAULT 'facial',
    detalle     TEXT,
    confianza   NUMERIC(5,4),                 -- Score de similitud 0.0 a 1.0
    ip_origen   VARCHAR(45),                 -- IPv4 o IPv6
    user_agent  VARCHAR(500),                 -- User agent del cliente
    latitud    NUMERIC(10,8),                -- Ubicación (opcional)
    longitud   NUMERIC(11,8),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla: intentos_fallidos
-- Contador de fallos para rate limiting y bloqueo
CREATE TABLE IF NOT EXISTS intentos_fallidos (
    id          SERIAL PRIMARY KEY,
    usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
    cantidad    INTEGER DEFAULT 1,
    ip_bloqueada VARCHAR(45),                 -- IP que generó los fallos
    ultima_vez  TIMESTAMPTZ DEFAULT NOW(),
    desbloqueado_en TIMESTAMPTZ              -- Cuándo se levantó el bloqueo
);

-- Tabla: alertas
-- Alertas generadas por el sistema
CREATE TABLE IF NOT EXISTS alertas (
    id          SERIAL PRIMARY KEY,
    tipo        VARCHAR(50) NOT NULL,        -- Tipo de alerta
    titulo      VARCHAR(200),                 -- Título breve
    descripcion TEXT,
    prioridad   VARCHAR(20) DEFAULT 'media', -- baja, media, alta, critica
    usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    resuelta    BOOLEAN DEFAULT FALSE,
    resuelta_por INTEGER,                     -- ID del admin que resolvió
    resuelta_en TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLAS ADICIONALES
-- ============================================================

-- Tabla: sesiones
-- Control de sesiones activas (opcional para futuras mejoras)
CREATE TABLE IF NOT EXISTS sesiones (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token           VARCHAR(255) NOT NULL UNIQUE,
    ip_address      VARCHAR(45),
    user_agent      VARCHAR(500),
    iniciada_en     TIMESTAMPTZ DEFAULT NOW(),
    expira_en       TIMESTAMPTZ,
    activa          BOOLEAN DEFAULT TRUE
);

-- Tabla: api_keys
-- Keys de API para autenticar clientes (futuro)
CREATE TABLE IF NOT EXISTS api_keys (
    id          SERIAL PRIMARY KEY,
    key_hash    VARCHAR(255) NOT NULL UNIQUE,
    nombre      VARCHAR(100),
    activa      BOOLEAN DEFAULT TRUE,
    ultima_uso  TIMESTAMPTZ,
    expira_en   TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ÍNDICES PARA MEJORAR RENDIMIENTO
-- ============================================================

-- Índices para logs
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_usuario_id ON logs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_logs_estado ON logs(estado);
CREATE INDEX IF NOT EXISTS idx_logs_fecha_estado ON logs(created_at DESC, estado);

-- Índices para biometria
CREATE INDEX IF NOT EXISTS idx_biometria_usuario ON biometria(usuario_id);
CREATE INDEX IF NOT EXISTS idx_biometria_activa ON biometria(activo);

-- Índices para alertas
CREATE INDEX IF NOT EXISTS idx_alertas_tipo ON alertas(tipo);
CREATE INDEX IF NOT EXISTS idx_alertas_resuelta ON alertas(resuelta);
CREATE INDEX IF NOT EXISTS idx_alertas_fecha_tipo ON alertas(created_at DESC, tipo);

-- Índices para intentos_fallidos
CREATE INDEX IF NOT EXISTS idx_intentos_usuario ON intentos_fallidos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_intentos_fecha ON intentos_fallidos(ultima_vez DESC);

-- Índices para usuarios
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
CREATE INDEX IF NOT EXISTS idx_usuarios_activo ON usuarios(activo);

-- Índices para sesiones
CREATE INDEX IF NOT EXISTS idx_sesiones_token ON sesiones(token);
CREATE INDEX IF NOT EXISTS idx_sesiones_activa ON sesiones(activa);

-- ============================================================
-- FUNCIONES Y TRIGGERS
-- ============================================================

-- Función: Actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para actualizar updated_at en usuarios
DROP TRIGGER IF EXISTS update_usuarios_updated_at ON usuarios;
CREATE TRIGGER update_usuarios_updated_at
    BEFORE UPDATE ON usuarios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- FUNCIONES UTILITARIAS
-- ============================================================

-- Función: Obtener usuarios activos con biometría
CREATE OR REPLACE FUNCTION get_usuarios_activos()
RETURNS TABLE (
    id SERIAL,
    nombre VARCHAR(120),
    email VARCHAR(255),
    encoding JSONB,
    creado_en TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.id,
        u.nombre,
        u.email,
        b.encoding,
        u.created_at
    FROM usuarios u
    LEFT JOIN biometria b ON b.usuario_id = u.id AND b.activo = TRUE
    WHERE u.activo = TRUE
    ORDER BY u.id ASC;
END;
$$ LANGUAGE plpgsql;

-- Función: Obtener logs de acceso por usuario
CREATE OR REPLACE FUNCTION get_logs_usuario(
    p_usuario_id INTEGER,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id INTEGER,
    usuario_id INTEGER,
    nombre VARCHAR(120),
    estado VARCHAR(20),
    metodo VARCHAR(30),
    detalle TEXT,
    confianza NUMERIC(5,4),
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        l.id,
        l.usuario_id,
        u.nombre,
        l.estado,
        l.metodo,
        l.detalle,
        l.confianza,
        l.created_at
    FROM logs l
    LEFT JOIN usuarios u ON u.id = l.usuario_id
    WHERE l.usuario_id = p_usuario_id OR p_usuario_id IS NULL
    ORDER BY l.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- Función: Obtener estadísticas de accesos
CREATE OR REPLACE FUNCTION get_estadisticas_accesos(
    p_dias INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_accesos INTEGER,
    accesos_permitidos INTEGER,
    accesos_denegados INTEGER,
    tasa_exito NUMERIC(5,4),
    usuarios_unicos INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER AS total_accesos,
        COUNT(*) FILTER (WHERE l.estado = 'permitido') AS accesos_permitidos,
        COUNT(*) FILTER (WHERE l.estado = 'denegado') AS accesos_denegados,
        CASE
            WHEN COUNT(*) > 0
            THEN COUNT(*) FILTER (WHERE l.estado = 'permitido')::NUMERIC / COUNT(*)
            ELSE 0
        END AS tasa_exito,
        COUNT(DISTINCT l.usuario_id)::INTEGER AS usuarios_unicos
    FROM logs l
    WHERE l.created_at >= NOW() - (p_dias || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- Función: Limpiar logs antiguos (política de retención)
CREATE OR REPLACE FUNCTION limpiar_logs_antiguos(p_dias INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    eliminados INTEGER;
BEGIN
    DELETE FROM logs
    WHERE created_at < NOW() - (p_dias || ' days')::INTERVAL;
    
    GET DIAGNOSTICS eliminados = ROW_COUNT;
    RETURN eliminados;
END;
$$ LANGUAGE plpgsql;

-- Función: Verificar y desbloquear usuarios temporalmente bloqueados
CREATE OR REPLACE FUNCTION verificar_bloqueos(p_minutos_bloqueo INTEGER DEFAULT 5)
RETURNS INTEGER AS $$
DECLARE
    desbloqueados INTEGER;
BEGIN
    UPDATE intentos_fallidos
    SET cantidad = 0,
        desbloqueado_en = NOW()
    WHERE ultima_vez < NOW() - (p_minutos_bloqueo || ' minutes')::INTERVAL
      AND cantidad > 0;
    
    GET DIAGNOSTICS desbloqueados = ROW_COUNT;
    RETURN desbloqueados;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- POLÍTICAS DE RETENCIÓN (Opcional - configurar en Neon)
-- ============================================================

-- Nota: Neon no soporta pg_cron nativamente.
-- Para automatizar la limpieza, usar GitHub Actions o webhooks externos.

-- Ejemplo de cleanup manual:
-- SELECT limpiar_logs_antiguos(90);
-- SELECT verificar_bloqueos(5);

-- ============================================================
-- COMENTARIOS DE DOCUMENTACIÓN
-- ============================================================

COMMENT ON TABLE usuarios          IS 'Usuarios registrados en el sistema';
COMMENT ON TABLE biometria         IS 'Encodings faciales (embeddings) por usuario';
COMMENT ON TABLE logs              IS 'Historial de intentos de acceso';
COMMENT ON TABLE intentos_fallidos IS 'Contador de fallos para detectar ataques';
COMMENT ON TABLE alertas           IS 'Alertas generadas por el sistema';
COMMENT ON TABLE sesiones          IS 'Sesiones activas de usuarios';
COMMENT ON TABLE api_keys          IS 'Claves de API para autenticación';

-- Comentarios de columnas
COMMENT ON COLUMN logs.confianza   IS 'Score de similitud facial (0.0 a 1.0)';
COMMENT ON COLUMN logs.ip_origen   IS 'Dirección IP del cliente que intentó acceder';
COMMENT ON COLUMN alertas.prioridad IS 'Nivel de severidad de la alerta';

-- ============================================================
-- DATOS DE EJEMPLO (Solo para desarrollo)
-- ============================================================

-- INSERT INTO usuarios (nombre, email) VALUES
-- ('Admin', 'admin@security.local'),
-- ('Usuario Prueba', 'test@security.local');
