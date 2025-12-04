/**
 * MOBIX - Authentication Module
 * Handles login, register with survey, and user state
 */

import { CONFIG } from './config.js';
import { state } from './state.js';

const API_BASE = CONFIG.API_BASE;

class AuthManager {
  constructor() {
    this.modal = null;
    this.loginForm = null;
    this.registerForm = null;
    this.currentStep = 1;
  }

  init() {
    this.modal = document.getElementById('authModal');
    this.loginForm = document.getElementById('loginForm');
    this.registerForm = document.getElementById('registerForm');

    if (!this.modal) return;

    // Check for existing token
    const token = localStorage.getItem('mobix_token');
    if (token) {
      this.validateToken(token);
    }

    // Modal controls
    const authCloseBtn = document.getElementById('authCloseBtn');
    const showRegister = document.getElementById('showRegister');
    const showLogin = document.getElementById('showLogin');
    
    if (authCloseBtn) authCloseBtn.addEventListener('click', () => this.closeModal());
    if (showRegister) showRegister.addEventListener('click', (e) => { e.preventDefault(); this.showRegister(); });
    if (showLogin) showLogin.addEventListener('click', (e) => { e.preventDefault(); this.showLogin(); });

    // Overlay click to close
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) this.closeModal();
    });

    // Login form
    const loginFormElement = document.getElementById('loginFormElement');
    if (loginFormElement) loginFormElement.addEventListener('submit', (e) => { e.preventDefault(); this.handleLogin(); });

    // Register form - Step navigation
    const nextToSurvey = document.getElementById('nextToSurvey');
    const backToBasic = document.getElementById('backToBasic');
    if (nextToSurvey) nextToSurvey.addEventListener('click', () => { if (this.validateBasicInfo()) this.showStep(2); });
    if (backToBasic) backToBasic.addEventListener('click', () => this.showStep(1));

    // Register form submission
    const registerFormElement = document.getElementById('registerFormElement');
    if (registerFormElement) registerFormElement.addEventListener('submit', (e) => { e.preventDefault(); this.handleRegister(); });

    // Chip selection
    this.setupChipGroups();

    // Profile button click
    const profileBtn = document.getElementById('profileBtn');
    if (profileBtn) {
      profileBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (state.user) {
          this.loadProfileData();
          if (window.sidebarNavigate) window.sidebarNavigate('profile');
        } else {
          this.openModal();
        }
      });
    }

    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) logoutBtn.addEventListener('click', () => this.logout());

    // Setup avatar upload
    this.setupAvatarUpload();
  }

  setupChipGroups() {
    const chipGroups = document.querySelectorAll('.chip-group');
    chipGroups.forEach(group => {
      const chips = group.querySelectorAll('.chip');
      const hiddenInput = group.nextElementSibling;

      chips.forEach(chip => {
        chip.addEventListener('click', () => {
          // Remove active from all chips in this group
          chips.forEach(c => c.classList.remove('active'));
          // Add active to clicked chip
          chip.classList.add('active');
          // Update hidden input value
          if (hiddenInput && hiddenInput.tagName === 'INPUT') {
            hiddenInput.value = chip.dataset.value;
          }
          
          // Update progress
          this.updateProgress();
        });
      });
    });
  }

  openModal() {
    if (!this.modal) return;
    this.modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  closeModal() {
    this.modal.classList.remove('active');
    document.body.style.overflow = '';
    // Reset forms
    this.showLogin();
    this.showStep(1);
  }

  showLogin() {
    this.loginForm.classList.add('active');
    this.registerForm.classList.remove('active');
  }

  showRegister() {
    this.registerForm.classList.add('active');
    this.loginForm.classList.remove('active');
  }

  showStep(stepNumber) {
    const steps = document.querySelectorAll('.register-step');
    steps.forEach((step, index) => {
      if (index + 1 === stepNumber) {
        step.classList.add('active');
      } else {
        step.classList.remove('active');
      }
    });
    this.currentStep = stepNumber;
    
    if (stepNumber === 2) {
      this.updateProgress();
    }
  }

  validateBasicInfo() {
    const email = document.getElementById('registerEmail').value;
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;

    if (!email || !username || !password) {
      this.showNotification('Please fill in all fields', 'error');
      return false;
    }

    if (username.length < 3) {
      this.showNotification('Username must be at least 3 characters', 'error');
      return false;
    }

    if (password.length < 6) {
      this.showNotification('Password must be at least 6 characters', 'error');
      return false;
    }

    return true;
  }

  updateProgress() {
    const requiredFields = [
      document.getElementById('fullName'),
      document.getElementById('dateOfBirth'),
      document.getElementById('gender'),
      document.getElementById('country'),
      document.getElementById('travelReasons'),
      document.getElementById('travelFrequency'),
      document.getElementById('budget')
    ];

    const filledCount = requiredFields.filter(field => field.value).length;
    const progress = (filledCount / requiredFields.length) * 100;
    
    const progressFill = document.querySelector('.progress-fill');
    if (progressFill) {
      progressFill.style.width = `${progress}%`;
    }
  }

  async handleLogin() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (response.ok) {
        // Store token and user data
        localStorage.setItem('mobix_token', data.access_token);
        state.user = data.user;
        state.token = data.access_token;

        this.showNotification(`Welcome back, ${data.user.username}!`, 'success');
        this.closeModal();
        
        // Update UI
        this.updateUIForLoggedInUser();
        
        // Navigate to profile after short delay
        setTimeout(() => {
          window.sidebarNavigate('profile');
        }, 1000);
      } else {
        this.showNotification(data.detail || 'Login failed', 'error');
      }
    } catch (error) {
      console.error('Login error:', error);
      this.showNotification('An error occurred during login', 'error');
    }
  }

  async handleRegister() {
    // Validate all survey fields
    const fullName = document.getElementById('fullName').value;
    const dateOfBirth = document.getElementById('dateOfBirth').value;
    const gender = document.getElementById('gender').value;
    const country = document.getElementById('country').value;
    const travelReasons = document.getElementById('travelReasons').value;
    const travelFrequency = document.getElementById('travelFrequency').value;
    const budget = document.getElementById('budget').value;
    const interests = document.getElementById('interests').value;

    if (!fullName || !dateOfBirth || !gender || !country || !travelReasons || !travelFrequency || !budget) {
      this.showNotification('Please complete all required fields', 'error');
      return;
    }

    const email = document.getElementById('registerEmail').value;
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;

    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email,
          username,
          password,
          full_name: fullName,
          gender,
          date_of_birth: dateOfBirth,
          country,
          interests,
          travel_frequency: travelFrequency,
          budget,
          travel_reasons: travelReasons
        })
      });

      const data = await response.json();

      if (response.ok) {
        // Store token and user data
        localStorage.setItem('mobix_token', data.access_token);
        state.user = data.user;
        state.token = data.access_token;

        this.showNotification(`Welcome to MOBIX, ${data.user.username}!`, 'success');
        this.closeModal();
        
        // Update UI
        this.updateUIForLoggedInUser();
        
        // Navigate to profile after short delay
        setTimeout(() => {
          window.sidebarNavigate('profile');
        }, 1500);
      } else {
        this.showNotification(data.detail || 'Registration failed', 'error');
      }
    } catch (error) {
      console.error('Registration error:', error);
      this.showNotification('An error occurred during registration', 'error');
    }
  }

  async validateToken(token) {
    try {
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        state.user = data;
        state.token = token;
        this.updateUIForLoggedInUser();
      } else {
        // Token invalid, clear it
        localStorage.removeItem('mobix_token');
        state.user = null;
        state.token = null;
      }
    } catch (error) {
      console.error('Token validation error:', error);
      localStorage.removeItem('mobix_token');
      state.user = null;
      state.token = null;
    }
  }

  updateUIForLoggedInUser() {
    // Update profile button to show user initials
    const profileBtn = document.getElementById('profileBtn');
    if (state.user) {
      profileBtn.classList.add('logged-in');
      profileBtn.innerHTML = `
        <div style="font-weight: 700; font-size: 14px;">
          ${state.user.username.substring(0, 2).toUpperCase()}
        </div>
      `;
      profileBtn.title = `${state.user.username} - Profile`;
    }
  }

  setupAvatarUpload() {
    const changeAvatarBtn = document.getElementById('changeAvatarBtn');
    const avatarInput = document.getElementById('avatarInput');
    
    if (changeAvatarBtn && avatarInput) {
      changeAvatarBtn.addEventListener('click', () => {
        avatarInput.click();
      });
      
      avatarInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        // Validate file type
        if (!file.type.startsWith('image/')) {
          this.showNotification('Please select an image file', 'error');
          return;
        }
        
        // Validate file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
          this.showNotification('Image must be smaller than 5MB', 'error');
          return;
        }
        
        // Upload image
        await this.uploadProfileImage(file);
      });
    }
  }

  async uploadProfileImage(file) {
    if (!state.token) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch(`${API_BASE}/api/auth/upload-profile-image`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${state.token}`
        },
        body: formData
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Update avatar display
        const profileAvatar = document.getElementById('profileAvatar');
        if (profileAvatar && data.profile_image) {
          // Create image element
          const img = document.createElement('img');
          img.src = `${API_BASE}${data.profile_image}`;
          img.style.cssText = 'width: 100%; height: 100%; border-radius: 50%; object-fit: cover;';
          profileAvatar.innerHTML = '';
          profileAvatar.appendChild(img);
        }
        
        this.showNotification('Profile picture updated!', 'success');
      } else {
        const error = await response.json();
        this.showNotification(error.detail || 'Upload failed', 'error');
      }
    } catch (error) {
      console.error('Upload error:', error);
      this.showNotification('Failed to upload image', 'error');
    }
  }

  loadProfileData() {
    if (!state.user) return;

    // Update profile header
    const profileAvatar = document.getElementById('profileAvatar');
    const profileName = document.getElementById('profileName');
    const profileEmail = document.getElementById('profileEmail');

    if (profileAvatar && state.user.username) {
      // Check if user has profile image
      if (state.user.profile_image) {
        const img = document.createElement('img');
        img.src = `${API_BASE}${state.user.profile_image}`;
        img.style.cssText = 'width: 100%; height: 100%; border-radius: 50%; object-fit: cover;';
        profileAvatar.innerHTML = '';
        profileAvatar.appendChild(img);
      } else {
        profileAvatar.textContent = state.user.username.substring(0, 2).toUpperCase();
      }
    }
    if (profileName) {
      profileName.textContent = state.user.full_name || state.user.username;
    }
    if (profileEmail) {
      profileEmail.textContent = state.user.email;
    }

    // Show logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
      logoutBtn.style.display = 'flex';
    }
  }

  logout() {
    localStorage.removeItem('mobix_token');
    state.user = null;
    state.token = null;
    
    // Reset profile button
    const profileBtn = document.getElementById('profileBtn');
    profileBtn.classList.remove('logged-in');
    profileBtn.innerHTML = `
      <span class="profile-text">Login / Register</span>
      <svg class="profile-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"/>
      </svg>
    `;
    profileBtn.title = 'Login / Register';
    
    // Hide logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
      logoutBtn.style.display = 'none';
    }
    
    this.showNotification('You have been logged out', 'success');
    
    // Navigate to home
    setTimeout(() => {
      window.navigation.showScreen('hero');
    }, 1000);
  }

  showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed;
      top: 90px;
      right: 24px;
      background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#667eea'};
      color: white;
      padding: 16px 24px;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      z-index: 10000;
      animation: slideInRight 0.4s ease, slideOutRight 0.4s ease 3s;
      font-weight: 600;
      max-width: 350px;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3400);
  }
}

export const auth = new AuthManager();
export default auth;
