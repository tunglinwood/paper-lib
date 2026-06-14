# Project Overview — Paper Library

## 应用场景简述

**Paper Library** 是一个面向华领医药（Hua Medicine）研究团队的学术文献管理知识库，专注于 Dorzagliatin（多格列艾汀）、Glucokinase（葡萄糖激酶）及 2 型糖尿病领域的研究文献管理。

核心应用场景：
- 研究团队**集中管理 355+ 篇核心文献**，支持全文模糊检索、语义检索、多维度筛选（年份/来源/主题标签）
- 支持**AI 驱动的自然语言检索**（Page Agent），用户可通过自然语言指令快速定位目标文献
- 管理员可在线**上传、编辑、审核、删除**文献，支持 PDF 自动提取全文与元数据（crawl4ai + LLM 流水线）
- 支持**文献详情页预览**（可伸缩滑动面板）及**内嵌式预览**（`embed.html`，可供第三方 iframe 嵌入）
- 支持**双语界面**（英文/中文），适应国际化团队需求

---

## 合作开发团队

| 角色 | 说明 |
|------|------|
| 华领医药研究团队 | 需求提出方、内容审核与文献 curated |
| Claude Code AI 开发 | 全栈开发（FastAPI 后端 + 原生 HTML/JS/CSS 前端） |
| 技术栈 | FastAPI / Uvicorn, SQLite + pgvector + PostgreSQL, Bun dev server, crawl4ai, kalm-emb-12b 嵌入模型, GLM-4.5-air LLM |

---

## 当前开发进展简述

全文模糊检索 API 与语义检索 API（基于 pgvector 3840 维嵌入）均已上线，主站与管理后台均接入 REST API 实现 500ms 自动搜索；文献管理后台支持上传、批量删除、元数据编辑与重复检测；PDF 元数据提取通过 crawl4ai + LLM 流水线自动完成；AI 自然语言检索（Page Agent）、双语界面（EN/ZH）、可伸缩文献详情面板及内嵌预览（`embed.html`）均已就绪；后端通过 PM2 持久化部署，跨会话持续运行。当前唯一待实施项为将文献编辑从独立弹窗整合至详情面板内联编辑。**关键指标**：355 篇文献，覆盖 9 个来源、年份 1974–2026，PDF 总量约 1.5 GB，初始加载体积优化 86%（5.5MB → 735KB）。


---

## 成果展示

### 服务地址

| 服务 | 地址 | 端口 |
|------|------|------|
| 主站 | `http://<server-ip>:5173/` | 5173 |
| 管理后台 | `http://<server-ip>:5173/admin` | 5173 |
| 内嵌预览 | `http://<server-ip>:5173/embed.html?paper_id=<id>` | 5173 |
| 搜索 API | `http://<server-ip>:5173/api/search?q=DAWN` | 5173 |
| 后端直接访问 | `http://<server-ip>:9000/` | 9000 |

### 文档

- `CLAUDE.md` — 完整项目文档（架构、API、数据模型、开发命令）
- `docs/search-api.md` — 搜索 API 文档
