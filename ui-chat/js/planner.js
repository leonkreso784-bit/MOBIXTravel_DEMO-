// ========================================
// MOBIX Planner Functions
// ========================================

(function() {
  'use strict';
  
  document.addEventListener('DOMContentLoaded', function() {
    console.log('[MOBIX Planner] Initializing...');
    
    // ========== ITINERARY MANAGEMENT ==========
    var itineraries = JSON.parse(localStorage.getItem('mobix_itineraries') || '[]');
    var currentItineraryId = null;
    var dayCounter = 0;
    
    function renderItineraryList() {
      var list = document.getElementById('plannerList');
      if (!list) return;
      
      list.innerHTML = '';
      itineraries.forEach(function(item) {
        var div = document.createElement('div');
        div.className = 'itinerary-item' + (item.id === currentItineraryId ? ' active' : '');
        div.innerHTML = '<div class="itinerary-item-title">' + (item.origin || 'Unknown') + ' → ' + item.destination + '</div>' +
                       '<div class="itinerary-item-destination">' + item.destination + '</div>' +
                       '<div class="itinerary-item-dates">' + item.startDate + ' - ' + item.endDate + '</div>';
        div.onclick = function() { loadItinerary(item.id); };
        list.appendChild(div);
      });
    }
    
    function showEditor(show) {
      var empty = document.getElementById('plannerEmptyState');
      var editor = document.getElementById('plannerEditor');
      if (empty) empty.classList.toggle('hidden', show);
      if (editor) editor.classList.toggle('hidden', !show);
    }
    
    function loadItinerary(id) {
      var item = itineraries.find(function(i) { return i.id === id; });
      if (!item) return;
      
      currentItineraryId = id;
      document.getElementById('plannerEditorTitle').textContent = item.destination || 'Edit Itinerary';
      document.getElementById('itineraryOrigin').value = item.origin || '';
      document.getElementById('itineraryDestination').value = item.destination || '';
      document.getElementById('itineraryStartDate').value = item.startDate || '';
      document.getElementById('itineraryEndDate').value = item.endDate || '';
      document.getElementById('itineraryBudget').value = item.budget || '';
      document.getElementById('itineraryNotes').value = item.notes || '';
      
      // Render days
      var daysContainer = document.getElementById('daysContainer');
      daysContainer.innerHTML = '';
      dayCounter = 0;
      if (item.days && item.days.length > 0) {
        item.days.forEach(function(day) { addDayCard(day); });
      }
      
      showEditor(true);
      renderItineraryList();
    }
    
    function createNewItinerary() {
      currentItineraryId = 'itin_' + Date.now();
      document.getElementById('plannerEditorTitle').textContent = 'New Itinerary';
      document.getElementById('itineraryOrigin').value = '';
      document.getElementById('itineraryDestination').value = '';
      document.getElementById('itineraryStartDate').value = '';
      document.getElementById('itineraryEndDate').value = '';
      document.getElementById('itineraryBudget').value = '';
      document.getElementById('itineraryNotes').value = '';
      document.getElementById('daysContainer').innerHTML = '';
      dayCounter = 0;
      addDayCard(); // Add first day
      showEditor(true);
    }
    
    function saveItinerary() {
      var data = {
        id: currentItineraryId,
        origin: document.getElementById('itineraryOrigin').value,
        destination: document.getElementById('itineraryDestination').value,
        startDate: document.getElementById('itineraryStartDate').value,
        endDate: document.getElementById('itineraryEndDate').value,
        budget: document.getElementById('itineraryBudget').value,
        notes: document.getElementById('itineraryNotes').value,
        days: []
      };
      
      // Collect days data
      document.querySelectorAll('.day-card').forEach(function(card, index) {
        var activities = [];
        card.querySelectorAll('.activity-item input').forEach(function(input) {
          if (input.value.trim()) activities.push(input.value.trim());
        });
        var notesEl = card.querySelector('.day-notes textarea');
        data.days.push({
          dayNumber: index + 1,
          activities: activities,
          notes: notesEl ? notesEl.value : ''
        });
      });
      
      // Update or add
      var idx = itineraries.findIndex(function(i) { return i.id === currentItineraryId; });
      if (idx >= 0) {
        itineraries[idx] = data;
      } else {
        itineraries.push(data);
      }
      
      localStorage.setItem('mobix_itineraries', JSON.stringify(itineraries));
      renderItineraryList();
      showToast('Itinerary saved!', 'success');
    }
    
    async function deleteItinerary() {
      if (!currentItineraryId) return;
      
      var confirmed = await showConfirmModal({
        title: 'Delete Itinerary',
        message: 'Are you sure you want to delete this itinerary? This action cannot be undone.',
        confirmText: 'Delete'
      });
      
      if (!confirmed) return;
      
      itineraries = itineraries.filter(function(i) { return i.id !== currentItineraryId; });
      localStorage.setItem('mobix_itineraries', JSON.stringify(itineraries));
      currentItineraryId = null;
      showEditor(false);
      renderItineraryList();
    }
    
    function addDayCard(dayData) {
      dayCounter++;
      var container = document.getElementById('daysContainer');
      var card = document.createElement('div');
      card.className = 'day-card';
      card.innerHTML = 
        '<div class="day-card-header">' +
          '<h4>Day ' + dayCounter + '</h4>' +
          '<button type="button" class="btn-remove-day" onclick="this.closest(\'.day-card\').remove()">✕</button>' +
        '</div>' +
        '<div class="activities-container">' +
          '<div class="activities-label">Activities</div>' +
          '<div class="activities-list"></div>' +
          '<button type="button" class="btn-add-activity" onclick="window.MOBIX.addActivity(this)">+ Add Activity</button>' +
        '</div>' +
        '<div class="day-notes">' +
          '<label>Notes</label>' +
          '<textarea rows="2" placeholder="Notes for this day...">' + (dayData && dayData.notes ? dayData.notes : '') + '</textarea>' +
        '</div>';
      
      container.appendChild(card);
      
      // Add activities
      var activitiesList = card.querySelector('.activities-list');
      if (dayData && dayData.activities) {
        dayData.activities.forEach(function(act) {
          addActivityItem(activitiesList, act);
        });
      } else {
        addActivityItem(activitiesList, '');
      }
    }
    
    function addActivityItem(list, value) {
      var div = document.createElement('div');
      div.className = 'activity-item';
      div.innerHTML = '<input type="text" placeholder="Enter activity..." value="' + (value || '') + '">' +
                     '<button type="button" class="btn-remove-activity" onclick="this.parentElement.remove()">✕</button>';
      list.appendChild(div);
    }
    
    // Make functions global
    window.MOBIX = window.MOBIX || {};
    window.MOBIX.addActivity = function(btn) {
      var list = btn.previousElementSibling;
      addActivityItem(list, '');
    };
    
    // Setup planner buttons
    var btnAddItinerary = document.getElementById('btnAddItinerary');
    if (btnAddItinerary) {
      btnAddItinerary.onclick = createNewItinerary;
    }
    
    var btnSaveItinerary = document.getElementById('btnSaveItinerary');
    if (btnSaveItinerary) {
      btnSaveItinerary.onclick = function(e) {
        e.preventDefault();
        saveItinerary();
      };
    }
    
    var btnDeleteItinerary = document.getElementById('btnDeleteItinerary');
    if (btnDeleteItinerary) {
      btnDeleteItinerary.onclick = deleteItinerary;
    }
    
    var btnAddDay = document.getElementById('btnAddDay');
    if (btnAddDay) {
      btnAddDay.onclick = function() { addDayCard(); };
    }
    
    // Initial render
    renderItineraryList();
    if (itineraries.length === 0) {
      showEditor(false);
    }
    
    // ========== TRAVEL NOTE ==========
    var travelNote = JSON.parse(localStorage.getItem('mobix_travel_note') || '{"notes":"","plans":[],"transports":[],"hotels":[],"restaurants":[],"activitys":[]}');
    
    // Initialize notes editor
    var notesEditor = document.getElementById('travelNotesEditor');
    if (notesEditor) {
      // Load saved notes
      notesEditor.value = travelNote.notes || '';
      
      // Auto-save on input with debounce
      var saveTimeout;
      notesEditor.addEventListener('input', function() {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(function() {
          saveTravelNotes(true); // silent save
        }, 1000);
      });
    }
    
    // Save notes button
    var btnSaveNotes = document.getElementById('btnSaveNotes');
    if (btnSaveNotes) {
      btnSaveNotes.onclick = function() {
        saveTravelNotes(false); // show notification
      };
    }
    
    function saveTravelNotes(silent) {
      if (notesEditor) {
        travelNote.notes = notesEditor.value;
        localStorage.setItem('mobix_travel_note', JSON.stringify(travelNote));
        
        if (!silent) {
          var status = document.getElementById('notesSavedStatus');
          if (status) {
            status.textContent = '✓ Notes saved!';
            status.classList.add('show');
            setTimeout(function() {
              status.classList.remove('show');
            }, 2000);
          }
          showToast('Notes saved successfully!', 'success');
        }
      }
    }
    
    // Create Plan Modal
    var btnCreatePlan = document.getElementById('btnCreatePlan');
    var createPlanModal = document.getElementById('createPlanModal');
    var createPlanForm = document.getElementById('createPlanForm');
    
    if (btnCreatePlan && createPlanModal) {
      btnCreatePlan.onclick = function() {
        createPlanModal.classList.remove('hidden');
        // Set default dates
        var today = new Date();
        var nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
        document.getElementById('planStartDate').value = today.toISOString().split('T')[0];
        document.getElementById('planEndDate').value = nextWeek.toISOString().split('T')[0];
      };
      
      // Close modal on backdrop click
      createPlanModal.querySelector('.modal-backdrop').onclick = function() {
        createPlanModal.classList.add('hidden');
      };
    }
    
    if (createPlanForm) {
      createPlanForm.onsubmit = function(e) {
        e.preventDefault();
        
        var plan = {
          id: 'plan_' + Date.now(),
          title: document.getElementById('planTitle').value,
          destination: document.getElementById('planDestination').value,
          budget: document.getElementById('planBudget').value,
          startDate: document.getElementById('planStartDate').value,
          endDate: document.getElementById('planEndDate').value,
          notes: document.getElementById('planNotes').value,
          createdAt: new Date().toISOString()
        };
        
        // Add plan info to notes
        var planText = '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n';
        planText += '📍 ' + plan.title.toUpperCase() + '\n';
        planText += '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n';
        planText += '🌍 Destination: ' + plan.destination + '\n';
        planText += '📅 Dates: ' + plan.startDate + ' to ' + plan.endDate + '\n';
        if (plan.budget) planText += '💰 Budget: $' + plan.budget + '\n';
        if (plan.notes) planText += '📝 Notes: ' + plan.notes + '\n';
        planText += '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n';
        
        // Append to notes
        if (notesEditor) {
          notesEditor.value += planText;
          travelNote.notes = notesEditor.value;
        }
        
        // Save plan
        if (!travelNote.plans) travelNote.plans = [];
        travelNote.plans.push(plan);
        localStorage.setItem('mobix_travel_note', JSON.stringify(travelNote));
        
        // Update header
        var tripTitle = document.getElementById('tripTitle');
        var tripSubtitle = document.getElementById('tripSubtitle');
        if (tripTitle) tripTitle.textContent = '✏️ ' + plan.title;
        if (tripSubtitle) tripSubtitle.textContent = plan.destination + ' • ' + plan.startDate + ' to ' + plan.endDate;
        
        // Close modal and show toast
        createPlanModal.classList.add('hidden');
        createPlanForm.reset();
        showToast('Travel plan created! Start adding details to your notes.', 'success');
      };
    }
    
    function renderTravelNote() {
      var empty = document.getElementById('tripEmpty');
      var sections = document.getElementById('tripSections');
      
      var hasItems = (travelNote.transports && travelNote.transports.length) ||
                     (travelNote.hotels && travelNote.hotels.length) ||
                     (travelNote.restaurants && travelNote.restaurants.length) ||
                     (travelNote.activitys && travelNote.activitys.length);
      
      if (hasItems) {
        if (empty) empty.classList.add('hidden');
        if (sections) sections.classList.remove('hidden');
        
        renderTravelNoteSection('tripTransportItems', travelNote.transports || []);
        renderTravelNoteSection('tripHotelItems', travelNote.hotels || []);
        renderTravelNoteSection('tripRestaurantItems', travelNote.restaurants || []);
        renderTravelNoteSection('tripActivityItems', travelNote.activitys || []);
      } else {
        if (empty) empty.classList.remove('hidden');
        if (sections) sections.classList.add('hidden');
      }
    }
    
    function renderTravelNoteSection(containerId, items) {
      var container = document.getElementById(containerId);
      if (!container) return;
      
      container.innerHTML = '';
      if (!items || items.length === 0) {
        container.innerHTML = '<p style="color:#94a3b8;font-size:14px;">No items added yet</p>';
        return;
      }
      
      items.forEach(function(item) {
        var div = document.createElement('div');
        div.className = 'trip-item';
        
        // Build image style if image_url exists
        var imageStyle = item.image_url ? 'background-image: url(\'' + item.image_url + '\'); background-size: cover; background-position: center;' : '';
        
        div.innerHTML = 
          '<div class="trip-item-image" style="' + imageStyle + '"></div>' +
          '<div class="trip-item-info">' +
            '<div class="trip-item-title">' + item.title + '</div>' +
            '<div class="trip-item-subtitle">' + item.subtitle + '</div>' +
          '</div>' +
          '<button class="btn-remove-item" onclick="window.MOBIX.removeFromTravelNote(\'' + item.id + '\', \'' + containerId + '\')">✕</button>';
        container.appendChild(div);
      });
    }
    
    window.MOBIX.removeFromTravelNote = function(id, containerId) {
      var category = containerId.replace('trip', '').replace('Items', '').toLowerCase() + 's';
      if (category === 'activityss') category = 'activitys';
      
      if (travelNote[category]) {
        travelNote[category] = travelNote[category].filter(function(i) { return i.id !== id; });
        localStorage.setItem('mobix_travel_note', JSON.stringify(travelNote));
      }
      
      renderTravelNote();
    };
    
    // Add to travel note from planner options - NOW USES NEW TRAVEL NOTE SYSTEM
    window.MOBIX.addToTravelNote = function(id, category, btn) {
      var card = btn.closest('.option-card');
      var title = card.querySelector('.option-card-title').textContent;
      var subtitleEl = card.querySelector('.option-card-subtitle');
      var subtitle = subtitleEl ? subtitleEl.textContent : '';
      var priceEl = card.querySelector('.option-card-price');
      var price = priceEl ? priceEl.textContent : '';
      var detailsEl = card.querySelector('.option-card-details');
      var details = detailsEl ? detailsEl.textContent : '';
      var ratingEl = card.querySelector('.option-card-rating');
      var rating = ratingEl ? ratingEl.textContent.replace('⭐', '').trim() : '';
      
      // Get image URL from the card
      var imageEl = card.querySelector('.option-card-image');
      var imageUrl = '';
      if (imageEl) {
        var bgImage = imageEl.style.backgroundImage;
        if (bgImage) {
          imageUrl = bgImage.replace(/^url\(['"]?/, '').replace(/['"]?\)$/, '');
        }
      }
      
      // Determine card type based on category
      var cardType = 'activity';
      if (category === 'transport') cardType = 'plane';
      else if (category === 'hotel') cardType = 'hotel';
      else if (category === 'restaurant') cardType = 'restaurant';
      
      // Build full card data for new Travel Note system
      var cardData = {
        type: category,
        mode: cardType,
        name: title,
        title: title,
        address: subtitle,
        city: subtitle,
        details: details,
        description: details,
        price: price.replace(/[€$]/g, '').trim(),
        rating: rating,
        image_url: imageUrl,
        photo: imageUrl,
        image: imageUrl
      };
      
      // Use new Travel Note system if available
      if (window.MOBIX.addCardToTravelNote) {
        window.MOBIX.addCardToTravelNote(cardData, btn);
      } else {
        // Fallback to old system
        var item = {
          id: id,
          title: title,
          subtitle: subtitle,
          price: price,
          image_url: imageUrl,
          addedAt: new Date().toISOString()
        };
        
        var key = category + 's';
        if (!travelNote[key]) travelNote[key] = [];
        travelNote[key].push(item);
        localStorage.setItem('mobix_travel_note', JSON.stringify(travelNote));
        
        btn.classList.add('added');
        btn.innerHTML = '✓ Added to Travel Note';
        btn.disabled = true;
        card.classList.add('added');
        
        renderTravelNote();
      }
    };
    
    // Make addToTravelNote available globally
    window.addToTravelNote = window.MOBIX.addToTravelNote;
    
    // Clear all trip
    var btnClearTrip = document.getElementById('btnClearTrip');
    if (btnClearTrip) {
      btnClearTrip.onclick = async function() {
        var confirmed = await showConfirmModal({
          title: 'Clear Travel Note',
          message: 'Are you sure you want to clear all notes and saved items?',
          confirmText: 'Clear All'
        });
        
        if (confirmed) {
          travelNote = { notes: '', plans: [], transports: [], hotels: [], restaurants: [], activitys: [] };
          localStorage.setItem('mobix_travel_note', JSON.stringify(travelNote));
          
          // Clear notes editor
          if (notesEditor) {
            notesEditor.value = '';
          }
          
          // Reset header
          var tripTitle = document.getElementById('tripTitle');
          var tripSubtitle = document.getElementById('tripSubtitle');
          if (tripTitle) tripTitle.textContent = '✏️ My Travel Note';
          if (tripSubtitle) tripSubtitle.textContent = 'Plan your perfect trip';
          
          renderTravelNote();
          showToast('Travel note cleared', 'info');
        }
      };
    }
    
    // Initial render - also restore header if plan exists
    renderTravelNote();
    
    // Restore header from last plan if exists
    if (travelNote.plans && travelNote.plans.length > 0) {
      var lastPlan = travelNote.plans[travelNote.plans.length - 1];
      var tripTitle = document.getElementById('tripTitle');
      var tripSubtitle = document.getElementById('tripSubtitle');
      if (tripTitle) tripTitle.textContent = '✏️ ' + lastPlan.title;
      if (tripSubtitle) tripSubtitle.textContent = lastPlan.destination + ' • ' + lastPlan.startDate + ' to ' + lastPlan.endDate;
    }
    
    // ========== GENERATE TRAVEL PLAN ==========
    var btnGenerate = document.getElementById('btnGenerate');
    if (btnGenerate) {
      btnGenerate.onclick = generateTravelPlan;
    }
    
    async function generateTravelPlan() {
      var originField = document.getElementById('itineraryOrigin');
      var destination = document.getElementById('itineraryDestination').value;
      var startDate = document.getElementById('itineraryStartDate').value;
      var endDate = document.getElementById('itineraryEndDate').value;
      var budget = document.getElementById('itineraryBudget').value;
      
      // Get origin from origin field or use Zagreb as default
      var origin = originField ? originField.value : null;
      
      if (!destination) {
        showToast('Please enter a destination', 'warning');
        return;
      }
      
      console.log('[MOBIX Planner] Generating plan:', { origin: origin, destination: destination });
      
      // Show results section and loading
      var results = document.getElementById('generatedResults');
      var loading = document.getElementById('resultsLoading');
      if (results) results.classList.remove('hidden');
      if (loading) loading.classList.remove('hidden');
      
      btnGenerate.disabled = true;
      btnGenerate.innerHTML = '<div class="loading-spinner" style="width:20px;height:20px;border-width:2px;"></div> Searching real flights...';
      
      try {
        // Call the NEW planner API endpoint
        var response = await fetch(window.__MOBIX_API_BASE__ + '/api/planner/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            origin: origin || 'Zagreb',
            destination: destination,
            departure_date: startDate || null,
            return_date: endDate || null,
            budget: budget ? parseInt(budget) : null,
            adults: 1
          })
        });
        
        if (!response.ok) {
          throw new Error('API request failed');
        }
        
        var data = await response.json();
        
        if (loading) loading.classList.add('hidden');
        
        // Render real options from API
        renderTransportOptions('transportOptions', data.transport || []);
        renderHotelOptions('hotelOptions', data.hotels || []);
        renderRestaurantOptions('restaurantOptions', data.restaurants || []);
        renderActivityOptions('activityOptions', data.activities || []);
        
        showToast('Found ' + (data.transport || []).length + ' transport options and ' + (data.hotels || []).length + ' hotels!', 'success');
        
      } catch (error) {
        console.error('Generate error:', error);
        if (loading) loading.classList.add('hidden');
        showToast('Using cached results...', 'info');
        // Fallback to mock options
        generateMockOptions(destination, startDate, endDate, budget);
      }
      
      btnGenerate.disabled = false;
      btnGenerate.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg> Generate Travel Plan';
    }
    
    // ========== RENDER FUNCTIONS FOR REAL DATA ==========
    
    function renderTransportOptions(containerId, options) {
      var container = document.getElementById(containerId);
      if (!container) return;
      
      container.innerHTML = '';
      options.forEach(function(opt) {
        var isAdded = travelNote.transports && travelNote.transports.some(function(i) { return i.id === opt.id; });
        
        var card = document.createElement('div');
        card.className = 'option-card' + (isAdded ? ' added' : '');
        
        var imageUrl = opt.image_url || 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=400&h=200&fit=crop';
        var typeIcon = opt.type === 'flight' ? '✈️' : (opt.type === 'bus' ? '🚌' : (opt.type === 'train' ? '🚂' : '🚗'));
        
        // Use contain for logos (transport), cover for photos
        var bgSize = (opt.type === 'flight' || opt.type === 'bus' || opt.type === 'train') ? 'contain' : 'cover';
        var html = '<div class="option-card-image" style="background-image: url(\'' + imageUrl + '\'); background-size: ' + bgSize + ';"></div>';
        html += '<div class="option-card-title">' + opt.title + '</div>';
        html += '<div class="option-card-subtitle">' + opt.subtitle + '</div>';
        
        html += '<div class="option-card-details">';
        if (opt.duration) html += '<span class="option-detail">⏱️ ' + opt.duration + '</span>';
        if (opt.carrier) html += '<span class="option-detail">' + typeIcon + ' ' + opt.carrier + '</span>';
        if (opt.stops_text) html += '<span class="option-detail">📍 ' + opt.stops_text + '</span>';
        if (opt.departure_time && opt.arrival_time) {
          html += '<span class="option-detail">🕐 ' + opt.departure_time + ' → ' + opt.arrival_time + '</span>';
        }
        html += '</div>';
        
        html += '<div class="option-card-price">€' + opt.price + '</div>';
        
        // Booking link button
        if (opt.booking_link) {
          html += '<a href="' + opt.booking_link + '" target="_blank" class="btn-book-now">🔗 Book Now</a>';
        }
        
        var btnClass = isAdded ? 'btn-add-to-note added' : 'btn-add-to-note';
        var btnText = isAdded ? '✓ Added to Travel Note' : '+ Add to Travel Note';
        html += '<button class="' + btnClass + '" onclick="window.MOBIX.addToTravelNote(\'' + opt.id + '\', \'transport\', this)" ' + (isAdded ? 'disabled' : '') + '>' + btnText + '</button>';
        
        card.innerHTML = html;
        container.appendChild(card);
      });
    }
    
    function renderHotelOptions(containerId, options) {
      var container = document.getElementById(containerId);
      if (!container) return;
      
      container.innerHTML = '';
      options.forEach(function(opt) {
        var isAdded = travelNote.hotels && travelNote.hotels.some(function(i) { return i.id === opt.id; });
        
        var card = document.createElement('div');
        card.className = 'option-card' + (isAdded ? ' added' : '');
        
        var imageUrl = opt.image_url || 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400&h=200&fit=crop';
        
        var html = '<div class="option-card-image" style="background-image: url(\'' + imageUrl + '\'); background-size: cover;"></div>';
        html += '<div class="option-card-title">' + opt.name + '</div>';
        html += '<div class="option-card-subtitle">' + opt.subtitle + '</div>';
        
        if (opt.rating) {
          html += '<div class="option-card-rating">';
          html += '<span class="rating-stars">' + '★'.repeat(Math.round(opt.rating)) + '</span>';
          html += '<span class="rating-count">' + opt.rating + ' (' + (opt.reviews || 0) + ' reviews)</span>';
          html += '</div>';
        }
        
        html += '<div class="option-card-price">€' + opt.price_per_night + '/night</div>';
        
        if (opt.booking_link) {
          html += '<a href="' + opt.booking_link + '" target="_blank" class="btn-book-now">🔗 Book on Booking.com</a>';
        }
        
        var btnClass = isAdded ? 'btn-add-to-note added' : 'btn-add-to-note';
        var btnText = isAdded ? '✓ Added to Travel Note' : '+ Add to Travel Note';
        html += '<button class="' + btnClass + '" onclick="window.MOBIX.addToTravelNote(\'' + opt.id + '\', \'hotel\', this)" ' + (isAdded ? 'disabled' : '') + '>' + btnText + '</button>';
        
        card.innerHTML = html;
        container.appendChild(card);
      });
    }
    
    function renderRestaurantOptions(containerId, options) {
      var container = document.getElementById(containerId);
      if (!container) return;
      
      container.innerHTML = '';
      options.forEach(function(opt) {
        var isAdded = travelNote.restaurants && travelNote.restaurants.some(function(i) { return i.id === opt.id; });
        
        var card = document.createElement('div');
        card.className = 'option-card' + (isAdded ? ' added' : '');
        
        var imageUrl = opt.image_url || 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=400&h=200&fit=crop';
        
        var html = '<div class="option-card-image" style="background-image: url(\'' + imageUrl + '\'); background-size: cover;"></div>';
        html += '<div class="option-card-title">' + opt.name + '</div>';
        html += '<div class="option-card-subtitle">' + opt.subtitle + '</div>';
        
        html += '<div class="option-card-details">';
        if (opt.price_level) html += '<span class="option-detail">' + opt.price_level + '</span>';
        if (opt.address) html += '<span class="option-detail">📍 ' + opt.address.substring(0, 30) + '</span>';
        html += '</div>';
        
        if (opt.rating) {
          html += '<div class="option-card-rating">';
          html += '<span class="rating-stars">' + '★'.repeat(Math.round(opt.rating)) + '</span>';
          html += '<span class="rating-count">' + opt.rating + ' (' + (opt.reviews || 0) + ' reviews)</span>';
          html += '</div>';
        }
        
        if (opt.booking_link) {
          html += '<a href="' + opt.booking_link + '" target="_blank" class="btn-book-now">🔗 View on Maps</a>';
        }
        
        var btnClass = isAdded ? 'btn-add-to-note added' : 'btn-add-to-note';
        var btnText = isAdded ? '✓ Added to Travel Note' : '+ Add to Travel Note';
        html += '<button class="' + btnClass + '" onclick="window.MOBIX.addToTravelNote(\'' + opt.id + '\', \'restaurant\', this)" ' + (isAdded ? 'disabled' : '') + '>' + btnText + '</button>';
        
        card.innerHTML = html;
        container.appendChild(card);
      });
    }
    
    function renderActivityOptions(containerId, options) {
      var container = document.getElementById(containerId);
      if (!container) return;
      
      container.innerHTML = '';
      options.forEach(function(opt) {
        var isAdded = travelNote.activitys && travelNote.activitys.some(function(i) { return i.id === opt.id; });
        
        var card = document.createElement('div');
        card.className = 'option-card' + (isAdded ? ' added' : '');
        
        var imageUrl = opt.image_url || 'https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=400&h=200&fit=crop';
        
        var html = '<div class="option-card-image" style="background-image: url(\'' + imageUrl + '\'); background-size: cover;"></div>';
        html += '<div class="option-card-title">' + opt.name + '</div>';
        html += '<div class="option-card-subtitle">' + opt.subtitle + '</div>';
        
        if (opt.rating) {
          html += '<div class="option-card-rating">';
          html += '<span class="rating-stars">' + '★'.repeat(Math.round(opt.rating)) + '</span>';
          html += '<span class="rating-count">' + opt.rating + ' (' + (opt.reviews || 0) + ' reviews)</span>';
          html += '</div>';
        }
        
        if (opt.price) {
          html += '<div class="option-card-price">€' + opt.price + '</div>';
        }
        
        if (opt.booking_link) {
          html += '<a href="' + opt.booking_link + '" target="_blank" class="btn-book-now">🔗 More Info</a>';
        }
        
        var btnClass = isAdded ? 'btn-add-to-note added' : 'btn-add-to-note';
        var btnText = isAdded ? '✓ Added to Travel Note' : '+ Add to Travel Note';
        html += '<button class="' + btnClass + '" onclick="window.MOBIX.addToTravelNote(\'' + opt.id + '\', \'activity\', this)" ' + (isAdded ? 'disabled' : '') + '>' + btnText + '</button>';
        
        card.innerHTML = html;
        container.appendChild(card);
      });
    }
    
    function generateMockOptions(destination) {
      var transportOptions = [
        { id: 't1', type: 'flight', title: 'Direct Flight to ' + destination, subtitle: 'Economy Class', airline: 'Various Airlines', duration: '2-4 hours', price: Math.floor(Math.random() * 300 + 150) },
        { id: 't2', type: 'flight', title: 'Budget Flight to ' + destination, subtitle: 'Low-cost Carrier', airline: 'Budget Air', duration: '3-5 hours', price: Math.floor(Math.random() * 150 + 80) },
        { id: 't3', type: 'train', title: 'Train to ' + destination, subtitle: 'High-speed Rail', duration: '4-6 hours', price: Math.floor(Math.random() * 100 + 50) }
      ];
      
      var hotelOptions = [
        { id: 'h1', type: 'hotel', title: 'Luxury Hotel ' + destination, subtitle: '5-star • City Center', rating: 4.8, reviews: 2341, price: Math.floor(Math.random() * 200 + 150) },
        { id: 'h2', type: 'hotel', title: 'Boutique Hotel ' + destination, subtitle: '4-star • Old Town', rating: 4.5, reviews: 892, price: Math.floor(Math.random() * 120 + 80) },
        { id: 'h3', type: 'hotel', title: 'Budget Inn ' + destination, subtitle: '3-star • Near Station', rating: 4.2, reviews: 567, price: Math.floor(Math.random() * 60 + 40) }
      ];
      
      var restaurantOptions = [
        { id: 'r1', type: 'restaurant', title: 'La Maison Gourmet', subtitle: 'French Fine Dining', rating: 4.9, reviews: 1245, cuisine: 'French', price: '$$$' },
        { id: 'r2', type: 'restaurant', title: 'Trattoria Bella', subtitle: 'Authentic Italian', rating: 4.6, reviews: 876, cuisine: 'Italian', price: '$$' },
        { id: 'r3', type: 'restaurant', title: 'Street Food Market', subtitle: 'Local Specialties', rating: 4.4, reviews: 2103, cuisine: 'Local', price: '$' }
      ];
      
      var activityOptions = [
        { id: 'a1', type: 'activity', title: 'City Walking Tour', subtitle: '3 hours • Guide included', rating: 4.7, reviews: 3421, price: 25 },
        { id: 'a2', type: 'activity', title: 'Museum Pass', subtitle: 'Access to 5 museums', rating: 4.5, reviews: 1876, price: 45 },
        { id: 'a3', type: 'activity', title: 'Food & Wine Tasting', subtitle: '4 hours • 6 tastings', rating: 4.8, reviews: 654, price: 75 },
        { id: 'a4', type: 'activity', title: 'Day Trip Excursion', subtitle: 'Full day • Transport included', rating: 4.6, reviews: 432, price: 95 }
      ];
      
      renderOptions('transportOptions', transportOptions, 'transport');
      renderOptions('hotelOptions', hotelOptions, 'hotel');
      renderOptions('restaurantOptions', restaurantOptions, 'restaurant');
      renderOptions('activityOptions', activityOptions, 'activity');
    }
    
    function renderOptions(containerId, options, category) {
      var container = document.getElementById(containerId);
      if (!container) return;
      
      container.innerHTML = '';
      options.forEach(function(opt) {
        var isAdded = travelNote[category + 's'] && travelNote[category + 's'].some(function(i) { return i.id === opt.id; });
        
        var card = document.createElement('div');
        card.className = 'option-card' + (isAdded ? ' added' : '');
        card.innerHTML = createOptionCardHTML(opt, category, isAdded);
        container.appendChild(card);
      });
    }
    
    function createOptionCardHTML(opt, category, isAdded) {
      var html = '<div class="option-card-image"></div>';
      html += '<div class="option-card-title">' + opt.title + '</div>';
      html += '<div class="option-card-subtitle">' + opt.subtitle + '</div>';
      
      html += '<div class="option-card-details">';
      if (opt.duration) html += '<span class="option-detail">⏱️ ' + opt.duration + '</span>';
      if (opt.airline) html += '<span class="option-detail">✈️ ' + opt.airline + '</span>';
      if (opt.cuisine) html += '<span class="option-detail">🍴 ' + opt.cuisine + '</span>';
      html += '</div>';
      
      if (opt.rating) {
        html += '<div class="option-card-rating">';
        html += '<span class="rating-stars">★★★★★</span>';
        html += '<span class="rating-count">' + opt.rating + ' (' + opt.reviews + ' reviews)</span>';
        html += '</div>';
      }
      
      if (typeof opt.price === 'number') {
        html += '<div class="option-card-price">$' + opt.price + '</div>';
      } else {
        html += '<div class="option-card-price">' + opt.price + '</div>';
      }
      
      var btnClass = isAdded ? 'btn-add-to-note added' : 'btn-add-to-note';
      var btnText = isAdded ? '✓ Added to Travel Note' : '+ Add to Travel Note';
      html += '<button class="' + btnClass + '" onclick="window.MOBIX.addToTravelNote(\'' + opt.id + '\', \'' + category + '\', this)" ' + (isAdded ? 'disabled' : '') + '>' + btnText + '</button>';
      
      return html;
    }
    
    console.log('[MOBIX Planner] Initialization complete');
  });
})();
