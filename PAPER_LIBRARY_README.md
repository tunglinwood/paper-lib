# 📚 Paper Library - Enhanced UX

## 🌐 Access URL

**Open in your browser:**
```
http://174.1.21.3:3000/static-assets/index.html
```

This is the **same location** as your original `index.html` - just refreshed with the new UI!

---

## ✨ Features

### 🌐 Bilingual Interface
- **🇨🇳 Chinese (中文)** - Default language
- **🇺🇸 English** - Switch anytime
- Language preference saved automatically
- Quick language switcher in header
- All UI elements fully translated

### 🔍 Search & Discovery
- Full-text search across titles, authors, venues, tags
- **⚡ Real-time search** with debouncing (300ms)
- Filter by year, source, topic
- Click topic tags to find related papers
- Sort by relevance, year, or title

### 👁️ Preview & Browse
- Human-readable titles (no more SHA256 hashes!)
- Paper detail modal with full metadata
- **🆕 Embedded PDF viewer** - preview papers inline
- Related papers suggestions
- DOI, venue, year, authors displayed

### 📥 Export & Share
- Bulk selection & BibTeX export
- Direct PDF download
- Citation export

### 📊 Statistics
- **360 papers** indexed
- **~1.5 GB** total size
- **7 sources** (Hua Publication, GK Science, etc.)
- **Years:** 2014-2024

---

## 🎯 Quick Start

1. **Open the URL** in your browser
2. **Search** - Type keywords (e.g., "dorzagliatin", "diabetes")
3. **Filter** - Use sidebar (year, source, topics)
4. **Preview** - Click paper title for details
5. **Download** - Click "Download" for PDF
6. **Export** - Select multiple, export as BibTeX

---

## 📁 Files

- **Main UI:** `/opt/fastgpt/4.9.8/static-assets/index.html`
- **Archive:** `/opt/fastgpt/4.9.8/static-assets/archive/_unsorted/Library/`
- **Index:** `/opt/fastgpt/4.9.8/static-assets/archive/_unsorted/Library/index.jsonl`

---

## 🔧 Troubleshooting

**Page not loading?**
1. Check FastGPT container is running
2. Verify port 3000 is accessible
3. Check browser console (F12) for errors

**Papers not showing?**
- Page loads `archive/_unsorted/Library/index.jsonl`
- Verify archive folder exists
- Check file permissions

**PDFs not downloading?**
- PDFs served from archive folder
- Ensure paths are correct
- Check browser download settings

---

**Built with ❤️ for the research team**
