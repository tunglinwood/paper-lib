/**
 * Download-button module for pdf2htmlEX-generated paper HTML pages.
 *
 * Adds a fixed "Download PDF" button in the top-right corner. The button
 * derives the paper ID from the current page URL (`/papers/<paper_id>.html`)
 * and links to the matching PDF file.
 */
(function () {
  if (document.getElementById('paper-download-btn')) return;

  const paperId = window.location.pathname
    .split('/')
    .pop()
    .replace(/\.html$/i, '');

  if (!paperId || !paperId.startsWith('sha256_')) return;

  const pdfUrl = `/archive/_unsorted/Library/01_curated/original/${paperId}.pdf`;

  const btn = document.createElement('a');
  btn.id = 'paper-download-btn';
  btn.href = pdfUrl;
  btn.download = `${paperId}.pdf`;
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
  });

  btn.addEventListener('mouseenter', () => {
    btn.style.backgroundColor = '#1d4ed8';
  });
  btn.addEventListener('mouseleave', () => {
    btn.style.backgroundColor = '#2563eb';
  });

  // Some browsers ignore the download attribute for non-same-origin URLs.
  // The PDFs are served from the same origin, so this works as expected.
  document.body.appendChild(btn);
})();
