// backend/lib/db.js
/**
 * Conexión a PostgreSQL serverless usando Neon.
 * 
 * Se usa un pool de conexiones con límite reducido porque en serverless
 * cada función puede crear instancias independientes; el pool evita
 * agotar las conexiones disponibles en Neon.
 * 
 * La variable DATABASE_URL se configura en Vercel Dashboard o .env local.
 * Formato: postgresql://user:password@host/dbname?sslmode=require
 */

const { Pool } = require('pg');

if (!process.env.DATABASE_URL) {
  throw new Error('Variable de entorno DATABASE_URL no configurada');
}

// Singleton del pool para reutilizar entre invocaciones calientes
let pool;

function getPool() {
  if (!pool) {
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: { rejectUnauthorized: false },  // Requerido por Neon
      max: 5,                               // Límite para serverless
      idleTimeoutMillis: 30_000,
      connectionTimeoutMillis: 5_000,
    });

    pool.on('error', (err) => {
      console.error('[DB] Error inesperado en cliente idle:', err.message);
    });
  }
  return pool;
}

/**
 * Ejecuta una query parametrizada.
 * 
 * @param {string} text  - Query SQL con placeholders $1, $2, ...
 * @param {Array}  params - Parámetros correspondientes
 * @returns {Promise<import('pg').QueryResult>}
 * 
 * @example
 * const result = await query(
 *   'SELECT * FROM usuarios WHERE email = $1',
 *   ['usuario@ejemplo.com']
 * );
 */
async function query(text, params = []) {
  const client = await getPool().connect();
  try {
    const start  = Date.now();
    const result = await client.query(text, params);
    const ms     = Date.now() - start;
    console.log(`[DB] query ejecutada en ${ms}ms — filas: ${result.rowCount}`);
    return result;
  } finally {
    client.release();
  }
}

module.exports = { query };
