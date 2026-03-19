// backend/api/alertas.js
/**
 * GET  /api/alertas — Listar alertas (con filtros opcionales)
 * POST /api/alertas — Crear una nueva alerta
 * PATCH /api/alertas/:id — Marcar alerta como resuelta
 * DELETE /api/alertas/:id — Eliminar una alerta
 * 
 * Query params GET:
 *   limit     (default 50, max 500)
 *   offset    (default 0)
 *   tipo      (intentos_excedidos, liveness_fallo, etc)
 *   resuelta  (true | false)
 *   usuario_id
 * 
 * Body POST:
 * {
 *   "tipo":        "intentos_excedidos",
 *   "descripcion": "3 intentos fallidos detectados",
 *   "usuario_id":  5
 * }
 * 
 * Body PATCH:
 * {
 *   "resuelta": true
 * }
 */

const { query }      = require('../lib/db');
const validateApiKey = require('../middleware/validateApiKey');

const TIPOS_VALIDOS = [
  'intentos_excedidos',
  'liveness_fallo',
  'rostro_desconocido',
  'acceso_no_autorizado',
  'error_sistema',
  'bloqueo_cuenta',
  'otro'
];

module.exports = async (req, res) => {
  if (!validateApiKey(req, res)) return;

  // ── GET: listar alertas ─────────────────────────────────────────
  if (req.method === 'GET') {
    const limit     = Math.min(parseInt(req.query.limit    ?? '50', 10), 500);
    const offset    = Math.max(parseInt(req.query.offset   ?? '0',  10), 0);
    const tipo      = req.query.tipo      ?? null;
    const resuelta  = req.query.resuelta  ?? null;
    const usuarioId = req.query.usuario_id ?? null;

    const conditions = [];
    const params     = [];

    if (tipo) {
      params.push(tipo);
      conditions.push(`a.tipo = $${params.length}`);
    }
    if (resuelta !== null) {
      params.push(resuelta === 'true');
      conditions.push(`a.resuelta = $${params.length}`);
    }
    if (usuarioId) {
      params.push(parseInt(usuarioId, 10));
      conditions.push(`a.usuario_id = $${params.length}`);
    }

    const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';

    params.push(limit, offset);

    try {
      const result = await query(
        `SELECT
           a.id,
           a.tipo,
           a.descripcion,
           a.usuario_id,
           u.nombre AS usuario_nombre,
           a.resuelta,
           a.creada_en
         FROM alertas a
         LEFT JOIN usuarios u ON u.id = a.usuario_id
         ${where}
         ORDER BY a.creada_en DESC
         LIMIT $${params.length - 1}
         OFFSET $${params.length}`,
        params
      );

      // Total sin paginación
      const countResult = await query(
        `SELECT COUNT(*) AS total FROM alertas a ${where}`,
        params.slice(0, params.length - 2)
      );

      return res.status(200).json({
        total:   parseInt(countResult.rows[0].total, 10),
        limit,
        offset,
        alertas: result.rows,
      });

    } catch (err) {
      console.error('[alertas GET] Error:', err.message);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  // ── POST: crear alerta ──────────────────────────────────────────
  if (req.method === 'POST') {
    const {
      tipo,
      descripcion,
      usuario_id = null,
    } = req.body ?? {};

    if (!tipo || !TIPOS_VALIDOS.includes(tipo)) {
      return res.status(400).json({
        error: `Campo 'tipo' requerido. Valores válidos: ${TIPOS_VALIDOS.join(', ')}`,
      });
    }

    if (!descripcion || descripcion.trim().length === 0) {
      return res.status(400).json({
        error: 'Campo descripcion requerido y no vacío',
      });
    }

    try {
      const result = await query(
        `INSERT INTO alertas (tipo, descripcion, usuario_id)
         VALUES ($1, $2, $3)
         RETURNING id, creada_en`,
        [tipo, descripcion.trim(), usuario_id]
      );

      console.log(`[alerta] Creada: tipo=${tipo} usuario_id=${usuario_id}`);

      return res.status(201).json({
        alerta_id: result.rows[0].id,
        creada_en: result.rows[0].creada_en,
        mensaje:   'Alerta registrada correctamente',
      });

    } catch (err) {
      console.error('[alertas POST] Error:', err.message);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  // ── PATCH: marcar alerta como resuelta ──────────────────────────
  if (req.method === 'PATCH') {
    // Extraer ID de la URL: /api/alertas/123
    const urlParts = req.url.split('/');
    const alertaId = parseInt(urlParts[urlParts.length - 1], 10);

    if (!alertaId || isNaN(alertaId)) {
      return res.status(400).json({ error: 'ID de alerta inválido' });
    }

    const { resuelta } = req.body ?? {};

    if (resuelta === undefined) {
      return res.status(400).json({ error: 'Campo resuelta requerido' });
    }

    try {
      const result = await query(
        `UPDATE alertas
         SET resuelta = $1
         WHERE id = $2
         RETURNING id, resuelta`,
        [resuelta, alertaId]
      );

      if (result.rowCount === 0) {
        return res.status(404).json({ error: 'Alerta no encontrada' });
      }

      return res.status(200).json({
        alerta_id: result.rows[0].id,
        resuelta:  result.rows[0].resuelta,
        mensaje:   'Alerta actualizada correctamente',
      });

    } catch (err) {
      console.error('[alertas PATCH] Error:', err.message);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  // ── DELETE: eliminar alerta ──────────────────────────────────────
  if (req.method === 'DELETE') {
    const urlParts = req.url.split('/');
    const alertaId = parseInt(urlParts[urlParts.length - 1], 10);

    if (!alertaId || isNaN(alertaId)) {
      return res.status(400).json({ error: 'ID de alerta inválido' });
    }

    try {
      const result = await query(
        `DELETE FROM alertas WHERE id = $1 RETURNING id`,
        [alertaId]
      );

      if (result.rowCount === 0) {
        return res.status(404).json({ error: 'Alerta no encontrada' });
      }

      return res.status(200).json({
        mensaje: 'Alerta eliminada correctamente',
      });

    } catch (err) {
      console.error('[alertas DELETE] Error:', err.message);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  return res.status(405).json({ error: 'Método no permitido' });
};
