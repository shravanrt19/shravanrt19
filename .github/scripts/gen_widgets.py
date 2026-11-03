"""Builds assets/trophies.svg and assets/activity.svg from live GitHub data.
Run with --demo to build placeholder (zero-data) versions without calling the API."""
import os, sys, json, datetime, urllib.request, urllib.parse

USER = os.environ.get("GH_USER", "shravanrt19")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = open(os.path.join(HERE, "ps2p.b64")).read().strip()
CSS = ("@font-face{font-family:'PS2P';src:url(data:font/woff2;base64,%s) format('woff2');}"
       "text{font-family:'PS2P','Courier New',monospace;}") % FONT
PINK, CYAN, YEL, PUR, CARD = "#FF206E", "#00F5FF", "#FFD23F", "#9B5DE5", "#2D0140"

def http(url, data=None):
    h = {"User-Agent": "profile-widgets", "Accept": "application/vnd.github+json"}
    if TOKEN: h["Authorization"] = "Bearer " + TOKEN
    if data is not None: data = json.dumps(data).encode(); h["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=30) as r:
        return json.load(r)

def fetch():
    """returns (stats dict, list of (date, count) for last 30 days)"""
    today = datetime.date.today()
    days = [today - datetime.timedelta(days=i) for i in range(29, -1, -1)]
    stats = dict(stars=0, followers=0, commits=0, repos=0, prs=0, issues=0)
    counts = {d.isoformat(): 0 for d in days}
    gql_ok = False
    if TOKEN:
        try:
            q = """query($login:String!){user(login:$login){followers{totalCount}
              repositories(ownerAffiliations:OWNER,isFork:false,first:100){totalCount nodes{stargazerCount}}
              pullRequests{totalCount} issues{totalCount}
              contributionsCollection{totalCommitContributions
                contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
            u = http("https://api.github.com/graphql", {"query": q, "variables": {"login": USER}})["data"]["user"]
            stats.update(stars=sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
                         followers=u["followers"]["totalCount"], repos=u["repositories"]["totalCount"],
                         prs=u["pullRequests"]["totalCount"], issues=u["issues"]["totalCount"],
                         commits=u["contributionsCollection"]["totalCommitContributions"])
            for w in u["contributionsCollection"]["contributionCalendar"]["weeks"]:
                for d in w["contributionDays"]:
                    if d["date"] in counts: counts[d["date"]] = d["contributionCount"]
            gql_ok = True
        except Exception as e:
            print("GraphQL failed, using REST fallback:", e)
    if not gql_ok:
        u = http(f"https://api.github.com/users/{USER}")
        stats.update(followers=u["followers"], repos=u["public_repos"])
        repos = http(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
        stats["stars"] = sum(r["stargazers_count"] for r in repos)
        for key, q in (("prs", f"author:{USER} type:pr"), ("issues", f"author:{USER} type:issue")):
            try: stats[key] = http("https://api.github.com/search/issues?q=" + urllib.parse.quote(q))["total_count"]
            except Exception: pass
        try: stats["commits"] = http("https://api.github.com/search/commits?q=" + urllib.parse.quote(f"author:{USER}"))["total_count"]
        except Exception: pass
        try:
            for ev in http(f"https://api.github.com/users/{USER}/events/public?per_page=100"):
                d = ev["created_at"][:10]
                if d in counts: counts[d] += len(ev.get("payload", {}).get("commits", [])) if ev["type"] == "PushEvent" else 1
        except Exception: pass
    return stats, [(d.isoformat(), counts[d.isoformat()]) for d in days]

RANKS = ["?", "C", "B", "A", "S", "SSS"]
RCOL = {"?": "#6b5b7b", "C": CYAN, "B": PUR, "A": YEL, "S": PINK, "SSS": "#FFFFFF"}
METRICS = [("STARS", "stars", [1, 10, 30, 100, 500]), ("FOLLOWERS", "followers", [1, 10, 30, 100, 500]),
           ("COMMITS", "commits", [1, 100, 500, 1000, 4000]), ("REPOS", "repos", [1, 5, 15, 30, 60]),
           ("PULL REQS", "prs", [1, 10, 50, 150, 500]), ("ISSUES", "issues", [1, 10, 50, 150, 500])]
CUP = ["#########", "#.#####.#", "#.#####.#", "#.#####.#", ".#######.", "..#####..",
       "...###...", "....#....", "....#....", "..#####..", ".#######."]

def trophies(stats):
    W, cw, gap = 888, 140, 8
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 170" width="{W}" height="170"><style>{CSS}</style>']
    x0 = (W - (6 * cw + 5 * gap)) / 2
    for i, (title, key, th) in enumerate(METRICS):
        v = stats[key]; lvl = sum(v >= t for t in th); rank = RANKS[lvl]; col = RCOL[rank]
        x = x0 + i * (cw + gap); cx = x + cw / 2
        out.append(f'<rect x="{x}" y="4" width="{cw}" height="162" rx="8" fill="{CARD}" stroke="{col}" stroke-width="2"/>')
        px = 6; ox = cx - 9 * px / 2
        cup = "".join(f'<rect x="{ox + c * px}" y="{22 + r * px}" width="{px}" height="{px}" fill="{col}"/>'
                      for r, row in enumerate(CUP) for c, ch in enumerate(row) if ch == "#")
        out.append(f'<g>{cup}<animateTransform attributeName="transform" type="translate" values="0 0;0 -4;0 0" '
                   f'dur="2.4s" begin="{i*0.25}s" repeatCount="indefinite"/></g>')
        if lvl:
            out.append(f'<rect x="{cx+30}" y="24" width="4" height="4" fill="#fff"><animate attributeName="opacity" '
                       f'values="0;1;0" dur="1.8s" begin="{i*0.4}s" repeatCount="indefinite"/></rect>')
        out.append(f'<text x="{cx}" y="108" font-size="9" fill="#C9D1D9" text-anchor="middle">{title}</text>')
        out.append(f'<text x="{cx}" y="130" font-size="14" fill="{YEL}" text-anchor="middle">{v}</text>')
        out.append(f'<text x="{cx}" y="154" font-size="10" fill="{col}" text-anchor="middle">RANK {rank}</text>')
    out.append("</svg>")
    return "\n".join(out)

def activity(series):
    W, H, L, R, T, B = 888, 260, 50, 24, 30, 46
    mx = max(4, max(c for _, c in series)); n = len(series)
    px = lambda i: L + i * (W - L - R) / (n - 1)
    py = lambda c: T + (H - T - B) * (1 - c / mx)
    pts = [(px(i), py(c)) for i, (_, c) in enumerate(series)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{L},{H-B} " + line + f" {px(n-1):.1f},{H-B}"
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><style>{CSS}</style>',
         f'<rect x="2" y="2" width="{W-4}" height="{H-4}" rx="10" fill="{CARD}"/>']
    for g in range(5):
        v = mx * g / 4; y = py(v)
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="{CYAN}" stroke-opacity=".15" stroke-dasharray="4 6"/>')
        o.append(f'<text x="{L-8}" y="{y+3:.1f}" font-size="8" fill="#C9D1D9" text-anchor="end">{round(v)}</text>')
    o.append(f'<polygon points="{area}" fill="{PINK}" fill-opacity=".15"/>')
    o.append(f'<polyline points="{line}" fill="none" stroke="{PINK}" stroke-width="3" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0">'
             f'<animate attributeName="stroke-dashoffset" from="1" to="0" dur="2.5s" fill="freeze"/></polyline>')
    for i, ((x, y), (d, c)) in enumerate(zip(pts, series)):
        o.append(f'<rect x="{x-3:.1f}" y="{y-3:.1f}" width="6" height="6" fill="{YEL}"><animate attributeName="opacity" '
                 f'values="0;1" dur="0.01s" begin="{2.5*i/n:.2f}s" fill="freeze"/></rect>')
        if i % 5 == 0 or i == n - 1:
            o.append(f'<text x="{x:.1f}" y="{H-B+22}" font-size="8" fill="#C9D1D9" text-anchor="middle">{d[5:]}</text>')
    o.append(f'<text x="{W/2}" y="{H-8}" font-size="8" fill="{CYAN}" text-anchor="middle">CONTRIBUTIONS / DAY - LAST 30 DAYS</text></svg>')
    return "\n".join(o)

if __name__ == "__main__":
    if "--demo" in sys.argv:
        stats = dict(stars=0, followers=0, commits=0, repos=0, prs=0, issues=0)
        today = datetime.date.today()
        series = [((today - datetime.timedelta(days=29 - i)).isoformat(), 0) for i in range(30)]
    else:
        stats, series = fetch()
    root = os.path.abspath(os.path.join(HERE, "..", ".."))
    os.makedirs(os.path.join(root, "assets"), exist_ok=True)
    open(os.path.join(root, "assets", "trophies.svg"), "w").write(trophies(stats))
    open(os.path.join(root, "assets", "activity.svg"), "w").write(activity(series))
    print("done", stats)
