"""Generates the CVSF Process Simulator logo: glass ring with the screw helix (front flights bold, back flights fine)
and the PTFE screw core, optionally with the lettering CVSF below (desktop icon).

    python assets/gen_logo.py [folder]

writes cvsf_icon.svg (emblem, used in the app and the manuals), cvsf_icon_text.svg (emblem + CVSF, desktop icon),
cvsf_wordmark.svg, and - if rsvg-convert and Pillow are available - cvsf_icon_256.png, cvsf_favicon.png and cvsf.ico
(sizes 16-32 px without lettering, 48-256 px with lettering).
"""
import math
import os
import shutil
import subprocess
import sys

NAVY_T, NAVY_B = "#22405e", "#08131f"
LINE = "#dbeaf7"


def _helix_paths(c, cy, A, P, x0, x1, n=500):
    pts = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        th = 2 * math.pi * (x - x0) / P
        pts.append((x, cy - A * math.cos(th), math.sin(th) >= 0))
    segs, seg = [], []
    for p in pts:
        if seg and seg[-1][2] != p[2]:
            segs.append(seg)
            seg = [seg[-1]]
        seg.append(p)
    segs.append(seg)
    return segs


def icon_svg(size=512, text=False):
    W = 512
    c = 256
    cy = 222 if text else 256                 # emblem centre
    R = 150 if text else 172                  # outer glass ring
    s = R / 172
    A, P = 68 * s, 92 * s
    x0, x1 = c - 176 * s, c + 176 * s
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {W} {W}">',
           f'''<defs>
  <radialGradient id="bg" cx="0.5" cy="0.38" r="0.8"><stop offset="0" stop-color="{NAVY_T}"/>
    <stop offset="1" stop-color="{NAVY_B}"/></radialGradient>
  <linearGradient id="core" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/>
    <stop offset="1" stop-color="#c3ced9"/></linearGradient>
  <clipPath id="inner"><circle cx="{c}" cy="{cy}" r="{148 * s:.1f}"/></clipPath>
</defs>''',
           '<rect x="8" y="8" width="496" height="496" rx="108" fill="url(#bg)"/>',
           f'<circle cx="{c}" cy="{cy}" r="{R}" fill="#ffffff" fill-opacity="0.04" stroke="{LINE}" stroke-width="{6 * s:.1f}"/>']
    # glass highlight
    a0, a1, rh = math.radians(200), math.radians(252), 160 * s      # screen angles (y downwards)
    out.append(f'<path d="M{c + rh * math.cos(a0):.1f} {cy + rh * math.sin(a0):.1f} '
               f'A{rh:.1f} {rh:.1f} 0 0 1 {c + rh * math.cos(a1):.1f} {cy + rh * math.sin(a1):.1f}" '
               f'stroke="#ffffff" stroke-opacity="0.6" stroke-width="{5 * s:.1f}" fill="none" stroke-linecap="round"/>')
    out.append('<g clip-path="url(#inner)">')
    segs = _helix_paths(c, cy, A, P, x0, x1)
    for sg in segs:
        if not sg[-1][2]:
            d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y, _ in sg)
            out.append(f'<path d="{d}" stroke="#ffffff" stroke-opacity="0.3" stroke-width="{6 * s:.1f}" fill="none" '
                       f'stroke-linecap="round"/>')
    out.append(f'<rect x="{x0 - 20:.1f}" y="{cy - 16 * s:.1f}" width="{x1 - x0 + 40:.1f}" height="{32 * s:.1f}" '
               f'rx="{16 * s:.1f}" fill="url(#core)"/>')
    for sg in segs:
        if sg[-1][2]:
            d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y, _ in sg)
            out.append(f'<path d="{d}" stroke="#ffffff" stroke-width="{14 * s:.1f}" fill="none" '
                       f'stroke-linecap="round"/>')
    out.append('</g>')
    out.append(f'<circle cx="{c}" cy="{cy}" r="{148 * s:.1f}" fill="none" stroke="{LINE}" stroke-opacity="0.5" '
               f'stroke-width="3"/>')
    if text:
        out.append('<line x1="136" y1="402" x2="376" y2="402" stroke="#8fa6bb" stroke-opacity="0.5" stroke-width="3"/>')
        out.append('<text x="256" y="454" text-anchor="middle" font-family="Segoe UI, DejaVu Sans, Arial, sans-serif" '
                   'font-weight="600" font-size="44" letter-spacing="19" fill="#dbe6f0">CVSF</text>')
    out.append('</svg>')
    return "\n".join(out)


def wordmark_svg():
    ic = icon_svg(120).replace('<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 512 512">',
                               '<svg x="0" y="0" width="120" height="120" viewBox="0 0 512 512">')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="560" height="120" viewBox="0 0 560 120">
{ic}
<text x="138" y="66" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="56" font-weight="700" fill="#16395F" letter-spacing="6">CVSF</text>
<text x="140" y="98" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="22" font-weight="500" fill="#5A6B7D" letter-spacing="3.5">PROCESS SIMULATOR</text>
</svg>'''


def render(d):
    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        print("rsvg-convert not found: PNG/ICO not written")
        return
    from PIL import Image
    tmp = {}
    for sz in (16, 24, 32, 48, 64, 128, 256):
        src = os.path.join(d, "cvsf_icon_text.svg" if sz >= 48 else "cvsf_icon.svg")
        out = os.path.join(d, f"_ico_{sz}.png")
        subprocess.run([rsvg, "-w", str(sz), "-h", str(sz), src, "-o", out], check=True)
        tmp[sz] = out
    shutil.copy(tmp[256], os.path.join(d, "cvsf_icon_256.png"))
    subprocess.run([rsvg, "-w", "64", "-h", "64", os.path.join(d, "cvsf_icon.svg"), "-o",
                    os.path.join(d, "cvsf_favicon.png")], check=True)
    imgs = [Image.open(tmp[sz]).convert("RGBA") for sz in sorted(tmp)]
    imgs[-1].save(os.path.join(d, "cvsf.ico"), format="ICO", sizes=[(sz, sz) for sz in sorted(tmp)],
                  append_images=imgs[:-1])
    for f in tmp.values():
        os.remove(f)


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    open(f"{d}/cvsf_icon.svg", "w").write(icon_svg())
    open(f"{d}/cvsf_icon_text.svg", "w").write(icon_svg(text=True))
    open(f"{d}/cvsf_wordmark.svg", "w").write(wordmark_svg())
    render(d)
    print("logo written to", d)
