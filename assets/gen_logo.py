"""Generates the CVSF Process Simulator logo (SVG): helical screw in three CVSF modules with filter cake particles."""
import math

def icon_svg(size=512, bg=True):
    W = 512
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {W} {W}">']
    out.append('''<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#16395F"/><stop offset="1" stop-color="#0A1E33"/></linearGradient>
  <linearGradient id="tube" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.30"/><stop offset="0.45" stop-color="#FFFFFF" stop-opacity="0.07"/>
    <stop offset="1" stop-color="#FFFFFF" stop-opacity="0.16"/></linearGradient>
  <linearGradient id="shaft" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#F2F5F8"/><stop offset="0.5" stop-color="#AEB8C4"/><stop offset="1" stop-color="#6F7C8B"/></linearGradient>
  <linearGradient id="cake" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#F4C55A"/><stop offset="1" stop-color="#C98A12"/></linearGradient>
  <linearGradient id="flange" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#7F8C9B"/><stop offset="0.5" stop-color="#E9EEF3"/><stop offset="1" stop-color="#7F8C9B"/></linearGradient>
  <clipPath id="inner"><rect x="58" y="186" width="396" height="140" rx="20"/></clipPath>
</defs>''')
    if bg:
        out.append(f'<rect x="8" y="8" width="496" height="496" rx="112" fill="url(#bg)"/>')
        out.append('<rect x="8" y="8" width="496" height="496" rx="112" fill="none" stroke="#3E6E9E" stroke-width="4" stroke-opacity="0.6"/>')
    x0, x1, yt, yb = 58, 454, 186, 326
    # tube body
    out.append(f'<rect x="{x0}" y="{yt}" width="{x1-x0}" height="{yb-yt}" rx="20" fill="url(#tube)"/>')
    # filter cake inside: grows over the first module (cake formation), constant afterwards
    zS = 150
    pts = [(x0, yb)] + [(x, yb - 52 * math.sqrt(min((x - x0) / (zS - x0), 1.0))) for x in range(x0, x1 + 1, 6)] + [(x1, yb)]
    out.append('<g clip-path="url(#inner)">')
    out.append('<polygon points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + '" fill="url(#cake)"/>')
    # supernatant suspension above the growing cake in the first module
    sus = [(x, yb - 52 * math.sqrt(min((x - x0) / (zS - x0), 1.0))) for x in range(x0, zS + 1, 4)]
    top = [(x, yt + 44 + 52 * (x - x0) / (zS - x0) * 0.85) for x in range(zS, x0 - 1, -4)]
    out.append('<polygon points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in sus + top) + '" fill="#3FA9F5" fill-opacity="0.55"/>')
    # particles (bipyramidal crystals) in the cake
    import random
    random.seed(4)
    for _ in range(70):
        x = random.uniform(x0 + 8, x1 - 6)
        h = 52 * math.sqrt(min((x - x0) / (zS - x0), 1.0))
        if h < 10:
            continue
        y = random.uniform(yb - h + 6, yb - 4)
        s = random.uniform(4.5, 7.5); r = random.uniform(-30, 30)
        out.append(f'<polygon transform="translate({x:.1f},{y:.1f}) rotate({r:.0f})" points="0,{-s*1.5:.1f} {s:.1f},0 0,{s*1.5:.1f} {-s:.1f},0" '
                   f'fill="#FFF3D0" fill-opacity="0.85" stroke="#8A5A00" stroke-width="1"/>')
    # particles in suspension
    for _ in range(12):
        x = random.uniform(x0 + 6, zS - 20)
        y = random.uniform(yt + 50 + 40 * (x - x0) / (zS - x0), yb - 52 * math.sqrt((x - x0) / (zS - x0)) - 6)
        s = 4.5
        out.append(f'<polygon transform="translate({x:.1f},{y:.1f}) rotate({random.uniform(-40,40):.0f})" points="0,{-s*1.5} {s},0 0,{s*1.5} {-s},0" fill="#FFF3D0" fill-opacity="0.9"/>')
    # screw: back flights (dim), shaft, front flights (bright)
    P = 44.0
    flights = []
    x = x0 - P
    while x < x1 + P:
        flights.append(x); x += P
    for xs in flights:   # back half of each flight
        out.append(f'<path d="M {xs+P/2:.1f} {yt+4} C {xs+P*0.62:.1f} {yt+40} {xs+P*0.88:.1f} {yb-40} {xs+P:.1f} {yb-4}" '
                   f'fill="none" stroke="#9FB3C8" stroke-opacity="0.35" stroke-width="5" stroke-linecap="round"/>')
    out.append(f'<rect x="{x0-30}" y="{256-12}" width="{x1-x0+60}" height="24" rx="6" fill="url(#shaft)"/>')
    for xs in flights:   # front half of each flight
        out.append(f'<path d="M {xs+P:.1f} {yb-4} C {xs+P*1.18:.1f} {yb-40} {xs+P*1.38:.1f} {yt+40} {xs+P*1.5:.1f} {yt+4}" '
                   f'fill="none" stroke="#FFFFFF" stroke-width="7" stroke-linecap="round"/>')
    out.append('</g>')
    # frit (filter medium) below the first module, filtrate drops
    out.append(f'<rect x="{x0+14}" y="{yb}" width="{190-x0-26}" height="10" fill="#C9D2DC"/>')
    for xx in range(x0 + 22, 182, 14):
        out.append(f'<line x1="{xx}" y1="{yb}" x2="{xx}" y2="{yb+10}" stroke="#7F8C9B" stroke-width="2"/>')
    for xx, yy, s in [(92, 368, 1.0), (128, 392, 0.8), (160, 362, 0.9)]:
        out.append(f'<path transform="translate({xx},{yy}) scale({s})" d="M 0 -16 C 6 -6 11 0 11 6 A 11 11 0 0 1 -11 6 C -11 0 -6 -6 0 -16 Z" fill="#3FA9F5"/>')
    # tube outline and module flanges
    out.append(f'<rect x="{x0}" y="{yt}" width="{x1-x0}" height="{yb-yt}" rx="20" fill="none" stroke="#E9EEF3" stroke-width="6"/>')
    for xf in (190, 322):
        out.append(f'<rect x="{xf-9}" y="{yt-18}" width="18" height="{yb-yt+36}" rx="5" fill="url(#flange)" stroke="#0A1E33" stroke-width="2"/>')
    # drive coupling on the right, inlet funnel on the left
    out.append(f'<rect x="{x1+2}" y="{256-26}" width="22" height="52" rx="6" fill="url(#flange)"/>')
    out.append(f'<path d="M 74 120 L 130 120 L 112 160 L 112 186 L 92 186 L 92 160 Z" fill="#3FA9F5" fill-opacity="0.9" stroke="#E9EEF3" stroke-width="4" stroke-linejoin="round"/>')
    # air / washing liquid arrows into modules 2 and 3
    for xa, col in [(256, "#7FD1FF"), (388, "#9BE3B0")]:
        out.append(f'<path d="M {xa} 118 L {xa} 162" stroke="{col}" stroke-width="9" stroke-linecap="round"/>'
                   f'<path d="M {xa-15} 152 L {xa} 172 L {xa+15} 152" fill="none" stroke="{col}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>')
    out.append('</svg>')
    return "\n".join(out)


def wordmark_svg():
    ic = icon_svg(120).replace('<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 512 512">',
                                '<svg x="0" y="0" width="120" height="120" viewBox="0 0 512 512">')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="560" height="120" viewBox="0 0 560 120">
{ic}
<text x="138" y="66" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="56" font-weight="800" fill="#16395F" letter-spacing="2">CVSF</text>
<text x="140" y="98" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="22" font-weight="500" fill="#5A6B7D" letter-spacing="3.5">PROCESS SIMULATOR</text>
</svg>'''


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    open(f"{d}/cvsf_icon.svg", "w").write(icon_svg())
    open(f"{d}/cvsf_wordmark.svg", "w").write(wordmark_svg())
