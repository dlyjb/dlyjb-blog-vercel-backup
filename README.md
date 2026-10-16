# dlyjb 的博客 · Vercel 备份站

「dlyjb 的博客」主站（https://dgy.qzz.io/）的静态备份镜像。

- **内容源头：** Notion 内容库（与主站同一个库，父页面 `3f8e7eff-cf45-81b4-b37d-e6b930e7f48b`）。
  Notion 是唯一的 source of truth；本仓库不存文章正文的另一个副本，只存
  `generate_static.py` 生成的 `dist/` 静态文件。
- **渲染：** `generate_static.py` 沿用主站 Cloudflare Worker（`blog_proxy.js`）
  的解析与渲染规则：同样的「文章索引」表解析（扫描全部表、按页面 ID 去重）、
  同样的正文块渲染（标题/段落/引用/代码/callout/图片/列表）、同样的 CSS
  （深海军蓝 `#141c2e` + 金色 `#e8a020`）、同样的文章 URL 格式
  `/YYYY/MM/DD/<页面ID去横线>/`。首页是同样的三栏布局（左分类 / 中文章列表 /
  右日期归档）。
- **静态化差异：** Vercel 上没有服务端过滤，所以首页的分类 / 月份筛选由
  客户端 JS 实现：文章卡片带 `data-category` / `data-date` 属性，JS 读取
  `?cat=` / `?month=` 参数过滤并高亮侧栏。文章页、RSS 与主站一致。
- **SEO：** 备份站所有页面带 `noindex, nofollow`，避免与主站重复收录；
  正式地址以主站 `dgy.qzz.io` 为准。

## 重新生成

```bash
python3 generate_static.py
```

不需要任何 API Key / Token。脚本用 Notion 公开的 `loadPageChunk`
接口（与 Worker 相同）拉取内容，输出到 `dist/`：

- `dist/index.html` — 首页
- `dist/<YYYY>/<MM>/<DD>/<32hex>/index.html` — 每篇文章
- `dist/feed.xml` — RSS（最新 10 篇，全文）
- `dist/404.html` — 找不到文章时的提示页

## 自动更新

`.github/workflows/build.yml`：

- 每次 push 到 `main` 时重新生成并提交 `dist/` 的变化；
- 每天 22:45 UTC（北京时间次日 06:45，主站 06:30 发布之后）定时重新生成；
- 也可手动 `workflow_dispatch` 触发。

工作流不需要任何 secret。

## Vercel 部署

**不要设置构建命令。** `dist/` 已提交进仓库，Vercel 直接原样 serving 即可：

- Framework Preset: **None**（或 Other / Static）
- Build Command: （留空）
- Output Directory: `dist`
- Root Directory: 仓库根目录
- Install Command: （留空）

如果设置了构建命令，Vercel 会在部署时重新跑生成脚本，一旦 Notion 接口
抖动就会导致部署失败；提交 `dist/` + 无构建步骤是最稳的备份站做法。
