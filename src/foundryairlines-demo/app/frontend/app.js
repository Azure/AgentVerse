class FoundryAirlinesDemo {
    constructor() {
        this.runButton = document.getElementById('runButton');
        this.resultsGrid = document.getElementById('resultsGrid');
        this.toast = document.getElementById('toast');
        this.eventSource = null;
        this.flightCards = new Map();
        
        this.init();
    }

    init() {
        this.runButton.addEventListener('click', () => this.runDemo());
    }

    runDemo() {
        this.resetState();
        this.runButton.disabled = true;
        this.runButton.innerHTML = '<span class="button-icon">⏳</span> Running...';

        this.eventSource = new EventSource('/api/run' + (document.getElementById('cachedToggle')?.checked ? '?cached=1' : ''));

        this.eventSource.addEventListener('agent_start', (e) => {
            const data = JSON.parse(e.data);
            this.handleAgentStart(data);
        });

        this.eventSource.addEventListener('agent_log', (e) => {
            const data = JSON.parse(e.data);
            this.handleAgentLog(data);
        });

        this.eventSource.addEventListener('agent_done', (e) => {
            const data = JSON.parse(e.data);
            this.handleAgentDone(data);
        });

        this.eventSource.addEventListener('flight', (e) => {
            const data = JSON.parse(e.data);
            this.handleFlight(data);
        });

        this.eventSource.addEventListener('banner', (e) => {
            const data = JSON.parse(e.data);
            this.handleBanner(data);
        });

        this.eventSource.addEventListener('done', (e) => {
            this.handleDone();
        });

        this.eventSource.addEventListener('error', (e) => {
            const data = JSON.parse(e.data);
            this.handleError(data);
        });

        this.eventSource.onerror = (error) => {
            console.error('SSE Error:', error);
            this.showToast('Connection error. Please try again.');
            this.cleanup();
        };
    }

    resetState() {
        // Reset all agent cards
        document.querySelectorAll('.agent-card').forEach(card => {
            card.removeAttribute('data-status');
            const statusDot = card.querySelector('.status-dot');
            const statusText = card.querySelector('.status-text');
            const agentLog = card.querySelector('.agent-log');
            
            statusDot.setAttribute('data-status', 'idle');
            statusText.textContent = 'Idle';
            agentLog.innerHTML = '';
        });

        // Clear results
        this.resultsGrid.innerHTML = '';
        this.flightCards.clear();
    }

    handleAgentStart(data) {
        const card = document.querySelector(`[data-agent="${data.agent}"]`);
        if (!card) return;

        card.setAttribute('data-status', 'running');
        const statusDot = card.querySelector('.status-dot');
        const statusText = card.querySelector('.status-text');
        const agentLog = card.querySelector('.agent-log');

        statusDot.setAttribute('data-status', 'running');
        statusText.innerHTML = '<span style="display: inline-block; animation: spin 1s linear infinite;">⚙️</span> Running';
        
        const logEntry = document.createElement('div');
        logEntry.textContent = `▶ ${data.message}`;
        agentLog.appendChild(logEntry);
        agentLog.scrollTop = agentLog.scrollHeight;
    }

    handleAgentLog(data) {
        const card = document.querySelector(`[data-agent="${data.agent}"]`);
        if (!card) return;

        const agentLog = card.querySelector('.agent-log');
        const logEntry = document.createElement('div');
        logEntry.textContent = `  ${data.message}`;
        agentLog.appendChild(logEntry);
        agentLog.scrollTop = agentLog.scrollHeight;
    }

    handleAgentDone(data) {
        const card = document.querySelector(`[data-agent="${data.agent}"]`);
        if (!card) return;

        card.removeAttribute('data-status');
        const statusDot = card.querySelector('.status-dot');
        const statusText = card.querySelector('.status-text');

        statusDot.setAttribute('data-status', 'done');
        statusText.innerHTML = '✓ Done';
    }

    handleFlight(payload) {
        const data = payload.data || payload;
        const flightCard = document.createElement('div');
        flightCard.className = 'flight-card';
        flightCard.setAttribute('data-flight-id', data.id);

        flightCard.innerHTML = `
            <div class="banner-image-container loading">
                <div class="skeleton"></div>
            </div>
            <div class="flight-info">
                <div class="flight-header">
                    <div class="flight-route">
                        <div class="flight-code">${data.code}</div>
                        <div class="route-text">${data.origin} → ${data.destination}</div>
                        <div class="flight-date">${data.date}</div>
                    </div>
                    <div class="flight-price">
                        €${data.price_eur}
                        <div class="flight-price-label">per person</div>
                    </div>
                </div>
                <div class="flight-details">
                    <div class="detail-item">
                        <div class="detail-label">Destination</div>
                        <div class="detail-value">${data.destination_city}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Occupancy</div>
                        <div class="detail-value">${data.occupancy_pct}%</div>
                    </div>
                </div>
                <div class="event-tag">Awaiting event…</div>
            </div>
        `;

        this.resultsGrid.appendChild(flightCard);
        this.flightCards.set(data.id, flightCard);
    }

    handleBanner(payload) {
        const data = payload.data || payload;
        const flightCard = this.flightCards.get(data.flight_id);
        if (!flightCard) return;

        const imageContainer = flightCard.querySelector('.banner-image-container');
        const eventTag = flightCard.querySelector('.event-tag');

        imageContainer.classList.remove('loading');
        imageContainer.innerHTML = `<img src="${data.image_url}" alt="Campaign banner" class="banner-image">`;

        const ev = data.event || {};
        const title = typeof ev === 'string' ? ev : (ev.title || '');
        const desc = typeof ev === 'string' ? '' : (ev.short_description || '');
        eventTag.innerHTML = desc
            ? `<strong>${title}</strong><br><span style="font-weight:400;opacity:.8">${desc}</span>`
            : title;
    }

    handleDone() {
        this.cleanup();
    }

    handleError(data) {
        this.showToast(data.message);
        this.cleanup();
    }

    cleanup() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        
        this.runButton.disabled = false;
        this.runButton.innerHTML = '<span class="button-icon">▶</span> Run Demo';
    }

    showToast(message) {
        this.toast.textContent = message;
        this.toast.classList.add('show');
        
        setTimeout(() => {
            this.toast.classList.remove('show');
        }, 5000);
    }
}

// Add spinner animation
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

// Initialize the demo
document.addEventListener('DOMContentLoaded', () => {
    new FoundryAirlinesDemo();
});
