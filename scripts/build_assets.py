#!/usr/bin/env python3
"""Generate the animated light/dark SVG assets used by the profile README.

Setup (once):  cd scripts && npm install && pip install fonttools brotli
Run:           python3 scripts/build_assets.py

Every SVG embeds its own subset of the Inter font, so text renders the same on
every device. All motion is CSS, and every animation stops for viewers who set
prefers-reduced-motion. Base styles hold the final state, so a frozen frame
always shows complete content.
"""
import base64
import html
import io
import os
import re

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
NODE = os.path.join(ROOT, "scripts", "node_modules")
FONT_FILES = {
    500: os.path.join(NODE, "@fontsource/inter/files/inter-latin-500-normal.woff2"),
    700: os.path.join(NODE, "@fontsource/inter/files/inter-latin-700-normal.woff2"),
    800: os.path.join(NODE, "@fontsource/inter/files/inter-latin-800-normal.woff2"),
}
ICONS = os.path.join(NODE, "simple-icons/icons")
W = 1200

# ---------------------------------------------------------------- themes ----
THEMES = {
    "dark": dict(
        bg="#0A0E1A", bg2="#0F1526", text="#E8EEF8", text2="#A9B8D3", muted="#8A9AB6",
        border="#FFFFFF", border_op=0.10, glass_top=0.07, glass_bot=0.02,
        a1="#22D3EE", a2="#6366F1", a3="#A78BFA", grid_op=0.07, blob_op=0.55,
        tint_op=0.14, chip_bg="#FFFFFF", chip_op=0.06,
    ),
    "light": dict(
        bg="#F7F9FD", bg2="#EEF2FA", text="#0B1220", text2="#334155", muted="#5B6B84",
        border="#0B1220", border_op=0.10, glass_top=0.95, glass_bot=0.75,
        a1="#0891B2", a2="#4F46E5", a3="#7C3AED", grid_op=0.06, blob_op=0.28,
        tint_op=0.10, chip_bg="#0B1220", chip_op=0.05,
    ),
}

# ------------------------------------------------------------ font tools ----
_fonts = {w: TTFont(p) for w, p in FONT_FILES.items()}


def text_width(s, size, weight):
    f = _fonts[weight]
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    total = 0
    for ch in s:
        g = cmap.get(ord(ch))
        total += hmtx[g][0] if g else upm * 0.5
    return total * size / upm


def wrap(s, size, weight, max_w):
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if text_width(trial, size, weight) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def font_face(svg_body):
    """Subset each Inter weight to exactly the characters each SVG uses."""
    used = {}
    for m in re.finditer(r'<text[^>]*class="([^"]*)"[^>]*>(.*?)</text>', svg_body, re.S):
        weight = 800 if "w8" in m.group(1) else 700 if "w7" in m.group(1) else 500
        chars = html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))
        used.setdefault(weight, set()).update(chars)
    rules = []
    for weight, chars in sorted(used.items()):
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern"]
        sub = subset.Subsetter(opts)
        font = TTFont(FONT_FILES[weight])
        sub.populate(text="".join(chars) + " ")
        sub.subset(font)
        buf = io.BytesIO()
        font.flavor = "woff2"
        font.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        rules.append(
            f"@font-face{{font-family:'InterX';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
        )
    return "".join(rules)


# ---------------------------------------------------------------- helpers ---
def esc(s):
    return html.escape(s, quote=True)


def T(x, y, s, size, weight=500, fill="", anchor="start", extra="", cls=""):
    w = {500: "w5", 700: "w7", 800: "w8"}[weight]
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    f = f' fill="{fill}"' if fill else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{w} {cls}" font-size="{size}"'
            f'{a}{f} {extra}>{esc(s)}</text>')


BASE_CSS = """
text{font-family:'InterX',ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;font-kerning:none}
.w5{font-weight:500}.w7{font-weight:700}.w8{font-weight:800}
.fu{animation:fu .9s cubic-bezier(.2,.7,.2,1) both}
@keyframes fu{from{opacity:0;transform:translateY(14px)}}
.fi{animation:fi 1.1s ease both}
@keyframes fi{from{opacity:0}}
.pulse{animation:pulse 2.4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.ring{animation:ring 2.4s ease-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes ring{from{transform:scale(.6);opacity:.9}to{transform:scale(2.4);opacity:0}}
.spin{animation:spin 18s linear infinite;transform-box:view-box}
@keyframes spin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def svg(width, height, body, title, css=""):
    style = BASE_CSS + css
    raw = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">'
           f'<title>{esc(title)}</title>{body}</svg>')
    return raw.replace("<title>", f"<style>{font_face(raw)}{style}</style><title>", 1)


def glass(t, x, y, w, h, gid, r=20):
    """A frosted card: soft vertical gloss, hairline border, top highlight."""
    return (
        f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{t["chip_bg"] if t is THEMES["dark"] else "#FFFFFF"}" '
        f'stop-opacity="{t["glass_top"]}"/>'
        f'<stop offset="1" stop-color="{t["chip_bg"] if t is THEMES["dark"] else "#FFFFFF"}" '
        f'stop-opacity="{t["glass_bot"]}"/></linearGradient>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#{gid})" '
        f'stroke="{t["border"]}" stroke-opacity="{t["border_op"]}"/>'
        f'<path d="M{x + r} {y + 0.5}H{x + w - r}" stroke="#FFFFFF" '
        f'stroke-opacity="{0.18 if t is THEMES["dark"] else 0.9}"/>'
    )


def accent_grad(t, gid, x1="0", y1="0", x2="1", y2="0"):
    return (f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{t["a1"]}"/><stop offset="1" stop-color="{t["a2"]}"/>'
            f'</linearGradient>')


def write(name, theme, content):
    path = os.path.join(OUT, f"{name}-{theme}.svg")
    with open(path, "w") as fh:
        fh.write(content)
    return path


# ------------------------------------------------------------------ hero ----
def hero(t):
    H = 400
    css = """
.d1{animation:drift1 22s ease-in-out infinite alternate}
.d2{animation:drift2 26s ease-in-out infinite alternate}
.d3{animation:drift3 30s ease-in-out infinite alternate}
@keyframes drift1{to{transform:translate(120px,40px)}}
@keyframes drift2{to{transform:translate(-140px,-30px)}}
@keyframes drift3{to{transform:translate(80px,-50px)}}
.bar{animation:bar 1.2s cubic-bezier(.2,.7,.2,1) .7s both;transform-box:fill-box;transform-origin:left}
@keyframes bar{from{transform:scaleX(0)}}
.orb1{animation:spin 26s linear infinite;transform-origin:950px 205px}
.orb2{animation:spin 40s linear infinite reverse;transform-origin:950px 205px}
.orb3{animation:spin 16s linear infinite;transform-origin:950px 205px}
"""
    d = [
        "<defs>",
        f'<clipPath id="c"><rect width="{W}" height="{H}" rx="28"/></clipPath>',
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["bg"]}"/>'
        f'<stop offset="1" stop-color="{t["bg2"]}"/></linearGradient>',
    ]
    for i, c in enumerate([t["a1"], t["a2"], t["a3"]]):
        d.append(f'<radialGradient id="b{i}"><stop offset="0" stop-color="{c}" stop-opacity="{t["blob_op"]}"/>'
                 f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>')
    d += [
        f'<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">'
        f'<path d="M40 0H0V40" fill="none" stroke="{t["text"]}" stroke-opacity="{t["grid_op"]}"/></pattern>',
        '<radialGradient id="gm" cx=".35" cy=".45" r=".75"><stop offset="0" stop-color="#fff"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>',
        f'<mask id="m"><rect width="{W}" height="{H}" fill="url(#gm)"/></mask>',
        f'<linearGradient id="name" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["text"]}"/>'
        f'<stop offset="1" stop-color="{t["text2"]}"/></linearGradient>',
        accent_grad(t, "acc"),
        "</defs>",
        '<g clip-path="url(#c)">',
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
        '<g class="d1"><circle cx="220" cy="80" r="300" fill="url(#b0)"/></g>',
        '<g class="d2"><circle cx="1000" cy="360" r="320" fill="url(#b1)"/></g>',
        '<g class="d3"><circle cx="620" cy="-40" r="260" fill="url(#b2)"/></g>',
        f'<rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#m)"/>',
    ]
    # status pill
    label = "Building AI agents in production"
    pw = text_width(label, 15, 500) + 52
    d += [
        '<g class="fu" style="animation-delay:.05s">',
        f'<rect x="64" y="64" width="{pw:.0f}" height="34" rx="17" fill="{t["chip_bg"]}" '
        f'fill-opacity="{t["chip_op"]}" stroke="{t["border"]}" stroke-opacity="{t["border_op"]}"/>',
        f'<circle cx="84" cy="81" r="9" fill="{t["a1"]}" fill-opacity=".35" class="ring"/>',
        f'<circle cx="84" cy="81" r="4.5" fill="{t["a1"]}"/>',
        T(100, 86.5, label, 15, 500, t["text2"]),
        "</g>",
        f'<g class="fu" style="animation-delay:.2s">{T(60, 192, "Subhadeep Ghorai", 76, 800, "url(#name)", extra="letter-spacing=\'-2\'")}</g>',
        f'<g class="fu" style="animation-delay:.38s">'
        f'{T(64, 240, "Software Engineer  ·  AI Agents  ·  Real-time Systems", 26, 500, t["text2"])}</g>',
        f'<rect x="64" y="266" width="120" height="4" rx="2" fill="url(#acc)" class="bar"/>',
        f'<g class="fu" style="animation-delay:.55s">'
        f'{T(64, 314, "Newton School of Technology", 19, 700, t["text"])}'
        f'{T(64 + text_width("Newton School of Technology", 19, 700) + 12, 314, "— teaching System Design to 300+ engineers", 19, 500, t["muted"])}'
        f"</g>",
    ]
    # orbit graphic: an agent network quietly turning
    cx, cy = 950, 205
    d.append('<g class="fi" style="animation-delay:.4s">')
    for r, op in [(150, 0.16), (108, 0.22), (66, 0.30)]:
        d.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["text"]}" '
                 f'stroke-opacity="{op}" stroke-dasharray="{"3 7" if r == 150 else "none"}"/>')
    d.append(f'<g class="orb1"><circle cx="{cx + 150}" cy="{cy}" r="7" fill="{t["a1"]}"/>'
             f'<circle cx="{cx - 150}" cy="{cy}" r="4" fill="{t["text2"]}"/></g>')
    d.append(f'<g class="orb2"><circle cx="{cx}" cy="{cy - 108}" r="6" fill="{t["a2"]}"/>'
             f'<circle cx="{cx + 76}" cy="{cy + 76}" r="4" fill="{t["a3"]}"/></g>')
    d.append(f'<g class="orb3"><circle cx="{cx + 66}" cy="{cy}" r="5" fill="{t["a3"]}"/></g>')
    d.append(f'<circle cx="{cx}" cy="{cy}" r="34" fill="url(#acc)" fill-opacity=".18" class="ring"/>')
    d.append(f'<circle cx="{cx}" cy="{cy}" r="26" fill="url(#acc)"/>')
    d.append(f'<path d="M{cx - 9} {cy - 8}l-8 8 8 8M{cx + 9} {cy - 8}l8 8-8 8" fill="none" '
             f'stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    d.append("</g>")
    d.append(f'</g><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="28" fill="none" '
             f'stroke="{t["border"]}" stroke-opacity="{t["border_op"]}"/>')
    return svg(W, H, "".join(d), "Subhadeep Ghorai — Software Engineer, AI Agents, Real-time Systems", css)


# ------------------------------------------------------------ link pills ----
LINK_ICONS = {
    "globe": lambda c: (f'<circle cx="12" cy="12" r="9" fill="none" stroke="{c}" stroke-width="1.8"/>'
                        f'<path d="M3 12h18M12 3c2.8 3 2.8 15 0 18M12 3c-2.8 3-2.8 15 0 18" fill="none" '
                        f'stroke="{c}" stroke-width="1.8"/>'),
    "in": lambda c: (f'<rect x="3" y="3" width="18" height="18" rx="4" fill="none" stroke="{c}" stroke-width="1.8"/>'
                     f'<path d="M8 10v6M8 7.3v.2M12 16v-6M12 13c0-2 1.2-3 2.6-3S17 11 17 13v3" fill="none" '
                     f'stroke="{c}" stroke-width="1.8" stroke-linecap="round"/>'),
    "mail": lambda c: (f'<rect x="3" y="5.5" width="18" height="13" rx="3" fill="none" stroke="{c}" stroke-width="1.8"/>'
                       f'<path d="M4 7.5l8 6 8-6" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"/>'),
}


def pill(t, label, icon, primary=False):
    h = 52
    w = int(text_width(label, 17, 700) + 92)
    fg = "#FFFFFF" if primary else t["text"]
    css = """.sh{animation:sh 4.5s ease-in-out infinite}
@keyframes sh{0%,55%{transform:translateX(-120px)}85%,100%{transform:translateX(420px)}}"""
    d = ["<defs>", accent_grad(t, "acc"),
         '<linearGradient id="gl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
         '<stop offset=".5" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
         '</linearGradient>',
         f'<clipPath id="pc"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{h / 2 - 1}"/></clipPath></defs>']
    if primary:
        d.append(f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{h / 2 - 1}" fill="url(#acc)"/>')
        d.append('<g clip-path="url(#pc)"><rect class="sh" x="0" y="0" width="70" height="60" '
                 'fill="url(#gl)" transform="skewX(-20)"/></g>')
    else:
        d.append(f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{h / 2 - 1}" fill="{t["chip_bg"]}" '
                 f'fill-opacity="{t["chip_op"] + 0.02}" stroke="{t["border"]}" stroke-opacity="{t["border_op"] + 0.06}"/>')
    d.append(f'<g transform="translate(26 14)">{LINK_ICONS[icon](fg)}</g>')
    d.append(T(62, 32.5, label, 17, 700, fg))
    return svg(w, h, "".join(d), label, css)


# --------------------------------------------------------- section title ----
def section(t, idx, title):
    H = 84
    tw = text_width(title, 34, 800)
    lx = 64 + 46 + tw + 28
    css = f""".ln{{animation:ln 1.4s cubic-bezier(.2,.7,.2,1) .25s both;transform-box:fill-box;transform-origin:left}}
@keyframes ln{{from{{transform:scaleX(0)}}}}
.gd{{animation:gd 5s cubic-bezier(.45,0,.55,1) 1.4s infinite}}
@keyframes gd{{0%{{transform:translateX(0);opacity:0}}10%{{opacity:1}}90%{{opacity:1}}100%{{transform:translateX({W - lx - 8:.0f}px);opacity:0}}}}"""
    d = ["<defs>", accent_grad(t, "acc"),
         f'<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="{t["a1"]}" stop-opacity=".9"/>'
         f'<stop offset="1" stop-color="{t["a2"]}" stop-opacity="0"/></linearGradient></defs>',
         f'<g class="fu">{T(64, 55, idx, 18, 700, "url(#acc)")}{T(110, 57, title, 34, 800, t["text"], extra="letter-spacing=\'-0.5\'")}</g>',
         f'<rect class="ln" x="{lx:.0f}" y="44" width="{W - lx:.0f}" height="1.5" fill="url(#fade)"/>',
         f'<circle class="gd" cx="{lx:.0f}" cy="44.75" r="3" fill="{t["a1"]}"/>']
    return svg(W, H, "".join(d), f"{idx} {title}", css)


# --------------------------------------------------------- what I build -----
def icon_agent(t):
    return (f'<circle cx="32" cy="32" r="18" fill="none" stroke="{t["a1"]}" stroke-opacity=".35" stroke-dasharray="2 4"/>'
            f'<circle cx="32" cy="32" r="10" fill="{t["a1"]}" fill-opacity=".25" class="ring"/>'
            f'<circle cx="32" cy="32" r="7" fill="{t["a1"]}"/>'
            f'<g class="spin" style="animation-duration:7s;transform-origin:32px 32px">'
            f'<circle cx="50" cy="32" r="3.5" fill="{t["a2"]}"/><circle cx="23" cy="16.4" r="3" fill="{t["a3"]}"/>'
            f'<circle cx="23" cy="47.6" r="3" fill="{t["text2"]}"/></g>')


def icon_flow(t):
    s = (f'<rect x="8" y="22" width="14" height="20" rx="4" fill="none" stroke="{t["a1"]}" stroke-width="2"/>'
         f'<rect x="42" y="22" width="14" height="20" rx="4" fill="none" stroke="{t["a2"]}" stroke-width="2"/>'
         f'<path d="M22 32h20" stroke="{t["text"]}" stroke-opacity=".25" stroke-width="2"/>')
    for i in range(3):
        s += (f'<circle cx="22" cy="32" r="2.6" fill="{t["a1"]}" class="pk" '
              f'style="animation-delay:{i * 0.6:.1f}s"/>')
    return s


def icon_loop(t):
    return (f'<circle cx="32" cy="32" r="18" fill="none" stroke="{t["text"]}" stroke-opacity=".18" stroke-width="3"/>'
            f'<g class="spin" style="animation-duration:2.6s;transform-origin:32px 32px">'
            f'<circle cx="32" cy="32" r="18" fill="none" stroke="url(#acc)" stroke-width="3" '
            f'stroke-linecap="round" stroke-dasharray="30 84"/>'
            f'<circle cx="50" cy="32" r="3.5" fill="{t["a1"]}"/></g>'
            f'<circle cx="32" cy="32" r="4" fill="{t["a2"]}" class="pulse"/>')


BUILD = [
    ("AI-native engineering",
     "Claude Code as a collaborator, guided by encoded engineering rules. Shipped ADCMS to 642 users and SQL Heist City in 14 days.",
     icon_agent),
    ("Real-time systems",
     "React, TypeScript, Node.js, MongoDB, Redis and WebSockets, running in production for real users.",
     icon_flow),
    ("Developer tools",
     "Tools that make hard concepts visible, shaped by 2,500+ live teaching sessions.",
     icon_loop),
]


def build_cards(t):
    H, gap = 296, 24
    cw = (W - 2 * gap) / 3
    css = """.pk{animation:pk 1.8s linear infinite}
@keyframes pk{0%{transform:translateX(0);opacity:0}15%{opacity:1}85%{opacity:1}100%{transform:translateX(20px);opacity:0}}"""
    d = ["<defs>", accent_grad(t, "acc")]
    body = []
    for i, (title, desc, icon) in enumerate(BUILD):
        x = i * (cw + gap)
        body.append(f'<g class="fu" style="animation-delay:{0.1 + i * 0.15:.2f}s">')
        body.append(glass(t, x + 0.5, 0.5, cw - 1, H - 1, f"g{i}"))
        body.append(f'<rect x="{x + 28}" y="28" width="64" height="64" rx="16" fill="{t["a1"]}" '
                    f'fill-opacity="{t["tint_op"]}"/>')
        body.append(f'<g transform="translate({x + 28} 28)">{icon(t)}</g>')
        body.append(T(x + 28, 142, title, 23, 800, t["text"], extra="letter-spacing='-0.3'"))
        for j, line in enumerate(wrap(desc, 17, 500, cw - 56)):
            body.append(T(x + 28, 180 + j * 27, line, 17, 500, t["muted"]))
        body.append("</g>")
    d.append("</defs>")
    return svg(W, H, "".join(d + body), "What I build: AI-native engineering, real-time systems, developer tools", css)


# --------------------------------------------------------- project cards ----
PROJECTS = [
    ("eventloop", "01", "EventLoop Studio", "VS Code Marketplace",
     "A VS Code extension that runs your own JavaScript in a sandboxed Node vm and replays the Call Stack, "
     "Heap, microtasks, timers and the six libuv phases step by step. Real execution, not a canned animation.",
     ["TypeScript", "VS Code API", "React", "Node vm", "acorn"], []),
    ("adcms", "02", "ADCMS", "Internal platform · Newton School of Technology",
     "A course management platform that tracks student projects against tamper-proof GitHub commit history. "
     "Its first user signed in three days after the first commit, and it syncs every repository automatically "
     "three times a week. Built AI-native with Claude Code.",
     ["React", "Express", "MongoDB", "GitHub API", "Google Sheets API", "GitHub Actions"],
     [("642", "users"), ("3", "campuses"), ("2,967", "commits captured"), ("99.6%", "sync success")]),
    ("sqlheist", "03", "SQL Heist City", "Multiplayer game · AI-native build",
     "A multiplayer browser game that teaches SQL: every vault, heal and weapon costs a query while other "
     "players hunt you. Server-authoritative netcode, a locked-down SQLite grading sandbox and a versioned "
     "admin backend.",
     ["TypeScript", "Three.js", "WebSockets", "Express", "PostgreSQL", "React"],
     [("2.2 KB/s", "per client, down from 41"), ("9.1 ms", "p99 tick at 100 clients"), ("14 days", "to build")]),
    ("jana", "04", "Jana Academy", "Live in production",
     "A production platform with a Socket.io multiplayer quiz arena, server-side RS256 verification of "
     "Firebase tokens, Redis caching with stale fallback, and self-hosted analytics with Core Web Vitals.",
     ["React", "TypeScript", "Express", "MongoDB", "Redis", "Socket.io"], []),
]


def project(t, idx, title, badge, desc, chips, stats=()):
    lines = wrap(desc, 19, 500, 840)
    sy = 164 + len(lines) * 29 + 12 if stats else None
    chip_y = sy + 52 if stats else 164 + len(lines) * 29 + 4
    H = chip_y + 30 + 40
    per = 2 * (W - 2) + 2 * (H - 2)
    css = f""".cm{{animation:cm 7s linear infinite}}
@keyframes cm{{to{{stroke-dashoffset:-{per:.0f}}}}}"""
    d = ["<defs>", accent_grad(t, "acc"),
         f'<linearGradient id="num" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["a1"]}" stop-opacity=".55"/>'
         f'<stop offset="1" stop-color="{t["a2"]}" stop-opacity=".05"/></linearGradient>']
    body = [glass(t, 1, 1, W - 2, H - 2, "gc", r=24)]
    d.append("</defs>")
    # comet light travelling around the border
    body.append(f'<rect class="cm" x="1" y="1" width="{W - 2}" height="{H - 2}" rx="24" fill="none" '
                f'stroke="url(#acc)" stroke-width="2" stroke-linecap="round" '
                f'stroke-dasharray="180 {per - 180:.0f}"/>')
    body.append(T(W - 48, 150, idx, 150, 800, "none", "end",
                  f'stroke="url(#num)" stroke-width="2" letter-spacing="-6"', cls="fi"))
    bw = text_width(badge, 14, 700) + 44
    body.append('<g class="fu" style="animation-delay:.05s">')
    body.append(f'<rect x="44" y="40" width="{bw:.0f}" height="30" rx="15" fill="{t["a1"]}" fill-opacity="{t["tint_op"]}"/>')
    body.append(f'<circle cx="62" cy="55" r="4" fill="{t["a1"]}" class="pulse"/>')
    body.append(T(74, 60, badge, 14, 700, t["a1"]))
    body.append("</g>")
    body.append(f'<g class="fu" style="animation-delay:.15s">'
                f'{T(42, 124, title, 40, 800, t["text"], extra="letter-spacing=\'-1\'")}</g>')
    body.append('<g class="fu" style="animation-delay:.25s">')
    for j, line in enumerate(lines):
        body.append(T(44, 164 + j * 29, line, 19, 500, t["muted"]))
    body.append("</g>")
    if stats:
        body.append('<g class="fu" style="animation-delay:.3s">')
        sx = 44
        for k, (num, label) in enumerate(stats):
            if k:
                body.append(f'<rect x="{sx - 17:.0f}" y="{sy + 8}" width="1" height="22" fill="{t["border"]}" '
                            f'fill-opacity="{t["border_op"] + 0.08}"/>')
            body.append(T(sx, sy + 26, num, 22, 800, "url(#acc)"))
            nw = text_width(num, 22, 800)
            body.append(T(sx + nw + 8, sy + 26, label, 16, 500, t["muted"]))
            sx += nw + 8 + text_width(label, 16, 500) + 34
        body.append("</g>")
    cx, cy = 44, chip_y
    body.append('<g class="fu" style="animation-delay:.35s">')
    for c in chips:
        cw = text_width(c, 14, 700) + 28
        body.append(f'<rect x="{cx:.0f}" y="{cy}" width="{cw:.0f}" height="30" rx="8" fill="{t["chip_bg"]}" '
                    f'fill-opacity="{t["chip_op"]}" stroke="{t["border"]}" stroke-opacity="{t["border_op"]}"/>')
        body.append(T(cx + 14, cy + 20, c, 14, 700, t["text2"]))
        cx += cw + 10
    body.append("</g>")
    alt = f"{title} ({badge}): {desc}"
    if stats:
        alt += " " + ", ".join(f"{n} {l}" for n, l in stats) + "."
    return svg(W, H, "".join(d + body), alt, css)


# --------------------------------------------------------- window chrome ----
def window_bar(t):
    H = 46
    label = "EventLoop Studio — samples/01-classic-ordering.js"
    d = [f'<path d="M0 18a18 18 0 0 1 18-18h{W - 36}a18 18 0 0 1 18 18v{H - 18}H0z" fill="{t["bg2"]}" '
         f'stroke="{t["border"]}" stroke-opacity="{t["border_op"]}"/>']
    for i, c in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        d.append(f'<circle cx="{26 + i * 22}" cy="23" r="6.5" fill="{c}"/>')
    d.append(T(W / 2, 28.5, label, 14, 500, t["muted"], "middle"))
    return svg(W, H, "".join(d), "EventLoop Studio demo window")


# ----------------------------------------------------------------- stats ----
STATS = [("300+", "engineers taught"), ("50+", "hours a month automated"),
         ("2,500+", "live sessions led"), ("150+", "pull requests reviewed")]


def stats(t):
    H, gap = 176, 20
    tw = (W - 3 * gap) / 4
    size, lh = 54, 64
    digit_w = max(text_width(str(n), size, 800) for n in range(10))
    css = """.roll{animation:roll 1.8s cubic-bezier(.16,.84,.3,1) both}
@keyframes roll{from{transform:translateY(0)}}"""
    d = ["<defs>", accent_grad(t, "acc", "0", "0", "1", "1")]
    body = []
    for i, (num, label) in enumerate(STATS):
        x = i * (tw + gap)
        delay = 0.15 + i * 0.12
        d.append(f'<clipPath id="k{i}"><rect x="{x}" y="34" width="{tw}" height="{lh}"/></clipPath>')
        body.append(f'<g class="fu" style="animation-delay:{delay - 0.1:.2f}s">')
        body.append(glass(t, x + 0.5, 0.5, tw - 1, H - 1, f"g{i}"))
        body.append("</g>")
        width = sum(digit_w if ch.isdigit() else text_width(ch, size, 800) for ch in num)
        px = x + (tw - width) / 2
        base = 34 + lh - 14
        body.append(f'<g clip-path="url(#k{i})">')
        for k, ch in enumerate(num):
            if ch.isdigit():
                target = 10 + int(ch)
                col = "".join(T(px + digit_w / 2, base + n * lh, str(n % 10), size, 800, "url(#acc)", "middle")
                              for n in range(target + 1))
                body.append(f'<g class="roll" style="transform:translateY(-{target * lh}px);'
                            f'animation-delay:{delay + k * 0.08:.2f}s">{col}</g>')
                px += digit_w
            else:
                body.append(f'<g class="fi" style="animation-delay:{delay + 0.9:.2f}s">'
                            f'{T(px, base, ch, size, 800, "url(#acc)")}</g>')
                px += text_width(ch, size, 800)
        body.append("</g>")
        body.append(f'<g class="fi" style="animation-delay:{delay + 0.3:.2f}s">'
                    f'{T(x + tw / 2, 132, label, 16, 500, t["muted"], "middle")}</g>')
    d.append("</defs>")
    alt = "Impact: " + ", ".join(f"{n} {l}" for n, l in STATS)
    return svg(W, H, "".join(d + body), alt, css)


# ----------------------------------------------------------------- stack ----
STACK_ROWS = [
    [("typescript", "TypeScript"), ("javascript", "JavaScript"), ("python", "Python"), ("openjdk", "Java"),
     ("react", "React"), ("tailwindcss", "Tailwind CSS"), ("nodedotjs", "Node.js"), ("express", "Express")],
    [("socketdotio", "Socket.io"), ("mongodb", "MongoDB"), ("redis", "Redis"), ("firebase", "Firebase"),
     ("mysql", "MySQL"), ("claude", "Claude"), ("vercel", "Vercel"), ("git", "Git")],
]


def icon_path(slug):
    with open(os.path.join(ICONS, f"{slug}.svg")) as fh:
        return re.search(r'<path d="([^"]+)"', fh.read()).group(1)


def stack(t):
    H, rh = 168, 64
    css = ""
    d = ["<defs>",
         '<linearGradient id="ef" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
         '<stop offset=".1" stop-color="#fff"/><stop offset=".9" stop-color="#fff"/>'
         '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>',
         f'<mask id="em"><rect width="{W}" height="{H}" fill="url(#ef)"/></mask>']
    body = ['<g mask="url(#em)">']
    for r, row in enumerate(STACK_ROWS):
        chips, cx = [], 0
        for slug, label in row:
            cw = text_width(label, 16, 700) + 76
            chips.append(
                f'<g transform="translate({cx:.0f} 0)">'
                f'<rect width="{cw:.0f}" height="52" rx="14" fill="{t["chip_bg"]}" fill-opacity="{t["chip_op"]}" '
                f'stroke="{t["border"]}" stroke-opacity="{t["border_op"]}"/>'
                f'<path transform="translate(18 14)" d="{icon_path(slug)}" fill="{t["text2"]}"/>'
                f'{T(52, 32, label, 16, 700, t["text2"])}</g>')
            cx += cw + 14
        set_w = cx
        reps = int(W // set_w) + 2
        d.append(f'<g id="row{r}">{"".join(chips)}</g>')
        row_svg = "".join(f'<use href="#row{r}" x="{k * set_w:.0f}"/>' for k in range(reps))
        direction = "" if r == 0 else " reverse"
        css += (f".mq{r}{{animation:mq{r} {set_w / 28:.0f}s linear infinite{direction}}}"
                f"@keyframes mq{r}{{to{{transform:translateX(-{set_w:.0f}px)}}}}")
        y = 16 + r * (rh + 12)
        offset = 0 if r == 0 else -set_w / 2
        body.append(f'<g transform="translate({offset:.0f} {y})"><g class="mq{r}">{row_svg}</g></g>')
    body.append("</g>")
    d.append("</defs>")
    labels = ", ".join(l for row in STACK_ROWS for _, l in row)
    return svg(W, H, "".join(d + body), f"Stack: {labels}", css)


# ----------------------------------------------------------------- footer ---
def footer(t):
    H = 130

    def wave(amp, y, length=300):
        p = f"M0 {y}"
        for k in range(int(2 * W / length) + 2):
            x0 = k * length
            p += f" Q{x0 + length / 4} {y - amp} {x0 + length / 2} {y} T{x0 + length} {y}"
        return p + f" V{H} H0Z"

    css = """.wv1{animation:wv 14s linear infinite}.wv2{animation:wv 20s linear infinite reverse}
.wv3{animation:wv 28s linear infinite}@keyframes wv{to{transform:translateX(-600px)}}"""
    d = ["<defs>", accent_grad(t, "acc"), "</defs>",
         f'<g class="wv3" opacity=".18"><path d="{wave(14, 52, 300)}" fill="{t["a2"]}"/></g>',
         f'<g class="wv2" opacity=".22"><path d="{wave(10, 70, 200)}" fill="{t["a1"]}"/></g>',
         f'<g class="wv1" opacity=".9"><path d="{wave(8, 88, 300)}" fill="url(#acc)"/></g>']
    return svg(W, H, "".join(d), "Footer wave")


# ------------------------------------------------------------------- main ---
def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".svg"):
            os.remove(os.path.join(OUT, f))
    written = []
    for name, t in THEMES.items():
        written.append(write("hero", name, hero(t)))
        written.append(write("link-portfolio", name, pill(t, "Portfolio", "globe", primary=True)))
        written.append(write("link-linkedin", name, pill(t, "LinkedIn", "in")))
        written.append(write("link-email", name, pill(t, "Email", "mail")))
        for slug, idx, title in [("build", "01", "What I build"), ("work", "02", "Featured work"),
                                 ("impact", "03", "Impact"), ("stack", "04", "Stack"),
                                 ("activity", "05", "Activity")]:
            written.append(write(f"section-{slug}", name, section(t, idx, title)))
        written.append(write("build", name, build_cards(t)))
        for slug, idx, title, badge, desc, chips, pstats in PROJECTS:
            written.append(write(f"project-{slug}", name, project(t, idx, title, badge, desc, chips, pstats)))
        written.append(write("window-eventloop", name, window_bar(t)))
        written.append(write("stats", name, stats(t)))
        written.append(write("stack", name, stack(t)))
        written.append(write("footer", name, footer(t)))
    for p in written:
        print(f"{os.path.getsize(p) / 1024:6.1f} KB  {os.path.relpath(p, ROOT)}")


if __name__ == "__main__":
    main()
