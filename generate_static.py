#!/usr/bin/env python3
"""Generate the static Vercel backup mirror of 「dlyjb 的博客」.

Source of truth: the same Notion content library as the main site
(parent page 3f8e7eff-cf45-81b4-b37d-e6b930e7f48b, "文章索引" table).
Reads Notion's public loadPageChunk API with NO auth / NO secrets,
exactly like the Cloudflare Worker (blog_proxy.js) does.

Output: dist/ with index.html, one index.html per article at
<YYYY>/<MM>/<DD>/<32hex>/, feed.xml and 404.html.

Usage:
  python3 generate_static.py [--out dist]

No API keys / tokens are needed. Do not add any.
"""
import argparse
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover - fallback to stdlib
    requests = None
    import urllib.request

PARENT_PAGE_ID = "3f8e7eff-cf45-81b4-b37d-e6b930e7f48b"
API_URL = "https://dlyjb.notion.site/api/v3/loadPageChunk"
WEEK = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
SITE_URL = "https://dgy.qzz.io"
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Filled in at build time from the Worker's baseCss() (verbatim) — see _BASE_CSS.
BASE_CSS = ":root{--gold:#e8a020;--ink:#1b2430;--mut:#5b6472;--line:#e9edf3;--bg:#f4f6fa;--link:#2456a6}*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;color:var(--ink);background:var(--bg);line-height:1.8;font-size:16px}.hero{background:linear-gradient(120deg,#2b3f66 0%,#141c2e 60%,#0b101d 100%);color:#fff;padding:44px 20px 36px;text-align:center}.hero h1{font-size:34px;font-weight:800;letter-spacing:3px;margin-bottom:8px}.hero h1 a{color:#fff;text-decoration:none}.hero .sub{color:#9fb3d8;font-size:14px;letter-spacing:1px}.hero .meta{display:inline-block;margin-top:14px;background:rgba(232,160,32,.15);border:1px solid rgba(232,160,32,.45);color:#f3c96b;padding:5px 18px;border-radius:20px;font-size:13px}.layout{display:flex;max-width:1180px;margin:0 auto;gap:24px;padding:26px 18px 30px;align-items:flex-start}.side{width:230px;flex:0 0 230px;position:sticky;top:20px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 14px;max-height:calc(100vh - 40px);overflow:auto;box-shadow:0 2px 10px rgba(20,30,50,.05)}.side-title{font-weight:800;font-size:15px;margin-bottom:10px}.side ul{list-style:none}.side li a{display:block;font-size:14px;color:#33415c;text-decoration:none;padding:6px 10px;border-radius:6px}.side li a:hover,.side li a.on{background:#eef4ff;color:var(--link)}.side li a .n{float:right;color:#98a2b3;font-size:12px}.side details{margin-bottom:6px}.side summary{cursor:pointer;font-weight:700;font-size:14px;padding:6px 8px;border-radius:6px;list-style:none}.side summary::-webkit-details-marker{display:none}.side summary:before{content:'▸ ';color:var(--mut)}.side details[open] summary:before{content:'▾ '}.side summary:hover{background:#f0f4fa}.side details ul{margin:4px 0 8px}.side details li a{padding-left:22px}main{flex:1;min-width:0;max-width:720px}@media(max-width:900px){.layout{flex-direction:column}.side{width:100%;flex:none;position:static;max-height:none}}.post{background:#fff;border:1px solid var(--line);border-radius:14px;padding:22px 24px;margin-bottom:18px;box-shadow:0 2px 12px rgba(20,30,50,.06)}.post h2{font-size:20px;line-height:1.5;margin-bottom:8px}.post h2 a{color:var(--ink);text-decoration:none}.post h2 a:hover{color:var(--link)}.pmeta{display:flex;gap:10px;align-items:center;font-size:13px;color:var(--mut);margin-bottom:6px}.cat{display:inline-block;font-size:12px;font-weight:700;color:#fff;background:#33415c;padding:2px 10px;border-radius:6px}.cat.vpn{background:#7c3aed}a{color:var(--link)}.article{background:#fff;border:1px solid var(--line);border-radius:14px;padding:30px 34px;box-shadow:0 2px 12px rgba(20,30,50,.06)}.article h1{font-size:28px;line-height:1.4;margin-bottom:12px}.article h2{font-size:21px;margin:28px 0 12px;padding-bottom:8px;border-bottom:2px solid var(--line)}.article h3{font-size:18px;margin:24px 0 10px}.article h4{font-size:16px;margin:20px 0 8px}.article p{margin:12px 0;color:#2a3442}.article ul,.article ol{margin:12px 0 12px 24px;color:#2a3442}.article li{margin:6px 0}.article blockquote{border-left:4px solid var(--gold);background:#fffaf0;padding:10px 16px;margin:16px 0;border-radius:0 8px 8px 0;color:#5b4a1e}.article pre{background:#141c2e;color:#dbe6fa;padding:16px 18px;border-radius:10px;overflow:auto;margin:16px 0;font-size:14px}.article code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}.article p code{background:#eef2f7;padding:2px 6px;border-radius:4px;font-size:14px;color:#b03a2e}.article img{max-width:100%;border-radius:10px}.article hr{border:none;border-top:1px solid var(--line);margin:24px 0}.callout{background:#f6f9ff;border:1px solid #dbe7fb;border-radius:10px;padding:12px 16px;margin:16px 0}.crumb{font-size:14px;color:var(--mut);margin-bottom:16px}.crumb a{color:var(--link);text-decoration:none}.empty{background:#fff;border:1px dashed var(--line);border-radius:12px;padding:40px;text-align:center;color:var(--mut)}footer{text-align:center;color:#98a2b3;font-size:13px;padding:26px 16px 40px}@media(max-width:600px){.hero h1{font-size:26px}.article{padding:22px 20px}.article h1{font-size:23px}}"


def esc(s):
    return html.escape(str(s), quote=True)


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    if requests is not None:
        r = requests.post(url, data=data,
                          headers={"Content-Type": "application/json"},
                          timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"notion api {r.status_code}")
        return r.json()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_blocks(page_id):
    """Port of the Worker's fetchBlocks(): loop loadPageChunk up to 30 chunks."""
    blocks = {}
    cursor = {"stack": []}
    chunk_number = 0
    while chunk_number < 30:
        data = post_json(API_URL, {
            "pageId": page_id, "limit": 50, "cursor": cursor,
            "chunkNumber": chunk_number, "verticalColumns": False,
        })
        record_map = (data.get("recordMap") or {}).get("block") or {}
        for _bid, b in record_map.items():
            v = ((b or {}).get("value") or {}).get("value")
            if v and v.get("alive") is not False:
                blocks[_bid] = v
        cursor = data.get("cursor")
        chunk_number += 1
        if not cursor or not cursor.get("stack"):
            break
    return blocks


def plain_text(block):
    out = ""
    for seg in ((block.get("properties") or {}).get("title") or []):
        out += seg[0] if isinstance(seg, list) else str(seg)
    return out


def rich_text(prop):
    out = ""
    for seg in (prop or []):
        if not isinstance(seg, list) or not seg:
            continue
        t = esc(seg[0]).replace("\n", "<br>")
        for fmt in (seg[1] if len(seg) > 1 else []) or []:
            if not isinstance(fmt, list) or not fmt:
                continue
            f, val = fmt[0], (fmt[1] if len(fmt) > 1 else None)
            if f == "b":
                t = "<strong>" + t + "</strong>"
            elif f == "i":
                t = "<em>" + t + "</em>"
            elif f == "s":
                t = "<s>" + t + "</s>"
            elif f == "c":
                t = "<code>" + t + "</code>"
            elif f == "_":
                t = "<u>" + t + "</u>"
            elif f == "a":
                t = '<a href="' + esc(val) + '" target="_blank" rel="noopener">' + t + "</a>"
        out += t
    return out


def row_cells(row):
    cells = []
    props = row.get("properties") or {}
    for key in sorted(props.keys()):
        segs = props[key]
        if not isinstance(segs, list):
            continue
        txt = ""
        for seg in segs:
            if isinstance(seg, list):
                txt += str(seg[0])
            elif isinstance(seg, str):
                txt += seg
        cells.append(txt)
    return cells


def parse_index(blocks, parent_page):
    """Port of the Worker's parseIndex(): scan ALL tables, dedupe by pageId."""
    articles = []
    seen = set()
    table_ids = []
    for bid in (parent_page or {}).get("content") or []:
        v = blocks.get(bid)
        if v and v.get("type") == "table":
            table_ids.append(bid)
    if not table_ids:
        for bid, v in blocks.items():
            if v.get("type") == "table":
                table_ids.append(bid)
    for tid in table_ids:
        table = blocks.get(tid) or {}
        for row_id in table.get("content") or []:
            row = blocks.get(row_id)
            if not row or row.get("type") != "table_row":
                continue
            date = cat = title = pid = ""
            for cell in row_cells(row):
                t = cell.strip()
                if not t:
                    continue
                if DATE_RE.match(t):
                    date = t
                elif UUID_RE.match(t):
                    pid = t
                elif t in ("电脑网络", "VPN"):
                    cat = t
                elif len(t) > len(title):
                    title = t
            if not date or not pid or not title:
                continue  # skip header / incomplete rows
            if pid in seen:
                continue
            seen.add(pid)
            articles.append({"date": date, "category": cat or "未分类",
                             "title": title, "pageId": pid})
    return articles


def fmt_date(ds):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(ds))
    if not m:
        return {"md": ds, "full": ds, "week": ""}
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    import datetime as _dt
    weekday = _dt.date(y, mo, d).weekday()  # Mon=0
    week = WEEK[(weekday + 1) % 7]
    return {"md": f"{mo}月{d}日", "full": f"{y}年{mo}月{d}日", "week": week}


def article_url(a):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(a["date"]))
    dp = f"{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else "2026/10/13"
    return "/" + dp + "/" + a["pageId"].replace("-", "") + "/"


def render_body(blocks, page):
    """Port of the Worker's renderBody()."""
    parts = []
    list_open = None  # 'ul' | 'ol'

    def close_list():
        nonlocal list_open
        if list_open:
            parts.append("</ul>" if list_open == "ul" else "</ol>")
            list_open = None

    for bid in (page or {}).get("content") or []:
        v = blocks.get(bid)
        if not v:
            continue
        t = v.get("type")
        rich = rich_text((v.get("properties") or {}).get("title"))
        if t in ("bulleted_list", "numbered_list"):
            want = "ul" if t == "bulleted_list" else "ol"
            if list_open != want:
                close_list()
                parts.append("<ul>" if want == "ul" else "<ol>")
                list_open = want
            parts.append("<li>" + rich + "</li>")
        else:
            close_list()
            if t == "header":
                parts.append("<h2>" + rich + "</h2>")
            elif t == "sub_header":
                parts.append("<h3>" + rich + "</h3>")
            elif t == "sub_sub_header":
                parts.append("<h4>" + rich + "</h4>")
            elif t == "text":
                if plain_text(v).strip():
                    parts.append("<p>" + rich + "</p>")
            elif t == "quote":
                parts.append("<blockquote>" + rich + "</blockquote>")
            elif t == "code":
                parts.append("<pre><code>" + esc(plain_text(v)) + "</code></pre>")
            elif t == "callout":
                parts.append('<div class="callout">' + rich + "</div>")
            elif t == "divider":
                parts.append("<hr>")
            elif t == "image":
                p = v.get("properties") or {}
                src = ""
                if p.get("source") and p["source"][0]:
                    src = p["source"][0][0]
                elif (v.get("format") or {}).get("display_source"):
                    src = v["format"]["display_source"]
                if src:
                    parts.append('<p><img src="' + esc(src) +
                                 '" alt="" loading="lazy"></p>')
    close_list()
    return "".join(parts)


def strip_tags(html_text):
    s = re.sub(r"<[^>]*>", " ", str(html_text))
    s = (s.replace("&quot;", '"').replace("&amp;", "&")
         .replace("&lt;", "<").replace("&gt;", ">"))
    return re.sub(r"\s+", " ", s).strip()


def cdata(s):
    return "<![CDATA[" + str(s).replace("]]>", "]]]]><![CDATA[>") + "]]>"


def rss_feed(articles, bodies):
    """Same shape as the Worker's rssFeed(): latest 10, full body in content:encoded."""
    items = []
    for a in articles[:10]:
        body = bodies.get(a["pageId"], "")
        pub = datetime.strptime(a["date"] + " 06:30:00+08:00",
                                "%Y-%m-%d %H:%M:%S%z").astimezone(
                                    timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        desc = strip_tags(body)[:200]
        items.append(
            "  <item>\n"
            f"    <title>{cdata(a['title'])}</title>\n"
            f"    <link>{SITE_URL}{article_url(a)}</link>\n"
            f"    <guid isPermaLink=\"false\">dgy-{a['pageId'].replace('-', '')}</guid>\n"
            f"    <pubDate>{pub}</pubDate>\n"
            "    <dc:creator>admin</dc:creator>\n"
            f"    <category>{cdata(a['category'])}</category>\n"
            f"    <description>{cdata(desc)}</description>\n"
            f"    <content:encoded>{cdata(body)}</content:encoded>\n"
            "  </item>")
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:atom="http://www.w3.org/2005/Atom">\n'
            "<channel>\n"
            f"  <title>{cdata('dlyjb 的博客')}</title>\n"
            f"  <link>{SITE_URL}/</link>\n"
            f"  <description>{cdata('电脑网络与 VPN 技术科普 · 每日更新')}</description>\n"
            "  <language>zh-CN</language>\n"
            f"  <lastBuildDate>{now}</lastBuildDate>\n"
            f'  <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml" />\n'
            + "\n".join(items) + "\n</channel>\n</rss>")


# ---------- page templates (same layout as the Worker) ----------

FILTER_JS = """
<script>
(function(){
  var params = new URLSearchParams(location.search);
  var cat = params.get('cat') || '';
  var month = params.get('month') || '';
  if (!cat && !month) return;
  var cards = document.querySelectorAll('article.post');
  var shown = 0;
  cards.forEach(function (c) {
    var ok = (!cat || c.dataset.category === cat) &&
             (!month || (c.dataset.date || '').indexOf(month) === 0);
    c.style.display = ok ? '' : 'none';
    if (ok) shown++;
  });
  var empty = document.getElementById('filter-empty');
  if (empty) empty.style.display = shown ? 'none' : '';
  var meta = document.getElementById('hero-meta');
  if (meta) {
    var label = cat || (month ? month.replace('-', '年') + '月' : '');
    if (label) meta.textContent = label;
  }
  if (cat || month) {
    var t = 'dlyjb 的博客 · ' + (cat || (month ? month.replace('-', '年') + '月' : ''));
    document.title = t;
  }
  document.querySelectorAll('.side a').forEach(function (a) {
    try {
      var u = new URL(a.getAttribute('href'), location.origin);
      var p = new URLSearchParams(u.search);
      var on = (cat && p.get('cat') === cat) || (month && p.get('month') === month);
      if (on) a.classList.add('on');
    } catch (e) {}
  });
})();
</script>
"""


def hero_html(sub):
    return ('<header class="hero"><h1><a href="/">dlyjb 的博客</a></h1>'
            '<div class="sub">电脑网络与 VPN 技术科普 · 每日更新</div>'
            + (f'<div class="meta" id="hero-meta">{esc(sub)}</div>' if sub else "")
            + "</header>")


def sidebar_cats(articles):
    counts, order = {}, []
    for a in articles:
        c = a["category"] or "未分类"
        if c not in counts:
            counts[c] = 0
            order.append(c)
        counts[c] += 1
    h = '<aside class="side"><div class="side-title">📁 分类</div><ul>'
    h += (f'<li><a href="/">全部文章<span class="n">{len(articles)}</span></a></li>')
    for c in order:
        import urllib.parse as _up
        h += (f'<li><a href="/?cat={_up.quote(c)}">{esc(c)}'
              f'<span class="n">{counts[c]}</span></a></li>')
    return h + "</ul></aside>"


def sidebar_dates(articles):
    groups, order = {}, []
    for a in articles:
        m = re.match(r"(\d{4})-(\d{2})", str(a["date"]))
        key = f"{m.group(1)}-{m.group(2)}" if m else "其他"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(a)
    h = '<aside class="side"><div class="side-title">📅 按日期浏览</div>'
    for g, key in enumerate(order):
        m = re.match(r"(\d{4})-(\d{2})", key)
        label = f"{int(m.group(1))}年{int(m.group(2))}月" if m else key
        h += (f"<details{' open' if g == 0 else ''}><summary>{esc(label)} "
              f'<span style="color:#98a2b3;font-weight:400">({len(groups[key])})</span></summary><ul>')
        for a in groups[key]:
            fd = fmt_date(a["date"])
            h += (f'<li><a href="/?month={esc(key)}">{esc(fd["md"])} {esc(fd["week"])}</a></li>')
        h += "</ul></details>"
    return h + "</aside>"


def page_head(title):
    # noindex: this is a backup mirror; the canonical site is dgy.qzz.io.
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n"
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<meta name="robots" content="noindex, nofollow">\n'
            f"<title>{esc(title)}</title>\n<style>\n{BASE_CSS}\n</style>\n</head>\n<body>\n")


def page_footer():
    return ("<footer>dlyjb 的博客 · 备份站 · 内容同步自 Notion · 与主站 dgy.qzz.io 同步</footer>\n"
            "</body>\n</html>")


def homepage_html(articles):
    h = page_head("dlyjb 的博客") + hero_html(f"共 {len(articles)} 篇文章")
    h += '\n<div class="layout">\n' + sidebar_cats(articles) + "<main>\n"
    h += '<div class="empty" id="filter-empty" style="display:none">这个筛选条件下还没有文章</div>'
    for a in articles:
        fd = fmt_date(a["date"])
        cls = "cat vpn" if a["category"] == "VPN" else "cat"
        h += (f'<article class="post" data-category="{esc(a["category"])}" '
              f'data-date="{esc(a["date"])}"><div class="pmeta"><span>'
              f'{esc(fd["full"])} {esc(fd["week"])}</span>'
              f'<span class="{cls}">{esc(a["category"])}</span></div>'
              f'<h2><a href="{article_url(a)}">{esc(a["title"])}</a></h2></article>\n')
    h += "</main>\n" + sidebar_dates(articles) + "\n</div>\n"
    h += FILTER_JS + page_footer()
    return h


def article_html(a, body_html, articles):
    import urllib.parse as _up
    fd = fmt_date(a["date"])
    cls = "cat vpn" if a["category"] == "VPN" else "cat"
    h = page_head(f"{a['title']} · dlyjb 的博客") + hero_html("")
    h += '\n<div class="layout">\n' + sidebar_cats(articles) + "<main>\n"
    h += (f'<div class="crumb"><a href="/">首页</a> / '
          f'<a href="/?cat={_up.quote(a["category"])}">{esc(a["category"])}</a> / 正文</div>\n')
    h += (f'<article class="article"><h1>{esc(a["title"])}</h1>'
          f'<div class="pmeta"><span>{esc(fd["full"])} {esc(fd["week"])}</span>'
          f'<span class="{cls}">{esc(a["category"])}</span></div>\n'
          + body_html + "</article>\n")
    h += "</main>\n" + sidebar_dates(articles) + "\n</div>\n" + page_footer()
    return h


def not_found_html():
    h = page_head("文章不存在 · dlyjb 的博客") + hero_html("")
    h += ('\n<div class="layout"><main style="margin:0 auto">'
          '<div class="empty"><h2 style="margin-bottom:8px">文章不存在</h2>'
          '<p>该链接对应的文章已不在备份站中。</p>'
          '<p style="margin-top:12px"><a href="/">回首页</a> · '
          '<a href="https://dgy.qzz.io/">去主站 dgy.qzz.io</a></p></div></main></div>\n')
    h += page_footer()
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist", help="output directory (default: dist)")
    args = ap.parse_args()
    out = args.out
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = out if os.path.isabs(out) else os.path.join(script_dir, out)

    print("fetching parent page index ...", flush=True)
    blocks = fetch_blocks(PARENT_PAGE_ID)
    parent_page = blocks.get(PARENT_PAGE_ID) or blocks.get(PARENT_PAGE_ID.replace("-", ""))
    articles = parse_index(blocks, parent_page)
    articles.sort(key=lambda x: x["date"], reverse=True)
    print(f"index: {len(articles)} articles", flush=True)

    bodies = {}
    for i, a in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {a['date']} {a['title']}", flush=True)
        ab = fetch_blocks(a["pageId"])
        apage = ab.get(a["pageId"]) or ab.get(a["pageId"].replace("-", ""))
        bodies[a["pageId"]] = render_body(ab, apage)

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(homepage_html(articles))
    for a in articles:
        rel = article_url(a).strip("/")
        d = os.path.join(out_dir, rel)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(article_html(a, bodies[a["pageId"]], articles))
    with open(os.path.join(out_dir, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(rss_feed(articles, bodies))
    with open(os.path.join(out_dir, "404.html"), "w", encoding="utf-8") as f:
        f.write(not_found_html())

    summary = {"articles": len(articles),
               "titles": [a["title"] for a in articles],
               "out": out_dir}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
