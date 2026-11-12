document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = 'http://localhost:8000/api/v1';
    const chatContainer = document.getElementById('chat-container');
    const inputField = document.getElementById('query-input');
    const uploadInput = document.getElementById('file-upload');
    const refreshDocsBtn = document.getElementById('refresh-docs');
    const loadDemoBtn = document.getElementById('load-demo');
    const documentContext = document.getElementById('document-context');
    const systemStatus = document.getElementById('system-status');

    init();

    async function init() {
        await checkHealth();
        await loadDocuments();
    }

    inputField.addEventListener('keypress', async (e) => {
        if (e.key !== 'Enter') return;
        const query = inputField.value.trim();
        if (!query) return;

        appendMessage('user', `> ${escapeHtml(query)}`);
        inputField.value = '';
        const loaderId = appendMessage('system', 'Analyse en cours, veuillez patienter...');

        try {
            const response = await fetch(`${API_BASE}/audit/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    document_context: documentContext.value || 'all'
                })
            });

            if (!response.ok) {
                const errorData = await safeJson(response);
                throw new Error(errorData?.detail || 'Erreur de communication avec le serveur.');
            }

            const data = await response.json();
            updateMessage(loaderId, formatResponse(data.response));
        } catch (error) {
            updateMessage(loaderId, `[ERREUR] : ${escapeHtml(error.message)}`);
            document.getElementById(loaderId)?.classList.add('error-msg');
        }
    });

    uploadInput.addEventListener('change', async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        appendMessage('user', `> Upload demandé : ${escapeHtml(file.name)}`);
        const loaderId = appendMessage('system', 'Indexation du document en cours...');

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${API_BASE}/documents/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await safeJson(response);
                throw new Error(errorData?.detail || 'Échec du téléversement.');
            }

            const data = await response.json();
            updateMessage(loaderId, `[UPLOAD OK] ${escapeHtml(data.filename)} indexé. document_id=${escapeHtml(data.document.document_id)}`);
            await loadDocuments();
        } catch (error) {
            updateMessage(loaderId, `[ERREUR UPLOAD] : ${escapeHtml(error.message)}`);
            document.getElementById(loaderId)?.classList.add('error-msg');
        } finally {
            uploadInput.value = '';
        }
    });

    loadDemoBtn.addEventListener('click', async () => {
        const loaderId = appendMessage('system', 'Chargement de la démonstration en cours...');
        try {
            const response = await fetch(`${API_BASE}/demo/load`, { method: 'POST' });
            if (!response.ok) {
                const errorData = await safeJson(response);
                throw new Error(errorData?.detail || 'Impossible de charger la démonstration.');
            }
            const data = await response.json();
            const queries = (data.sample_queries || []).map((item) => `- ${escapeHtml(item)}`).join('<br>');
            updateMessage(loaderId, `[DEMO OK] ${data.count} documents chargés.<br><br>[ESSAIS CONSEILLÉS]<br>${queries}`);
            await loadDocuments();
        } catch (error) {
            updateMessage(loaderId, `[ERREUR DEMO] : ${escapeHtml(error.message)}`);
            document.getElementById(loaderId)?.classList.add('error-msg');
        }
    });

    refreshDocsBtn.addEventListener('click', loadDocuments);

    async function checkHealth() {
        try {
            const response = await fetch('http://localhost:8000/health');
            if (!response.ok) throw new Error();
            const data = await response.json();
            systemStatus.textContent = `${data.status.toUpperCase()} | ${data.version}`;
        } catch {
            systemStatus.textContent = 'BACKEND HORS LIGNE';
        }
    }

    async function loadDocuments() {
        try {
            const response = await fetch(`${API_BASE}/documents`);
            if (!response.ok) throw new Error('Impossible de charger les documents.');
            const data = await response.json();
            const documents = data.documents || [];

            documentContext.innerHTML = '<option value="all">Tous les documents</option>';
            documents.forEach((doc) => {
                const option = document.createElement('option');
                option.value = doc.document_id;
                option.textContent = `${doc.filename} (${doc.chunks} chunks)`;
                documentContext.appendChild(option);
            });
        } catch (error) {
            appendMessage('error', `[ALERTE] ${escapeHtml(error.message)}`);
        }
    }

    function appendMessage(sender, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}-msg`;
        const id = `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        msgDiv.id = id;
        msgDiv.innerHTML = text;
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return id;
    }

    function updateMessage(id, text) {
        const msgDiv = document.getElementById(id);
        if (msgDiv) {
            msgDiv.innerHTML = text;
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    function formatResponse(payload) {
        if (!payload) return '[RESULTAT] : Réponse vide.';
        const answer = escapeHtml(payload.answer || 'Aucune réponse.');
        const citations = Array.isArray(payload.citations)
            ? payload.citations.map((c) =>
                `[#${c.rank}] ${escapeHtml(c.filename || 'inconnu')} / ${escapeHtml(c.chunk_id || '-')}`
              ).join('<br>')
            : 'Aucune citation.';
        return `[MODE] ${escapeHtml(payload.mode || 'unknown')}<br><br>[RESULTAT]<br>${answer.replace(/\n/g, '<br>')}<br><br>[SOURCES]<br>${citations}`;
    }

    async function safeJson(response) {
        try {
            return await response.json();
        } catch {
            return null;
        }
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});
