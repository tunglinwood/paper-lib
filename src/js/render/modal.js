import { state } from '../state.js';
import { escapeHtml } from '../utils/helpers.js';
import { t } from '../i18n.js';
import { PDF_BASE } from '../api.js';

// --- Panel resize ---
const STORAGE_KEY = 'paperLibPanelWidth';
const MIN_WIDTH = 320;
const DEFAULT_WIDTH = 420;

export function setupPanelResize() {
    const modal = document.getElementById('paperModal');
    if (!modal) return;

    // Create resize handle element (sibling of .modal-content)
    const handle = document.createElement('div');
    handle.className = 'modal-resize-handle';
    handle.setAttribute('role', 'separator');
    handle.setAttribute('aria-orientation', 'vertical');
    modal.appendChild(handle);

    // Load saved width
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            const w = parseInt(saved, 10);
            if (w >= MIN_WIDTH) {
                document.documentElement.style.setProperty('--panel-width', `${w}px`);
            }
        }
    } catch {}

    // Drag logic
    let startX = 0;
    let startWidth = 0;

    handle.addEventListener('mousedown', (e) => {
        e.preventDefault();
        startX = e.clientX;
        const content = modal.querySelector('.modal-content');
        startWidth = content ? content.getBoundingClientRect().width : DEFAULT_WIDTH;
        handle.classList.add('active');
        content?.classList.add('resizing');
        document.body.style.userSelect = 'none';

        const onMove = (e) => {
            const delta = startX - e.clientX; // drag left = wider
            const newWidth = Math.max(MIN_WIDTH, Math.min(window.innerWidth * 0.9, startWidth + delta));
            document.documentElement.style.setProperty('--panel-width', `${newWidth}px`);
        };

        const onUp = () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            handle.classList.remove('active');
            content?.classList.remove('resizing');
            document.body.style.userSelect = '';
            // Persist
            try {
                localStorage.setItem(STORAGE_KEY, Math.round(startWidth + (document.documentElement.clientWidth * 0.9)));
                // Recalculate from current CSS value
                const current = content?.getBoundingClientRect().width || DEFAULT_WIDTH;
                localStorage.setItem(STORAGE_KEY, Math.round(current));
            } catch {}
        };

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    });
}

export function showModal(paper) {
    state.currentPaper = paper;

    // Build meta info
    let metaHtml = '';
    if (paper.year) metaHtml += `<p style="margin-bottom:0.25rem;"><strong>${t('year')}:</strong> ${paper.year}</p>`;
    if (paper.venue) metaHtml += `<p style="margin-bottom:0.25rem;"><strong>${t('venue')}:</strong> ${escapeHtml(paper.venue)}</p>`;
    if (paper.doi) metaHtml += `<p style="margin-bottom:0.25rem;"><strong>${t('doi')}:</strong> ${escapeHtml(paper.doi)}</p>`;
    if (paper.abstract) metaHtml += `<p style="margin-bottom:0.25rem;"><strong>${t('abstract')}:</strong> ${escapeHtml(paper.abstract)}</p>`;

    // Tags
    let tagsHtml = '';
    if (paper.tags && paper.tags.length) {
        tagsHtml = `<div style="display:flex;flex-wrap:wrap;gap:0.4rem;margin-top:0.5rem;">` +
            paper.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('') + `</div>`;
    }

    // PDF viewer — expanded by default
    let pdfViewerHtml = '';
    if (paper.file_path) {
        pdfViewerHtml = `
        <div class="pdf-viewer-container" style="margin-top:1rem;">
            <iframe id="pdfPreviewFrame" class="pdf-preview" title="PDF preview of ${escapeHtml(paper.title || 'Untitled')}" src="${PDF_BASE}${paper.file_path}"></iframe>
        </div>`;
    }

    // Related papers
    const paperTitle = (paper.title || '').toLowerCase().split(/\s+/).filter(w => w.length > 4);
    const related = state.allPapers.filter(p =>
        p.paper_id !== paper.paper_id &&
        paperTitle.some(word => (p.title || '').toLowerCase().includes(word))
    ).slice(0, 5);

    let relatedHtml = '';
    if (related.length) {
        relatedHtml = `<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #f0f0f0;">
            <h3 style="margin-bottom:0.5rem;">${t('relatedPapers')}</h3>` +
            related.map(p => {
                const hasHtml = !!p.html_path;
                const action = hasHtml ? 'view-html' : 'show-paper';
                const href = hasHtml ? `/papers/${p.paper_id}.html` : `#${p.paper_id}`;
                const target = hasHtml ? ' target="_blank" rel="noopener"' : '';
                return `
                <div style="padding:0.5rem;border-bottom:1px solid #f0f0f0;cursor:pointer;" data-action="${action}" data-id="${p.paper_id}">
                    <a href="${href}"${target} style="text-decoration:none;color:inherit;display:block;">
                        <strong>${escapeHtml(p.title || t('untitled'))}</strong>
                        <div style="font-size:0.85rem;color:#666;">${(p.authors || []).join(', ') || t('unknownAuthors')}</div>
                    </a>
                </div>`;
            }).join('') + `</div>`;
    } else {
        relatedHtml = `<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #f0f0f0;">
            <h3 style="margin-bottom:0.5rem;">${t('relatedPapers')}</h3>
            <p style="color:#666;font-size:0.85rem;">${t('noRelatedPapers')}</p></div>`;
    }

    document.getElementById('paperModal').querySelector('.modal-content').innerHTML = `
        <div class="modal-header">
            <div>
                <h2 id="modalTitle" style="font-size:1.3rem;margin-bottom:0.5rem;"></h2>
                <p id="modalAuthors" style="color:#666;"></p>
            </div>
            <button class="modal-close" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
            <div style="margin-bottom:0.5rem;">${metaHtml}${tagsHtml}</div>
            ${pdfViewerHtml}
            ${relatedHtml}
        </div>
    `;

    // Re-set title/authors after innerHTML replace
    document.getElementById('modalTitle').textContent = paper.title || t('untitled');
    document.getElementById('modalAuthors').textContent = (paper.authors || []).join(', ') || t('unknownAuthors');

    document.getElementById('paperModal').classList.add('active');
}

export function closeModal() {
    document.getElementById('paperModal').classList.remove('active');
    // Clear iframe src to free memory
    const iframe = document.getElementById('pdfPreviewFrame');
    if (iframe) iframe.src = '';
    state.currentPaper = null;
}
