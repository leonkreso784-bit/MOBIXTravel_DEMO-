/**
 * MOBIX - UI Utilities Module
 * Helper funkcije za UI manipulaciju
 */

import { CONFIG } from './config.js';

class UIManager {
  constructor() {
    this.notificationContainer = null;
    this.themeToggle = null;
    this.hamburgerBtn = null;
    this.sidebar = null;
  }

  init() {
    // Kreiraj notification container ako ne postoji
    this.notificationContainer = document.getElementById('notificationContainer');
    if (!this.notificationContainer) {
      this.notificationContainer = document.createElement('div');
      this.notificationContainer.id = 'notificationContainer';
      this.notificationContainer.className = 'notification-container';
      document.body.appendChild(this.notificationContainer);
    }

    // Inicijalizuj dark mode
    this.themeToggle = document.getElementById('themeToggle');
    this.initDarkMode();

    // Inicijalizuj hamburger i sidebar
    this.hamburgerBtn = document.getElementById('hamburgerBtn');
    this.sidebar = document.querySelector('.sidebar');
    this.initSidebar();
  }

  // Sidebar Management
  initSidebar() {
    if (!this.hamburgerBtn) return;

    this.sidebar = document.querySelector('.sidebar');
    const closeSidebar = document.getElementById('closeSidebar');
    const overlay = document.querySelector('.sidebar-overlay');

    if (!this.sidebar) return;

    // Toggle sidebar on hamburger click
    this.hamburgerBtn.addEventListener('click', () => {
      this.sidebar.classList.toggle('active');
      if (overlay) overlay.classList.toggle('active');
    });

    // Close sidebar on close button
    if (closeSidebar) {
      closeSidebar.addEventListener('click', () => {
        this.sidebar.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
      });
    }

    // Close sidebar when clicking overlay
    if (overlay) {
      overlay.addEventListener('click', () => {
        this.sidebar.classList.remove('active');
        overlay.classList.remove('active');
      });
    }
  }

    console.log('✅ Sidebar initialized');
  }

  // Notification System
  showNotification(message, type = 'info', title = '') {
    if (!this.notificationContainer) return;

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;

    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };

    notification.innerHTML = `
      <div class="notification-icon">${icons[type] || icons.info}</div>
      <div class="notification-content">
        ${title ? `<div class="notification-title">${title}</div>` : ''}
        <div class="notification-message">${message}</div>
      </div>
      <button class="notification-close">×</button>
    `;

    // Close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
      notification.remove();
    });

    this.notificationContainer.appendChild(notification);

    // Auto-remove
    setTimeout(() => {
      if (notification.parentElement) {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
      }
    }, CONFIG.UI.NOTIFICATION_DURATION);
  }

  // Loading States
  showLoading(buttonId, loadingText = 'Loading...') {
    const button = document.getElementById(buttonId);
    if (!button) return;

    button.disabled = true;
    button.dataset.originalText = button.textContent;
    button.innerHTML = `
      <span class="spinner"></span>
      <span>${loadingText}</span>
    `;
  }

  hideLoading(buttonId, originalText = null) {
    const button = document.getElementById(buttonId);
    if (!button) return;

    button.disabled = false;
    button.textContent = originalText || button.dataset.originalText || 'Submit';
    delete button.dataset.originalText;
  }

  // Dark Mode
  initDarkMode() {
    const savedDarkMode = localStorage.getItem(CONFIG.STORAGE_KEYS.DARK_MODE) === 'true';
    
    if (this.themeToggle) {
      this.themeToggle.checked = savedDarkMode;
      this.themeToggle.addEventListener('change', () => this.toggleDarkMode());
    }

    if (savedDarkMode) {
      document.body.classList.add('dark-mode');
    }
    
    console.log('🌓 Dark mode initialized:', savedDarkMode);
  }

  toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem(CONFIG.STORAGE_KEYS.DARK_MODE, isDark ? 'true' : 'false');
    
    console.log('🌓 Dark mode toggled:', isDark ? 'ON' : 'OFF');
  }

  // Date Picker Helper
  populateDatePicker(monthId, dayId, yearId) {
    const monthEl = document.getElementById(monthId);
    const dayEl = document.getElementById(dayId);
    const yearEl = document.getElementById(yearId);

    if (!monthEl || !dayEl || !yearEl) return;

    // Months
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    monthEl.innerHTML = '<option value="">Month</option>';
    months.forEach((month, index) => {
      const option = document.createElement('option');
      option.value = String(index + 1).padStart(2, '0');
      option.textContent = month;
      monthEl.appendChild(option);
    });

    // Days
    dayEl.innerHTML = '<option value="">Day</option>';
    for (let i = 1; i <= 31; i++) {
      const option = document.createElement('option');
      option.value = String(i).padStart(2, '0');
      option.textContent = i;
      dayEl.appendChild(option);
    }

    // Years
    const currentYear = new Date().getFullYear();
    yearEl.innerHTML = '<option value="">Year</option>';
    for (let i = currentYear; i >= currentYear - 100; i--) {
      const option = document.createElement('option');
      option.value = i;
      option.textContent = i;
      yearEl.appendChild(option);
    }
  }

  // Typing Animation
  initTypingAnimation() {
    const typingTextEl = document.getElementById('typingText');
    if (!typingTextEl) return;

    const textsData = typingTextEl.getAttribute('data-texts');
    if (!textsData) return;

    let texts = CONFIG.TYPING_TEXTS;
    try {
      texts = JSON.parse(textsData);
    } catch (e) {
      console.warn('Failed to parse typing texts, using default');
    }

    let textIndex = 0;
    let charIndex = 0;
    let isDeleting = false;

    const type = () => {
      const currentText = texts[textIndex];

      if (isDeleting) {
        typingTextEl.textContent = currentText.substring(0, charIndex - 1);
        charIndex--;
      } else {
        typingTextEl.textContent = currentText.substring(0, charIndex + 1);
        charIndex++;
      }

      let typeSpeed = isDeleting ? 50 : 100;

      if (!isDeleting && charIndex === currentText.length) {
        typeSpeed = 2000;
        isDeleting = true;
      } else if (isDeleting && charIndex === 0) {
        isDeleting = false;
        textIndex = (textIndex + 1) % texts.length;
        typeSpeed = 500;
      }

      setTimeout(type, typeSpeed);
    };

    type();
  }
}

export const ui = new UIManager();
export default ui;
