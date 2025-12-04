/**
 * MOBIX - Chat Module
 * Upravlja chat funkcionalnostima
 */

import { api } from './api.js';
import { state } from './state.js';
import { ui } from './ui.js';

class ChatManager {
  constructor() {
    this.chatMessages = null;
    this.chatInput = null;
    this.sendBtn = null;
    this.newChatBtn = null;
  }

  init() {
    // Učitaj DOM elemente
    this.chatMessages = document.getElementById('chatMessages');
    this.chatInput = document.getElementById('chatInput');
    this.sendBtn = document.getElementById('sendBtn');
    this.newChatBtn = document.getElementById('newChatBtn');

    // Postavi event listenere
    this.setupEventListeners();

    // Učitaj chat history
    this.renderChatHistoryList();

    // Prikaži welcome message
    this.showWelcomeMessage();

    // Učitaj aktivni chat ili kreiraj novi
    if (state.activeChatId && state.savedChats.find(c => c.id === state.activeChatId)) {
      this.loadChat(state.activeChatId);
    } else if (state.savedChats.length > 0) {
      this.loadChat(state.savedChats[0].id);
    } else {
      this.createNewChat();
    }

    console.log('✅ Chat Manager initialized');
  }

  setupEventListeners() {
    // Send button
    if (this.sendBtn) {
      this.sendBtn.addEventListener('click', () => this.sendMessage());
    }

    // Enter to send
    if (this.chatInput) {
      // Auto-resize
      this.chatInput.addEventListener('input', () => {
        this.chatInput.style.height = 'auto';
        this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 150) + 'px';
      });

      // Enter key
      this.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
    }

    // New chat button
    if (this.newChatBtn) {
      this.newChatBtn.addEventListener('click', () => this.createNewChat());
    }
  }

  async sendMessage() {
    if (!this.chatInput || !this.chatMessages) return;

    const message = this.chatInput.value.trim();
    if (!message) return;

    // Dodaj user poruku u UI
    this.addMessageToUI('user', message);
    state.chatHistory.push({ role: 'user', content: message });

    // Očisti input
    this.chatInput.value = '';
    this.chatInput.style.height = 'auto';

    // Dodaj typing indicator
    this.showTypingIndicator();

    try {
      // Pošalji na backend
      console.log('Sending message to API:', message);
      const response = await api.sendMessage(message, state.sessionId);
      console.log('API response:', response);
      
      // Ukloni typing indicator
      this.hideTypingIndicator();

      // Dodaj assistant poruku - Backend vraća "reply" ne "response"
      const botResponse = response.reply || response.response || response.message || 'Hvala na poruci!';
      this.addMessageToUI('assistant', botResponse);
      state.chatHistory.push({ role: 'assistant', content: botResponse });

      // Ažuriraj trenutni chat
      this.updateCurrentChat(message, botResponse);

    } catch (error) {
      console.error('Chat error:', error);
      this.hideTypingIndicator();
      this.addMessageToUI('assistant', 'Izvините, došlo je do greške. Provjerite da li je server pokrenut.');
      ui.showNotification('Failed to send message: ' + error.message, 'error');
    }
  }

  addMessageToUI(role, content) {
    if (!this.chatMessages) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = this.formatMessage(content);
    
    messageDiv.appendChild(contentDiv);
    this.chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
  }

  formatMessage(content) {
    // Osnovni Markdown formatting
    let formatted = content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
    
    return formatted;
  }

  showTypingIndicator() {
    if (!this.chatMessages) return;

    const indicator = document.createElement('div');
    indicator.id = 'typingIndicator';
    indicator.className = 'chat-message assistant-message typing-indicator';
    indicator.innerHTML = `
      <div class="message-content">
        <div class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    `;
    this.chatMessages.appendChild(indicator);
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
  }

  hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
  }

  showWelcomeMessage() {
    if (!this.chatMessages) return;

    const welcomeHTML = `
      <div class="chat-message assistant-message">
        <div class="message-content">
          <p>👋 Pozdrav! Ja sam vaš AI putni\u010dki asistent.</p>
          <p>Mogu vam pomo\u0107i sa:</p>
          <ul>
            <li>🔍 Pronalaženjem destinacija i lokacija</li>
            <li>✈️ Planiranjem putovanja</li>
            <li>🏨 Preporukama za hotele i restorane</li>
            <li>🎯 Savjetima za putovanje</li>
          </ul>
          <p>Kako vam mogu pomo\u0107i danas?</p>
        </div>
      </div>
    `;
    this.chatMessages.innerHTML = welcomeHTML;
  }

  createNewChat() {
    const chatId = 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    const newChat = {
      id: chatId,
      title: 'Novi razgovor',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      sessionId: state.getOrCreateSession()
    };

    state.savedChats.unshift(newChat);
    state.saveSavedChats();
    state.saveActiveChatId(chatId);

    // Očisti trenutni chat UI
    state.chatHistory = [];
    if (this.chatMessages) {
      this.chatMessages.innerHTML = '';
      this.showWelcomeMessage();
    }

    // Kreiraj novu sesiju
    state.sessionId = state.getOrCreateSession();
    newChat.sessionId = state.sessionId;
    state.saveSavedChats();

    this.renderChatHistoryList();
    return chatId;
  }

  loadChat(chatId) {
    const chat = state.savedChats.find(c => c.id === chatId);
    if (!chat) return;

    state.saveActiveChatId(chatId);
    state.chatHistory = JSON.parse(JSON.stringify(chat.messages || []));
    state.sessionId = chat.sessionId || state.getOrCreateSession();

    // Re-render poruke
    if (this.chatMessages) {
      this.chatMessages.innerHTML = '';
      if (state.chatHistory.length === 0) {
        this.showWelcomeMessage();
      } else {
        state.chatHistory.forEach(msg => {
          this.addMessageToUI(msg.role, msg.content);
        });
      }
    }

    this.renderChatHistoryList();
  }

  updateCurrentChat(userMessage, assistantMessage) {
    const chat = state.savedChats.find(c => c.id === state.activeChatId);
    if (!chat) return;

    chat.messages = state.chatHistory;
    chat.updatedAt = new Date().toISOString();

    // Ažuriraj naslov na osnovu prve poruke
    if (chat.messages.length === 2) {
      chat.title = userMessage.substring(0, 30) + (userMessage.length > 30 ? '...' : '');
    }

    state.saveSavedChats();
    this.renderChatHistoryList();
  }

  renderChatHistoryList() {
    const listEl = document.getElementById('chatHistoryList');
    if (!listEl) return;

    if (state.savedChats.length === 0) {
      listEl.innerHTML = '<div class="chat-history-empty">No conversations yet</div>';
      return;
    }

    listEl.innerHTML = '';
    state.savedChats.forEach(chat => {
      const item = document.createElement('button');
      item.className = 'chat-history-item';
      if (chat.id === state.activeChatId) {
        item.classList.add('active');
      }

      const date = new Date(chat.updatedAt);
      item.innerHTML = `
        <div class="chat-history-content">
          <div class="chat-history-title">${chat.title}</div>
          <div class="chat-history-date">${date.toLocaleDateString()}</div>
        </div>
        <button class="chat-history-delete" data-chat-id="${chat.id}">🗑️</button>
      `;

      item.addEventListener('click', (e) => {
        if (!e.target.classList.contains('chat-history-delete')) {
          this.loadChat(chat.id);
        }
      });

      const deleteBtn = item.querySelector('.chat-history-delete');
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.deleteChat(chat.id);
      });

      listEl.appendChild(item);
    });
  }

  deleteChat(chatId) {
    state.savedChats = state.savedChats.filter(c => c.id !== chatId);
    state.saveSavedChats();

    if (state.activeChatId === chatId) {
      if (state.savedChats.length > 0) {
        this.loadChat(state.savedChats[0].id);
      } else {
        this.createNewChat();
      }
    }

    this.renderChatHistoryList();
  }

  showWelcomeMessage() {
    if (!this.chatMessages) return;

    const welcomeHTML = `
      <div class="welcome-message">
        <div class="welcome-icon">👋</div>
        <h2>Welcome to MOBIX Travel Assistant!</h2>
        <p>I'm here to help you plan your perfect trip. Ask me anything about destinations, travel tips, or recommendations.</p>
        <div class="welcome-suggestions">
          <button class="suggestion-chip" data-suggestion="What are the best places to visit in Europe?">
            🌍 Best places in Europe
          </button>
          <button class="suggestion-chip" data-suggestion="I need a budget-friendly vacation idea">
            💰 Budget vacation ideas
          </button>
          <button class="suggestion-chip" data-suggestion="What should I pack for a beach vacation?">
            🏖️ Beach packing tips
          </button>
          <button class="suggestion-chip" data-suggestion="Recommend a 7-day itinerary for Japan">
            🗾 Japan itinerary
          </button>
        </div>
      </div>
    `;

    this.chatMessages.innerHTML = welcomeHTML;

    // Add click handlers for suggestions
    document.querySelectorAll('.suggestion-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const suggestion = chip.getAttribute('data-suggestion');
        if (this.chatInput) {
          this.chatInput.value = suggestion;
          this.sendMessage();
        }
      });
    });
  }
}

export const chat = new ChatManager();
export default chat;
