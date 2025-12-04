// ========================================
// MOBIX Configuration
// ========================================

window.MOBIX = window.MOBIX || {};

// API Configuration
window.MOBIX.API_BASE = 'http://127.0.0.1:8005';

// Make it also available as __MOBIX_API_BASE__ for backward compatibility
window.__MOBIX_API_BASE__ = window.MOBIX.API_BASE;

console.log('[MOBIX] Config loaded, API_BASE:', window.MOBIX.API_BASE);
