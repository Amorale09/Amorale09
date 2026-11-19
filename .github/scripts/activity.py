"""Render the contribution calendar as a dithered SVG (no dependencies).

Usage: activity.py <login> <out.svg> [calendar.json]
Without calendar.json it queries the GitHub GraphQL API using $GITHUB_TOKEN.
"""
import json
import os
import sys
import urllib.request
from datetime import date

BG, FG, DIM = "#0a0f08", "#c8ff3c", "#5c7a1e"
def _bayer(n):
    if n == 1:
        return [[0]]
    m = _bayer(n // 2)
    return ([[4 * v for v in r] + [4 * v + 2 for v in r] for r in m] +
            [[4 * v + 3 for v in r] + [4 * v + 1 for v in r] for r in m])


N = 8
BAYER = _bayer(N)                 # 8x8 ordered dither, values 0..63
THRESH = (0, 12, 26, 44, 64)      # lit pixels per level, out of 64
QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{contributionCount date weekday}}}}}}"""

CELL, PX = 28, 3          # cell pitch, dither pixel size (cell body = 4*PX)
W, LEFT, TOP = 1600, 80, 110


def fetch(login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": "bearer " + os.environ["GITHUB_TOKEN"]},
    )
    data = json.load(urllib.request.urlopen(req))
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level(n, mx):
    if n <= 0:
        return 0
    return min(4, 1 + int(3 * (n - 1) / max(mx - 1, 1) + 0.0001))


def main():
    login, out = sys.argv[1], sys.argv[2]
    if len(sys.argv) > 3:
        raw = json.load(open(sys.argv[3], encoding="utf-8"))
        cal = raw["data"]["viewer"]["contributionsCollection"]["contributionCalendar"]
    else:
        cal = fetch(login)
    weeks = cal["weeks"]
    mx = max(d["contributionCount"] for w in weeks for d in w["contributionDays"]) or 1

    BODY = N * PX
    # one <pattern> per level: 8x8 bayer pixels
    defs = []
    for k in range(5):
        rects = "".join(
            f'<rect x="{x*PX}" y="{y*PX}" width="{PX}" height="{PX}"/>'
            for y in range(N) for x in range(N) if BAYER[y][x] < THRESH[k]
        )
        defs.append(
            f'<pattern id="l{k}" width="{BODY}" height="{BODY}" patternUnits="userSpaceOnUse">'
            f'<g fill="{FG}">{rects}</g></pattern>'
        )

    body, months = [], []
    last_month = None
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            x = LEFT + wi * CELL
            y = TOP + d["weekday"] * CELL
            k = level(d["contributionCount"], mx)
            if k == 0:
                body.append(f'<rect x="{x}" y="{y}" width="{BODY}" height="{BODY}" fill="none" '
                            f'stroke="{DIM}" stroke-opacity="0.45" stroke-width="1"/>')
            else:
                body.append(f'<g transform="translate({x},{y})"><rect width="{BODY}" height="{BODY}" '
                            f'fill="url(#l{k})"/></g>')
        first = w["contributionDays"][0]["date"]
        m = date.fromisoformat(first).month
        if m != last_month and wi < len(weeks) - 2:
            months.append((wi, date.fromisoformat(first).strftime("%b").lower()))
            last_month = m

    font = 'font-family="Consolas, \'DejaVu Sans Mono\', monospace"'
    texts = [f'<text x="10" y="52" {font} font-size="44" fill="{DIM}">[02]</text>',
             f'<text x="{LEFT+80}" y="52" {font} font-size="44" font-weight="bold" fill="{FG}">'
             f'{cal["totalContributions"]} contributions / last year</text>']
    for wi, name in months:
        texts.append(f'<text x="{LEFT + wi*CELL}" y="{TOP-14}" {font} font-size="22" fill="{DIM}">{name}</text>')
    for row, name in ((1, "mon"), (3, "wed"), (5, "fri")):
        texts.append(f'<text x="6" y="{TOP + row*CELL + 18}" {font} font-size="22" fill="{DIM}">{name}</text>')

    ly = TOP + 7 * CELL + 36
    texts.append(f'<text x="{LEFT}" y="{ly+16}" {font} font-size="22" fill="{DIM}">less</text>')
    for k in range(5):
        lx = LEFT + 70 + k * (BODY + 8)
        if k == 0:
            body.append(f'<rect x="{lx}" y="{ly}" width="{BODY}" height="{BODY}" fill="none" stroke="{DIM}" stroke-opacity="0.45"/>')
        else:
            body.append(f'<g transform="translate({lx},{ly})"><rect width="{BODY}" height="{BODY}" fill="url(#l{k})"/></g>')
    texts.append(f'<text x="{LEFT + 70 + 5*(BODY+8) + 8}" y="{ly+16}" {font} font-size="22" fill="{DIM}">more</text>')
    H = ly + BODY + 40
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
           f'<defs>{"".join(defs)}</defs><rect width="{W}" height="{H}" fill="{BG}"/>'
           f'{"".join(texts)}{"".join(body)}</svg>')
    open(out, "w", encoding="utf-8").write(svg)
    print("wrote", out, len(svg), "bytes")


main()
