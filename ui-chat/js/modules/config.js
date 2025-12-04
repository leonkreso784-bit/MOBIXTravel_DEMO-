/**
 * MOBIX - Configuration Module
 * Centralna konfiguracija za cijelu aplikaciju
 */

// Named export for direct import
export const API_BASE = window.__MOBIX_API_BASE__ || 'http://127.0.0.1:8000';

export const CONFIG = {
  // API Configuration
  API_BASE: API_BASE,
  
  // Local Storage Keys
  STORAGE_KEYS: {
    SESSION: 'mobix_session_v2',
    AUTH_TOKEN: 'mobix_auth_token',
    USER_DATA: 'mobix_user_data',
    CHATS: 'mobix_chats_v2',
    ACTIVE_CHAT: 'mobix_active_chat',
    ITINERARIES: 'mobix_itineraries_v2',
    DARK_MODE: 'mobix_dark_mode'
  },
  
  // UI Settings
  UI: {
    ANIMATION_DURATION: 300,
    CHAT_MAX_HEIGHT: 150,
    NOTIFICATION_DURATION: 3000
  },
  
  // Typing Animation Texts
  TYPING_TEXTS: [
    "Your AI Travel Assistant",
    "Plan Your Perfect Journey",
    "Discover Amazing Destinations",
    "Book Flights, Hotels & More",
    "Experience the World"
  ]
};

export default CONFIG;
