/**
 * MOBIX - State Management Module
 * Upravlja globalnim stanjem aplikacije
 */

import { CONFIG } from './config.js';

class StateManager {
  constructor() {
    this.currentScreen = 'hero';
    this.sessionId = this.getOrCreateSession();
    this.chatHistory = [];
    this.savedChats = this.loadSavedChats();
    this.activeChatId = this.loadActiveChatId();
    this.itineraries = this.loadItineraries();
    this.activeItineraryId = null;
    this.currentUser = null;
    this.authToken = localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
  }

  // Session Management
  getOrCreateSession() {
    let sid = localStorage.getItem(CONFIG.STORAGE_KEYS.SESSION);
    if (!sid) {
      sid = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem(CONFIG.STORAGE_KEYS.SESSION, sid);
    }
    return sid;
  }

  // Chat Management
  loadSavedChats() {
    try {
      const stored = localStorage.getItem(CONFIG.STORAGE_KEYS.CHATS);
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      console.error('Failed to load saved chats:', e);
      return [];
    }
  }

  saveSavedChats() {
    try {
      localStorage.setItem(CONFIG.STORAGE_KEYS.CHATS, JSON.stringify(this.savedChats));
    } catch (e) {
      console.error('Failed to save chats:', e);
    }
  }

  loadActiveChatId() {
    return localStorage.getItem(CONFIG.STORAGE_KEYS.ACTIVE_CHAT) || null;
  }

  saveActiveChatId(chatId) {
    if (chatId) {
      localStorage.setItem(CONFIG.STORAGE_KEYS.ACTIVE_CHAT, chatId);
    } else {
      localStorage.removeItem(CONFIG.STORAGE_KEYS.ACTIVE_CHAT);
    }
    this.activeChatId = chatId;
  }

  // Itinerary Management
  loadItineraries() {
    try {
      const stored = localStorage.getItem(CONFIG.STORAGE_KEYS.ITINERARIES);
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      console.error('Failed to load itineraries:', e);
      return [];
    }
  }

  saveItineraries() {
    try {
      localStorage.setItem(CONFIG.STORAGE_KEYS.ITINERARIES, JSON.stringify(this.itineraries));
    } catch (e) {
      console.error('Failed to save itineraries:', e);
    }
  }

  // User/Auth Management
  setUser(user, token) {
    this.currentUser = user;
    this.authToken = token;
    if (token) {
      localStorage.setItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN, token);
    }
    if (user) {
      localStorage.setItem(CONFIG.STORAGE_KEYS.USER_DATA, JSON.stringify(user));
    }
  }

  clearUser() {
    this.currentUser = null;
    this.authToken = null;
    localStorage.removeItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_DATA);
  }

  loadUser() {
    try {
      const stored = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_DATA);
      if (stored) {
        this.currentUser = JSON.parse(stored);
      }
    } catch (e) {
      console.error('Failed to load user data:', e);
    }
  }

  // Dark Mode
  loadDarkMode() {
    const isDark = localStorage.getItem(CONFIG.STORAGE_KEYS.DARK_MODE) === 'true';
    return isDark;
  }

  saveDarkMode(isDark) {
    localStorage.setItem(CONFIG.STORAGE_KEYS.DARK_MODE, isDark);
  }
}

// Export singleton instance
export const state = new StateManager();
export default state;
