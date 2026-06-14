# Paper Library — 开发需求说明书

**项目名称**: Paper Library（华领医药学术文献检索库）

**版本**: 1.0

**更新日期**: 2026-06-11

---

## 目录

[1. 简介](#1-简介)
  [1.1 文档目的](#11-文档目的)
  [1.2 项目背景](#12-项目背景)
  [1.3 项目目标](#13-项目目标)
  [1.4 系统范围](#14-系统范围)
  [1.5 定义与缩写](#15-定义与缩写)

[2. 功能需求](#2-功能需求)
  [2.1 总体需求描述](#21-总体需求描述)
  [2.2 用户端功能需求](#22-用户端功能需求)
  [2.3 管理端功能需求](#23-管理端功能需求)

[3. 系统设计](#3-系统设计)
  [3.1 技术架构](#31-技术架构)
  [3.2 设计约束](#32-设计约束)
  [3.3 数据库表设计](#33-数据库表设计)
  [3.4 API 设计规范](#34-api-设计规范)
  [3.5 前端架构](#35-前端架构)
  [3.6 搜索功能设计](#36-搜索功能设计)
  [3.7 文献 HTML 转换流水线](#37-文献-html-转换流水线)
  [3.8 语义检索与嵌入流水线](#38-语义检索与嵌入流水线)
  [3.9 系统容错设计](#39-系统容错设计)
  [3.10 系统安全性设计](#310-系统安全性设计)

[4. 测试验证](#4-测试验证)
  [4.1 测试用例](#41-测试用例)

[5. 验收交付](#5-验收交付)
  [5.1 交付物清单](#51-交付物清单)
  [5.2 验收标准](#52-验收标准)

[6. 后续扩展工作](#6-后续扩展工作)

[7. 附录](#7-附录)
  [7.1 版本历史](#71-版本历史)
  [7.2 快速命令参考](#72-快速命令参考)
  [7.3 生产目录结构](#73-生产目录结构)

---

## 审批签署页

| | 姓名&事业部/部门 | 签名/日期（年月日） |
|---|---|---|
| **作者**: | | |
| **审核人**: | | |
| **批准人**: | | |

---

# 1. 简介

## 1.1 文档目的

本文档用于明确 Paper Library（华领医药学术文献检索库，以下简称"项目"）的业务目标、功能需求、技术架构与设计规范，为后续系统开发、维护、扩展提供统一、完整且可追溯的依据。

## 1.2 项目背景

华领医药（Hua Medicine）研究团队在日常研究中需要管理大量学术文献，聚焦 Dorzagliatin（多格列艾汀）、Glucokinase（葡萄糖激酶）及 2 型糖尿病领域。传统文献管理依赖手动翻阅和文件名搜索，效率低且难以快速定位相关内容。本项目旨在建立一个集中化的 Web 端文献管理知识库，支持全文模糊检索、语义检索、多维度筛选和在线预览。

### 1.2.1 业务背景

对研究团队而言：
- **文献集中管理**：355+ 篇核心文献统一管理，覆盖 9 个来源、年份 1974–2026
- **高效检索**：全文模糊搜索 + 语义搜索双引擎，快速定位目标文献
- **多维度筛选**：按年份、来源、主题标签过滤，缩小查找范围
- **在线预览**：HTML 版文献直接浏览器查看，无需下载 PDF
- **双语界面**：英文/中文切换，适应国际化团队需求

### 1.2.2 系统流程概述

系统部署于内网环境，核心流程如下：

1. **文献浏览**：用户打开主页，查看文献列表和统计信息
2. **模糊搜索**：输入关键词，系统返回按相关度排序的文献列表
3. **语义搜索**：通过自然语言查询，返回语义最相关的文献
4. **文献详情**：点击文献卡片查看元数据和摘要，支持在线预览
5. **管理员操作**：上传 PDF、编辑元数据、重新抓取文献信息、删除文献、批量操作
6. **文献转换**：PDF 自动转换为自包含 HTML，支持浏览器直接查看

## 1.3 项目目标

- 建设统一学术文献检索服务，集成模糊搜索与语义搜索双引擎
- 支持文献全文检索、多维度筛选（年份/来源/主题标签）
- 提供文献在线预览（HTML 版），无需下载即可阅读
- 提供管理后台，支持文献上传、编辑、删除、重复检测与元数据自动提取
- 支持 AI 驱动的自然语言检索（Page Agent 集成）
- 支持双语界面（英文/中文）
- 支持文献内嵌预览（embed.html，可供第三方 iframe 嵌入）

## 1.4 系统范围

| 维度 | 说明 |
|------|------|
| **生命周期覆盖** | 系统设计 → 开发实现 → 测试验证 → 部署运行 → 运维支持 |
| **系统组成** | 用户端（搜索、浏览、预览、筛选） + 管理端（上传、编辑、删除、重复检测、元数据提取） |
| **功能层面** | 模糊搜索、语义搜索、多维度筛选、文献卡片展示、HTML 预览、PDF 下载、BibTeX 导出 |
| **管理层面** | 文献上传、元数据编辑、重复检测、PDF 元数据自动提取、批量操作 |
| **运行环境** | 公司内部网络环境，FastAPI/Uvicorn + Bun dev server |
| **扩展性** | 模块化架构设计，支持后续功能扩展 |

## 1.5 定义与缩写

| **术语** | **解释** |
|--------|---------|
| Fuzzy Search | 模糊搜索，所有查询字符必须按顺序出现在目标文本中（不要求连续），按缺口数（gap count）排序 |
| Semantic Search | 语义搜索，基于 pgvector 3840 维嵌入向量 + 余弦相似度 |
| Embedding | 向量嵌入，将文本转换为高维数值向量用于语义相似度计算 |
| pdf2htmlEX | 将 PDF 转换为自包含 HTML 的工具（Docker 运行） |
| kalm-emb-12b | 远程嵌入 API 模型，用于文本向量化（3840 维） |
| GLM-4.5-air | 远程 LLM，用于文献元数据提取和 PDF 内容分析 |
| crawl4ai | PDF 文本提取工具，用于从 PDF 中提取全文内容 |
| Page Agent | AI 驱动的自然语言检索组件，集成在前端 |
| WAL | Write-Ahead Logging，SQLite 的日志模式，支持并发读取 |

---

# 2. 功能需求

## 2.1 总体需求描述

本项目采用"首页聚合 + 双引擎搜索 + 后台管理"的业务模式：
- 用户通过首页搜索入口输入关键词，系统自动返回匹配的文献列表
- 支持模糊搜索（全文字符匹配）和语义搜索（自然语言向量匹配）
- 支持按年份、来源、主题标签多维度筛选
- 所有文献管理功能（上传、编辑、删除、重复检测）通过管理后台统一维护
- 系统在内网环境下稳定运行，通过 PM2 进程管理实现自动重启

## 2.2 用户端功能需求

| **序号** | **功能模块** | **功能名称** | **描述** |
|--------|---------|--------|------|
| PL-M-01 | 搜索 | 模糊搜索 | 输入关键词，支持全文模糊匹配（标题、作者、期刊、标签、DOI、摘要），500ms 防抖 |
| PL-M-02 | 搜索 | 语义搜索 | 通过自然语言查询，返回按余弦相似度排序的结果（后端已实现，保留待调用） |
| PL-M-03 | 搜索 | 排序筛选 | 支持按相关度、年份、标题排序 |
| PL-M-04 | 筛选 | 年份筛选 | 按发表年份过滤文献 |
| PL-M-05 | 筛选 | 来源筛选 | 按文献来源（如 Hua Publication、GK Science 等）过滤 |
| PL-M-06 | 筛选 | 主题标签 | 点击主题标签快速定位相关文献 |
| PL-M-07 | 浏览 | 文献卡片 | 显示文献标题、作者、年份、期刊、标签 |
| PL-M-08 | 详情 | 滑动面板 | 点击文献标题打开侧滑详情面板，可调整宽度，宽度持久化 |
| PL-M-09 | 详情 | 相关文献 | 自动推荐相似文献 |
| PL-M-10 | 预览 | HTML 查看 | 查看文献的 HTML 转换版本（如有），浏览器直接阅读 |
| PL-M-11 | 预览 | PDF 预览 | 在详情面板内嵌预览 PDF |
| PL-M-12 | 操作 | PDF 下载 | 下载文献原始 PDF 文件 |
| PL-M-13 | 操作 | BibTeX 导出 | 导出文献引用为 BibTeX 格式 |
| PL-M-14 | 操作 | 批量选择 | 多选文献后批量导出 BibTeX |
| PL-M-15 | 趋势 | 热门文献 | 显示 7 天/30 天/全部热门文献排行（基于浏览统计） |
| PL-M-16 | 国际化 | 双语切换 | 英文/中文界面切换，偏好设置持久化 |
| PL-M-17 | AI | Page Agent | AI 驱动的自然语言检索，通过自然语言指令定位文献 |
| PL-M-18 | 嵌入 | embed.html | 独立的内嵌预览页面，支持第三方 iframe 嵌入 |

## 2.3 管理端功能需求

| **序号** | **功能模块** | **功能名称** | **描述** |
|--------|---------|--------|------|
| PL-A-01 | 管理 | 文献列表 | 浏览所有文献，支持搜索和排序 |
| PL-A-02 | 上传 | 单文件上传 | 上传 PDF 文件，自动保存并创建文献记录 |
| PL-A-03 | 上传 | 上传并提取 | 上传 PDF 后自动运行 crawl4ai + LLM 提取元数据，返回结果供审核确认后再入库 |
| PL-A-04 | 上传 | 多文件上传 | 同时上传多个 PDF 文件（支持 JSON body base64 编码） |
| PL-A-05 | 编辑 | 元数据编辑 | 编辑文献标题、作者、年份、期刊、DOI、标签、摘要等字段 |
| PL-A-06 | 编辑 | URL 元数据抓取 | 输入 URL，自动抓取文献元数据 |
| PL-A-07 | 编辑 | PDF 元数据重抓取 | 对已有 PDF 重新运行 crawl4ai + LLM 提取元数据并更新数据库 |
| PL-A-08 | 删除 | 单篇删除 | 删除单篇文献（同时删除 PDF 文件） |
| PL-A-09 | 删除 | 批量删除 | 多选文献后批量删除 |
| PL-A-10 | 检测 | 重复检测 | 上传前检测 SHA256 哈希是否已存在，避免重复入库 |
| PL-A-11 | HTML | 文献 HTML 查看 | 对已转换 HTML 的文献，提供"查看 HTML"按钮直接跳转阅读 |

---

# 3. 系统设计

## 3.1 技术架构

### 3.1.1 整体技术栈

- **后端**: Python 3.10+ + FastAPI + Uvicorn（生产环境，端口 9000）
- **前端**: Vanilla JavaScript (ES6 模块) + CSS3，无框架依赖
- **数据库**: SQLite（WAL 模式，busy_timeout 默认）
  - `papers.db`: 文献元数据 + 浏览统计
- **向量检索**: 远程 Embedding API (kalm-emb-12b, 3840-dim) + PostgreSQL + pgvector 0.7.0
- **PDF 提取**: crawl4ai（PDF 全文提取） + GLM-4.5-air LLM（元数据生成）
- **HTML 转换**: pdf2htmlEX Docker（自包含 HTML，内嵌 CSS/字体）
- **文件存储**: 本地文件系统（SHA256 命名，防目录遍历）
- **CORS**: `Access-Control-Allow-Origin: *`（所有 API 路由）
- **进程管理**: PM2（自动重启，`ecosystem.config.cjs`）
- **开发服务器**: Bun dev server（端口 5173，HMR 热更新，API 代理到 9000）

### 3.1.2 部署架构

- **应用层**: FastAPI/Uvicorn 直接服务静态文件 + API（端口 9000）
- **开发层**: Bun dev server 提供 HMR + API 代理（端口 5173）
- **数据层**: SQLite 单数据库（WAL 模式，支持并发读取），通过 Docker volume 持久化
- **进程管理**: PM2 管理前后端两个进程，自动重启，内存限制 500MB
- **外部服务**:
  - Embedding API: `174.1.21.3:8001/v1/embeddings`
  - PostgreSQL + pgvector: 容器 `pg`，端口 5432
  - LLM: `174.1.21.3:8000/v1/chat/completions`

## 3.2 设计约束

### 3.2.1 软硬件环境

- Python 3.10+ 运行时，FastAPI Web 框架，Uvicorn ASGI 服务器
- 远程 Embedding API 服务（kalm-emb-12b，3840-dim，HTTP 接口）
- 远程 LLM 服务（GLM-4.5-air，HTTP 接口）
- crawl4ai（PDF 文本提取，系统级依赖）
- pdf2htmlEX Docker（PDF→HTML 转换）
- 内网环境部署，HTTP 直连访问
- Bun 运行时（前端开发服务器）

## 3.3 数据库表设计

### 3.3.1 papers 表（papers.db）

| 字段 | 类型 | 描述 |
|------|------|------|
| `paper_id` | TEXT PK | `sha256_<hash>` 主键 |
| `title` | TEXT | 文献标题 |
| `authors` | TEXT | JSON 数组，作者列表 |
| `year` | INTEGER | 发表年份 |
| `venue` | TEXT | 期刊/会议名称 |
| `doi` | TEXT | DOI 字符串或 null |
| `arxiv_id` | TEXT | arXiv ID 或 null |
| `pmid` | TEXT | PubMed ID 或 null |
| `pmcid` | TEXT | PubMed Central ID 或 null |
| `file_path` | TEXT | PDF 相对路径 |
| `file_hash_sha256` | TEXT | 文件 SHA256 哈希 |
| `file_size_bytes` | INTEGER | 文件大小（字节） |
| `file_ext` | TEXT | 文件扩展名（`.pdf`） |
| `added_at` | TEXT | 添加时间（ISO 格式） |
| `tags` | TEXT | JSON 数组，主题标签 |
| `abstract` | TEXT | 摘要/总结或 null |
| `status` | TEXT | 状态（`"curated"`） |
| `source` | TEXT | 来源集合名称 |
| `kind` | TEXT | 类型（`"original"`） |
| `source_path` / `display_path` | TEXT | 路径信息 |
| `full_text` | TEXT | PDF 全文提取文本（仅 `/api/paper` 返回） |
| `html_path` | TEXT | 转换后 HTML 相对路径，或 null（未转换） |
| `created_at` / `updated_at` | TEXT | 自动时间戳 |

**索引**：
```sql
CREATE INDEX idx_papers_title ON papers(title);
CREATE INDEX idx_papers_year ON papers(year);
CREATE INDEX idx_papers_source ON papers(source);
CREATE INDEX idx_papers_venue ON papers(venue);
CREATE INDEX idx_papers_status ON papers(status);
```

### 3.3.2 views 表（papers.db）

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | INTEGER PK | 自增主键 |
| `paper_id` | TEXT | 外键，关联 papers 表 |
| `ts` | INTEGER | 浏览时间（Unix 毫秒） |
| `type` | TEXT | 浏览类型（`preview`/`pdf_open`） |

**索引**：
```sql
CREATE INDEX idx_views_paper_id ON views(paper_id);
CREATE INDEX idx_views_ts ON views(ts);
```

### 3.3.3 paper_embeddings 表（PostgreSQL + pgvector）

```sql
CREATE TABLE paper_embeddings (
    paper_id VARCHAR(255) PRIMARY KEY,
    full_text TEXT,
    embedding VECTOR(3840),
    abstract_embedding VECTOR(3840),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## 3.4 API 设计规范

### 3.4.1 公共 API

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/papers` | 获取所有文献列表（不含 full_text） |
| `GET` | `/api/paper?paper_id=xxx` | 获取单篇文献详情（含 full_text） |
| `GET` | `/api/search?q=...` | 模糊搜索（分页、筛选、排序） |
| `POST` | `/api/search-semantic` | 语义搜索（pgvector + kalm-emb-12b） |
| `POST` | `/api/track-view` | 记录文献浏览 |
| `GET` | `/api/rankings?window=7|30|all` | 热门文献排行 |

### 3.4.2 管理端 API

| 方法 | 路径 | 描述 |
|------|------|------|
| `POST` | `/api/admin/delete-papers` | 批量删除文献（同时删除 PDF） |
| `POST` | `/api/admin/update-paper` | 更新文献元数据 |
| `POST` | `/api/admin/upload` | 上传 PDF（multipart 或 JSON base64） |
| `POST` | `/api/admin/upload-and-crawl` | 上传 PDF 并自动提取元数据（不入库，待审核） |
| `POST` | `/api/admin/confirm-papers` | 确认审核后入库 |
| `POST` | `/api/admin/check-duplicates` | 检测重复文献（SHA256 哈希比对） |
| `POST` | `/api/admin/fetch-metadata` | 从 URL 提取元数据（运行 autofill_url.py） |
| `POST` | `/api/admin/extract-pdf-metadata` | 从 PDF base64 提取元数据 |
| `POST` | `/api/admin/crawl-pdf` | 对已有 PDF 重新提取元数据并更新 |

### 3.4.3 静态文件路由

| 路径 | 描述 |
|------|------|
| `GET /` | index.html（主站入口） |
| `GET /admin`, `/admin/` | admin.html（管理后台） |
| `GET /papers/{paper_id}.html` | 转换后的 HTML 文献 |
| `GET /embed.html` | 内嵌预览页面 |
| `GET /{full_path:path}` | 兜底静态文件服务 |

### 3.4.4 API 响应格式

**搜索响应**：
```json
{
  "results": [{ "paper_id": "...", "title": "...", "url": "...", "html_url": "..." }],
  "total": 355,
  "page": 1,
  "page_size": 20,
  "total_pages": 18
}
```

**错误响应**：
```json
{ "detail": "错误描述" }
```

## 3.5 前端架构

### 3.5.1 入口文件

| 文件 | 描述 |
|------|------|
| `index.html` | 主站入口，加载 `src/js/main.js` |
| `admin.html` | 管理后台入口，加载 `src/js/admin.js` |
| `embed.html` | 内嵌预览页面 |

### 3.5.2 JS 模块结构

```
src/js/
├── main.js           # 主站入口，事件委托初始化
├── admin.js          # 管理后台入口，CRUD 操作
├── agent.js          # Page Agent 集成
├── i18n.js           # 国际化（EN/ZH 翻译）
├── state.js          # 全局应用状态
├── api.js            # API 配置，fetch 封装
├── utils/helpers.js  # 工具函数（escapeHtml 等）
├── render/
│   ├── papers.js     # 文献卡片渲染 + 分页
│   ├── filters.js    # 年份药丸、来源过滤、主题
│   ├── trending.js   # 热门文献栏
│   └── modal.js      # 滑动详情面板（可调宽度）+ PDF 预览
└── actions/
    └── views.js      # 浏览统计、热门 API 调用
```

### 3.5.3 CSS 模块结构

```
src/css/
├── base.css     # CSS 重置、自定义属性
├── layout.css   # 网格布局、响应式断点
├── header.css
├── search.css
├── sidebar.css  # 统计、年份药丸、来源过滤、主题
├── trending.css # 热门文献栏
├── cards.css    # 文献卡片、批量操作
├── pagination.css
├── modal.css
├── loading.css
└── admin.css    # 管理后台表格、表单、批量操作
```

### 3.5.4 设计规范

- **事件委托**：所有动态元素使用 `data-action` 属性，禁止内联 `onclick`
- **XSS 防护**：所有用户输入值必须通过 `escapeHtml()` 转义
- **i18n**：所有用户可见文本使用 `t('key')`，语言存储在 `localStorage`
- **详情面板**：侧滑面板（非居中弹窗），宽度可调（最小 320px，默认 420px），宽度持久化

## 3.6 搜索功能设计

### 3.6.1 模糊搜索

- 匹配规则：查询的所有字符必须按顺序出现在目标文本中（不要求连续）
- 排序规则：按缺口数（gap count）排序，缺口越少 = 越连续 = 相关度越高
- 匹配范围：标题 > 作者/期刊/标签/DOI/摘要
- 标题匹配的结果优先显示，其他匹配结果在后
- 触发方式：前端每 500ms 防抖自动调用
- 分页支持：默认每页 20 条，最大 100 条
- 筛选支持：年份范围、来源、期刊

### 3.6.2 语义搜索

- 将查询通过 kalm-emb-12b 编码为 3840 维向量
- 通过 PostgreSQL + pgvector 进行余弦相似度搜索
- 结果与 SQLite 文献表交叉引用
- 返回相似度最高的前 N 条结果（默认 20 条）

## 3.7 文献 HTML 转换流水线

345/355 篇文献已转换为自包含 HTML：

- **工具**：pdf2htmlEX Docker（`--embed-css 1 --embed-font 1`）
- **输出目录**：`archive/_unsorted/Library/01_curated/html/{paper_id}.html`
- **特性**：CSS/字体内嵌，无外部依赖，浏览器直接查看
- **访问地址**：`/papers/{paper_id}.html`
- **并发**：支持 32 并发 worker，支持断点续传（`--resume`）
- **未转换**：10 篇文献因 PDF 文件缺失未转换

运行命令：
```bash
uv run python scripts/convert_papers_to_html.py --resume --workers 32
```

## 3.8 语义检索与嵌入流水线

### 3.8.1 基础设施

| 组件 | 详情 |
|------|------|
| PostgreSQL + pgvector 0.7.0 | 容器 `pg`，用户 `username`，数据库 `postgres`，端口 5432 |
| Embedding 模型 kalm-emb-12b | `174.1.21.3:8001/v1/embeddings`，3840 维 |
| LLM glm-4.5-air | `174.1.21.3:8000/v1/chat/completions` |
| PDF 提取 | crawl4ai `NaivePDFProcessorStrategy`（降级：PyMuPDF） |

### 3.8.2 嵌入脚本

| 脚本 | 描述 |
|------|------|
| `scripts/embed_all_papers.py` | 批量嵌入所有文献（支持 `--resume`） |
| `scripts/embed_new_paper.py` | 单篇文献嵌入 |
| `scripts/search_semantic.py` | CLI 语义搜索查询 |

## 3.9 系统容错设计

**全局异常捕获**：FastAPI 层面未处理异常返回统一错误响应，避免堆栈泄露。

**上传流水线容错**：文件上传通过 SHA256 哈希命名，自动去重。元数据提取失败不影响文件存储。后台嵌入任务失败不阻塞主流程。

**数据库容错**：SQLite WAL 模式支持并发读取，写操作串行化。`BEGIN IMMEDIATE` 事务确保写入一致性。

**crawl 并发控制**：每篇文献的 crawl 操作通过 `asyncio.Lock` 保护，防止并发重复提取。

**降级模式**：crawl4ai 提取失败时降级使用 PyMuPDF。

## 3.10 系统安全性设计

**XSS 防护**：前端所有用户输入值通过 `escapeHtml()` 转义，禁止 `innerHTML` 插入未转义内容。

**文件安全**：SHA256 哈希命名防止目录遍历攻击。文件路径严格校验。

**SQL 注入防护**：所有数据库查询使用参数化查询（`?` 占位符）。

**CORS**：`Access-Control-Allow-Origin: *`（内网使用，无认证需求）。

**管理端无认证**：管理端 API 无身份认证，依赖网络层访问控制（内网环境）。

---

# 4. 测试验证

## 4.1 测试用例

### 测试用例 T01：模糊搜索

| **步骤** | **说明** | **期望结果** |
|------|------|------|
| 1 | 在搜索框输入查询词（如 "dorzagliatin"） | 输入正常，500ms 后自动搜索 |
| 2 | 查看搜索结果 | 结果按相关度排序，显示标题、作者、年份 |
| 3 | 切换排序方式为"年份" | 结果按年份降序排列 |
| 4 | 应用年份筛选 | 仅显示指定年份范围内的结果 |
| 5 | 应用来源筛选 | 仅显示指定来源的文献 |
| 6 | 空查询 | 显示所有文献 |
| 7 | 无结果查询 | 显示"无结果"提示 |

### 测试用例 T02：文献详情面板

| **步骤** | **说明** | **期望结果** |
|------|------|------|
| 1 | 点击文献卡片标题 | 侧滑面板从右侧打开，显示完整元数据 |
| 2 | 调整面板宽度 | 拖动分隔条调整宽度，松开后保持 |
| 3 | 刷新页面 | 面板宽度保持不变 |
| 4 | 点击"相关文献" | 导航到相关文献卡片 |

### 测试用例 T03：文献 HTML 查看

| **步骤** | **说明** | **期望结果** |
|------|------|------|
| 1 | 查看有 HTML 版本的文献卡片 | 显示"View HTML"按钮 |
| 2 | 点击"View HTML"按钮 | 新标签页打开 HTML 版本文献 |
| 3 | 查看无 HTML 版本的文献卡片 | 不显示"View HTML"按钮 |

### 测试用例 T04：管理端上传

| **步骤** | **说明** | **期望结果** |
|------|------|------|
| 1 | 上传 PDF 文件 | 文件保存，文献记录入库 |
| 2 | 上传已存在的 PDF（SHA256 相同） | 重复检测提示已存在 |
| 3 | 上传并提取元数据 | 返回提取结果供审核，确认后入库 |
| 4 | 编辑文献元数据 | 更新成功，页面显示最新数据 |
| 5 | 删除文献 | 文献和 PDF 同时删除 |

### 测试用例 T05：双语切换

| **步骤** | **说明** | **期望结果** |
|------|------|------|
| 1 | 点击语言切换按钮 | 界面语言切换为中文/英文 |
| 2 | 刷新页面 | 语言偏好保持不变 |

---

# 5. 验收交付

## 5.1 交付物清单

### 5.1.1 文档

| **编号** | **名称** | **交付形式** |
|------|------|------|
| 1 | 开发需求说明书 | 本文档 |
| 2 | README.md | 项目主文档 |
| 3 | CLAUDE.md | 开发规范与架构文档 |
| 4 | docs/search-api.md | 搜索 API 文档 |
| 5 | EMBED_GUIDE.md | 内嵌预览集成指南 |

### 5.1.2 程序

| **组件** | **说明** |
|------|------|
| backend.py | FastAPI 后端（Uvicorn） |
| server.mjs | Bun 前端开发服务器 |
| src/js/* | 前端 JavaScript 模块 |
| src/css/* | 前端 CSS 样式 |
| index.html / admin.html / embed.html | HTML 入口文件 |
| db.py | SQLite 数据库辅助模块 |
| scripts/* | Python 工具脚本 |

## 5.2 验收标准

| **测试项** | **标准** |
|------|------|
| **功能完整性** | 所有需求已实现，核心流程无阻断 |
| **文档完整性** | CLAUDE.md、API 文档、部署指南已交付 |
| **安全性** | XSS 防护生效，参数化查询防注入，SHA256 命名防遍历 |
| **性能指标** | 搜索响应 < 1s，页面加载 < 2s，初始加载 < 735KB |
| **数据一致性** | 文献元数据准确，JSON 字段正确序列化/反序列化 |

---

# 6. 后续扩展工作

- 全文 PDF 内容搜索（当前仅搜索元数据字段）
- 文献引用关系图可视化
- 阅读列表与收藏夹功能
- 用户注解与高亮标注
- 文献阅读统计与分析
- 与 Zotero/Mendeley 等文献管理工具集成
- 管理员身份认证与权限控制
- 文献上传自动分类与标签生成
- 迁移到 PostgreSQL 以支持更高并发

---

# 7. 附录

## 7.1 版本历史

| **版本** | **修订者** | **变更内容** | **生效日期** |
|------|------|------|------|
| **1.0** | AI Assistant | 初始版本，基于 paper-lib 实际代码库编写 | 2026-06-11 |

## 7.2 快速命令参考

```bash
# 启动前后端（开发环境）
./start.sh

# 停止
./stop.sh

# 后端（前台）
uv run uvicorn backend:app --host 0.0.0.0 --port 9000

# 前端（前台，HMR）
bun run --hot server.mjs

# PM2（生产环境，自动重启）
pm2 start ecosystem.config.cjs
pm2 restart all

# PDF → HTML 转换
uv run python scripts/convert_papers_to_html.py --resume --workers 32

# 批量嵌入
uv run python scripts/embed_all_papers.py --resume

# 单篇嵌入
uv run python scripts/embed_new_paper.py <paper_id>

# 语义搜索 CLI
uv run python scripts/search_semantic.py '<embedding_json>' 20
```

## 7.3 生产目录结构

```
paper-lib/
├── index.html              # 主站入口
├── admin.html              # 管理后台入口
├── embed.html              # 内嵌预览页面
├── papers.db               # SQLite 数据库
├── backend.py              # FastAPI 后端
├── db.py                   # SQLite 辅助模块
├── server.mjs              # Bun 开发服务器
├── ecosystem.config.cjs    # PM2 进程配置
├── start.sh / stop.sh      # 启停脚本
├── src/
│   ├── css/                # 样式文件
│   └── js/                 # JavaScript 模块
├── archive/
│   └── _unsorted/Library/
│       └── 01_curated/
│           ├── original/   # PDF 文件（SHA256 命名）
│           └── html/       # 转换后的 HTML 文件
├── scripts/                # Python 工具脚本
├── Documentation/          # 项目文档
└── docs/                   # API 文档
```

---

**文档结束**