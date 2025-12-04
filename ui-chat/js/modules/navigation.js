/**
 * MOBIX - Navigation Module
 * Rukuje navigacijom između screenova
 */

import { state } from './state.js';

class Navigator {
  constructor() {
    this.screens = {};
    this.backBtn = null;
    this.currentScreen = 'hero';
    this.screenHistory = [];
  }

  // Inicijalizuj navigator sa DOM elementima
  init() {
    // Učitaj sve screenove
    this.screens = {
      hero: document.getElementById('heroScreen'),
      chat: document.getElementById('chatScreen'),
      profile: document.getElementById('profileScreen'),
      planner: document.getElementById('plannerScreen'),
      travelnote: document.getElementById('travelNoteScreen')
    };

    this.backBtn = document.getElementById('backBtn');

    // Postavi event listener za back button
    if (this.backBtn) {
      this.backBtn.addEventListener('click', () => {
        console.log('🔙 Back button clicked');
        this.goBack();
      });
    }

    // Handle browser back button
    window.addEventListener('popstate', (event) => {
      console.log('🔙 Browser back button');
      if (event.state && event.state.screen) {
        this.showScreen(event.state.screen, false); // false = don't push to history
      } else {
        this.showScreen('hero', false);
      }
    });

    // Set initial history state
    history.replaceState({ screen: 'hero' }, '', window.location.href);

    // Setup profile tabs
    this.setupProfileTabs();

    console.log('✅ Navigator initialized');
  }

  // Setup profile tabs functionality
  setupProfileTabs() {
    const profileTabs = document.querySelectorAll('.profile-tab');
    const profileContents = document.querySelectorAll('.profile-tab-content');

    profileTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetTab = tab.dataset.tab;
        
        // Update tab active states
        profileTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Update content active states
        profileContents.forEach(content => {
          if (content.dataset.content === targetTab) {
            content.classList.add('active');
          } else {
            content.classList.remove('active');
          }
        });
      });
    });

    // Setup preference chips
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('preference-chip')) {
        e.target.classList.toggle('selected');
      }
    });
  }

  // Prikaži određeni screen
  showScreen(screenName, pushHistory = true) {
    console.log(`🔄 Navigating to: ${screenName}`);
    
    // Sakrij sve screenove
    Object.entries(this.screens).forEach(([name, screen]) => {
      if (screen) {
        screen.classList.remove('active');
        screen.classList.add('hidden');
      }
    });

    // Prikaži traženi screen
    const targetScreen = this.screens[screenName];
    if (targetScreen) {
      targetScreen.classList.remove('hidden');
      targetScreen.classList.add('active');
      state.currentScreen = screenName;
      this.currentScreen = screenName;

      // Update browser history
      if (pushHistory) {
        history.pushState({ screen: screenName }, '', `#${screenName}`);
      }

      // Show/hide back button
      this.updateBackButton(screenName);

      // Posebne akcije za određene screenove
      this.onScreenShown(screenName);
      
      console.log(`✅ Screen shown: ${screenName}`);
    } else {
      console.error(`❌ Screen not found: ${screenName}`);
    }
  }

  // Go back to previous screen
  goBack() {
    history.back();
  }

  // Update back button visibility
  updateBackButton(screenName) {
    if (!this.backBtn) return;
    
    if (screenName === 'hero') {
      this.backBtn.classList.add('hidden');
    } else {
      this.backBtn.classList.remove('hidden');
    }
  }

  // Callback kada se screen prikaže
  onScreenShown(screenName) {
    switch(screenName) {
      case 'chat':
        // Focus chat input
        setTimeout(() => {
          const chatInput = document.getElementById('chatInput');
          if (chatInput) chatInput.focus();
        }, 100);
        break;
      
      case 'profile':
        // Load profile data
        if (window.mobixApp && window.mobixApp.auth) {
          window.mobixApp.auth.loadProfileData();
        }
        break;
    }
  }

  // Otvori sidebar
  openSidebar() {
    const sidebar = document.getElementById('sidebarMenu');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (sidebar) sidebar.classList.add('open');
    if (overlay) overlay.classList.add('active');
  }

  // Zatvori sidebar
  closeSidebar() {
    const sidebar = document.getElementById('sidebarMenu');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
  }

  // Navigacija iz sidebara
  navigateFromSidebar(screenName) {
    this.closeSidebar();
    this.showScreen(screenName);
  }
}

// Export singleton instance
export const navigator = new Navigator();
export default navigator;

// Globalna funkcija za onclick u HTML-u
window.sidebarNavigate = function(screenName) {
  navigator.navigateFromSidebar(screenName);
};
