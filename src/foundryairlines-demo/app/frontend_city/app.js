// City Activities Poster — SSE client
(function () {
    const form = document.getElementById('city-form');
    const input = document.getElementById('city-input');
    const runBtn = document.getElementById('run-btn');
    const progressSection = document.getElementById('progress-section');
    const logContainer = document.getElementById('log-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const activitiesSection = document.getElementById('activities-section');
    const activitiesContainer = document.getElementById('activities-container');
    const posterSection = document.getElementById('poster-section');
    const posterContainer = document.getElementById('poster-container');

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const city = input.value.trim();
        if (!city) return;
        startPipeline(city);
    });

    function startPipeline(city) {
        // Reset UI
        runBtn.disabled = true;
        runBtn.textContent = 'Generating…';
        logContainer.innerHTML = '';
        activitiesContainer.innerHTML = '';
        posterContainer.innerHTML = '';
        progressSection.style.display = 'block';
        activitiesSection.style.display = 'none';
        posterSection.style.display = 'none';
        setProgress(0, 'Starting…');

        const url = `/api/city?city=${encodeURIComponent(city)}`;
        const source = new EventSource(url);

        source.addEventListener('agent_start', (e) => {
            const data = JSON.parse(e.data);
            addLog(data.agent, data.message);
            if (data.agent === 'activities') {
                setProgress(10, 'Searching for activities…');
            } else if (data.agent === 'poster') {
                setProgress(60, 'Generating poster (this takes ~30-60s)…');
            }
        });

        source.addEventListener('agent_log', (e) => {
            const data = JSON.parse(e.data);
            addLog(data.agent, data.message);
        });

        source.addEventListener('agent_done', (e) => {
            const data = JSON.parse(e.data);
            addLog(data.agent, '✓ Done');
            if (data.agent === 'activities') {
                setProgress(50, 'Activities found!');
            } else if (data.agent === 'poster') {
                setProgress(100, 'Complete!');
            }
        });

        source.addEventListener('activity', (e) => {
            const raw = JSON.parse(e.data);
            const activity = raw.data || raw;
            activitiesSection.style.display = 'block';
            addActivityCard(activity);
        });

        source.addEventListener('poster', (e) => {
            const raw = JSON.parse(e.data);
            const poster = raw.data || raw;
            posterSection.style.display = 'block';
            posterContainer.innerHTML = `<img src="${poster.image_url}" alt="Travel poster for ${poster.city}">`;
        });

        source.addEventListener('error', (e) => {
            if (e.data) {
                const data = JSON.parse(e.data);
                addLog('error', data.message);
            }
        });

        source.addEventListener('done', (e) => {
            source.close();
            runBtn.disabled = false;
            runBtn.textContent = 'Generate Poster';
            setProgress(100, 'Pipeline complete.');
        });

        source.onerror = () => {
            source.close();
            runBtn.disabled = false;
            runBtn.textContent = 'Generate Poster';
            addLog('system', 'Connection lost.');
        };
    }

    function setProgress(pct, text) {
        progressBar.style.width = pct + '%';
        progressText.textContent = text;
    }

    function addLog(agent, message) {
        const el = document.createElement('div');
        el.className = 'log-entry';
        el.innerHTML = `<span class="agent-tag">[${agent}]</span>${escapeHtml(message)}`;
        logContainer.appendChild(el);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    function addActivityCard(activity) {
        const card = document.createElement('div');
        card.className = 'activity-card';
        const title = activity.title || 'Untitled';
        const category = activity.category || 'general';
        const description = activity.description || '';
        card.innerHTML = `
            <div class="category">${escapeHtml(category)}</div>
            <div class="title">${escapeHtml(title)}</div>
            <div class="description">${escapeHtml(description)}</div>
        `;
        activitiesContainer.appendChild(card);
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
})();
