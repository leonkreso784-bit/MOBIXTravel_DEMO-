// ========================================
// MOBIX Configuration
// ========================================

window.MOBIX = window.MOBIX || {};

// API Configuration - automatski detektira produkciju vs development
(function() {
    const hostname = window.location.hostname;
    
    // Ako smo na localhostu - koristi lokalni backend
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        window.MOBIX.API_BASE = 'http://127.0.0.1:8005';
    } else {
        // PRODUKCIJA: Railway backend URL
        // ZAMIJENI OVO sa pravim Railway URL-om nakon deploya!
        window.MOBIX.API_BASE = 'https://mobix-production.up.railway.app';
    }
    
    // Backward compatibility
    window.__MOBIX_API_BASE__ = window.MOBIX.API_BASE;
    
    console.log('[MOBIX] Config loaded, API_BASE:', window.MOBIX.API_BASE);
})();
