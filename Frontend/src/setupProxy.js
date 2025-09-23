// src/setupProxy.js
const { createProxyMiddleware } = require('http-proxy-middleware');

const local ={
      target: '',
      changeOrigin: true,
      secure: false,
    }

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware(local)
  );
};
