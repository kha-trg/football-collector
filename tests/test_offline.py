"""Kiểm thử logic tính toán bằng dữ liệu giả (không cần mạng, không cần API key)."""
import io, os, sys, random
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
os.environ.setdefault("API_FOOTBALL_KEY", "dummy")
import collect as K
import config as C

TEAMS = ["Arsenal", "Man City", "Liverpool", "Chelsea", "Everton", "Brentford"]


def fake_csv(season, seed):
    random.seed(seed)
    rows, d = [], datetime(2000 + int(season[:2]), 8, 10)
    for r in range(10):                       # 10 vòng
        random.shuffle(TEAMS)
        for i in range(0, len(TEAMS), 2):
            h, a = TEAMS[i], TEAMS[i + 1]
            rows.append({
                "Div": "E0", "Date": d.strftime("%d/%m/%Y"),
                "HomeTeam": h, "AwayTeam": a,
                "FTHG": random.randint(0, 4), "FTAG": random.randint(0, 3),
                "HC": random.randint(2, 11), "AC": random.randint(1, 9),
            })
        d += timedelta(days=7)
    df = pd.DataFrame(rows)
    df["_date"] = pd.to_datetime(df["Date"], dayfirst=True)
    return df.sort_values("_date")


def main():
    now = datetime(2026, 8, 19)
    cur, prev = K.season_code(now), K.season_code(now.replace(year=2025))
    assert (cur, prev) == ("2627", "2526"), (cur, prev)

    frames = [("E0", prev, fake_csv(prev, 1)), ("E0", cur, fake_csv(cur, 2))]

    # 1. map tên đội
    assert K.csv_name("Manchester City", frames) == "Man City"
    assert K.csv_name("Arsenal", frames) == "Arsenal"

    # 2. thống kê tại sân — đối chiếu tay
    rows = K.team_rows("Arsenal", frames, "H", cur)
    st = K.venue_stats(rows, "H")
    man_gf = int(rows["FTHG"].sum())
    man_o25 = int(((rows["FTHG"] + rows["FTAG"]) > 2.5).sum())
    man_btts = int(((rows["FTHG"] > 0) & (rows["FTAG"] > 0)).sum())
    assert (st["gf"], st["o25"], st["btts"]) == (man_gf, man_o25, man_btts)
    assert st["n"] == len(rows) and st["cf"] == round(rows["HC"].mean(), 1)

    # 3. sân khách phải đảo cột bàn thắng
    arows = K.team_rows("Arsenal", frames, "A", cur)
    ast = K.venue_stats(arows, "A")
    assert ast["gf"] == int(arows["FTAG"].sum())
    assert ast["ga"] == int(arows["FTHG"].sum())
    assert ast["cf"] == round(arows["AC"].mean(), 1)

    # 4. thắng cách biệt >=2
    bw, tot = K.big_wins("Arsenal", frames, cur)
    df = frames[1][2]
    h = df[df["HomeTeam"] == "Arsenal"]; a = df[df["AwayTeam"] == "Arsenal"]
    assert bw == int((h["FTHG"] - h["FTAG"] >= 2).sum()) + int((a["FTAG"] - a["FTHG"] >= 2).sum())
    assert tot == len(h) + len(a)

    # 5. form chỉ lấy 5 trận cuối
    o, n = K.form_o25("Arsenal", frames, "H")
    assert n == 5 and 0 <= o <= 5

    # 6. đội không tồn tại -> None, không crash
    assert K.venue_stats(K.team_rows("Doi Ma", frames, "H", cur), "H") is None
    assert K.form_o25("Doi Ma", frames, "H") is None
    assert K.fmt_venue(None, "goals") == K.MISSING

    # 7. thiếu cột góc -> báo THIẾU DỮ LIỆU chứ không bịa
    nog = frames[1][2].drop(columns=["HC", "AC"])
    st2 = K.venue_stats(nog[nog["HomeTeam"] == "Arsenal"], "H")
    assert K.fmt_venue(st2, "corner") == K.MISSING

    # 8. đội mới thăng hạng (không có ở mùa trước)
    assert K.played_this_season("Doi Moi Len", frames, prev) == 0

    print("PASS — tất cả kiểm thử logic tính toán")
    print(f"  Arsenal sân nhà {cur}: {st['gf']}-{st['ga']}, O2.5 {st['o25']}/{st['n']}, "
          f"BTTS {st['btts']}/{st['n']}, góc {st['cf']}-{st['ca']}")


if __name__ == "__main__":
    main()
