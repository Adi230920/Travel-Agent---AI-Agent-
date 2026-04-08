/* ═══════════════════════════════════════════════════════════
   GulliverAI — Frontend Logic (Premium Experience)
   ═══════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── Configuration ────────────────────────────────────────
  // Change PROD_API_URL to your Render URL after deployment
  const PROD_API_URL = 'https://gulliver-ai.onrender.com'; 
  const API_BASE = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
    ? 'http://127.0.0.1:8000'
    : PROD_API_URL;

  // ── DOM References ───────────────────────────────────────
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const screens = {
    input:             $('#screen-input'),
    loadingPlan:       $('#screen-loading-plan'),
    recommendations:   $('#screen-recommendations'),
    loadingItinerary:  $('#screen-loading-itinerary'),
    itinerary:         $('#screen-itinerary'),
  };

  const els = {
    form:                 $('#plan-form'),
    submitBtn:            $('#submit-btn'),
    recGrid:              $('#recommendations-grid'),
    accordion:            $('#itinerary-accordion'),
    itineraryTitle:       $('#itinerary-title'),
    itinerarySubtitle:    $('#itinerary-subtitle'),
    loadingPlanLabel:     $('#loading-plan-label'),
    loadingPlanSub:       $('#screen-loading-plan .loading-sub'),
    loadingItineraryLabel:$('#loading-itinerary-label'),
    loadingItinerarySub:  $('#screen-loading-itinerary .loading-sub'),
    errorBanner:          $('#error-banner'),
    errorMessage:         $('#error-message'),
    errorCloseBtn:        $('#error-close-btn'),
    backToFormBtn:        $('#back-to-form-btn'),
    backToRecsBtn:        $('#back-to-recommendations-btn'),
    restartBtn:           $('#restart-btn'),
    transportSection:     $('#transport-section'),
    flightList:           $('#flight-list'),
  };

  // ── State ────────────────────────────────────────────────
  let sessionId = null;
  let recommendations = [];
  let destinationImages = {};
  let errorTimer = null;

  // ═══════════════════════════════════════════════════════════
  // Screen Management
  // ═══════════════════════════════════════════════════════════

  function showScreen(name) {
    Object.values(screens).forEach((s) => {
      s.classList.remove('active');
      s.style.display = 'none'; // Ensure they are fully hidden
    });
    if (screens[name]) {
      screens[name].style.display = 'block';
      // Trigger reflow for animation
      void screens[name].offsetWidth;
      screens[name].classList.add('active');
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Initial state
  showScreen('input');

  // ═══════════════════════════════════════════════════════════
  // Error Banner
  // ═══════════════════════════════════════════════════════════

  function showError(message) {
    els.errorMessage.textContent = message;
    els.errorBanner.classList.add('visible');

    clearTimeout(errorTimer);
    errorTimer = setTimeout(hideError, 8000);
  }

  function hideError() {
    els.errorBanner.classList.remove('visible');
    clearTimeout(errorTimer);
  }

  els.errorCloseBtn.addEventListener('click', hideError);

  // ═══════════════════════════════════════════════════════════
  // API Helpers
  // ═══════════════════════════════════════════════════════════

  async function apiFetch(endpoint, body) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || data.error || `Server error (${res.status})`);
    }

    if (data.error) {
      throw new Error(data.error);
    }

    return data;
  }

  // ═══════════════════════════════════════════════════════════
  // Form Submission → /api/plan
  // ═══════════════════════════════════════════════════════════

  els.form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
      origin_city:        $('#origin-city').value.trim(),
      travel_type:        $('input[name="travel_type"]:checked').value,
      departure_date:     $('#departure-date').value,
      return_date:        $('#return-date').value,
      travel_pace:        $('input[name="travel_pace"]:checked').value,
      budget:             $('#budget').value,
      travel_style:       $('#travel-style').value,
      weather_preference: $('#weather-preference').value,
    };

    // Validation
    if (!formData.origin_city) {
      showError('Please specify a departure city.');
      return;
    }

    // Show loading
    showScreen('loadingPlan');
    els.loadingPlanLabel.textContent = 'Curating Your Options';
    els.loadingPlanSub.textContent = 'Analysing global destinations and local cultures...';

    const labelTimers = [
      setTimeout(() => { 
        els.loadingPlanLabel.textContent = 'Fetching Weather Data'; 
        els.loadingPlanSub.textContent = 'Checking real-time conditions for ideal matches...';
      }, 3000),
      setTimeout(() => { 
        els.loadingPlanLabel.textContent = 'Consulting GulliverAI'; 
        els.loadingPlanSub.textContent = 'Our intelligence is ranking the best fits for you...';
      }, 6500),
    ];

    try {
      const data = await apiFetch('/api/plan', formData);

      labelTimers.forEach(clearTimeout);
      sessionId = data.session_id;
      recommendations = data.recommendations || [];
      destinationImages = data.destination_images || {};

      if (recommendations.length === 0) {
        throw new Error('No destinations matched your criteria. Try widening your preferences.');
      }

      renderRecommendations(recommendations);
      showScreen('recommendations');
    } catch (err) {
      labelTimers.forEach(clearTimeout);
      showError(err.message || 'The Gulliver system encountered an unexpected detour.');
      showScreen('input');
    }
  });

  // ═══════════════════════════════════════════════════════════
  // Render Recommendation Cards
  // ═══════════════════════════════════════════════════════════

  function renderRecommendations(recs) {
    els.recGrid.innerHTML = '';

    recs.forEach((rec, index) => {
      const card = document.createElement('div');
      card.className = 'rec-card';
      card.setAttribute('tabindex', '0');
      card.setAttribute('role', 'button');
      
      const name = rec.destination || 'Selected Escape';
      const country = rec.country || '';
      const reason = rec.reason || '';
      const weatherScore = rec.weather_score != null ? rec.weather_score : '';
      const budgetFit = rec.budget_fit || '';
      const imageUrl = destinationImages[name] || '';

      card.innerHTML = `
        <div class="rec-card-image" style="background-image: url('${imageUrl}')"></div>
        <div class="rec-card-content">
          <div class="rec-card-header">
            <div class="rec-info">
              <span class="country">${escapeHtml(country)}</span>
              <h3>${escapeHtml(name)}</h3>
            </div>
            ${weatherScore !== '' ? `<span class="weather-badge">☀ ${escapeHtml(String(weatherScore))}/10</span>` : ''}
          </div>
          <p class="reason">${escapeHtml(reason)}</p>
          <div class="rec-footer">
            <span class="budget-fit">${escapeHtml(budgetFit)} budget</span>
            <span class="cta-text">Select Destination →</span>
          </div>
        </div>
      `;

      card.addEventListener('click', () => selectDestination(rec));
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          selectDestination(rec);
        }
      });

      els.recGrid.appendChild(card);
    });
  }

  // ═══════════════════════════════════════════════════════════
  // Destination Selection → /api/itinerary
  // ═══════════════════════════════════════════════════════════

  async function selectDestination(rec) {
    const destName = rec.destination;

    showScreen('loadingItinerary');
    els.loadingItineraryLabel.textContent = 'Architecting Itinerary';
    els.loadingItinerarySub.textContent = 'Crafting a unique day-by-day sequence for ' + destName + '...';

    const labelTimers = [
      setTimeout(() => { els.loadingItineraryLabel.textContent = 'Optimising Routes'; }, 3000),
      setTimeout(() => { els.loadingItineraryLabel.textContent = 'Polishing Local Tips'; }, 6000),
    ];

    try {
      const data = await apiFetch('/api/itinerary', {
        session_id: sessionId,
        selected_destination: destName,
      });

      labelTimers.forEach(clearTimeout);

      const itinerary = data.itinerary;
      const flights = data.transport_options || [];

      if (!itinerary || (typeof itinerary === 'object' && Object.keys(itinerary).length === 0)) {
        throw new Error('Gulliver failed to map this journey. Please try another destination.');
      }

      renderTransport(flights);
      renderItinerary(itinerary, destName);
      showScreen('itinerary');
    } catch (err) {
      labelTimers.forEach(clearTimeout);
      showError(err.message || 'Something went wrong while building your map.');
      showScreen('recommendations');
    }
  }

  function renderTransport(flights) {
    els.flightList.innerHTML = '';
    if (!flights || flights.length === 0) {
      els.transportSection.style.display = 'none';
      return;
    }

    els.transportSection.style.display = 'block';
    flights.forEach(f => {
      const item = document.createElement('div');
      item.className = 'flight-item';
      item.innerHTML = `
        <div class="flight-meta">
          <span class="carrier">${escapeHtml(f.carrier)}</span>
          <span class="duration">⏱ ${escapeHtml(f.duration)}</span>
        </div>
        <div class="flight-times">
          <div class="time-point">
            <span class="time">${new Date(f.departure).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
          </div>
          <div class="flight-path"></div>
          <div class="time-point">
            <span class="time">${new Date(f.arrival).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
          </div>
        </div>
        <div class="flight-price">${escapeHtml(f.price)}</div>
      `;
      els.flightList.appendChild(item);
    });
  }

  // ═══════════════════════════════════════════════════════════
  // Render Itinerary Accordion
  // ═══════════════════════════════════════════════════════════

  function renderItinerary(itinerary, destName) {
    els.itineraryTitle.textContent = `${destName}`;
    els.itinerarySubtitle.textContent = `A masterfully crafted journey through ${destName}.`;
    els.accordion.innerHTML = '';

    let days = [];

    // Normalise itinerary shape
    if (itinerary.itinerary && typeof itinerary.itinerary === 'object') {
      const inner = itinerary.itinerary;
      const keys = Object.keys(inner).filter(k => k.toLowerCase().startsWith('day'));
      if (keys.length > 0) {
        keys.sort((a,b) => (parseInt(a.replace(/\D/g,'')) || 0) - (parseInt(b.replace(/\D/g,'')) || 0));
        days = keys.map((k, i) => ({ day: i + 1, ...inner[k] }));
      }
    } else if (Array.isArray(itinerary.days)) {
      days = itinerary.days;
    }

    if (days.length === 0) {
        // Final fallback: raw display
        days = [{ day: 1, morning: "Itinerary data received but couldn't be parsed into days. Please check back later." }];
    }

    days.forEach((dayObj, idx) => {
      const dayNum = dayObj.day || idx + 1;
      const morning   = dayObj.morning   || dayObj.Morning   || '—';
      const afternoon = dayObj.afternoon || dayObj.Afternoon || '—';
      const evening   = dayObj.evening   || dayObj.Evening   || '—';
      const tip       = dayObj.tip       || dayObj.Tip       || '';

      const panel = document.createElement('div');
      panel.className = 'day-panel';
      if (idx === 0) panel.classList.add('open');

      panel.innerHTML = `
        <button class="day-header" aria-expanded="${idx === 0 ? 'true' : 'false'}" id="day-header-${dayNum}">
          <h3>Day ${dayNum}</h3>
          <span class="chevron">▼</span>
        </button>
        <div class="day-body" role="region" aria-labelledby="day-header-${dayNum}">
          <div class="day-content">
            <div class="time-slot">
              <span class="time-label">Morning</span>
              <span class="time-desc">${escapeHtml(morning)}</span>
            </div>
            <div class="time-slot">
              <span class="time-label">Afternoon</span>
              <span class="time-desc">${escapeHtml(afternoon)}</span>
            </div>
            <div class="time-slot">
              <span class="time-label">Evening</span>
              <span class="time-desc">${escapeHtml(evening)}</span>
            </div>
            ${dayObj.food_spots ? `
            <div class="food-section">
              <span class="time-label">Culinary Highlights</span>
              <div class="food-grid">
                ${dayObj.food_spots.map(fs => `
                  <div class="food-card">
                    <div class="food-header">
                      <span class="food-name">${escapeHtml(fs.name)}</span>
                      ${fs.rating && fs.rating !== 'N/A' ? `<span class="food-rating">⭐ ${escapeHtml(fs.rating)}</span>` : ''}
                    </div>
                    <p class="food-reason">${escapeHtml(fs.reason)}</p>
                  </div>
                `).join('')}
              </div>
            </div>` : ''}
            ${tip ? `
            <div class="tip-box">
              <span class="time-label">Pro Tip</span>
              <div class="time-desc-wrapper">
                <p class="time-desc">${escapeHtml(tip)}</p>
              </div>
            </div>` : ''}
          </div>
        </div>
      `;

      const header = panel.querySelector('.day-header');
      header.addEventListener('click', () => {
        const isOpen = panel.classList.toggle('open');
        header.setAttribute('aria-expanded', String(isOpen));
      });

      els.accordion.appendChild(panel);
    });
  }

  // ═══════════════════════════════════════════════════════════
  // Navigation Buttons
  // ═══════════════════════════════════════════════════════════

  els.backToFormBtn.addEventListener('click', () => showScreen('input'));
  els.backToRecsBtn.addEventListener('click', () => showScreen('recommendations'));
  els.restartBtn.addEventListener('click', () => {
    sessionId = null;
    recommendations = [];
    els.form.reset();
    showScreen('input');
  });

  // ═══════════════════════════════════════════════════════════
  // Utilities
  // ═══════════════════════════════════════════════════════════

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

})();
