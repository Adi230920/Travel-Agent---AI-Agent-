/* ═══════════════════════════════════════════════════════════
   AI Travel Agent — Frontend Logic (Vanilla JS)
   ═══════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── Configuration ────────────────────────────────────────
  const API_BASE = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
    ? 'http://127.0.0.1:8000'
    : '';

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
    loadingItineraryLabel:$('#loading-itinerary-label'),
    errorBanner:          $('#error-banner'),
    errorMessage:         $('#error-message'),
    errorCloseBtn:        $('#error-close-btn'),
    backToFormBtn:        $('#back-to-form-btn'),
    backToRecsBtn:        $('#back-to-recommendations-btn'),
    restartBtn:           $('#restart-btn'),
  };

  // ── State ────────────────────────────────────────────────
  let sessionId = null;
  let recommendations = [];
  let errorTimer = null;

  // ═══════════════════════════════════════════════════════════
  // Screen Management
  // ═══════════════════════════════════════════════════════════

  /**
   * Show a single screen and hide all others.
   * @param {'input'|'loadingPlan'|'recommendations'|'loadingItinerary'|'itinerary'} name
   */
  function showScreen(name) {
    Object.values(screens).forEach((s) => s.classList.remove('active'));
    if (screens[name]) {
      screens[name].classList.add('active');
    }
  }

  // ═══════════════════════════════════════════════════════════
  // Error Banner
  // ═══════════════════════════════════════════════════════════

  function showError(message) {
    els.errorMessage.textContent = message;
    els.errorBanner.classList.add('visible');

    // Auto-hide after 5 seconds
    clearTimeout(errorTimer);
    errorTimer = setTimeout(hideError, 5000);
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
      // FastAPI HTTPException returns { detail: "..." }
      throw new Error(data.detail || data.error || `Server error (${res.status})`);
    }

    // Legacy format: backend returns { error, step } on failure
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
      budget:             $('#budget').value,
      duration:           parseInt($('#duration').value, 10),
      travel_style:       $('#travel-style').value,
      weather_preference: $('#weather-preference').value,
    };

    // ── Guardrail validation (before any API call) ──────────
    if (!formData.origin_city) {
      showError('Please enter a departure city.');
      return;
    }
    if (!formData.budget) {
      showError('Please select a budget range.');
      return;
    }
    if (!formData.duration || formData.duration < 1 || formData.duration > 30) {
      showError('Duration must be between 1 and 30 days.');
      return;
    }
    if (!formData.travel_style) {
      showError('Please select a travel style.');
      return;
    }
    if (!formData.weather_preference) {
      showError('Please select a weather preference.');
      return;
    }

    // Show loading
    showScreen('loadingPlan');
    els.loadingPlanLabel.textContent = 'Finding destinations...';

    // Simulate step progression for better UX
    const labelTimers = [
      setTimeout(() => { els.loadingPlanLabel.textContent = 'Checking weather data...'; }, 2500),
      setTimeout(() => { els.loadingPlanLabel.textContent = 'Asking AI for recommendations...'; }, 5000),
      setTimeout(() => { els.loadingPlanLabel.textContent = 'Ranking destinations...'; }, 8000),
    ];

    try {
      const data = await apiFetch('/api/plan', formData);

      labelTimers.forEach(clearTimeout);
      sessionId = data.session_id;
      recommendations = data.recommendations || [];

      if (recommendations.length === 0) {
        throw new Error('No recommendations received. Please try different preferences.');
      }

      renderRecommendations(recommendations);
      showScreen('recommendations');
    } catch (err) {
      labelTimers.forEach(clearTimeout);
      showError(err.message || 'Something went wrong while finding destinations.');
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
      card.setAttribute('aria-label', `Select ${rec.name || rec.destination}`);
      card.dataset.index = index;

      const name = rec.name || rec.destination || 'Unknown';
      const country = rec.country || '';
      const reason = rec.reason || rec.description || '';
      const weatherScore = rec.weather_score != null ? rec.weather_score : '';

      card.innerHTML = `
        <div class="rec-card-header">
          <div>
            <div class="rec-card-name">${escapeHtml(name)}</div>
            ${country ? `<div class="rec-card-country">${escapeHtml(country)}</div>` : ''}
          </div>
          ${weatherScore !== '' ? `<span class="weather-badge">☀ ${escapeHtml(String(weatherScore))}/10</span>` : ''}
        </div>
        ${reason ? `<p class="rec-card-reason">${escapeHtml(reason)}</p>` : ''}
        <span class="rec-card-cta">Click to plan →</span>
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
    const destName = rec.name || rec.destination;

    // Show loading
    showScreen('loadingItinerary');
    els.loadingItineraryLabel.textContent = 'Building your itinerary...';

    const labelTimers = [
      setTimeout(() => { els.loadingItineraryLabel.textContent = 'Planning activities for each day...'; }, 2500),
      setTimeout(() => { els.loadingItineraryLabel.textContent = 'Adding local tips and food spots...'; }, 5500),
    ];

    try {
      const data = await apiFetch('/api/itinerary', {
        session_id: sessionId,
        selected_destination: destName,
      });

      labelTimers.forEach(clearTimeout);

      const itinerary = data.itinerary;
      if (!itinerary || Object.keys(itinerary).length === 0) {
        throw new Error('No itinerary was generated. Please try again.');
      }

      renderItinerary(itinerary, destName);
      showScreen('itinerary');
    } catch (err) {
      labelTimers.forEach(clearTimeout);
      showError(err.message || 'Something went wrong while building the itinerary.');
      showScreen('recommendations');
    }
  }

  // ═══════════════════════════════════════════════════════════
  // Render Itinerary Accordion
  // ═══════════════════════════════════════════════════════════

  function renderItinerary(itinerary, destName) {
    els.itineraryTitle.textContent = `Your ${destName} Itinerary`;
    els.itinerarySubtitle.textContent = `A curated day-by-day plan just for you.`;
    els.accordion.innerHTML = '';

    // The itinerary may come as:
    //   { days: [ { day: 1, morning: "...", afternoon: "...", evening: "..." }, ... ] }
    //   or { "Day 1": { morning, afternoon, evening }, ... }
    //   We handle both shapes.

    let days = [];

    if (Array.isArray(itinerary.days)) {
      days = itinerary.days;
    } else if (typeof itinerary === 'object') {
      // Try to build from keys like "Day 1", "day_1", etc.
      const keys = Object.keys(itinerary).filter(
        (k) => k.toLowerCase().startsWith('day') || !isNaN(k)
      );

      if (keys.length > 0) {
        // Sort keys by numeric portion
        keys.sort((a, b) => {
          const numA = parseInt(a.replace(/\D/g, ''), 10) || 0;
          const numB = parseInt(b.replace(/\D/g, ''), 10) || 0;
          return numA - numB;
        });
        days = keys.map((k, i) => {
          const val = itinerary[k];
          if (typeof val === 'object') {
            return { day: i + 1, ...val };
          }
          return { day: i + 1, morning: String(val), afternoon: '', evening: '' };
        });
      } else if (itinerary.itinerary) {
        // Recursive unwrap
        return renderItinerary(itinerary.itinerary, destName);
      } else {
        // Fallback: show raw data nicely
        days = [{ day: 1, morning: JSON.stringify(itinerary, null, 2), afternoon: '', evening: '' }];
      }
    }

    days.forEach((dayObj, idx) => {
      const dayNum = dayObj.day || idx + 1;
      const morning   = dayObj.morning   || dayObj.Morning   || '—';
      const afternoon = dayObj.afternoon || dayObj.Afternoon || '—';
      const evening   = dayObj.evening   || dayObj.Evening   || '—';
      const tip       = dayObj.tip       || dayObj.Tip       || '';

      const panel = document.createElement('div');
      panel.className = 'day-panel';
      // Auto-expand Day 1
      if (idx === 0) panel.classList.add('open');

      panel.innerHTML = `
        <button class="day-header" aria-expanded="${idx === 0 ? 'true' : 'false'}" id="day-header-${dayNum}">
          <span>Day ${dayNum}</span>
          <span class="day-chevron">▼</span>
        </button>
        <div class="day-body" role="region" aria-labelledby="day-header-${dayNum}">
          <div class="day-body-inner">
            <div class="time-slot">
              <span class="time-label">Morning</span>
              <span class="time-content">${escapeHtml(morning)}</span>
            </div>
            <div class="time-slot">
              <span class="time-label">Afternoon</span>
              <span class="time-content">${escapeHtml(afternoon)}</span>
            </div>
            <div class="time-slot">
              <span class="time-label">Evening</span>
              <span class="time-content">${escapeHtml(evening)}</span>
            </div>
            ${tip ? `
            <div class="time-slot tip-slot">
              <span class="time-label">💡 Tip</span>
              <span class="time-content">${escapeHtml(tip)}</span>
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

  els.backToFormBtn.addEventListener('click', () => {
    showScreen('input');
  });

  els.backToRecsBtn.addEventListener('click', () => {
    showScreen('recommendations');
  });

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
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

})();
