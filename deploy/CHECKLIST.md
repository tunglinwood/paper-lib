# Deployment Checklist

Use this checklist when deploying the Paper Library on distributed machines.

## Pre-Deployment

- [ ] Backend machine has Python 3.13+ installed
- [ ] Backend machine has Docker installed (for PDF→HTML conversion)
- [ ] Backend machine has UV installed
- [ ] Frontend machine has Node.js 18+ or Bun installed
- [ ] Network connectivity between frontend and backend machines
- [ ] Firewall rules configured (port 9000 open for frontend → backend)
- [ ] SSL certificates obtained (if using HTTPS)

## Backend Setup

- [ ] Clone repository to backend machine
- [ ] Run `deploy/setup-backend.sh`
- [ ] Edit `.env` file:
  - [ ] Set `ALLOWED_ORIGINS` to frontend URL(s)
  - [ ] Verify `LLM_BASE_URL` and `LLM_MODEL` are correct
- [ ] Verify backend is running: `curl http://localhost:9000/api/papers`
- [ ] Test CORS from frontend machine: `curl -I http://backend:9000/api/papers`
  - Should see `Access-Control-Allow-Origin` header

## Frontend Setup

- [ ] Copy frontend files to frontend machine:
  - `index.html`, `admin.html`, `embed.html`
  - `src/` directory
  - `deploy/server.distributed.mjs` (or use nginx)
- [ ] Run `deploy/setup-frontend.sh <backend-url>`
  - Or manually update `API_BASE` in `src/js/api.js`
- [ ] Verify API connectivity: `curl http://backend:9000/api/papers`
- [ ] (Optional) Copy HTML paper files to `/papers/` directory
  - Or configure nginx to proxy `/papers/` to backend

## Testing

- [ ] Open frontend in browser
- [ ] Verify papers load (check paper count matches backend)
- [ ] Test search functionality
- [ ] Test paper detail modal opens
- [ ] Test "View HTML" button works
- [ ] Test admin panel:
  - [ ] Can view paper list
  - [ ] Can search papers
  - [ ] Can edit paper metadata
  - [ ] Can delete papers
  - [ ] Can upload new papers
- [ ] Check browser console for errors (F12 → Console)
- [ ] Check network tab for failed requests (F12 → Network)

## Production Hardening (Optional)

- [ ] Configure nginx for frontend (see `deploy/nginx-frontend.conf`)
- [ ] Enable HTTPS with Let's Encrypt
- [ ] Restrict CORS `ALLOWED_ORIGINS` to specific domains
- [ ] Add API authentication (API key or JWT)
- [ ] Set up monitoring (PM2 + log rotation)
- [ ] Configure automated backups for `papers.db`
- [ ] Set up log rotation for nginx and PM2
- [ ] Configure firewall rules (ufw/iptables)
- [ ] Set up automated updates (git pull + restart scripts)

## Common Issues

### CORS Errors
**Symptom:** Browser console shows "Access-Control-Allow-Origin" errors  
**Fix:** Update `ALLOWED_ORIGINS` in backend `.env` and restart backend

### API Connection Failed
**Symptom:** Frontend shows empty paper list or "Failed to fetch"  
**Fix:** Check `API_BASE` in `src/js/api.js` and verify backend is reachable

### HTML Papers Not Loading
**Symptom:** "View HTML" shows 404  
**Fix:** Either sync HTML files to frontend or proxy `/papers/` to backend

### Slow Performance
**Symptom:** Frontend takes long to load  
**Fix:** Enable gzip in nginx, add cache headers, consider CDN

## Post-Deployment

- [ ] Document deployment URLs for team
- [ ] Set up monitoring alerts
- [ ] Test backup and restore procedure
- [ ] Create update deployment script (optional)
- [ ] Train team on admin panel usage

## Rollback Plan

If deployment fails:

1. **Backend issues:**
   - Check logs: `pm2 logs paper-lib-backend`
   - Restart: `pm2 restart paper-lib-backend`
   - Rollback code: `git checkout <previous-commit>`

2. **Frontend issues:**
   - Check nginx logs: `sudo tail -f /var/log/nginx/error.log`
   - Reload nginx: `sudo systemctl reload nginx`
   - Rollback files: restore from backup

3. **Database issues:**
   - Restore from backup: `sqlite3 papers.db ".restore '/backup/papers-YYYYMMDD.db'"`
   - Restart backend: `pm2 restart paper-lib-backend`

## Support

- Backend logs: `pm2 logs paper-lib-backend`
- Frontend logs: `sudo tail -f /var/log/nginx/error.log`
- PM2 status: `pm2 status`
- Database stats: `sqlite3 papers.db "SELECT COUNT(*) FROM papers;"`
