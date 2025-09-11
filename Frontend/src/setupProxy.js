// src/setupProxy.js
const { createProxyMiddleware } = require('http-proxy-middleware');

const local ={
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
    }

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware(local)
  );
};
