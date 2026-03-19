// backend/api/register.js
/**
 * POST /api/register
 * 
 * Registra un nuevo usuario junto con su embedding facial.
 * 
 * Body esperado:
 * {
 *   "nombre":   "Juan Pérez",
 *   "email":    "juan@ejemplo.com",
 *   "encoding": [0.123, -0.456, ...]  // array de 128 floats
 * }
 * 
 * Respuesta 201:
 * { "usuario_id": 7, "mensaje": "Usuario registrado correctamente" }
 */

const { query }       = require('../lib/db');
const validateApiKey  = require('../middleware/validateApiKey');

module.exports = async (req, res) => {
  // ── Seguridad ──────────────────────────────────────────────
  if (!validateApiKey(req, res)) return;

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  // ── Validación de entrada ──────────────────────────────────
  const { nombre, email, encoding } = req.body ?? {};

  if (!nombre || !email || !Array.isArray(encoding)) {
    return res.status(400).json({
      error: 'Campos requeridos: nombre, email, encoding (array)',
    });
  }

  if (encoding.length !== 128) {
    return res.status(400).json({
      error: `El encoding debe tener exactamente 128 valores (recibidos: ${encoding.length})`,
    });
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return res.status(400).json({ error: 'Formato de email inválido' });
  }

  // ── Inserción en BD ───────────────────────────────────────
  try {
    // Transacción: insertar usuario + biometría en una sola operación
    await query('BEGIN');

    const userResult = await query(
      `INSERT INTO usuarios (nombre, email)
       VALUES ($1, $2)
       ON CONFLICT (email) DO NOTHING
       RETURNING id`,
      [nombre.trim(), email.toLowerCase().trim()]
    );

    if (userResult.rowCount === 0) {
      await query('ROLLBACK');
      return res.status(409).json({ error: 'El email ya está registrado' });
    }

    const usuario_id = userResult.rows[0].id;

    await query(
      `INSERT INTO biometria (usuario_id, encoding)
       VALUES ($1, $2)`,
      [usuario_id, JSON.stringify(encoding)]
    );

    await query('COMMIT');

    console.log(`[register] Usuario registrado: id=${usuario_id} email=${email}`);

    return res.status(201).json({
      usuario_id,
      mensaje: 'Usuario registrado correctamente',
    });

  } catch (err) {
    await query('ROLLBACK').catch(() => {});
    console.error('[register] Error en BD:', err.message);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
};
