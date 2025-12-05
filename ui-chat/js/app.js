/**
 * MOBIX - Main Application
 * Glavni entry point aplikacije - Samo Chatbot
 */

import { CONFIG } from './modules/config.js';
import { state } from './modules/state.js';
import { api } from './modules/api.js';
import { navigator } from './modules/navigation.js';
import { chat } from './modules/chat.js';
import { ui } from './modules/ui.js';
import { auth } from './modules/auth.js';

class MobixApp {
  constructor() {
    this.initialized = false;
  }

  async init() {
    if (this.initialized) return;
    
    try {
      // Inicijalizuj module
      ui.init();
      navigator.init();
      chat.init();
      auth.init();

      // Postavi event listenere
      this.setupEventListeners();

      // Inicijaliziraj UI komponente
      this.initUIComponents();
      
      // Inicijaliziraj video pozadinu za iOS
      this.initHeroVideo();

      // Prikaži hero screen
      navigator.showScreen('hero');

      this.initialized = true;

    } catch (error) {
      console.error('MOBIX Init Failed:', error);
      ui.showNotification('Failed to initialize app', 'error');
    }
  }
  
  initHeroVideo() {
    const heroVideo = document.getElementById('heroVideo');
    const heroScreen = document.getElementById('heroScreen');
    
    if (!heroVideo || !heroScreen) return;
    
    // Detektiraj iOS/mobilne uređaje
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    // Na mobilnim uređajima, odmah prikaži fallback sliku
    if (isMobile) {
      heroScreen.classList.add('show-fallback');
      console.log('Mobile detected, showing fallback image');
      return;
    }
    
    // Video error handler za desktop
    heroVideo.addEventListener('error', () => {
      console.warn('Hero video failed to load, showing fallback');
      heroScreen.classList.add('video-failed');
    });
    
    // Ako video ne počne u 5 sekundi, prikaži fallback
    const videoTimeout = setTimeout(() => {
      if (heroVideo.readyState < 2) {
        console.warn('Hero video timeout, showing fallback');
        heroScreen.classList.add('video-failed');
      }
    }, 5000);
    
    // Očisti timeout ako se video učita
    heroVideo.addEventListener('canplay', () => {
      clearTimeout(videoTimeout);
      heroScreen.classList.remove('video-failed', 'show-fallback');
    });
    
    // Pokušaj pokrenuti video (iOS Safari)
    heroVideo.play().catch(() => {
      console.warn('Video autoplay blocked, showing fallback');
      heroScreen.classList.add('video-failed');
    });
  }

  setupEventListeners() {
    // Global sidebar navigation function
    window.sidebarNavigate = (screenName) => {
      navigator.showScreen(screenName);
      
      // Close sidebar and overlay after navigation
      const sidebar = document.querySelector('.sidebar');
      const overlay = document.querySelector('.sidebar-overlay');
      if (sidebar) sidebar.classList.remove('active');
      if (overlay) overlay.classList.remove('active');
    };

    // Global navigation reference for other modules
    window.navigation = navigator;
    
    // Hero Screen Button
    const startChatting = document.getElementById('startChatting');
    if (startChatting) {
      startChatting.addEventListener('click', () => {
        navigator.showScreen('chat');
      });
    }
  }

  initUIComponents() {
    // Typing animation
    try {
      ui.initTypingAnimation();
    } catch (error) {
      console.error('Typing animation failed:', error);
    }
  }
}

// Kreiraj globalnu instancu
console.log('Creating MobixApp instance...');
const app = new MobixApp();

// Izloži na window za debugging
window.mobixApp = {
  app,
  config: CONFIG,
  state,
  api,
  navigator,
  chat,
  ui,
  auth
};

// Pokreni app kada je DOM spreman
if (document.readyState === 'loading') {
  console.log('DOM still loading, waiting for DOMContentLoaded...');
  document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded fired, initializing app...');
    app.init();
  });
} else {
  console.log('DOM already loaded, initializing app immediately...');
  app.init();
}

export default app;
