// backend/middleware/validateApiKey.js
/**
 * Middleware que valida la API Key enviada en el header X-API-Key.
 * 
 * Uso en cualquier endpoint de Vercel:
 *   const validateApiKey = require('../middleware/validateApiKey');
 *   module.exports = async (req, res) => {
 *     if (!validateApiKey(req, res)) return;
 *     // ... lógica del endpoint
 *   };
 */

const VALID_API_KEY = process.env.API_KEY;

/**
 * @param {import('http').IncomingMessage} req
 * @param {import('http').ServerResponse}  res
 * @returns {boolean} true si es válida, false si ya respondió con 401/403
 */
function validateApiKey(req, res) {
  if (!VALID_API_KEY) {
    console.error('[Auth] Variable API_KEY no configurada en el servidor');
    res.status(500).json({ error: 'Configuración del servidor incompleta' });
    return false;
  }

  const provided = req.headers['x-api-key'];

  if (!provided) {
    res.status(401).json({ error: 'API Key requerida' });
    return false;
  }

  // Comparación en tiempo constante para evitar timing attacks
  if (!timingSafeEqual(provided, VALID_API_KEY)) {
    res.status(403).json({ error: 'API Key inválida' });
    return false;
  }

  return true;
}

/**
 * Comparación de strings en tiempo constante.
 * Evita ataques de timing que explotarían una comparación directa (===).
 */
function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

module.exports = validateApiKey;
