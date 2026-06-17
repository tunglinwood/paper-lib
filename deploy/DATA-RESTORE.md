# Restoring Paper Data from a GitHub Release

This guide explains how to download the released paper archive (PDFs, HTML conversions, and the SQLite database) and load it into a Paper Library backend deployment.

---

## When to Use This

Use these steps after the backend has been deployed with PM2/Uvicorn but before users start using the site. The release assets contain:

- `papers.db` — SQLite database with all paper metadata
- `archive/_unsorted/Library/01_curated/original/` — original PDF files
- `archive/_unsorted/Library/01_curated/html/` — converted HTML versions
- `archive/_unsorted/Library/01_curated/working/` and `annotated/` — processing files

---

## Prerequisites

- The Paper Library repo is cloned on the backend machine.
- The backend environment is ready (`uv`, Python 3.13, dependencies installed).
- The backend is running under PM2 (or is stopped and will be restarted after the restore).
- You have enough disk space for both the split downloads **and** the extracted archive (about 2.4 GB compressed + 3.2 GB extracted).

---

## 1. Identify the Release

Find the release URL, for example:

```text
https://github.com/OWNER/REPO/releases/tag/v1.0.0
```

The release assets are usually split because GitHub limits individual files to 2 GB. In this project they are named:

```text
paper-lib-data-part-aa
paper-lib-data-part-ab
```

---

## 2. Download the Split Assets

Change to the project directory and download both parts:

```bash
cd /path/to/paper-lib

RELEASE_TAG="v1.0.0"
ASSET_BASE="https://github.com/OWNER/REPO/releases/download/${RELEASE_TAG}"

curl -L -o paper-lib-data-part-aa "${ASSET_BASE}/paper-lib-data-part-aa"
curl -L -o paper-lib-data-part-ab "${ASSET_BASE}/paper-lib-data-part-ab"
```

> **Tip:** If a download is interrupted, resume it with `curl -C -`:
> ```bash
> curl -C - -L -o paper-lib-data-part-aa "${ASSET_BASE}/paper-lib-data-part-aa"
> ```

Verify the files are present:

```bash
ls -lh paper-lib-data-part-*
```

Expected output (sizes will vary by release):

```text
-rw-r--r-- 1 user user 1.2G ... paper-lib-data-part-aa
-rw-r--r-- 1 user user 1.2G ... paper-lib-data-part-ab
```

---

## 3. Reassemble the Zip Archive

Concatenate the parts in order:

```bash
cat paper-lib-data-part-* > paper-lib-data.zip
ls -lh paper-lib-data.zip
```

---

## 4. Extract the Archive

If `unzip` is available:

```bash
unzip -q paper-lib-data.zip
```

If `unzip` is not installed, use Python through `uv`:

```bash
uv run python -m zipfile -e paper-lib-data.zip .
```

After extraction you should see:

```text
papers.db
archive/
```

Quick sanity check:

```bash
ls -lh papers.db
du -sh archive
find archive/_unsorted/Library/01_curated/original -name '*.pdf' | wc -l
find archive/_unsorted/Library/01_curated/html    -name '*.html' | wc -l
```

---

## 5. Restart the Backend

If the backend is already running under PM2, restart it so the new `papers.db` and archive are loaded:

```bash
pm2 restart paper-lib-backend
pm2 save
```

If it is not running yet:

```bash
pm2 start ecosystem.config.cjs --only paper-lib-backend
pm2 save
```

---

## 6. Verify the Restore

Run a few quick checks:

```bash
# Number of papers
curl -s http://localhost:9000/api/papers | python3 -c "import sys, json; print(len(json.load(sys.stdin)))"

# Search endpoint
curl -s 'http://localhost:9000/api/search?q=diabetes&page_size=1' | python3 -m json.tool | head -20

# Trending / rankings
curl -s 'http://localhost:9000/api/rankings?window=all' | python3 -c "import sys, json; print(len(json.load(sys.stdin)))"

# A sample PDF file (use a real paper_id from /api/papers)
curl -s -o /dev/null -w '%{http_code}\n' \
  'http://localhost:9000/archive/_unsorted/Library/01_curated/original/<PAPER_ID>.pdf'

# A sample HTML file
curl -s -o /dev/null -w '%{http_code}\n' \
  'http://localhost:9000/papers/<PAPER_ID>.html'
```

---

## 7. Clean Up (Optional)

Once everything is verified, remove the downloaded split files and zip to save disk space:

```bash
rm -f paper-lib-data-part-aa paper-lib-data-part-ab paper-lib-data.zip
```

---

## Troubleshooting

### `curl` download is very slow or times out

Resume with `-C -` or use a download manager such as `aria2c`:

```bash
aria2c -x 4 -s 4 "${ASSET_BASE}/paper-lib-data-part-aa"
aria2c -x 4 -s 4 "${ASSET_BASE}/paper-lib-data-part-ab"
```

### Backend still returns an empty paper list

- Confirm that `papers.db` was extracted into the project root and is not 0 bytes.
- Confirm PM2 is running the backend from the same directory where `papers.db` lives:
  ```bash
  pm2 describe paper-lib-backend
  ```
- Restart the backend again:
  ```bash
  pm2 restart paper-lib-backend
  ```

### PDF or HTML links return 404

- Confirm the `archive/` directory exists at the project root.
- Confirm the request URL uses the path expected by the frontend, e.g. `/archive/_unsorted/Library/01_curated/original/<id>.pdf`.
- Check the backend logs:
  ```bash
  pm2 logs paper-lib-backend
  ```

---

## One-Command Reference

For a release at `https://github.com/OWNER/REPO/releases/tag/v1.0.0`:

```bash
cd /path/to/paper-lib
RELEASE_TAG="v1.0.0"
ASSET_BASE="https://github.com/OWNER/REPO/releases/download/${RELEASE_TAG}"

curl -L -o paper-lib-data-part-aa "${ASSET_BASE}/paper-lib-data-part-aa"
curl -L -o paper-lib-data-part-ab "${ASSET_BASE}/paper-lib-data-part-ab"

cat paper-lib-data-part-* > paper-lib-data.zip
uv run python -m zipfile -e paper-lib-data.zip .

pm2 restart paper-lib-backend
pm2 save

# Verify
curl -s http://localhost:9000/api/papers | python3 -c "import sys, json; print(len(json.load(sys.stdin)))"
```
