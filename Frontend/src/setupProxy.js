// src/setupProxy.js
const { createProxyMiddleware } = require('http-proxy-middleware');

const local ={
      target: 'http://localhost:8000',
      changeOrigin: true,
    }
// const prod ={
//       target: 'https://cap-irve.digetit.com',
//       changeOrigin: true,
//     }
// const dev={
//   target: 'https://cap-irve-stage.digetit.com/',
//       changeOrigin: true,
// }
module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware(local)
  );
};
