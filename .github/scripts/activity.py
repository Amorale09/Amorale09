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
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{contributionCount date weekday}}}}}}"""

CELL, PX = 26, 5          # cell pitch, dither pixel size (cell body = 4*PX)
W, LEFT, TOP = 1600, 90, 70


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

    # one <pattern> per level: 4x4 bayer pixels, 0/6/9/13/16 of 16 lit
    defs = []
    for k in range(5):
        rects = "".join(
            f'<rect x="{x*PX}" y="{y*PX}" width="{PX}" height="{PX}"/>'
            for y in range(4) for x in range(4) if BAYER[y][x] < (0, 6, 9, 13, 16)[k]
        )
        defs.append(
            f'<pattern id="l{k}" width="{4*PX}" height="{4*PX}" patternUnits="userSpaceOnUse">'
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
                body.append(f'<rect x="{x}" y="{y}" width="{4*PX}" height="{4*PX}" fill="none" '
                            f'stroke="{DIM}" stroke-opacity="0.45" stroke-width="1"/>')
            else:
                body.append(f'<g transform="translate({x},{y})"><rect width="{4*PX}" height="{4*PX}" '
                            f'fill="url(#l{k})"/></g>')
        first = w["contributionDays"][0]["date"]
        m = date.fromisoformat(first).month
        if m != last_month and wi < len(weeks) - 2:
            months.append((wi, date.fromisoformat(first).strftime("%b").lower()))
            last_month = m

    font = 'font-family="Consolas, \'DejaVu Sans Mono\', monospace"'
    texts = [f'<text x="10" y="40" {font} font-size="30" fill="{DIM}">[02]</text>',
             f'<text x="{LEFT+20}" y="40" {font} font-size="30" font-weight="bold" fill="{FG}">'
             f'{cal["totalContributions"]} contributions / last year</text>']
    for wi, name in months:
        texts.append(f'<text x="{LEFT + wi*CELL}" y="{TOP-10}" {font} font-size="18" fill="{DIM}">{name}</text>')
    for row, name in ((1, "mon"), (3, "wed"), (5, "fri")):
        texts.append(f'<text x="10" y="{TOP + row*CELL + 17}" {font} font-size="18" fill="{DIM}">{name}</text>')

    H = TOP + 7 * CELL + 30
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
           f'<defs>{"".join(defs)}</defs><rect width="{W}" height="{H}" fill="{BG}"/>'
           f'{"".join(texts)}{"".join(body)}</svg>')
    open(out, "w", encoding="utf-8").write(svg)
    print("wrote", out, len(svg), "bytes")


main()
