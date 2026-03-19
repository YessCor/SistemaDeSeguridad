// backend/api/logs.js
/**
 * GET  /api/logs         — Historial de accesos (con filtros opcionales)
 * POST /api/logs         — Registrar un nuevo evento de acceso
 *
 * Query params GET:
 *   limit  (default 50, max 500)
 *   offset (default 0)
 *   estado (permitido | denegado | error)
 *   usuario_id
 *
 * Body POST:
 * {
 *   "usuario_id": 7,          // opcional si no se identificó el usuario
 *   "estado":     "denegado",
 *   "metodo":     "facial",
 *   "detalle":    "Rostro no reconocido",
 *   "confianza":  0.31
 * }
 */

const { query }      = require('../lib/db');
const validateApiKey = require('../middleware/validateApiKey');

module.exports = async (req, res) => {
  if (!validateApiKey(req, res)) return;

  // ── GET: listar logs ───────────────────────────────────────
  if (req.method === 'GET') {
    const limit     = Math.min(parseInt(req.query.limit  ?? '50',  10), 500);
    const offset    = Math.max(parseInt(req.query.offset ?? '0',   10), 0);
    const estado    = req.query.estado     ?? null;
    const usuarioId = req.query.usuario_id ?? null;

    const conditions = [];
    const params     = [];

    if (estado) {
      params.push(estado);
      conditions.push(`l.estado = $${params.length}`);
    }
    if (usuarioId) {
      params.push(parseInt(usuarioId, 10));
      conditions.push(`l.usuario_id = $${params.length}`);
    }

    const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';

    params.push(limit, offset);

    try {
      const result = await query(
        `SELECT
           l.id,
           l.usuario_id,
           u.nombre AS usuario_nombre,
           l.estado,
           l.metodo,
           l.detalle,
           l.confianza,
           l.fecha
         FROM logs l
         LEFT JOIN usuarios u ON u.id = l.usuario_id
         ${where}
         ORDER BY l.fecha DESC
         LIMIT $${params.length - 1}
         OFFSET $${params.length}`,
        params
      );

      // Total sin paginación
      const countResult = await query(
        `SELECT COUNT(*) AS total FROM logs l ${where}`,
        params.slice(0, params.length - 2)
      );

      return res.status(200).json({
        total:  parseInt(countResult.rows[0].total, 10),
        limit,
        offset,
        logs:   result.rows,
      });

    } catch (err) {
      console.error('[logs GET] Error:', err.message);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  // ── POST: registrar log ────────────────────────────────────
  if (req.method === 'POST') {
    const {
      usuario_id = null,
      estado,
      metodo     = 'facial',
      detalle    = '',
      confianza  = 0,
    } = req.body ?? {};

    const ESTADOS_VALIDOS = ['permitido', 'denegado', 'error'];

    if (!estado || !ESTADOS_VALIDOS.includes(estado)) {
      return res.status(400).json({
        error: `Campo 'estado' requerido. Valores válidos: ${ESTADOS_VALIDOS.join(', ')}`,
      });
    }

    try {
      const result = await query(
        `INSERT INTO logs (usuario_id, estado, metodo, detalle, confianza)
         VALUES ($1, $2, $3, $4, $5)
         RETURNING id, fecha`,
        [usuario_id, estado, metodo, detalle, confianza]
      );

      return res.status(201).json({
        log_id: result.rows[0].id,
        fecha:  result.rows[0].fecha,
        mensaje: 'Log registrado',
      });

    } catch (err) {
      console.error('[logs POST] Error:', err.message);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  return res.status(405).json({ error: 'Método no permitido' });
};
