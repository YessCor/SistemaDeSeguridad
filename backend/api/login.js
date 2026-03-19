// backend/api/login.js
/**
 * POST /api/login
 * 
 * El sistema local ya realizó el matching facial. Este endpoint:
 *  - Verifica si el usuario tiene bloqueo activo por intentos fallidos
 *  - Registra el resultado del intento
 *  - Resetea el contador si el acceso es concedido
 *  - Genera alerta si se supera el límite de intentos
 * 
 * Body esperado:
 * {
 *   "usuario_id": 7,
 *   "estado":     "permitido" | "denegado",
 *   "confianza":  0.92,
 *   "metodo":     "facial"
 * }
 */

const { query }      = require('../lib/db');
const validateApiKey = require('../middleware/validateApiKey');

const MAX_ATTEMPTS  = parseInt(process.env.MAX_FAILED_ATTEMPTS ?? '3', 10);
const LOCKOUT_MIN   = parseInt(process.env.LOCKOUT_MINUTES     ?? '5', 10);

module.exports = async (req, res) => {
  if (!validateApiKey(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'Método no permitido' });

  const { usuario_id, estado, confianza = 0, metodo = 'facial' } = req.body ?? {};

  if (!usuario_id || !estado) {
    return res.status(400).json({ error: 'Campos requeridos: usuario_id, estado' });
  }

  try {
    // ── Verificar bloqueo activo ───────────────────────────
    const lockResult = await query(
      `SELECT cantidad, ultima_vez
         FROM intentos_fallidos
        WHERE usuario_id = $1`,
      [usuario_id]
    );

    if (lockResult.rows.length > 0) {
      const { cantidad, ultima_vez } = lockResult.rows[0];
      const minutesSince = (Date.now() - new Date(ultima_vez).getTime()) / 60_000;

      if (cantidad >= MAX_ATTEMPTS && minutesSince < LOCKOUT_MIN) {
        return res.status(423).json({
          error: 'Usuario bloqueado temporalmente',
          bloqueado_hasta: new Date(new Date(ultima_vez).getTime() + LOCKOUT_MIN * 60_000),
        });
      }
    }

    // ── Registrar log del intento ──────────────────────────
    await query(
      `INSERT INTO logs (usuario_id, estado, metodo, confianza, detalle)
       VALUES ($1, $2, $3, $4, $5)`,
      [usuario_id, estado, metodo, confianza, `Intento desde sistema local`]
    );

    if (estado === 'permitido') {
      // Resetear contador de fallos
      await query(
        `DELETE FROM intentos_fallidos WHERE usuario_id = $1`,
        [usuario_id]
      );
      return res.status(200).json({ acceso: true, mensaje: 'Bienvenido' });
    }

    // ── Acceso denegado: actualizar contador ───────────────
    await query(
      `INSERT INTO intentos_fallidos (usuario_id, cantidad, ultima_vez)
       VALUES ($1, 1, NOW())
       ON CONFLICT (usuario_id)
       DO UPDATE SET cantidad = intentos_fallidos.cantidad + 1,
                     ultima_vez = NOW()`,
      [usuario_id]
    );

    // Recuperar cantidad actualizada
    const failRow = await query(
      `SELECT cantidad FROM intentos_fallidos WHERE usuario_id = $1`,
      [usuario_id]
    );
    const nuevaCantidad = failRow.rows[0]?.cantidad ?? 1;

    if (nuevaCantidad >= MAX_ATTEMPTS) {
      await query(
        `INSERT INTO alertas (tipo, descripcion, usuario_id)
         VALUES ($1, $2, $3)`,
        ['intentos_excedidos', `${nuevaCantidad} intentos fallidos registrados`, usuario_id]
      );
    }

    return res.status(200).json({
      acceso: false,
      mensaje: 'Acceso denegado',
      intentos_fallidos: nuevaCantidad,
    });

  } catch (err) {
    console.error('[login] Error:', err.message);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
};
