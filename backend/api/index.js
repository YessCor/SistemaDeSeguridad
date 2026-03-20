// backend/api/index.js
/**
 * Manejador principal para Vercel Serverless Functions
 * Sirve la API y archivos estáticos
 */

const fs = require('fs');
const path = require('path');

// Importar handlers de API
const registerHandler = require('./register');
const loginHandler = require('./login');
const logsHandler = require('./logs');
const usuariosHandler = require('./usuarios');
const alertasHandler = require('./alertas');

module.exports = async (req, res) => {
  const { url } = req;
  
  // Rutas de API
  if (url.startsWith('/api/')) {
    // Rutas de la API
    if (url === '/api/usuarios' || url.startsWith('/api/usuarios?')) {
      return usuariosHandler(req, res);
    }
    if (url === '/api/login' || url.startsWith('/api/login?')) {
      return loginHandler(req, res);
    }
    if (url === '/api/logs' || url.startsWith('/api/logs?')) {
      return logsHandler(req, res);
    }
    if (url === '/api/register' || url.startsWith('/api/register?')) {
      return registerHandler(req, res);
    }
    if (url.startsWith('/api/alertas')) {
      return alertasHandler(req, res);
    }
    
    return res.status(404).json({ error: 'Endpoint no encontrado' });
  }
  
  // Archivos estáticos
  if (url === '/' || url === '/test-panel') {
    const htmlPath = path.join(__dirname, 'test-panel.html');
    try {
      const html = fs.readFileSync(htmlPath, 'utf8');
      res.setHeader('Content-Type', 'text/html');
      return res.status(200).send(html);
    } catch (err) {
      return res.status(500).json({ error: 'Error al cargar la página' });
    }
  }
  
  return res.status(404).json({ error: 'Página no encontrada' });
};