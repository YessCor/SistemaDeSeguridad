// backend/api/usuarios.js
/**
 * GET /api/usuarios
 *
 * Retorna todos los usuarios activos junto con sus embeddings faciales.
 * El sistema local descarga esta lista al arrancar para construir
 * el índice de reconocimiento facial en memoria.
 *
 * Respuesta 200:
 * [
 *   {
 *     "id": 1,
 *     "nombre": "Juan Pérez",
 *     "email": "juan@ejemplo.com",
 *     "encoding": [0.123, ...],   // 128 floats o null si no tiene biometría
 *     "creado_en": "2025-01-15T..."
 *   },
 *   ...
 * ]
 */

const { query }      = require('../lib/db');
const validateApiKey = require('../middleware/validateApiKey');

module.exports = async (req, res) => {
  if (!validateApiKey(req, res)) return;

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  try {
    const result = await query(
      `SELECT
         u.id,
         u.nombre,
         u.email,
         u.creado_en,
         b.encoding
       FROM usuarios u
       LEFT JOIN biometria b ON b.usuario_id = u.id
       WHERE u.activo = TRUE
       ORDER BY u.id ASC`
    );

    // Parsear el JSONB de encoding (viene como string desde pg)
    const usuarios = result.rows.map((row) => ({
      ...row,
      encoding: row.encoding
        ? (typeof row.encoding === 'string' ? JSON.parse(row.encoding) : row.encoding)
        : null,
    }));

    return res.status(200).json(usuarios);

  } catch (err) {
    console.error('[usuarios] Error:', err.message);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
};
