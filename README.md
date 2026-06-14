# 📚 Paper Library - Enhanced UX

A modern web interface for searching, browsing, and exporting research papers from the archive.

## ✨ Features Implemented

### 🔍 **Search & Discovery**
- **Full-text search** across titles, authors, venues, tags, and notes
- **Real-time filtering** by year, source, and topic
- **Topic tags** - click any topic to find related papers
- **Smart sorting** - by relevance, year, or title

### 📖 **Paper Preview**
- **Detail modal** with full metadata
- **Related papers** - automatically suggested based on title similarity
- **Quick actions** - preview, download, export citation

### 📥 **Export & Share**
- **Bulk selection** - select multiple papers
- **BibTeX export** - export selected papers as citations
- **Direct download** - download individual PDFs

### 🎨 **User Experience**
- **Clean, modern UI** - responsive design
- **Human-readable titles** - no more SHA256 hashes!
- **Rich metadata** - DOI, venue, year, authors displayed
- **Topic visualization** - see popular research areas
- **Statistics dashboard** - total papers, library size

### 🗂️ **Smart Organization**
- **Auto-categorization** by source (Hua Publication, Glucokinase Research, etc.)
- **Year filtering** - browse by publication year
- **Topic extraction** - Dorzagliatin, Glucokinase, Diabetes, Clinical Trials

---

## 🚀 Access via FastGPT

The paper library is now a **static site** served by your FastGPT Docker container.

### URL
```
http://174.1.21.3:3000/static-assets/paper-lib/index.html
```

Or if you're on the same network:
```
http://localhost:3000/static-assets/paper-lib/index.html
```

### No Installation Needed!
✅ No Python dependencies  
✅ No separate server  
✅ Works directly through FastGPT  

---

## 📁 File Location

```
/opt/fastgpt/4.9.8/static-assets/paper-lib/index.html
```

The FastGPT container automatically serves this at `/static-assets/paper-lib/index.html`

---

## 📊 Library Stats

- **Total Papers:** 360
- **Total Size:** ~1.5 GB
- **Sources:** Hua Publication, Glucokinase Research, etc.
- **Years:** 2014-2024
- **Topics:** Dorzagliatin, Diabetes, Glucokinase, Clinical Trials

---

## 🔧 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/papers?q=search` | Search papers |
| `GET /api/paper/<id>` | Get paper details + related |
| `GET /api/download/<id>` | Download PDF |
| `GET /api/export?ids=1,2,3` | Export BibTeX |
| `GET /api/stats` | Library statistics |

---

## 📁 File Structure

```
paper-lib/
├── app.py              # Flask backend
├── templates/
│   └── index.html      # Web UI
├── static/             # Static assets
├── requirements.txt    # Python dependencies
├── start.sh           # Startup script
└── README.md          # This file
```

---

## 🎯 Future Enhancements

- [ ] Full-text PDF search (OCR + text extraction)
- [ ] PDF inline viewer
- [ ] Citation graph visualization
- [ ] User annotations & highlights
- [ ] Reading lists & collections
- [ ] Integration with Zotero/Mendeley
- [ ] Access analytics & logs
- [ ] Duplicate detection

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** Vanilla JS + CSS
- **Data:** JSONL index
- **Search:** In-memory full-text search

---

**Built with ❤️ for the research team**
