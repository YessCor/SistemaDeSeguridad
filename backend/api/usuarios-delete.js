// backend/api/usuarios-delete.js
/**
 * DELETE /api/usuarios/:id
 * 
 * Elimina un usuario y todos sus datos biométricos asociados.
 * Cumple con el derecho al olvido (GDPR/Ley 1581 de Colombia).
 * 
 * Esta operación es IRREVERSIBLE. Elimina:
 * - Biometría del usuario
 * - Logs asociados
 * - Intentos fallidos
 * - Alertas asociadas
 * - Finalmente el usuario
 * 
 * Response 200:
 * {
 *   "mensaje": "Usuario eliminado correctamente",
 *   "usuario_id": 5
 * }
 * 
 * Response 404:
 * {
 *   "error": "Usuario no encontrado"
 * }
 */

const { query }      = require('../lib/db');
const validateApiKey = require('../middleware/validateApiKey');

module.exports = async (req, res) => {
  if (!validateApiKey(req, res)) return;

  if (req.method !== 'DELETE') {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  // Extraer ID de la URL: /api/usuarios/123
  const urlParts = req.url.split('/');
  const usuarioId = parseInt(urlParts[urlParts.length - 1], 10);

  if (!usuarioId || isNaN(usuarioId)) {
    return res.status(400).json({ error: 'ID de usuario inválido' });
  }

  try {
    // Verificar que el usuario existe
    const userExists = await query(
      'SELECT id, nombre, email FROM usuarios WHERE id = $1',
      [usuarioId]
    );

    if (userExists.rowCount === 0) {
      return res.status(404).json({ error: 'Usuario no encontrado' });
    }

    const userInfo = userExists.rows[0];

    // Iniciar transacción para eliminar todos los datos relacionados
    await query('BEGIN');

    // 1. Eliminar biometría
    await query('DELETE FROM biometria WHERE usuario_id = $1', [usuarioId]);

    // 2. Eliminar logs (se usa SET NULL pero por seguridad eliminamos)
    await query('DELETE FROM logs WHERE usuario_id = $1', [usuarioId]);

    // 3. Eliminar intentos fallidos
    await query('DELETE FROM intentos_fallidos WHERE usuario_id = $1', [usuarioId]);

    // 4. Eliminar alertas
    await query('DELETE FROM alertas WHERE usuario_id = $1', [usuarioId]);

    // 5. Eliminar el usuario
    await query('DELETE FROM usuarios WHERE id = $1', [usuarioId]);

    await query('COMMIT');

    console.log(`[usuarios DELETE] Usuario eliminado: id=${usuarioId} nombre=${userInfo.nombre}`);

    return res.status(200).json({
      mensaje:   'Usuario eliminado correctamente',
      usuario_id: usuarioId,
    });

  } catch (err) {
    await query('ROLLBACK').catch(() => {});
    console.error('[usuarios DELETE] Error:', err.message);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
};
