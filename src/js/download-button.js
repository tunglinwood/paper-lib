/**
 * Download-button module for pdf2htmlEX-generated paper HTML pages.
 *
 * Adds a fixed "Download PDF" button in the top-right corner. When clicked,
 * it fetches the matching PDF as a blob and triggers a browser download so
 * the file is saved with the correct name, even if the browser would otherwise
 * just display it inline.
 */
(function () {
  if (document.getElementById('paper-download-btn')) return;

  const paperId = window.location.pathname
    .split('/')
    .pop()
    .replace(/\.html$/i, '');

  if (!paperId || !paperId.startsWith('sha256_')) return;

  const pdfUrl = `/archive/_unsorted/Library/01_curated/original/${paperId}.pdf`;
  const pdfFilename = `${paperId}.pdf`;

  const btn = document.createElement('button');
  btn.id = 'paper-download-btn';
  btn.type = 'button';
  btn.textContent = 'Download PDF';
  btn.title = 'Download original PDF';

  Object.assign(btn.style, {
    position: 'fixed',
    top: '12px',
    right: '12px',
    zIndex: '99999',
    padding: '8px 14px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: '14px',
    fontWeight: '600',
    lineHeight: '1.25',
    textDecoration: 'none',
    borderRadius: '6px',
    boxShadow: '0 2px 6px rgba(0,0,0,0.25)',
    cursor: 'pointer',
    border: 'none',
    outline: 'none',
    pointerEvents: 'auto',
  });

  btn.addEventListener('mouseenter', () => {
    btn.style.backgroundColor = '#1d4ed8';
  });
  btn.addEventListener('mouseleave', () => {
    btn.style.backgroundColor = '#2563eb';
  });

  btn.addEventListener('click', async () => {
    btn.textContent = 'Downloading…';
    btn.style.opacity = '0.7';
    try {
      const response = await fetch(pdfUrl, { credentials: 'same-origin' });
      if (!response.ok) {
        throw new Error(`Failed to fetch PDF: ${response.status} ${response.statusText}`);
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = pdfFilename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (err) {
      console.error('[download-button]', err);
      window.open(pdfUrl, '_blank');
    } finally {
      btn.textContent = 'Download PDF';
      btn.style.opacity = '1';
    }
  });

  document.body.appendChild(btn);
})();
