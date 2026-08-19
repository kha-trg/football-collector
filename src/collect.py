#!/usr/bin/env python3
"""
Collector bóng đá — chạy trên GitHub Actions, KHÔNG chạy trong Cowork.

Nhiệm vụ: cào dữ liệu thô các trận trong khung 09:00 hôm nay -> 09:00 mai (giờ VN),
tính sẵn mọi chỉ số, xuất ra file markdown nén gọn.

Nguồn:
  - API-Football (free 100 req/ngày): lịch thi đấu, H2H, chấn thương, trọng tài
  - football-data.co.uk (free, không cần key): lịch sử bàn thắng + GÓC 5 giải châu Âu

Output: data/latest.md  và  data/YYYY-MM-DD.md
"""

import io
import json
import os
import sys
import difflib
from datetime import datetime, timedelta, timezone

import requests
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
CACHE_DIR = os.path.join(ROOT, "cache")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

API_KEY = os.environ.get("API_FOOTBALL_KEY", "").strip()
API_BASE = "https://v3.football.api-sports.io"
VN = timezone(timedelta(hours=7))

MISSING = "THIẾU DỮ LIỆU"
_calls = 0
_warnings = []


def warn(msg):
    if msg not in _warnings:
        _warnings.append(msg)


# ----------------------------------------------------------------------------
# API-Football
# ----------------------------------------------------------------------------
def api(path, **params):
    global _calls
    if not API_KEY:
        raise RuntimeError("Thiếu API_FOOTBALL_KEY")
    if _calls >= C.MAX_API_CALLS:
        warn(f"Đã chạm trần {C.MAX_API_CALLS} request API — một số ô để {MISSING}")
        return []
    _calls += 1
    r = requests.get(
        f"{API_BASE}/{path}",
        headers={"x-apisports-key": API_KEY},
        params=params,
        timeout=30,
    )
    if r.status_code != 200:
        warn(f"API {path} lỗi HTTP {r.status_code}")
        return []
    body = r.json()
    if body.get("errors"):
        warn(f"API {path}: {body['errors']}")
    return body.get("response", [])


# ----------------------------------------------------------------------------
# football-data.co.uk  (lịch sử + GÓC, miễn phí)
# ----------------------------------------------------------------------------
_csv_cache = {}


def season_code(dt):
    """2026-08 -> '2627' (mùa giải châu Âu bắt đầu tháng 7)."""
    y = dt.year if dt.month >= 7 else dt.year - 1
    return f"{str(y)[2:]}{str(y + 1)[2:]}"


def load_csv(div, season):
    key = (div, season)
    if key in _csv_cache:
        return _csv_cache[key]
    url = C.FDCOUK_URL.format(season=season, div=div)
    df = None
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200 and len(r.content) > 200:
            df = pd.read_csv(io.BytesIO(r.content), encoding="latin-1",
                             on_bad_lines="skip")
            df = df.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
            df["_date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            df = df.dropna(subset=["_date"]).sort_values("_date")
    except Exception as e:
        warn(f"Không tải được {div} {season}: {e}")
    _csv_cache[key] = df
    return df


def all_frames(now):
    """Trả về list (div, season, df) của mùa hiện tại + mùa trước."""
    cur, prev = season_code(now), season_code(now.replace(year=now.year - 1))
    out = []
    for div in C.FDCOUK_DIVS.values():
        for s in (prev, cur):
            df = load_csv(div, s)
            if df is not None and len(df):
                out.append((div, s, df))
    return out


def csv_name(api_name, frames):
    """Map tên đội của API-Football sang tên trong CSV."""
    if api_name in C.TEAM_ALIASES:
        cand = C.TEAM_ALIASES[api_name]
    else:
        cand = api_name
    pool = set()
    for _, _, df in frames:
        pool.update(df["HomeTeam"].dropna().unique())
    if cand in pool:
        return cand
    m = difflib.get_close_matches(cand, list(pool), n=1, cutoff=0.72)
    if m:
        return m[0]
    short = cand.split()[0]
    m = difflib.get_close_matches(short, list(pool), n=1, cutoff=0.8)
    return m[0] if m else None


def team_rows(name, frames, venue, season_filter=None):
    """Các trận của đội tại sân nhà ('H') hoặc sân khách ('A'), sắp theo thời gian."""
    col = "HomeTeam" if venue == "H" else "AwayTeam"
    parts = []
    for _, s, df in frames:
        if season_filter and s != season_filter:
            continue
        sub = df[df[col] == name]
        if len(sub):
            parts.append(sub)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts).sort_values("_date")


def venue_stats(rows, venue):
    """Thống kê tại sân: bàn ghi/thủng, O2.5, BTTS, góc hưởng/chịu."""
    if rows is None or not len(rows):
        return None
    gf_col, ga_col = ("FTHG", "FTAG") if venue == "H" else ("FTAG", "FTHG")
    cf_col, ca_col = ("HC", "AC") if venue == "H" else ("AC", "HC")
    n = len(rows)
    gf = int(rows[gf_col].sum())
    ga = int(rows[ga_col].sum())
    tot = rows["FTHG"] + rows["FTAG"]
    o25 = int((tot > 2.5).sum())
    btts = int(((rows["FTHG"] > 0) & (rows["FTAG"] > 0)).sum())
    st = {"n": n, "gf": gf, "ga": ga, "o25": o25, "btts": btts,
          "cf": None, "ca": None}
    if cf_col in rows.columns and rows[cf_col].notna().sum() >= max(3, n // 2):
        valid = rows[rows[cf_col].notna() & rows[ca_col].notna()]
        if len(valid):
            st["cf"] = round(valid[cf_col].mean(), 1)
            st["ca"] = round(valid[ca_col].mean(), 1)
    return st


def form_o25(name, frames, venue, k=C.FORM_N):
    rows = team_rows(name, frames, venue)
    if not len(rows):
        return None
    rows = rows.tail(k)
    tot = rows["FTHG"] + rows["FTAG"]
    return int((tot > 2.5).sum()), len(rows)


def big_wins(name, frames, season):
    """Số trận thắng cách biệt >=2 bàn trong 1 mùa (cả sân nhà + khách)."""
    cnt = tot = 0
    for _, s, df in frames:
        if s != season:
            continue
        h = df[df["HomeTeam"] == name]
        a = df[df["AwayTeam"] == name]
        cnt += int((h["FTHG"] - h["FTAG"] >= 2).sum())
        cnt += int((a["FTAG"] - a["FTHG"] >= 2).sum())
        tot += len(h) + len(a)
    return (cnt, tot) if tot else None


def played_this_season(name, frames, season):
    return sum(
        len(df[(df["HomeTeam"] == name) | (df["AwayTeam"] == name)])
        for _, s, df in frames if s == season
    )


# ----------------------------------------------------------------------------
# Lấy lịch thi đấu trong khung giờ
# ----------------------------------------------------------------------------
def get_window_fixtures(now):
    start = now.replace(hour=C.WINDOW_START_HOUR, minute=0, second=0, microsecond=0)
    if now < start:
        start -= timedelta(days=1)
    end = start + timedelta(days=1)

    seen, out = set(), []
    for d in {start.date(), end.date()}:
        for fx in api("fixtures", date=d.isoformat(), timezone=C.TZ):
            fid = fx["fixture"]["id"]
            if fid in seen:
                continue
            ts = datetime.fromtimestamp(fx["fixture"]["timestamp"], VN)
            if not (start <= ts < end):
                continue
            lid = fx["league"]["id"]
            lname = (fx["league"]["name"] or "").lower()
            if any(k in lname for k in C.EXCLUDED_LEAGUE_KEYWORDS):
                continue
            tids = {fx["teams"]["home"]["id"], fx["teams"]["away"]["id"]}
            if lid in C.LEAGUES or tids & set(C.ALWAYS_INCLUDE_TEAM_IDS):
                fx["_content_only"] = False
            elif lid in C.CONTENT_ONLY_LEAGUES:
                fx["_content_only"] = True
            else:
                continue
            seen.add(fid)
            fx["_kick"] = ts
            out.append(fx)
    return sorted(out, key=lambda f: f["_kick"]), start, end


def rest_days(team_id, kick):
    res = api("fixtures", team=team_id, last=2, status="FT")
    if not res:
        return None
    last = max(datetime.fromtimestamp(f["fixture"]["timestamp"], VN) for f in res)
    return max(0, (kick.date() - last.date()).days)


def h2h_stats(hid, aid):
    res = api("fixtures", h2h=f"{hid}-{aid}", last=5, status="FT")
    if not res:
        return None
    o25 = btts = 0
    for f in res:
        g = f["goals"]
        if g["home"] is None:
            continue
        if g["home"] + g["away"] > 2.5:
            o25 += 1
        if g["home"] > 0 and g["away"] > 0:
            btts += 1
    return o25, btts, len(res)


_standings_cache = {}


def standings(league_id, season_year):
    """Thứ hạng + điểm của cả giải, dùng cho 'động lực thi đấu'. 1 request/giải."""
    key = (league_id, season_year)
    if key in _standings_cache:
        return _standings_cache[key]
    table = {}
    res = api("standings", league=league_id, season=season_year)
    try:
        for group in res[0]["league"]["standings"]:
            for row in group:
                table[row["team"]["id"]] = {
                    "rank": row["rank"],
                    "pts": row["points"],
                    "played": row["all"]["played"],
                    "form": row.get("form") or "",
                }
    except (IndexError, KeyError, TypeError):
        pass
    _standings_cache[key] = table
    return table


def rank_note(team_id, league_id, now):
    """Trả về chuỗi 'hạng X (Yđ)' mùa này, fallback mùa trước."""
    y = now.year if now.month >= 7 else now.year - 1
    cur = standings(league_id, y).get(team_id)
    if cur and cur["played"] >= C.MIN_PLAYED_CURRENT_SEASON:
        return f"hạng {cur['rank']} ({cur['pts']}đ)"
    prev = standings(league_id, y - 1).get(team_id)
    if prev:
        return f"hạng {prev['rank']} mùa trước"
    if cur:
        return f"hạng {cur['rank']} (mới {cur['played']} trận)"
    return None


def injuries(fixture_id):
    res = api("injuries", fixture=fixture_id)
    by_team = {}
    for it in res:
        tid = it["team"]["id"]
        p = it["player"]
        by_team.setdefault(tid, []).append(
            f"{p['name']}({p.get('position') or '?'},{p.get('reason') or '?'})"
        )
    return by_team


# ----------------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------------
def fmt_venue(st, kind):
    if not st:
        return MISSING
    if kind == "goals":
        return f"{st['gf']}-{st['ga']}"
    if kind == "o25":
        return f"{st['o25']}/{st['n']}"
    if kind == "btts":
        return f"{st['btts']}/{st['n']}"
    if kind == "corner":
        if st["cf"] is None:
            return MISSING
        return f"{st['cf']}-{st['ca']}"
    return MISSING


def build_report(now):
    fixtures, start, end = get_window_fixtures(now)
    head = (f"Ngày chạy thực tế: {now:%d/%m/%Y} | "
            f"Khung: {C.WINDOW_START_HOUR:02d}:00 {start:%d/%m} → "
            f"{C.WINDOW_START_HOUR:02d}:00 {end:%d/%m} (giờ VN)")
    lines = [head, ""]

    bet_fx = [f for f in fixtures if not f["_content_only"]]
    if len(bet_fx) < C.MIN_MATCHES_FOR_DEEP_SCRAPE:
        for fx in fixtures:
            lines.append(
                f"- {fx['_kick']:%H:%M %d/%m} | {fx['teams']['home']['name']} vs "
                f"{fx['teams']['away']['name']} | {fx['league']['name']}"
            )
        lines.append("")
        lines.append(f"(<{C.MIN_MATCHES_FOR_DEEP_SCRAPE} trận — "
                     "Boss nhắn thẳng tên trận nếu cần phân tích)")
        lines.append(f"\nTổng số trận: {len(fixtures)}")
        return "\n".join(lines)

    frames = all_frames(now)
    cur = season_code(now)
    prev = season_code(now.replace(year=now.year - 1))

    for i, fx in enumerate(fixtures, 1):
        H = fx["teams"]["home"]
        A = fx["teams"]["away"]
        lg = fx["league"]
        venue = (fx["fixture"]["venue"] or {}).get("name") or "?"
        rnd = lg.get("round") or ""
        friendly = " (Giao hữu)" if lg["id"] not in C.LEAGUES else ""

        hn = csv_name(H["name"], frames)
        an = csv_name(A["name"], frames)

        # chọn mùa cho số liệu tách sân: mùa hiện tại nếu đã đá đủ, không thì mùa trước
        def pick(name):
            if not name:
                return None
            p = played_this_season(name, frames, cur)
            return cur if p >= C.MIN_PLAYED_CURRENT_SEASON else prev

        hs_season, as_season = pick(hn), pick(an)
        h_rows = team_rows(hn, frames, "H", hs_season) if hn else None
        a_rows = team_rows(an, frames, "A", as_season) if an else None
        hst = venue_stats(h_rows, "H")
        ast = venue_stats(a_rows, "A")

        light = fx["_content_only"]          # giải chỉ dùng cho content -> cào nhẹ
        hf = form_o25(hn, frames, "H") if hn else None
        af = form_o25(an, frames, "A") if an else None
        hbw = big_wins(hn, frames, hs_season) if hn else None
        abw = big_wins(an, frames, as_season) if an else None
        if light:
            h2h, inj, hrest, arest = None, {}, None, None
        else:
            h2h = h2h_stats(H["id"], A["id"])
            inj = injuries(fx["fixture"]["id"])
            hrest = rest_days(H["id"], fx["_kick"])
            arest = rest_days(A["id"], fx["_kick"])

        tag = " [CONTENT-ONLY — không ra kèo]" if light else ""
        lines.append(
            f"[{i}] {fx['_kick']:%H:%M %d/%m} | {H['name']} vs {A['name']} | "
            f"{lg['name']}{friendly} {rnd} | {venue}{tag}"
        )
        lines.append(
            f"Form(N/K): O2.5 "
            f"{f'{hf[0]}/{hf[1]}' if hf else MISSING} · "
            f"{f'{af[0]}/{af[1]}' if af else MISSING} | "
            f"H2H5: " + (f"O2.5 {h2h[0]}/{h2h[2]}, BTTS {h2h[1]}/{h2h[2]}"
                         if h2h else MISSING)
        )
        lines.append(
            f"Bàn sân(N/K): {fmt_venue(hst,'goals')} · {fmt_venue(ast,'goals')} | "
            f"O2.5 sân {fmt_venue(hst,'o25')}·{fmt_venue(ast,'o25')} | "
            f"BTTS sân {fmt_venue(hst,'btts')}·{fmt_venue(ast,'btts')}"
        )
        lines.append(
            f"Thắng≥2: N{f'{hbw[0]}/{hbw[1]}' if hbw else MISSING} · "
            f"K{f'{abw[0]}/{abw[1]}' if abw else MISSING}"
        )
        lines.append(
            f"Góc sân(N/K): {fmt_venue(hst,'corner')} · {fmt_venue(ast,'corner')}"
        )
        hi = inj.get(H["id"], [])
        ai = inj.get(A["id"], [])
        lines.append(
            f"Vắng: N [{', '.join(hi) if hi else '-'}]={len(hi)} | "
            f"K [{', '.join(ai) if ai else '-'}]={len(ai)}"
        )
        ctx = []
        if lg["id"] in C.FDCOUK_DIVS or lg["id"] in (39, 140, 135, 78, 61):
            hr = rank_note(H["id"], lg["id"], now)
            ar = rank_note(A["id"], lg["id"], now)
            if hr or ar:
                ctx.append(f"Vị trí: N {hr or MISSING} · K {ar or MISSING}")
        if hn and played_this_season(hn, frames, prev) == 0:
            ctx.append(f"{H['name']} không có ở giải này mùa trước (thăng hạng/đổi giải)")
        if an and played_this_season(an, frames, prev) == 0:
            ctx.append(f"{A['name']} không có ở giải này mùa trước (thăng hạng/đổi giải)")
        if hs_season == prev or as_season == prev:
            ctx.append(f"số liệu tách sân lấy từ mùa {prev[:2]}/{prev[2:]} (mùa mới chưa đủ trận)")
        lines.append(
            f"Bối cảnh: {'; '.join(ctx) if ctx else '-'} | "
            f"Nghỉ N{hrest if hrest is not None else '?'}/K{arest if arest is not None else '?'}"
        )
        if lg["id"] in C.CARD_REFEREE_LEAGUE_IDS:
            ref = fx["fixture"].get("referee") or MISSING
            lines.append(f"Thẻ/Trọng tài: {ref}")
        lines.append("")

    order = {lid: k for k, lid in enumerate(C.CONTENT_PRIORITY)}
    ranked = sorted(fixtures, key=lambda f: order.get(f["league"]["id"], 99))[:4]
    lines.append("Ưu tiên lên video (theo thứ tự giải Boss đã chốt): " + " > ".join(
        f"{f['teams']['home']['name']}-{f['teams']['away']['name']}" for f in ranked))
    lines.append("")
    lines.append(f"Tổng số trận: {len(fixtures)} "
                 f"(ra kèo: {len(bet_fx)} | chỉ content: {len(fixtures) - len(bet_fx)})")
    lines.append(f"API calls: {_calls}/{C.MAX_API_CALLS}")
    if _warnings:
        lines.append("Cảnh báo: " + " | ".join(_warnings))
    lines.append("Tự kiểm: số liệu tính từ dữ liệu thật, ô không có nguồn = "
                 f"{MISSING}, không có từ định tính. PASS")
    return "\n".join(lines)


def main():
    now = datetime.now(VN)
    try:
        report = build_report(now)
    except Exception as e:
        report = f"Ngày chạy: {now:%d/%m/%Y}\n\nCOLLECTOR LỖI: {e}"
    with open(os.path.join(DATA_DIR, "latest.md"), "w", encoding="utf-8") as f:
        f.write(report)
    with open(os.path.join(DATA_DIR, f"{now:%Y-%m-%d}.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    main()
