// ========================================
// MOBIX UI Functions
// ========================================

(function() {
  'use strict';
  
  // ========== CONFIRM MODAL ==========
  var confirmCallback = null;
  
  window.showConfirmModal = function(options) {
    var modal = document.getElementById('confirmModal');
    var title = document.getElementById('confirmModalTitle');
    var message = document.getElementById('confirmModalMessage');
    var okBtn = document.getElementById('confirmModalOk');
    
    if (!modal) return Promise.resolve(false);
    
    title.textContent = options.title || 'Are you sure?';
    message.textContent = options.message || 'This action cannot be undone.';
    okBtn.textContent = options.confirmText || 'Delete';
    
    modal.classList.add('active');
    
    return new Promise(function(resolve) {
      confirmCallback = resolve;
    });
  };
  
  // Wait for DOM
  document.addEventListener('DOMContentLoaded', function() {
    console.log('[MOBIX UI] Initializing...');
    
    // Setup confirm modal buttons
    var confirmModal = document.getElementById('confirmModal');
    var confirmOk = document.getElementById('confirmModalOk');
    var confirmCancel = document.getElementById('confirmModalCancel');
    
    if (confirmOk) {
      confirmOk.onclick = function() {
        confirmModal.classList.remove('active');
        if (confirmCallback) confirmCallback(true);
        confirmCallback = null;
      };
    }
    
    if (confirmCancel) {
      confirmCancel.onclick = function() {
        confirmModal.classList.remove('active');
        if (confirmCallback) confirmCallback(false);
        confirmCallback = null;
      };
    }
    
    // Close on background click
    if (confirmModal) {
      confirmModal.onclick = function(e) {
        if (e.target === confirmModal) {
          confirmModal.classList.remove('active');
          if (confirmCallback) confirmCallback(false);
          confirmCallback = null;
        }
      };
    }
    
    // ========== TOAST NOTIFICATIONS ==========
    window.showToast = function(message, type) {
      type = type || 'info';
      
      // Create container if doesn't exist
      var container = document.querySelector('.toast-container');
      if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
      }
      
      var toast = document.createElement('div');
      toast.className = 'toast toast-' + type;
      
      var icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
      };
      
      toast.innerHTML = '<span class="toast-icon">' + (icons[type] || icons.info) + '</span><span class="toast-message">' + message + '</span>';
      container.appendChild(toast);
      
      // Auto remove after 3 seconds
      setTimeout(function() {
        toast.classList.add('toast-fade-out');
        setTimeout(function() {
          toast.remove();
        }, 300);
      }, 3000);
    };
    
    // ========== NAVIGATION ==========
    window.sidebarNavigate = function(screenName) {
      console.log('[MOBIX UI] Navigate to:', screenName);
      
      var screenMap = {
        'chat': 'chatScreen',
        'planner': 'plannerScreen',
        'travelnote': 'travelNoteScreen',
        'profile': 'profileScreen',
        'hero': 'heroScreen',
        'about': 'aboutScreen'
      };
      
      var targetId = screenMap[screenName] || (screenName + 'Screen');
      
      // Hide all screens
      document.querySelectorAll('.screen').forEach(function(s) {
        s.classList.remove('active');
        s.classList.add('hidden');
      });
      
      // Show target screen
      var targetScreen = document.getElementById(targetId);
      if (targetScreen) {
        targetScreen.classList.remove('hidden');
        targetScreen.classList.add('active');
      }
      
      // Close sidebar
      var sidebar = document.querySelector('.sidebar');
      var overlay = document.querySelector('.sidebar-overlay');
      if (sidebar) sidebar.classList.remove('active');
      if (overlay) overlay.classList.remove('active');
      
      // Show/hide back button
      var backBtn = document.getElementById('backBtn');
      if (backBtn) {
        if (screenName === 'hero') {
          backBtn.classList.add('hidden');
        } else {
          backBtn.classList.remove('hidden');
        }
      }
    };
    
    // ========== HAMBURGER MENU ==========
    var hamburger = document.getElementById('hamburgerBtn');
    var sidebar = document.querySelector('.sidebar');
    var overlay = document.querySelector('.sidebar-overlay');
    
    if (hamburger && sidebar) {
      hamburger.onclick = function() {
        console.log('[MOBIX UI] Hamburger clicked');
        sidebar.classList.toggle('active');
        if (overlay) overlay.classList.toggle('active');
      };
    }
    
    // Close sidebar button
    var closeSidebar = document.getElementById('closeSidebar');
    if (closeSidebar && sidebar) {
      closeSidebar.onclick = function() {
        sidebar.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
      };
    }
    
    // Close sidebar on overlay click
    if (overlay) {
      overlay.onclick = function() {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
      };
    }
    
    // ========== BACK BUTTON ==========
    var backBtn = document.getElementById('backBtn');
    if (backBtn) {
      backBtn.onclick = function() {
        console.log('[MOBIX UI] Back button clicked');
        window.sidebarNavigate('hero');
      };
    }
    
    // ========== START CHATTING ==========
    var startBtn = document.getElementById('startChatting');
    if (startBtn) {
      startBtn.onclick = function() {
        console.log('[MOBIX UI] Start chatting clicked');
        window.sidebarNavigate('chat');
      };
    }
    
    // ========== AUTH MODAL ==========
    var profileBtn = document.getElementById('profileBtn');
    var authModal = document.getElementById('authModal');
    var authClose = document.getElementById('authCloseBtn');
    
    if (profileBtn && authModal) {
      profileBtn.onclick = function() {
        console.log('[MOBIX UI] Profile button clicked');
        authModal.classList.add('active');
        document.body.style.overflow = 'hidden';
      };
    }
    
    if (authClose && authModal) {
      authClose.onclick = function() {
        authModal.classList.remove('active');
        document.body.style.overflow = '';
      };
    }
    
    // Close modal on background click
    if (authModal) {
      authModal.onclick = function(e) {
        if (e.target === authModal) {
          authModal.classList.remove('active');
          document.body.style.overflow = '';
        }
      };
    }
    
    // Switch between login and register
    var showRegister = document.getElementById('showRegister');
    var showLogin = document.getElementById('showLogin');
    var loginForm = document.getElementById('loginForm');
    var registerForm = document.getElementById('registerForm');
    
    if (showRegister && loginForm && registerForm) {
      showRegister.onclick = function(e) {
        e.preventDefault();
        loginForm.classList.remove('active');
        registerForm.classList.add('active');
      };
    }
    
    if (showLogin && loginForm && registerForm) {
      showLogin.onclick = function(e) {
        e.preventDefault();
        registerForm.classList.remove('active');
        loginForm.classList.add('active');
      };
    }
    
    // Survey step navigation
    var nextToSurvey = document.getElementById('nextToSurvey');
    var backToBasic = document.getElementById('backToBasic');
    
    if (nextToSurvey) {
      nextToSurvey.onclick = function() {
        document.querySelector('.register-step[data-step="1"]').classList.remove('active');
        document.querySelector('.register-step[data-step="2"]').classList.add('active');
      };
    }
    
    if (backToBasic) {
      backToBasic.onclick = function() {
        document.querySelector('.register-step[data-step="2"]').classList.remove('active');
        document.querySelector('.register-step[data-step="1"]').classList.add('active');
      };
    }
    
    // Chip selection
    document.querySelectorAll('.chip-group .chip').forEach(function(chip) {
      chip.onclick = function() {
        var group = this.closest('.chip-group');
        var hiddenInput = group.nextElementSibling;
        var isMultiSelect = hiddenInput && hiddenInput.id === 'travelReasons';
        
        if (isMultiSelect) {
          this.classList.toggle('selected');
          var selected = Array.from(group.querySelectorAll('.chip.selected')).map(function(c) {
            return c.dataset.value;
          });
          if (hiddenInput) hiddenInput.value = selected.join(',');
        } else {
          group.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('selected'); });
          this.classList.add('selected');
          if (hiddenInput) hiddenInput.value = this.dataset.value;
        }
      };
    });
    
    // ========== TYPING ANIMATION ==========
    var typingText = document.getElementById('typingText');
    if (typingText) {
      var texts = ["Your AI Travel Assistant", "Plan Your Perfect Journey", "Discover Amazing Destinations"];
      var textIndex = 0, charIndex = 0, isDeleting = false;
      
      function typeText() {
        var current = texts[textIndex];
        if (isDeleting) {
          typingText.textContent = current.substring(0, charIndex - 1);
          charIndex--;
        } else {
          typingText.textContent = current.substring(0, charIndex + 1);
          charIndex++;
        }
        
        var speed = isDeleting ? 50 : 100;
        if (!isDeleting && charIndex === current.length) {
          speed = 2000;
          isDeleting = true;
        } else if (isDeleting && charIndex === 0) {
          isDeleting = false;
          textIndex = (textIndex + 1) % texts.length;
          speed = 500;
        }
        setTimeout(typeText, speed);
      }
      typeText();
    }
    
    // ========== MOBILE CHAT SIDEBAR TOGGLE ==========
    // Create toggle button for mobile
    var chatScreen = document.getElementById('chatScreen');
    var chatSidebar = document.querySelector('.chat-sidebar');
    
    if (chatScreen && chatSidebar) {
      // Create toggle button
      var toggleBtn = document.createElement('button');
      toggleBtn.className = 'btn-chat-history-toggle';
      toggleBtn.innerHTML = '📋';
      toggleBtn.title = 'Chat History';
      chatScreen.appendChild(toggleBtn);
      
      // Create overlay
      var chatOverlay = document.createElement('div');
      chatOverlay.className = 'chat-sidebar-overlay';
      chatScreen.appendChild(chatOverlay);
      
      // Toggle functionality
      toggleBtn.onclick = function() {
        chatSidebar.classList.toggle('mobile-open');
        chatOverlay.classList.toggle('active');
      };
      
      // Close on overlay click
      chatOverlay.onclick = function() {
        chatSidebar.classList.remove('mobile-open');
        chatOverlay.classList.remove('active');
      };
      
      // Close sidebar when chat item is clicked (mobile)
      chatSidebar.addEventListener('click', function(e) {
        if (e.target.closest('.chat-history-item')) {
          if (window.innerWidth <= 768) {
            chatSidebar.classList.remove('mobile-open');
            chatOverlay.classList.remove('active');
          }
        }
      });
    }
    
    console.log('[MOBIX UI] Initialization complete');
  });
})();
