// ========================================
// MOBIX Travel Note Module
// ========================================

(function() {
  'use strict';
  
  // ========== CONSTANTS ==========
  const STORAGE_KEY = 'mobix_travel_notes';
  
  // ========== STATE ==========
  let travelNotes = [];
  let activeNoteId = null;
  let autoSaveTimer = null;
  
  // ========== DOM ELEMENTS ==========
  let notesList = null;
  let noteEditor = null;
  let noteTitle = null;
  let noteContent = null;
  let savedCardsContainer = null;
  let emptyState = null;
  let editorContainer = null;
  let saveStatus = null;
  
  // ========== INITIALIZATION ==========
  document.addEventListener('DOMContentLoaded', function() {
    console.log('[MOBIX TravelNote] Initializing...');
    
    // Load DOM elements
    notesList = document.getElementById('travelNotesList');
    noteEditor = document.getElementById('travelNoteEditor');
    noteTitle = document.getElementById('noteTitle');
    noteContent = document.getElementById('noteContent');
    savedCardsContainer = document.getElementById('noteSavedCards');
    emptyState = document.getElementById('noteEmptyState');
    editorContainer = document.getElementById('noteEditorContainer');
    saveStatus = document.getElementById('noteSaveStatus');
    
    // Load notes from storage
    loadNotes();
    
    // Render notes list
    renderNotesList();
    
    // Setup event listeners
    setupEventListeners();
    
    // Expose global functions
    window.MOBIX = window.MOBIX || {};
    window.MOBIX.addCardToTravelNote = addCardToTravelNote;
    window.MOBIX.createNewTravelNote = createNewNote;
    window.MOBIX.openTravelNote = openNote;
    window.MOBIX.deleteTravelNote = deleteNote;
    window.MOBIX.getTravelNotes = function() { return travelNotes; };
    
    console.log('[MOBIX TravelNote] Initialized with', travelNotes.length, 'notes');
  });
  
  // ========== STORAGE ==========
  function loadNotes() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      travelNotes = stored ? JSON.parse(stored) : [];
      
      // Migration: Convert old format if exists
      const oldFormat = localStorage.getItem('mobix_travel_note');
      if (oldFormat && travelNotes.length === 0) {
        const oldData = JSON.parse(oldFormat);
        if (oldData.transports || oldData.hotels || oldData.restaurants || oldData.activitys) {
          // Create a note from old data
          const migratedNote = {
            id: 'note_migrated_' + Date.now(),
            title: 'My Travel Items',
            content: '',
            cards: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          };
          
          // Migrate cards
          ['transports', 'hotels', 'restaurants', 'activitys'].forEach(function(category) {
            if (oldData[category] && oldData[category].length > 0) {
              oldData[category].forEach(function(item) {
                migratedNote.cards.push({
                  ...item,
                  category: category.replace('activitys', 'activities')
                });
              });
            }
          });
          
          if (migratedNote.cards.length > 0) {
            travelNotes.push(migratedNote);
            saveNotes();
          }
        }
      }
    } catch(e) {
      console.error('[MOBIX TravelNote] Failed to load notes:', e);
      travelNotes = [];
    }
  }
  
  function saveNotes() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(travelNotes));
    } catch(e) {
      console.error('[MOBIX TravelNote] Failed to save notes:', e);
    }
  }
  
  // ========== NOTE MANAGEMENT ==========
  function createNewNote(initialTitle, initialCard) {
    const noteId = 'note_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
    const newNote = {
      id: noteId,
      title: initialTitle || 'New Travel Note',
      content: '',
      cards: initialCard ? [initialCard] : [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    travelNotes.unshift(newNote);
    saveNotes();
    renderNotesList();
    openNote(noteId);
    
    return noteId;
  }
  
  function openNote(noteId) {
    const note = travelNotes.find(function(n) { return n.id === noteId; });
    if (!note) {
      console.warn('[MOBIX TravelNote] Note not found:', noteId);
      return;
    }
    
    activeNoteId = noteId;
    
    // Update UI
    if (emptyState) emptyState.classList.add('hidden');
    if (editorContainer) editorContainer.classList.remove('hidden');
    
    // Populate editor
    if (noteTitle) {
      noteTitle.value = note.title;
    }
    if (noteContent) {
      noteContent.value = note.content;
    }
    
    // Render saved cards
    renderSavedCards(note.cards);
    
    // Update active state in list
    renderNotesList();
    
    // Focus content if empty
    if (!note.content && noteContent) {
      noteContent.focus();
    }
    
    updateSaveStatus('saved');
  }
  
  function saveCurrentNote() {
    if (!activeNoteId) return;
    
    const note = travelNotes.find(function(n) { return n.id === activeNoteId; });
    if (!note) return;
    
    // Update note data
    if (noteTitle) note.title = noteTitle.value || 'Untitled Note';
    if (noteContent) note.content = noteContent.value;
    note.updatedAt = new Date().toISOString();
    
    saveNotes();
    renderNotesList();
    updateSaveStatus('saved');
  }
  
  async function deleteNote(noteId) {
    const confirmed = await showConfirmModal({
      title: 'Delete Travel Note',
      message: 'Are you sure you want to delete this travel note? All saved items will be lost.',
      confirmText: 'Delete'
    });
    
    if (!confirmed) return;
    
    travelNotes = travelNotes.filter(function(n) { return n.id !== noteId; });
    saveNotes();
    
    if (activeNoteId === noteId) {
      activeNoteId = null;
      if (emptyState) emptyState.classList.remove('hidden');
      if (editorContainer) editorContainer.classList.add('hidden');
    }
    
    renderNotesList();
    showToast('Travel note deleted', 'success');
  }
  
  // ========== CARD MANAGEMENT ==========
  function addCardToTravelNote(cardData, buttonElement, targetNoteId) {
    console.log('[MOBIX TravelNote] Adding card:', cardData);
    
    // Decode if string
    if (typeof cardData === 'string') {
      try {
        cardData = JSON.parse(decodeURIComponent(cardData));
      } catch(e) {
        console.error('[MOBIX TravelNote] Failed to parse card data:', e);
        showToast('Error adding item', 'error');
        return;
      }
    }
    
    // Determine category and type
    let category = 'activities';
    let cardType = 'activity';
    const type = cardData.type || '';
    const mode = cardData.mode || '';
    
    if (type === 'transport' || mode === 'plane' || mode === 'car' || mode === 'bus' || mode === 'train') {
      category = 'transports';
      cardType = mode || 'plane';
    } else if (type === 'hotel') {
      category = 'hotels';
      cardType = 'hotel';
    } else if (type === 'restaurant') {
      category = 'restaurants';
      cardType = 'restaurant';
    }
    
    // Create card item - store ALL data for full card display
    const cardItem = {
      id: 'card_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5),
      title: cardData.name || cardData.title || cardData.route || 'Item',
      subtitle: cardData.address || cardData.city || cardData.airline || '',
      details: cardData.details || cardData.description || '',
      price: cardData.price || '',
      rating: cardData.rating || '',
      image_url: cardData.image_url || cardData.photo || cardData.image || '',
      link: cardData.link || cardData.url || '',
      category: category,
      cardType: cardType,
      data: cardData, // Keep full original data
      addedAt: new Date().toISOString()
    };
    
    // If no notes exist or no active note, create new one
    if (travelNotes.length === 0 || !activeNoteId) {
      // Create new note with this card
      const noteTitle = cardData.city ? 'Trip to ' + cardData.city : 'My Travel Note';
      const noteId = createNewNote(noteTitle, cardItem);
      
      // Update button
      if (buttonElement) {
        buttonElement.innerHTML = '✓ Added to new note';
        buttonElement.disabled = true;
        buttonElement.classList.add('added');
      }
      
      showToast('Created new Travel Note with item!', 'success');
      
      // Navigate to travel note screen
      if (window.sidebarNavigate) {
        setTimeout(function() {
          window.sidebarNavigate('travelnote');
        }, 500);
      }
      
      return noteId;
    }
    
    // Add to active note
    const note = travelNotes.find(function(n) { return n.id === activeNoteId; });
    if (note) {
      note.cards.push(cardItem);
      note.updatedAt = new Date().toISOString();
      saveNotes();
      
      // If on travel note screen, update UI
      renderSavedCards(note.cards);
    } else {
      // Fallback: add to first note
      travelNotes[0].cards.push(cardItem);
      travelNotes[0].updatedAt = new Date().toISOString();
      saveNotes();
    }
    
    // Update button
    if (buttonElement) {
      buttonElement.innerHTML = '✓ Added';
      buttonElement.disabled = true;
      buttonElement.classList.add('added');
    }
    
    showToast('Added to Travel Note!', 'success');
  }
  
  function removeCardFromNote(cardId) {
    if (!activeNoteId) return;
    
    const note = travelNotes.find(function(n) { return n.id === activeNoteId; });
    if (!note) return;
    
    note.cards = note.cards.filter(function(c) { return c.id !== cardId; });
    note.updatedAt = new Date().toISOString();
    saveNotes();
    renderSavedCards(note.cards);
    showToast('Item removed', 'success');
  }
  
  // ========== RENDERING ==========
  function renderNotesList() {
    if (!notesList) return;
    
    notesList.innerHTML = '';
    
    if (travelNotes.length === 0) {
      notesList.innerHTML = '<div class="notes-list-empty">No travel notes yet.<br>Create one or add items from Chat!</div>';
      return;
    }
    
    travelNotes.forEach(function(note) {
      const item = document.createElement('div');
      item.className = 'note-list-item' + (note.id === activeNoteId ? ' active' : '');
      
      const date = new Date(note.updatedAt);
      const dateStr = date.toLocaleDateString('hr-HR', { day: 'numeric', month: 'short' });
      const cardCount = note.cards ? note.cards.length : 0;
      
      item.innerHTML = 
        '<div class="note-item-content" onclick="window.MOBIX.openTravelNote(\'' + note.id + '\')">' +
          '<div class="note-item-icon">📝</div>' +
          '<div class="note-item-info">' +
            '<div class="note-item-title">' + escapeHtml(note.title) + '</div>' +
            '<div class="note-item-meta">' + dateStr + ' • ' + cardCount + ' items</div>' +
          '</div>' +
        '</div>' +
        '<button class="note-item-delete" onclick="event.stopPropagation(); window.MOBIX.deleteTravelNote(\'' + note.id + '\')" title="Delete">🗑️</button>';
      
      notesList.appendChild(item);
    });
  }
  
  function renderSavedCards(cards) {
    if (!savedCardsContainer) return;
    
    if (!cards || cards.length === 0) {
      savedCardsContainer.innerHTML = '<div class="no-cards-message">No saved items yet. Add items from Chat!</div>';
      return;
    }
    
    // Group by category
    const grouped = {
      transports: [],
      hotels: [],
      restaurants: [],
      activities: []
    };
    
    cards.forEach(function(card) {
      const cat = card.category || 'activities';
      if (grouped[cat]) {
        grouped[cat].push(card);
      } else {
        grouped.activities.push(card);
      }
    });
    
    let html = '';
    
    // Transport section
    if (grouped.transports.length > 0) {
      html += renderCardSection('✈️ Transportation', grouped.transports);
    }
    
    // Hotels section
    if (grouped.hotels.length > 0) {
      html += renderCardSection('🏨 Accommodation', grouped.hotels);
    }
    
    // Restaurants section
    if (grouped.restaurants.length > 0) {
      html += renderCardSection('🍽️ Dining', grouped.restaurants);
    }
    
    // Activities section
    if (grouped.activities.length > 0) {
      html += renderCardSection('🎯 Activities', grouped.activities);
    }
    
    savedCardsContainer.innerHTML = html;
  }
  
  function renderCardSection(title, cards) {
    let html = '<div class="note-card-section">';
    html += '<h4 class="note-card-section-title">' + title + '</h4>';
    html += '<div class="note-card-list">';
    
    cards.forEach(function(card) {
      html += renderNoteCard(card);
    });
    
    html += '</div></div>';
    return html;
  }
  
  function renderNoteCard(card) {
    const data = card.data || {};
    const cardType = card.cardType || data.type || data.mode || 'activity';
    
    // Icon and color mapping (same as chat)
    const iconMap = {
      'plane': '✈️',
      'car': '🚗',
      'bus': '🚌',
      'train': '🚆',
      'hotel': '🏨',
      'restaurant': '🍽️',
      'activity': '🎯'
    };
    
    const colorMap = {
      'plane': '#3B82F6',
      'car': '#10B981',
      'bus': '#F59E0B',
      'train': '#8B5CF6',
      'hotel': '#EC4899',
      'restaurant': '#F97316',
      'activity': '#06B6D4'
    };
    
    const icon = iconMap[cardType] || '📍';
    const color = colorMap[cardType] || '#6B7280';
    
    // Get image URL
    const imageUrl = card.image_url || data.image_url || data.photo || data.image || '';
    
    // Get details
    const details = card.details || data.details || data.description || '';
    
    // Get price with formatting
    let priceDisplay = '';
    if (card.price) {
      priceDisplay = typeof card.price === 'number' ? '€' + card.price : card.price;
      if (!priceDisplay.includes('€') && !priceDisplay.includes('$')) {
        priceDisplay = '€' + priceDisplay;
      }
    } else if (data.price) {
      priceDisplay = typeof data.price === 'number' ? '€' + data.price : data.price;
    }
    
    // Get rating
    const rating = card.rating || data.rating || '';
    
    // Get link
    const link = card.link || data.link || data.url || '';
    
    // Build card HTML - styled like chat cards
    let html = '<div class="travel-note-card" data-card-id="' + card.id + '" style="border-left-color: ' + color + '">';
    
    // Image section (if available)
    if (imageUrl) {
      html += '<div class="travel-note-card-image" style="background-image: url(\'' + escapeHtml(imageUrl) + '\')"></div>';
    }
    
    // Content section
    html += '<div class="travel-note-card-body">';
    
    // Header with icon and title
    html += '<div class="travel-note-card-header">';
    html += '<span class="travel-note-card-icon" style="background: ' + color + '">' + icon + '</span>';
    html += '<div class="travel-note-card-title">' + escapeHtml(card.title) + '</div>';
    html += '</div>';
    
    // Subtitle (location/address)
    if (card.subtitle) {
      html += '<div class="travel-note-card-subtitle">' + escapeHtml(card.subtitle) + '</div>';
    }
    
    // Details
    if (details) {
      html += '<div class="travel-note-card-details">' + escapeHtml(details) + '</div>';
    }
    
    // Meta info (rating, price)
    if (rating || priceDisplay) {
      html += '<div class="travel-note-card-meta">';
      if (rating) {
        html += '<span class="travel-note-card-rating">⭐ ' + rating + '</span>';
      }
      if (priceDisplay) {
        html += '<span class="travel-note-card-price">' + escapeHtml(priceDisplay) + '</span>';
      }
      html += '</div>';
    }
    
    // Actions
    html += '<div class="travel-note-card-actions">';
    if (link) {
      html += '<a href="' + escapeHtml(link) + '" target="_blank" class="travel-note-card-link">View Details</a>';
    }
    html += '<button class="travel-note-card-remove" onclick="window.MOBIX.removeCardFromNote(\'' + card.id + '\')" title="Remove from note">✕ Remove</button>';
    html += '</div>';
    
    html += '</div>'; // Close body
    html += '</div>'; // Close card
    
    return html;
  }
  
  // ========== EVENT LISTENERS ==========
  function setupEventListeners() {
    // New note button
    const newNoteBtn = document.getElementById('btnNewNote');
    if (newNoteBtn) {
      newNoteBtn.addEventListener('click', function() {
        createNewNote();
      });
    }
    
    // Title input - save on change
    if (noteTitle) {
      noteTitle.addEventListener('input', function() {
        scheduleAutoSave();
      });
      noteTitle.addEventListener('blur', function() {
        saveCurrentNote();
      });
    }
    
    // Content textarea - auto save
    if (noteContent) {
      noteContent.addEventListener('input', function() {
        scheduleAutoSave();
        autoResizeTextarea(noteContent);
      });
      noteContent.addEventListener('blur', function() {
        saveCurrentNote();
      });
    }
    
    // Save button
    const saveBtn = document.getElementById('btnSaveNote');
    if (saveBtn) {
      saveBtn.addEventListener('click', function() {
        saveCurrentNote();
        showToast('Note saved!', 'success');
      });
    }
    
    // Clear all button
    const clearBtn = document.getElementById('btnClearNote');
    if (clearBtn) {
      clearBtn.addEventListener('click', async function() {
        if (!activeNoteId) return;
        
        const confirmed = await showConfirmModal({
          title: 'Clear All Items',
          message: 'This will remove all saved items from this note. Your written notes will be preserved.',
          confirmText: 'Clear Items'
        });
        
        if (confirmed) {
          const note = travelNotes.find(function(n) { return n.id === activeNoteId; });
          if (note) {
            note.cards = [];
            note.updatedAt = new Date().toISOString();
            saveNotes();
            renderSavedCards([]);
            showToast('All items cleared', 'success');
          }
        }
      });
    }
    
    // Expose remove function globally
    window.MOBIX.removeCardFromNote = removeCardFromNote;
  }
  
  // ========== UTILITY FUNCTIONS ==========
  function scheduleAutoSave() {
    updateSaveStatus('saving');
    
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer);
    }
    
    autoSaveTimer = setTimeout(function() {
      saveCurrentNote();
    }, 1000);
  }
  
  function updateSaveStatus(status) {
    if (!saveStatus) return;
    
    if (status === 'saving') {
      saveStatus.textContent = 'Saving...';
      saveStatus.className = 'note-save-status saving';
    } else if (status === 'saved') {
      saveStatus.textContent = 'Saved';
      saveStatus.className = 'note-save-status saved';
    }
  }
  
  function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.max(200, textarea.scrollHeight) + 'px';
  }
  
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  function showToast(message, type) {
    // Use existing toast function if available
    if (window.showToast) {
      window.showToast(message, type);
      return;
    }
    
    // Simple fallback
    console.log('[MOBIX TravelNote] Toast:', message, type);
  }
  
  async function showConfirmModal(options) {
    // Use existing confirm modal if available
    if (window.showConfirmModal) {
      return window.showConfirmModal(options);
    }
    
    // Simple fallback
    return confirm(options.message);
  }
  
})();
