#!/usr/bin/env python3
"""Gera as imagens SVG do README no estilo do portfólio (claudio.dev).

Cada imagem sai em dois temas, iguais aos do portfólio: `noite` (escuro) e
`papel` (claro). O README escolhe entre eles com <picture> conforme o tema do
GitHub de quem visita. Cada SVG embute só os glifos da IBM Plex Mono que usa,
para renderizar igual em qualquer máquina, e respeita prefers-reduced-motion.

Uso:
    pip install fonttools brotli pillow
    python3 scripts/build_readme_assets.py

Na primeira execução as fontes são baixadas do Google Fonts para
~/.cache/claudio-readme-fonts (ou para a pasta em $FONT_DIR, se definida).
Textos e dados das imagens ficam nas constantes abaixo.
"""

import base64
import io
import os
import pathlib
import re
import urllib.request
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "readme"
PHOTO = OUT / "profile.jpg"
FONT_DIR = pathlib.Path(os.environ.get("FONT_DIR", pathlib.Path.home() / ".cache" / "claudio-readme-fonts"))
FONT_URLS = {
    400: "https://fonts.gstatic.com/s/ibmplexmono/v20/-F63fjptAgt5VM-kVkqdyU8n5ig.ttf",
    500: "https://fonts.gstatic.com/s/ibmplexmono/v20/-F6qfjptAgt5VM-kVkqdyU8n3twJ8lc.ttf",
    600: "https://fonts.gstatic.com/s/ibmplexmono/v20/-F6qfjptAgt5VM-kVkqdyU8n3vAO8lc.ttf",
}

# Paletas do portfólio (css/style.css, passe "hancore").
THEMES = {
    "noite": {
        "bg": "#0b0c0b", "surface": "#101210", "text": "#d8d2ba", "muted": "#8c8876",
        "dim": "#46463d", "border": "#34392e", "accent": "#7fae93", "warm": "#e0775c",
        "pink": "#e04a6a",
    },
    "papel": {
        "bg": "#eeece2", "surface": "#e8e5d9", "text": "#333a2e", "muted": "#636958",
        "dim": "#a5a995", "border": "#bbbda9", "accent": "#4b6b49", "warm": "#b4563c",
        "pink": "#c23a5a",
    },
}
CHAR = 0.6  # avanço da IBM Plex Mono, em em
FAMILY = '"CM Plex","IBM Plex Mono",SFMono-Regular,Consolas,"Liberation Mono",Menlo,monospace'

# ---------------------------------------------------------------- conteúdo

CODE = [
    "# Claudio Meireles — código, dados e ideias.",
    "# Backend / Data Engineering / Artificial Intelligence",
    "",
    "from dataclasses import dataclass",
    "",
    "@dataclass",
    "class Developer:",
    '    name: str = "Claudio Meireles"',
    '    location: str = "Brasília, BR"',
    '    role: str = "tech lead @ VM Medicina"',
    '    focus: tuple = ("backend", "data", "AI")',
    "",
    "    def build(self, idea):",
    "        prototype = self.explore(idea)",
    "        return self.refine(prototype)",
    "",
]
HERO_FACTS = [
    ("user", ["ClaudioAMF1"]),
    ("local", ["Brasília, BR"]),
    ("focus", ["backend", "data", "AI"]),
    ("agora", ["tech lead", "VM Medicina"]),
]
WHOAMI_FACTS = [
    ("agora", "tech lead · VM Medicina e Saúde Mental"),
    ("estudo", "Ciência da Computação · IDP"),
    ("pesquisa", "privacidade em apps de governo"),
    ("foco", "backend · dados · IA aplicada"),
]
SECTIONS = {
    "whoami": ("~", "whoami", None, None),
    "projetos": ("~/projetos", "ls", "SELEÇÃO · 8 PROJETOS", "Projetos"),
    "stack": ("~", "stack --languages", "COM EVIDÊNCIA NOS REPOSITÓRIOS", "Stack"),
    "trajetoria": ("~/trajetoria", "git log --oneline", "EXPERIÊNCIA & FORMAÇÃO", "Trajetória"),
    "contato": ("~/contato", "ls links/", "VAMOS CONVERSAR", "Tem uma ideia?"),
}
# Contagem de repositórios com evidência de cada tecnologia, como em
# assets/data/stack.json do portfólio.
LANGUAGES = [
    ("Python", "Py", 16), ("JavaScript", "JS", 9), ("HTML", "<>", 9), ("CSS", "#", 9),
    ("Shell", "$_", 6), ("C", "C", 4), ("TypeScript", "TS", 3), ("Jupyter Notebook", "Ju", 3),
    ("C++", "++", 2), ("Rust", "Rs", 1),
]
TOOLS = [
    ("Docker", "▣", 7), ("pandas", "▤", 7), ("PostgreSQL", "◆", 6), ("SQLAlchemy", "⛁", 5),
    ("Flask", "⚗\ufe0e", 5), ("NumPy", "∑", 5), ("Node.js", "⬡", 5), ("FastAPI", "⚡\ufe0e", 4),
    ("React", "⚛\ufe0e", 4), ("Redis", "◈", 3), ("scikit-learn", "◎", 3), ("Streamlit", "◣", 3),
    ("Kafka", "⫶", 2), ("Alembic", "↯", 2), ("OpenCV", "◐", 1),
]
AI_TOOLS = [("Claude Code", "✳\ufe0e"), ("Codex", "C"), ("GitHub Copilot", "⌥")]
# Ícones de linha dos projetos sem captura, copiados do portfólio (viewBox 80x40).
ICONS = {
    "legitrack": ("05", '<path d="M14 12 40 3 66 12ZM14 37H66M20 14V33M30 14V33M40 14V33M50 14V33M60 14V33"/>'),
    "crypto-pipeline": ("06", '<path d="M2 30 14 25 22 28 31 13 42 18 50 10 60 16 78 3"/>'
                        '<path class="faint" d="M2 39H78M2 19H78M2 1V39M21 1V39M40 1V39M59 1V39M78 1V39"/>'),
    "soccer-vision": ("07", '<rect x="2" y="2" width="76" height="36" rx="1"/>'
                      '<path d="M40 2V38M2 12H14V28H2M78 12H66V28H78"/><circle cx="40" cy="20" r="7"/>'
                      '<circle class="t" cx="28" cy="14" r="1.5"/><circle class="t" cx="54" cy="28" r="1.5"/>'
                      '<circle class="t" cx="49" cy="10" r="1.5"/><circle class="t" cx="19" cy="26" r="1.5"/>'),
    "tcc-pesquisa": ("08", '<rect x="24" y="2" width="20" height="36" rx="3"/><path d="M30 33H38"/>'
                     '<circle cx="54" cy="18" r="9"/><path d="M60 25 70 35"/>'
                     '<path class="faint" d="M2 10H18M2 18H14M2 26H18"/>'),
}

# ---------------------------------------------------------------- motor


def font_file(weight):
    path = FONT_DIR / f"IBMPlexMono-{weight}.ttf"
    if not path.exists():
        FONT_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(FONT_URLS[weight], path)
    return path


def woff2_subset(weight, chars):
    options = subset.Options()
    options.flavor = "woff2"
    options.hinting = False
    options.layout_features = []
    options.name_IDs = []
    font = TTFont(font_file(weight))
    subsetter = subset.Subsetter(options)
    subsetter.populate(text="".join(sorted(chars)))
    subsetter.subset(font)
    buffer = io.BytesIO()
    font.save(buffer)
    return base64.b64encode(buffer.getvalue()).decode()


def mix(a, b, amount):
    """Mistura duas cores hex como color-mix(in srgb, a amount, b)."""
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * amount + y * (1 - amount)):02x}" for x, y in zip(pa, pb))


PLOT = [
    ("s-m", 'opacity=".55"', "m0 48 32-4 19 2 22-10 28 9 25-19 28 14 18-5 22 12 28-22 27 4 19 7 26-16 29 10 30-2 26-15 24 8 25-4 31-10 33 8 25-7"),
    ("s-a", 'stroke-width="1.4"', "m0 55 30-3 22 4 27-18 17 8 28-7 28 3 20-23 24 14 30-9 24 12 18-19 30 5 28-10 24 16 28-23 27 10 28-8 25 4 30-6 23-3"),
]


def scale_path(d, box, view=(560, 68)):
    """Converte uma polilinha relativa (m x y dx dy ...) da caixa 560x68 para box."""
    numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", d)]
    sx, sy = box[2] / view[0], box[3] / view[1]
    x, y, points = 0.0, 0.0, []
    for k in range(0, len(numbers), 2):
        x, y = x + numbers[k], y + numbers[k + 1]
        points.append(f"{box[0] + x * sx:.1f} {box[1] + y * sy:.1f}")
    return "M" + "L".join(points)


def width(text, size):
    return len(text) * CHAR * size


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.body, self.defs, self.css = [], [], []
        self.chars = {400: set(), 500: set(), 600: set()}

    def add(self, markup):
        self.body.append(markup)

    def text(self, x, y, runs, size=12, anchor="start", attrs=""):
        """runs: str ou lista de (texto, classe[, peso])."""
        if isinstance(runs, str):
            runs = [(runs, "t")]
        spans = []
        for run in runs:
            content, cls = run[0], run[1]
            weight = run[2] if len(run) > 2 else 400
            self.chars[weight].update(content)
            bold = f' font-weight="{weight}"' if weight != 400 else ""
            spans.append(f'<tspan class="{cls}"{bold}>{escape(content)}</tspan>')
        anchor_attr = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.add(f'<text x="{x:g}" y="{y:g}" font-size="{size}"{anchor_attr}{attrs}>{"".join(spans)}</text>')

    def render(self, theme):
        p = THEMES[theme]
        faces = "".join(
            f'@font-face{{font-family:"CM Plex";font-weight:{w};'
            f'src:url(data:font/woff2;base64,{woff2_subset(w, chars)}) format("woff2")}}'
            for w, chars in self.chars.items() if chars
        )
        palette = (
            f".t{{fill:{p['text']}}}.m{{fill:{p['muted']}}}.d{{fill:{p['dim']}}}"
            f".a{{fill:{p['accent']}}}.w{{fill:{p['warm']}}}.p{{fill:{p['pink']}}}"
            f".bg{{fill:{p['bg']}}}.sf{{fill:{p['surface']}}}.on-t{{fill:{p['bg']}}}"
            f".lang{{fill:{mix(p['accent'], p['muted'], 0.55)}}}"
            f".s-b{{stroke:{p['border']}}}.s-d{{stroke:{p['dim']}}}.s-m{{stroke:{p['muted']}}}"
            f".s-t{{stroke:{p['text']}}}.s-a{{stroke:{p['accent']}}}"
            f".pink2{{fill:{mix(p['pink'], p['bg'], 0.7)}}}"
        )
        base = (
            f"text{{font-family:{FAMILY};white-space:pre}}"
            "@keyframes on{from{opacity:0}to{opacity:1}}"
            "@keyframes off{from{opacity:1}to{opacity:0}}"
            "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        )
        css = faces + palette + base + "".join(self.css)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.title)}">'
            f"<title>{escape(self.title)}</title><style>{css}</style>"
            f'<defs>{"".join(self.defs)}</defs>{"".join(self.body)}</svg>'
        )

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        for theme in THEMES:
            (OUT / f"{name}-{theme}.svg").write_text(self.render(theme), encoding="utf-8")


TOKENS = re.compile(
    r'(#.*$|"[^"]*"|\b\d+\b|\b(?:from|import|class|def|return|for|in|if|while|yield|is|not|None|True|False|self)\b)'
)


def highlight(line):
    """Mesmas regras do realce do portfólio (js/main.js, highlightLine)."""
    runs, position = [], 0
    for match in TOKENS.finditer(line):
        if match.start() > position:
            runs.append((line[position:match.start()], "m"))
        token = match.group(0)
        cls = "d" if token.startswith("#") else "w" if token[0] in "\"'0123456789" else "a"
        runs.append((token, cls))
        position = match.end()
    if position < len(line):
        runs.append((line[position:], "m"))
    return runs


# ---------------------------------------------------------------- imagens


def hero():
    """Entrada do portfólio: nvim abrindo claudio.py, digitado linha a linha."""
    W, H = 880, 486
    svg = Svg(W, H, "claudio.dev — nvim ~/portfolio/claudio.py: Claudio Meireles, backend, dados e IA, Brasília")
    size, row, gutter, code_x, top = 12.5, 20, 52, 66, 118
    cw = CHAR * size
    svg.add(f'<rect class="bg s-b" x=".5" y=".5" width="{W - 1}" height="{H - 1}"/>')

    # cabeçalho: marca, links
    svg.text(28, 38, [("cm", "t", 600)], size=16, attrs=' letter-spacing="-1.5"')
    svg.text(54, 38, [("claudio", "t"), (".dev", "m")], size=12.5)
    svg.text(W - 28, 38, [("github ↗", "m"), ("   ", "m"), ("linkedin ↗", "m"), ("   ", "m"), (":tema", "m")],
             size=11.5, anchor="end")

    # linha de boot: o comando é digitado antes do editor abrir
    boot = "nvim ~/portfolio/claudio.py"
    prompt = [("claudio", "t"), ("@dev", "m"), (" ~ ", "m"), ("›", "a"), (" ", "t")]
    boot_x = 28 + width("".join(r[0] for r in prompt), size)
    svg.text(28, 82, prompt + [(boot, "t")], size=size)

    dt, t = 0.026, 0.5
    steps = []  # (início, duração, x inicial, y da linha, nº de caracteres)
    covers = []
    steps.append((t, len(boot) * dt * 1.4, boot_x, 82, len(boot)))
    covers.append((boot_x, 82, len(boot), t, len(boot) * dt * 1.4))
    t += len(boot) * dt * 1.4 + 0.45
    editor_start = t

    rows = []
    for i, line in enumerate(CODE):
        y = top + i * row + 14
        if line:
            duration = len(line) * dt
            covers.append((code_x, y, len(line), t, duration))
            steps.append((t, duration, code_x, y, len(line)))
            rows.append((i, y, t))
            t += duration + 0.09
        else:
            steps.append((t, 0, code_x, y, 0))
            rows.append((i, y, t))
            t += 0.14
    end = t

    # editor: realce da linha atual, números, código, cortinas de digitação
    svg.defs.append(
        '<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset=".72" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="code-mask"><rect x="0" y="{top}" width="{W}" height="{len(CODE) * row}" fill="url(#fade)"/></mask>'
    )
    hl = ["@keyframes hl{"]
    for i, y, start in rows:
        hl.append(f"{start / end * 100:.3f}%{{transform:translateY({y - 14 - top}px);opacity:1}}")
    last_y = rows[-1][1] - 14 - top
    hl.append(f"0%{{opacity:0;transform:translateY(0)}}{editor_start / end * 100 - 0.01:.3f}%{{opacity:0}}"
              f"100%{{opacity:1;transform:translateY({last_y}px)}}}}")
    svg.css.append("".join(hl))
    svg.css.append(f".hl{{animation:hl {end:.2f}s steps(1,end) both}}")
    svg.add('<g mask="url(#code-mask)">')
    for i, y, start in rows:
        svg.text(gutter, y, [(str(i + 1), "d")], size=11.5, anchor="end",
                 attrs=f' class="ln" style="animation:on .01s linear {start:.2f}s both"')
        if CODE[i]:
            svg.text(code_x, y, highlight(CODE[i]), size=size)
    svg.add("</g>")

    # as cortinas deslizam para a direita; o recorte as mantém dentro do editor
    svg.defs.append(f'<clipPath id="editor"><rect x="0" y="0" width="572" height="{H}"/></clipPath>')
    svg.add('<g clip-path="url(#editor)">')
    for n, (x, y, chars, start, duration) in enumerate(covers):
        dx = chars * cw + 2
        svg.css.append(f"@keyframes c{n}{{to{{transform:translateX({dx:.1f}px)}}}}")
        svg.add(f'<rect class="bg cover" x="{x - 1:.1f}" y="{y - 13}" width="{dx + 2:.1f}" height="17" '
                f'style="animation:c{n} {duration:.2f}s steps({chars + 1},jump-none) {start:.2f}s both"/>')
    svg.add("</g>")

    svg.add(f'<rect class="hl t" x="12" y="{top}" width="{560 - 12}" height="{row}" fill-opacity=".055"/>')

    # cursor: anda com a digitação e pisca no fim
    first, last = steps[0], steps[-1]
    frames = ["@keyframes caret{", f"0%{{transform:translate({first[2]:.1f}px,{first[3] - 11}px);"
              "animation-timing-function:steps(1,end)}",
              f"100%{{transform:translate({last[2] + last[4] * cw:.1f}px,{last[3] - 11}px)}}"]
    for start, duration, x, y, chars in steps:
        timing = f"steps({chars + 1},jump-none)" if chars else "steps(1,end)"
        frames.append(f"{start / end * 100:.3f}%{{transform:translate({x:.1f}px,{y - 11}px);"
                      f"animation-timing-function:{timing}}}")
        if chars:
            frames.append(f"{(start + duration) / end * 100:.3f}%{{transform:translate({x + chars * cw:.1f}px,{y - 11}px);"
                          "animation-timing-function:steps(1,end)}")
    frames.append("}")
    svg.css.append("".join(frames))
    svg.css.append(f".caret{{animation:caret {end:.2f}s both}}"
                   f".caret-blink{{animation:blink 1.1s {end:.2f}s infinite}}")
    svg.add(f'<g class="caret-blink"><rect class="caret t" x="0" y="0" width="{cw:.1f}" height="14"/></g>')

    # barra de modo do vim
    bar_y = top + len(CODE) * row + 14
    svg.add(f'<rect class="sf" x="12" y="{bar_y}" width="{560 - 12}" height="18"/>')
    for label, cls, style in (("INSERT", "ins", f"animation:off .01s linear {end:.2f}s both"),
                              ("NORMAL", "nrm", f"animation:on .01s linear {end:.2f}s both")):
        svg.add(f'<g class="{cls}" style="{style}"><rect class="t" x="12" y="{bar_y}" width="58" height="18"/>')
        svg.text(41, bar_y + 13, [(label, "on-t", 600)], size=10, anchor="middle")
        svg.add("</g>")
    svg.text(80, bar_y + 13, [("~/portfolio/claudio.py", "m")], size=10)
    svg.text(560 - 6, bar_y + 13, [("python · utf-8", "d")], size=10, anchor="end")

    # coluna direita: fatos, como na barra lateral do portfólio
    fx, fy, key_w = 612, top + 4, 62
    y = fy
    for key, values in HERO_FACTS:
        svg.text(fx, y + 10, [(key, "m")], size=11)
        for k, value in enumerate(values):
            svg.text(fx + key_w, y + 10 + k * 16, [(value, "t")], size=11)
        y += 16 * len(values) + 12
        svg.add(f'<path class="s-b" d="M{fx} {y - 2}H{W - 28}"/>')
        y += 12
    svg.text(fx, y + 18, [("// pequenas ideias.", "d")], size=10.5)
    svg.text(fx, y + 34, [("// sistemas maiores.", "d")], size=10.5)
    svg.text(fx, bar_y + 13, [("UTC−3 / Brasília", "m")], size=10.5)

    svg.css.append(
        "@media (prefers-reduced-motion:reduce){.cover,.caret-blink,.ins{display:none}"
        ".hl,.ln,.nrm{animation:none!important}.hl{opacity:0}}"
    )
    svg.save("hero")


def whoami():
    """Cartão de identidade do painel whoami."""
    W, H = 880, 300
    svg = Svg(W, H, "Claudio Meireles — software developer em Brasília: backend, dados e inteligência artificial")
    svg.add(f'<rect class="sf s-d" x=".5" y=".5" width="{W - 1}" height="{H - 1}"/>')
    svg.text(24, 30, [("CM / SOFTWARE DEVELOPER", "m")], size=9.5, attrs=' letter-spacing=".8"')
    svg.text(W - 24, 30, [("Brasília, BR", "m")], size=9.5, anchor="end", attrs=' letter-spacing=".8"')
    svg.add(f'<path class="s-b" d="M24 42H{W - 24}"/>')

    svg.text(24, 78, [("hello, world.", "m")], size=11, attrs=' letter-spacing="1"')
    svg.text(22, 124, [("Claudio", "t", 500)], size=40)
    svg.text(22, 170, [("Meireles", "t", 500)], size=40)
    svg.text(22 + width("Meireles", 40), 170, [("_", "a", 500)], size=40, attrs=' class="blink"')
    svg.css.append(".blink{animation:blink 1.1s infinite}")
    svg.text(24, 198, [("backend · dados · inteligência artificial", "m")], size=11)

    x0, key_w = 390, 78
    for k, (key, value) in enumerate(WHOAMI_FACTS):
        y = 82 + k * 30
        svg.text(x0, y, [(key, "m")], size=11)
        svg.text(x0 + key_w, y, [(value, "t")], size=11)
        svg.add(f'<path class="s-b" d="M{x0} {y + 11}H{W - 24 - 108 - 22}"/>')

    # foto em escala de cinza, como no portfólio
    photo = Image.open(PHOTO)
    buffer = io.BytesIO()
    photo.save(buffer, "JPEG", quality=82)
    data = base64.b64encode(buffer.getvalue()).decode()
    px, py, pw, ph = W - 24 - 108, 58, 108, 136
    svg.add(f'<rect class="s-b" x="{px + .5}" y="{py + .5}" width="{pw - 1}" height="{ph - 1}" fill="none"/>')
    svg.add(f'<image x="{px + 4}" y="{py + 4}" width="{pw - 8}" height="{ph - 8}" opacity=".78" '
            f'preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{data}"/>')

    # sinal: as mesmas duas linhas do portfólio, desenhadas ao carregar
    box = (24, 214, W - 48, 48)
    grid = "".join(f"M{box[0]} {box[1] + box[3] * k / 4:.1f}H{box[0] + box[2]}" for k in (1, 2, 3))
    grid += "".join(f"M{box[0] + box[2] * k / 10:.1f} {box[1]}V{box[1] + box[3]}" for k in range(1, 10))
    svg.add(f'<path class="s-b" fill="none" d="{grid}"/>')
    for cls, extra, d in PLOT:
        svg.add(f'<path class="{cls} plot" pathLength="1" fill="none" {extra} d="{scale_path(d, box)}"/>')
    svg.css.append(".plot{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 2.6s cubic-bezier(.2,.7,.2,1) .3s forwards}"
                   "@keyframes draw{to{stroke-dashoffset:0}}")
    svg.add(f'<path class="s-b" d="M24 270H{W - 24}"/>')
    svg.text(24, 288, [("01 / construir", "m")], size=9.5, attrs=' letter-spacing=".8"')
    svg.text(W / 2, 288, [("02 / aprender", "m")], size=9.5, anchor="middle", attrs=' letter-spacing=".8"')
    svg.text(W - 24, 288, [("03 / compartilhar", "m")], size=9.5, anchor="end", attrs=' letter-spacing=".8"')
    svg.css.append("@media (prefers-reduced-motion:reduce){.blink{animation:none}.plot{animation:none;stroke-dashoffset:0}}")
    svg.save("whoami")


def section(name, path, command, eyebrow, title):
    """Cabeçalho de seção: prompt de duas linhas, sobrancelha e título."""
    W = 880
    H = 118 if title else 50
    svg = Svg(W, H, title or f"{path} › {command}")
    svg.text(0, 16, [("claudio", "t"), ("@dev", "m"), (f"  {path}", "m")], size=12.5)
    svg.text(0, 37, [("›", "a"), (f" {command}", "t")], size=12.5)
    caret_x = width(f"› {command} ", 12.5)
    svg.add(f'<rect class="t blink" x="{caret_x:.1f}" y="26" width="{CHAR * 12.5:.1f}" height="14"/>')
    svg.css.append(".blink{animation:blink 1.1s infinite}"
                   "@media (prefers-reduced-motion:reduce){.blink{animation:none}}")
    if eyebrow:
        svg.text(0, 74, [(eyebrow, "m")], size=10, attrs=' letter-spacing="1.6"')
    if title:
        svg.text(-1, 106, [(title, "t", 500)], size=26)
    svg.save(f"section-{name}")


def stack():
    """stack --languages / --tools / --ai-tools, como no painel do portfólio."""
    W, row = 880, 24
    langs_h = len(LANGUAGES) * row
    tool_rows = -(-len(TOOLS) // 3)
    H = langs_h + 54 + tool_rows * row + 54 + row + 30
    svg = Svg(W, H, "Stack: Python, JavaScript, TypeScript, C, Rust; Docker, PostgreSQL, FastAPI, Flask, React, Redis, Kafka e mais")
    svg.defs.append(
        '<pattern id="dots" width="3" height="3" patternUnits="userSpaceOnUse"><circle class="d" cx="1.5" cy="1.5" r=".9"/></pattern>'
        '<pattern id="bar" width="8" height="10" patternUnits="userSpaceOnUse"><rect class="p" width="7" height="10"/>'
        '<rect class="pink2" x="7" width="1" height="10"/></pattern>'
    )
    track_x, track_w = 200, 520
    top = max(count for *_, count in LANGUAGES)
    for k, (name, glyph, count) in enumerate(LANGUAGES):
        y = 4 + k * row
        svg.add(f'<rect class="s-m" fill="none" x="0.5" y="{y + 3.5}" width="27" height="15"/>')
        svg.text(14, y + 14.5, [(glyph, "t")], size=8.5, anchor="middle")
        svg.text(38, y + 15, [(name, "lang")], size=12)
        svg.add(f'<rect x="{track_x}" y="{y + 2}" width="{track_w}" height="18" fill="url(#dots)"/>')
        svg.add(f'<rect class="grow" x="{track_x}" y="{y + 2}" width="{track_w * count / top:.1f}" height="18" '
                f'fill="url(#bar)" style="animation-delay:{k * 70}ms"/>')
        svg.text(track_x + track_w + 34, y + 15, [(str(count), "w")], size=12, anchor="end")
        svg.text(track_x + track_w + 42, y + 15, [("repos" if count > 1 else "repo", "m")], size=12)
    svg.css.append(".grow{transform-box:fill-box;transform-origin:left;animation:grow .7s cubic-bezier(.2,.7,.2,1) both}"
                   "@keyframes grow{from{transform:scaleX(0)}}"
                   "@media (prefers-reduced-motion:reduce){.grow{animation:none}}")

    y = langs_h + 40
    svg.text(0, y, [("›", "a"), (" stack --tools", "t")], size=12.5)
    col = W / 3
    for k, (name, glyph, count) in enumerate(TOOLS):
        cx, cy = (k % 3) * col, y + 28 + (k // 3) * row
        svg.text(cx + 8, cy, [(glyph, "t")], size=12, anchor="middle")
        svg.text(cx + 26, cy, [(name, "t")], size=12)
        svg.text(cx + col - 40, cy, [(str(count), "w")], size=12, anchor="end")
    y += 28 + tool_rows * row + 26
    svg.text(0, y, [("›", "a"), (" stack --ai-tools", "t")], size=12.5)
    for k, (name, glyph) in enumerate(AI_TOOLS):
        svg.text(k * col + 8, y + 28, [(glyph, "t")], size=12, anchor="middle")
        svg.text(k * col + 26, y + 28, [(name, "t")], size=12)
    svg.text(0, H - 4, [("números: repositórios com evidência (arquivos, dependências)", "m")], size=10)
    svg.save("stack")


def icon_card(name, index, markup):
    """Capa dos projetos sem captura de tela: o ícone de linha do portfólio."""
    W, H = 640, 400
    svg = Svg(W, H, name)
    svg.add(f'<rect class="sf s-b" x=".5" y=".5" width="{W - 1}" height="{H - 1}"/>')
    svg.add(f'<svg x="140" y="90" width="360" height="180" viewBox="-2 -2 84 44">'
            f'<g class="s-t" fill="none" stroke-width="1.2" vector-effect="non-scaling-stroke">{markup}</g></svg>')
    svg.css.append(".faint{opacity:.3}")
    svg.add(f'<path class="s-b" d="M24 {H - 58}H{W - 24}"/>')
    svg.text(24, H - 26, [(name, "t")], size=20)
    svg.text(W - 24, H - 26, [(index, "d")], size=20, anchor="end")
    svg.save(f"card-{name}")


def footer():
    """Barra de modo do vim fechando o README."""
    W, H = 880, 26
    svg = Svg(W, H, "NORMAL — ~/ClaudioAMF1/README.md — pequenas ideias, sistemas maiores")
    svg.add(f'<rect class="sf" width="{W}" height="{H}"/><rect class="t" width="70" height="{H}"/>')
    svg.text(35, 17.5, [("NORMAL", "on-t", 600)], size=11, anchor="middle")
    svg.text(82, 17.5, [("~/ClaudioAMF1/README.md", "m")], size=11)
    svg.text(W - 10, 17.5, [("pequenas ideias. sistemas maiores.", "m"), ("   :wq", "d")], size=11, anchor="end")
    svg.save("footer")


def prepare_photo(source):
    """Recorta e reduz a foto do portfólio para o cartão whoami."""
    image = ImageOps.grayscale(Image.open(source))
    image = ImageOps.fit(image, (200, 256), Image.LANCZOS, centering=(0.5, 0.35))
    image.save(PHOTO, "JPEG", quality=82, optimize=True)


if __name__ == "__main__":
    if not PHOTO.exists() and os.environ.get("PROFILE_SOURCE"):
        prepare_photo(os.environ["PROFILE_SOURCE"])
    hero()
    whoami()
    for key, args in SECTIONS.items():
        section(key, *args)
    stack()
    for card, (index, markup) in ICONS.items():
        icon_card(card, index, markup)
    footer()
    for file in sorted(OUT.glob("*.svg")):
        print(f"{file.stat().st_size / 1024:6.1f} KB  {file.relative_to(ROOT)}")
