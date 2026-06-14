# Search API

## `GET /api/search`

Search and filter papers via fuzzy matching on title, authors, venue, tags, DOI, and abstract.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | `""` | Fuzzy search query. Matches against title, authors, venue, tags, DOI, and abstract. |
| `year_from` | int | `null` | Minimum publication year (inclusive). |
| `year_to` | int | `null` | Maximum publication year (inclusive). |
| `source` | string | `null` | Filter by source collection name. |
| `venue` | string | `null` | Filter by venue name. |
| `sort` | string | `null` | Sort order: `year`, `title`, or `relevance`. Default: `relevance` when `q` is provided, otherwise `year`. |
| `page` | int | `1` | Page number (1-based). |
| `page_size` | int | `20` | Results per page (max 100). |
| `include` | string | `null` | Comma-separated additional fields to include. Currently supports `full_text`. |

### Fuzzy Matching

The search uses character-level fuzzy matching: all query characters must appear in order within the target text, but not necessarily contiguously. This means typing `GKAct` will match "Glucokinase Activator".

Results are ranked by:
1. **Title matches first**, sorted by gap count (fewer gaps = more contiguous = higher rank)
2. **Other field matches** (authors, venue, tags, DOI, abstract) follow, in no particular order
3. Papers with no match are excluded

### Response

```json
{
  "results": [ ...paper objects... ],
  "total": 355,
  "page": 1,
  "page_size": 20,
  "total_pages": 18
}
```

Each paper object contains:
```json
{
  "paper_id": "sha256_<hash>",
  "title": "...",
  "authors": ["Author One", "Author Two"],
  "year": 2024,
  "venue": "Nature Medicine",
  "doi": "10.xxxx/xxxxx",
  "arxiv_id": null,
  "pmid": null,
  "pmcid": null,
  "file_path": "01_curated/original/<hash>.pdf",
  "file_hash_sha256": "<hash>",
  "file_size_bytes": 1234567,
  "file_ext": ".pdf",
  "added_at": "2024-01-15T00:00:00",
  "tags": ["tag1", "tag2"],
  "abstract": "...",
  "status": "curated",
  "source": "Hua Publication",
  "kind": "original",
  "source_path": "...",
  "display_path": "...",
  "created_at": "2024-01-15T00:00:00",
  "updated_at": "2024-01-15T00:00:00",
  "url": "/archive/_unsorted/Library/01_curated/original/<hash>.pdf"
}
```

| Field | Description |
|-------|-------------|
| `file_path` | Relative path from the PDF base directory. |
| `url` | Direct hyperlink to the PDF file, accessible from the browser. |

### Examples

**Basic fuzzy search:**
```bash
curl "http://localhost:5173/api/search?q=DAWN"
```

**Fuzzy search with year filter:**
```bash
curl "http://localhost:5173/api/search?q=dorzagliatin&year_from=2023"
```

**Filter by source with pagination:**
```bash
curl "http://localhost:5173/api/search?source=Poster&page=1&page_size=10"
```

**Sort by year descending (no query):**
```bash
curl "http://localhost:5173/api/search?sort=year"
```

**Combined filters with explicit relevance sort:**
```bash
curl "http://localhost:5173/api/search?q=GK&year_from=2020&year_to=2024&sort=relevance&page_size=50"
```

### Frontend Usage

```javascript
import { searchPapers } from './src/js/api.js';

// Simple search
const resp = await searchPapers({ q: 'DAWN' });
console.log(resp.total, resp.results);

// With all parameters
const resp = await searchPapers({
    q: 'glucokinase',
    year_from: 2020,
    year_to: 2024,
    source: 'Hua Publication',
    sort: 'relevance',
    page: 1,
    page_size: 20,
});
```
