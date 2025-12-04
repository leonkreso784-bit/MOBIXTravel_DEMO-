// ========================================
// MOBIX Chat Functions
// ========================================

(function() {
  'use strict';
  
  document.addEventListener('DOMContentLoaded', function() {
    console.log('[MOBIX Chat] Initializing...');
    
    // ========== DOM ELEMENTS ==========
    var chatMessages = document.getElementById('chatMessages');
    var chatInput = document.getElementById('chatInput');
    var sendBtn = document.getElementById('sendBtn');
    var newChatBtn = document.getElementById('newChatBtn');
    var chatHistoryList = document.getElementById('chatHistoryList');
    
    // ========== STATE ==========
    var chatSessionId = 'chat_' + Date.now();
    var chatHistory = [];
    var savedChats = JSON.parse(localStorage.getItem('mobix_saved_chats') || '[]');
    var currentChatId = null;
    
    // ========== WELCOME MESSAGE ==========
    function showChatWelcome() {
      if (!chatMessages) return;
      chatMessages.innerHTML = '';
      
      var welcome = document.createElement('div');
      welcome.className = 'welcome-message';
      welcome.innerHTML = 
        '<div class="welcome-icon">🌍</div>' +
        '<h2>Welcome to MOBIX</h2>' +
        '<p>Your AI travel assistant. Ask me about destinations, flights, hotels, or anything travel related!</p>' +
        '<div class="welcome-suggestions">' +
          '<button class="suggestion-chip" onclick="window.MOBIX.sendSuggestion(\'Best hotels in Paris\')">Best hotels in Paris</button>' +
          '<button class="suggestion-chip" onclick="window.MOBIX.sendSuggestion(\'Top restaurants in Rome\')">Top restaurants in Rome</button>' +
          '<button class="suggestion-chip" onclick="window.MOBIX.sendSuggestion(\'Things to do in Barcelona\')">Things to do in Barcelona</button>' +
          '<button class="suggestion-chip" onclick="window.MOBIX.sendSuggestion(\'Must see places in Tokyo\')">Must see places in Tokyo</button>' +
        '</div>';
      chatMessages.appendChild(welcome);
    }
    
    window.MOBIX = window.MOBIX || {};
    window.MOBIX.sendSuggestion = function(text) {
      if (chatInput) {
        chatInput.value = text;
        sendChatMessage();
      }
    };
    // Backward compatibility
    window.sendSuggestion = window.MOBIX.sendSuggestion;
    
    // ========== CARD PARSING ==========
    function parseCards(content) {
      var cards = [];
      var cardRegex = /\[CARD\]([\s\S]*?)\[\/CARD\]/g;
      var match;
      
      while ((match = cardRegex.exec(content)) !== null) {
        var cardContent = match[1];
        var card = {};
        
        var lines = cardContent.trim().split('\n');
        lines.forEach(function(line) {
          if (line.trim().startsWith('data:')) {
            var jsonStr = line.substring(line.indexOf(':') + 1).trim();
            try {
              card.data = JSON.parse(jsonStr);
            } catch(e) {
              console.log('[MOBIX Chat] Failed to parse card data:', jsonStr);
              card.data = {};
            }
          } else {
            var colonIndex = line.indexOf(':');
            if (colonIndex > 0) {
              var key = line.substring(0, colonIndex).trim();
              var value = line.substring(colonIndex + 1).trim();
              card[key] = value;
            }
          }
        });
        
        console.log('[MOBIX Chat] Parsed card:', card);
        cards.push({ card: card, fullMatch: match[0] });
      }
      
      console.log('[MOBIX Chat] Total cards found:', cards.length);
      return cards;
    }
    
    // ========== CARD RENDERING ==========
    function renderCard(card) {
      var type = card.type || 'activity';
      var title = card.title || 'Unknown';
      var city = card.city || '';
      var details = card.details || '';
      var link = card.link || '#';
      var data = card.data || {};
      
      var iconMap = {
        'plane': '✈️',
        'car': '🚗',
        'bus': '🚌',
        'train': '🚆',
        'hotel': '🏨',
        'restaurant': '🍽️',
        'activity': '🎯'
      };
      
      var colorMap = {
        'plane': '#3B82F6',
        'car': '#10B981',
        'bus': '#F59E0B',
        'train': '#8B5CF6',
        'hotel': '#EC4899',
        'restaurant': '#F97316',
        'activity': '#06B6D4'
      };
      
      var icon = iconMap[type] || '📍';
      var color = colorMap[type] || '#6B7280';
      
      // Clean title (remove emoji if already in title)
      var cleanTitle = title.replace(/^[🚗✈️🚌🚆🏨🍽️🎯]\s*/, '');
      
      var html = '<div class="chat-card" style="border-left-color: ' + color + '">';
      html += '<div class="chat-card-header">';
      html += '<span class="chat-card-icon" style="background: ' + color + '">' + icon + '</span>';
      html += '<div class="chat-card-title">' + cleanTitle + '</div>';
      html += '</div>';
      
      if (city) {
        html += '<div class="chat-card-subtitle">' + city + '</div>';
      }
      
      if (details) {
        html += '<div class="chat-card-details">' + details + '</div>';
      }
      
      html += '<div class="chat-card-actions">';
      if (link && link !== '#') {
        html += '<a href="' + link + '" target="_blank" class="chat-card-link">View Details</a>';
      }
      
      // Encode data for onclick - now uses new Travel Note system
      var encodedData = encodeURIComponent(JSON.stringify(data));
      html += '<button class="chat-card-add" onclick="window.MOBIX.addCardToTravelNote(\'' + encodedData + '\', this)">+ Add to Travel Note</button>';
      html += '</div>';
      html += '</div>';
      
      return html;
    }
    
    // ========== ADD CARD TO TRAVEL NOTE (Legacy fallback) ==========
    // This will be overridden by travelnote.js when loaded
    if (!window.MOBIX.addCardToTravelNote) {
      window.MOBIX.addCardToTravelNote = function(encodedData, btn) {
        console.log('[MOBIX Chat] Using fallback addCardToTravelNote');
        try {
          var data = JSON.parse(decodeURIComponent(encodedData));
          
          // Try to use new travel notes system
          var travelNotes = JSON.parse(localStorage.getItem('mobix_travel_notes') || '[]');
          
          // Determine category
          var category = 'activities';
          var type = data.type || '';
          var mode = data.mode || '';
          
          if (type === 'transport' || mode === 'plane' || mode === 'car' || mode === 'bus' || mode === 'train') {
            category = 'transports';
          } else if (type === 'hotel') {
            category = 'hotels';
          } else if (type === 'restaurant') {
            category = 'restaurants';
          }
          
          var cardItem = {
            id: 'card_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5),
            title: data.name || data.title || data.route || 'Item',
            subtitle: data.address || data.city || data.airline || '',
            price: data.price ? '€' + data.price : '',
            category: category,
            data: data,
            addedAt: new Date().toISOString()
          };
          
          // Create new note if none exist
          if (travelNotes.length === 0) {
            var noteTitle = data.city ? 'Trip to ' + data.city : 'My Travel Note';
            var newNote = {
              id: 'note_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5),
              title: noteTitle,
              content: '',
              cards: [cardItem],
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString()
            };
            travelNotes.push(newNote);
          } else {
            // Add to first note
            travelNotes[0].cards.push(cardItem);
            travelNotes[0].updatedAt = new Date().toISOString();
          }
          
          localStorage.setItem('mobix_travel_notes', JSON.stringify(travelNotes));
          
          // Update button
          if (btn) {
            btn.innerHTML = '✓ Added';
            btn.disabled = true;
            btn.classList.add('added');
          }
          
          showToast('Added to Travel Note!', 'success');
          
        } catch(e) {
          console.error('[MOBIX Chat] Error adding to travel note:', e);
          showToast('Error adding to travel note', 'error');
        }
      };
    }
    // Backward compatibility
    window.addCardToPlanner = window.MOBIX.addCardToTravelNote;
    
    // ========== ADD MESSAGE TO CHAT ==========
    function addChatMessage(role, content, skipSave) {
      console.log('[MOBIX Chat] addChatMessage:', role, 'length:', content ? content.length : 0);
      if (!chatMessages) {
        console.error('[MOBIX Chat] chatMessages element not found!');
        return;
      }
      
      // Remove welcome message if exists
      var welcome = chatMessages.querySelector('.welcome-message');
      if (welcome) welcome.remove();
      
      var messageDiv = document.createElement('div');
      messageDiv.className = 'chat-message ' + role + '-message';
      
      var contentDiv = document.createElement('div');
      contentDiv.className = 'message-content';
      
      if (role === 'assistant') {
        // Parse and render cards
        console.log('[MOBIX Chat] Parsing cards from content...');
        var cards = parseCards(content);
        console.log('[MOBIX Chat] Found', cards.length, 'cards');
        var processedContent = content;
        
        // Replace card blocks with rendered HTML
        cards.forEach(function(cardInfo, index) {
          console.log('[MOBIX Chat] Rendering card', index + 1, ':', cardInfo.card.type, cardInfo.card.title);
          var cardHtml = renderCard(cardInfo.card);
          processedContent = processedContent.replace(cardInfo.fullMatch, cardHtml);
        });
        
        // Format remaining text
        processedContent = processedContent
          // Convert markdown links [text](url) to clickable buttons
          .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="chat-link-btn">$1</a>')
          // Bold
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          // Italic
          .replace(/\*(.*?)\*/g, '<em>$1</em>')
          // Headers
          .replace(/^## (.*?)$/gm, '<h3 class="chat-heading">$1</h3>')
          .replace(/^### (.*?)$/gm, '<h4 class="chat-subheading">$1</h4>')
          // Horizontal rule
          .replace(/^---$/gm, '<hr class="chat-divider">')
          // Line breaks
          .replace(/\n/g, '<br>');
        
        contentDiv.innerHTML = processedContent;
      } else {
        // User message - simple formatting
        var formatted = content
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.*?)\*/g, '<em>$1</em>')
          .replace(/\n/g, '<br>');
        
        contentDiv.innerHTML = formatted;
      }
      
      messageDiv.appendChild(contentDiv);
      chatMessages.appendChild(messageDiv);
      
      // Scroll to bottom
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // ========== TYPING INDICATOR ==========
    function showTypingIndicator() {
      if (!chatMessages) return;
      
      var indicator = document.createElement('div');
      indicator.id = 'typingIndicator';
      indicator.className = 'chat-message assistant-message';
      indicator.innerHTML = 
        '<div class="message-content">' +
          '<div class="typing-dots">' +
            '<span></span><span></span><span></span>' +
          '</div>' +
        '</div>';
      chatMessages.appendChild(indicator);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function hideTypingIndicator() {
      var indicator = document.getElementById('typingIndicator');
      if (indicator) indicator.remove();
    }
    
    // ========== CHAT HISTORY MANAGEMENT ==========
    function generateChatId() {
      return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    function generateChatTitle(firstMessage) {
      var title = firstMessage.trim();
      if (title.length > 30) {
        title = title.substring(0, 30) + '...';
      }
      return title || 'New Chat';
    }
    
    function saveCurrentChat() {
      if (!currentChatId || chatHistory.length === 0) return;
      
      var existingIndex = savedChats.findIndex(function(c) { return c.id === currentChatId; });
      var existingChat = existingIndex >= 0 ? savedChats[existingIndex] : null;
      
      var chatData = {
        id: currentChatId,
        title: existingChat ? existingChat.title : generateChatTitle(chatHistory[0]?.content || 'New Chat'),
        messages: chatHistory,
        updatedAt: new Date().toISOString(),
        sessionId: chatSessionId
      };
      
      if (existingIndex >= 0) {
        savedChats[existingIndex] = chatData;
      } else {
        savedChats.unshift(chatData);
      }
      
      localStorage.setItem('mobix_saved_chats', JSON.stringify(savedChats));
      renderChatHistoryList();
    }
    
    function renderChatHistoryList() {
      if (!chatHistoryList) return;
      
      chatHistoryList.innerHTML = '';
      
      if (savedChats.length === 0) {
        chatHistoryList.innerHTML = '<div class="chat-history-empty">No conversations yet</div>';
        return;
      }
      
      savedChats.forEach(function(chat) {
        var item = document.createElement('div');
        item.className = 'chat-history-item' + (chat.id === currentChatId ? ' active' : '');
        
        var date = new Date(chat.updatedAt);
        var dateStr = date.toLocaleDateString('hr-HR', { day: 'numeric', month: 'short' });
        
        item.innerHTML = 
          '<div class="chat-history-item-content">' +
            '<div class="chat-history-title">' + chat.title + '</div>' +
            '<div class="chat-history-date">' + dateStr + '</div>' +
          '</div>' +
          '<button class="chat-history-delete" onclick="event.stopPropagation(); window.MOBIX.deleteChat(\'' + chat.id + '\')" title="Delete">🗑️</button>';
        
        item.onclick = function() {
          loadChat(chat.id);
        };
        
        chatHistoryList.appendChild(item);
      });
    }
    
    function loadChat(chatId) {
      var chat = savedChats.find(function(c) { return c.id === chatId; });
      if (!chat) {
        console.warn('[MOBIX Chat] Chat not found:', chatId);
        return;
      }
      
      console.log('[MOBIX Chat] Loading chat:', chatId, chat.title);
      
      // Hide typing indicator from previous chat if visible
      hideTypingIndicator();
      
      currentChatId = chatId;
      chatSessionId = chat.sessionId || chatId;
      chatHistory = chat.messages ? chat.messages.slice() : []; // Copy array
      
      if (chatMessages) {
        chatMessages.innerHTML = '';
        chatHistory.forEach(function(msg) {
          addChatMessage(msg.role, msg.content, true);
        });
      }
      
      renderChatHistoryList();
    }
    
    window.MOBIX.deleteChat = async function(chatId) {
      var confirmed = await showConfirmModal({
        title: 'Delete Conversation',
        message: 'Are you sure you want to delete this conversation? This action cannot be undone.',
        confirmText: 'Delete'
      });
      
      if (!confirmed) return;
      
      // Remove from array immediately
      savedChats = savedChats.filter(function(c) { return c.id !== chatId; });
      localStorage.setItem('mobix_saved_chats', JSON.stringify(savedChats));
      
      // If we deleted the current chat, start fresh
      if (currentChatId === chatId) {
        currentChatId = null;
        chatHistory = [];
        chatSessionId = null;
        
        // Load another chat or show welcome
        if (savedChats.length > 0) {
          loadChat(savedChats[0].id);
        } else {
          showChatWelcome();
          renderChatHistoryList();
        }
      } else {
        renderChatHistoryList();
      }
    };
    // Backward compatibility
    window.deleteChat = window.MOBIX.deleteChat;
    
    function startNewChat() {
      console.log('[MOBIX Chat] Starting new chat...');
      
      // Only save current chat if it has messages AND is already in savedChats
      if (currentChatId && chatHistory.length > 0) {
        var existingChat = savedChats.find(function(c) { return c.id === currentChatId; });
        if (existingChat) {
          saveCurrentChat();
        }
      }
      
      // Create completely fresh session
      currentChatId = generateChatId();
      chatSessionId = currentChatId;
      chatHistory = [];
      
      // Show welcome screen (this clears chat area)
      showChatWelcome();
      
      // Update sidebar - no chat should be active (it's a new unsaved chat)
      renderChatHistoryList();
      
      console.log('[MOBIX Chat] New chat started:', currentChatId);
    }
    
    // ========== SEND MESSAGE ==========
    async function sendChatMessage() {
      if (!chatInput || !chatMessages) return;
      
      var message = chatInput.value.trim();
      if (!message) return;
      
      // IMPORTANT: Capture the chat context BEFORE async operation
      var targetChatId = currentChatId;
      var targetSessionId = chatSessionId;
      var isFirstMessage = chatHistory.length === 0;
      
      addChatMessage('user', message);
      chatHistory.push({ role: 'user', content: message });
      
      // ALWAYS save after user sends message (so it exists when response arrives)
      saveCurrentChat();
      
      chatInput.value = '';
      chatInput.style.height = 'auto';
      
      showTypingIndicator();
      
      try {
        var response = await fetch(window.__MOBIX_API_BASE__ + '/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: message,
            session_id: targetSessionId
          })
        });
        
        var data = await response.json();
        
        // Check if user switched to different chat while waiting
        if (currentChatId !== targetChatId) {
          console.log('[MOBIX Chat] User switched chats, saving response to original chat:', targetChatId);
          
          var botResponse = data.reply || data.response || data.message || 'Hvala na poruci!';
          
          // Find the original chat in savedChats
          var originalChatIndex = savedChats.findIndex(function(c) { return c.id === targetChatId; });
          
          if (originalChatIndex >= 0) {
            // Chat exists - add response to it
            savedChats[originalChatIndex].messages.push({ role: 'assistant', content: botResponse });
            savedChats[originalChatIndex].updatedAt = new Date().toISOString();
          } else {
            // Chat wasn't saved yet (user switched before first message was saved)
            // Create new chat entry with the captured messages
            var newChatEntry = {
              id: targetChatId,
              title: generateChatTitle(message), // Use the original message for title
              messages: [
                { role: 'user', content: message },
                { role: 'assistant', content: botResponse }
              ],
              updatedAt: new Date().toISOString(),
              sessionId: targetSessionId
            };
            savedChats.unshift(newChatEntry);
          }
          
          localStorage.setItem('mobix_saved_chats', JSON.stringify(savedChats));
          renderChatHistoryList();
          
          // Remove typing indicator if still visible
          hideTypingIndicator();
          return;
        }
        
        // User is still in the same chat - normal flow
        hideTypingIndicator();
        
        var botResponse = data.reply || data.response || data.message || 'Hvala na poruci!';
        addChatMessage('assistant', botResponse);
        chatHistory.push({ role: 'assistant', content: botResponse });
        
        saveCurrentChat();
        
      } catch (error) {
        console.error('[MOBIX Chat] Error:', error);
        hideTypingIndicator();
        
        // Only show error if still in same chat
        if (currentChatId === targetChatId) {
          addChatMessage('assistant', 'Sorry, there was an error. Please make sure the server is running.');
        }
      }
    }
    
    // ========== EVENT LISTENERS ==========
    if (sendBtn) {
      sendBtn.onclick = function() {
        console.log('[MOBIX Chat] Send button clicked');
        sendChatMessage();
      };
    }
    
    if (chatInput) {
      chatInput.oninput = function() {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
      };
      
      chatInput.onkeydown = function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendChatMessage();
        }
      };
    }
    
    if (newChatBtn) {
      newChatBtn.onclick = function() {
        console.log('[MOBIX Chat] New chat button clicked');
        startNewChat();
      };
    }
    
    // ========== INITIALIZATION ==========
    if (savedChats.length > 0) {
      loadChat(savedChats[0].id);
    } else {
      startNewChat();
    }
    
    console.log('[MOBIX Chat] Initialization complete');
    console.log('[MOBIX Chat] Saved chats:', savedChats.length);
  });
})();
