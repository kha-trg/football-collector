"""
Cấu hình cho Collector bóng đá.
Sửa file này nếu muốn thêm/bớt giải đấu hoặc đổi ngưỡng.
"""

TZ = "Asia/Ho_Chi_Minh"

# Khung giờ cào: từ HH:00 ngày chạy -> HH:00 ngày hôm sau (giờ VN)
WINDOW_START_HOUR = 9

# Dưới ngưỡng này thì KHÔNG cào sâu, chỉ liệt kê tên trận
MIN_MATCHES_FOR_DEEP_SCRAPE = 4

# ---- Giải đấu theo dõi (league id của API-Football) ----
LEAGUES = {
    39:  "Premier League",
    140: "La Liga",
    135: "Serie A",
    78:  "Bundesliga",
    61:  "Ligue 1",
    2:   "Champions League",
    531: "UEFA Super Cup",
    45:  "FA Cup",
    528: "Community Shield",
    1:   "World Cup",
    4:   "Euro",
    9:   "Copa America",
    5:   "Nations League",
    34:  "WC Qualifiers South America",
}

# Giải CHỈ dùng cho content TikTok (quét rộng), KHÔNG ra kèo.
# Cào nhẹ: chỉ lịch + số liệu miễn phí từ CSV, không tốn request API cho H2H/chấn thương.
CONTENT_ONLY_LEAGUES = {
    40:  "EFL Championship",
    3:   "Europa League",
    848: "Conference League",
}

# Thứ tự ưu tiên khi chọn trận lên video (id càng đứng trước càng ưu tiên)
CONTENT_PRIORITY = [2, 39, 45, 40, 531, 528, 3, 848, 140, 135, 78, 61]

# Giải bị loại hoàn toàn (AFF/ASEAN...)
EXCLUDED_LEAGUE_KEYWORDS = ["asean", "aff", "aseanship"]

# Đội luôn cào mọi trận, kể cả giao hữu
ALWAYS_INCLUDE_TEAM_IDS = {541: "Real Madrid"}

# Giải cần cào thẻ + trọng tài (chỉ ĐT Nam Mỹ)
CARD_REFEREE_LEAGUE_IDS = {9, 34}

# ---- Nguồn dữ liệu lịch sử miễn phí (football-data.co.uk) ----
# Có cột HC/AC (góc nhà/khách) -> dùng thay cho API để tiết kiệm request
FDCOUK_DIVS = {
    39:  "E0",
    40:  "E1",
    140: "SP1",
    135: "I1",
    78:  "D1",
    61:  "F1",
}
FDCOUK_URL = "https://www.football-data.co.uk/mmz4281/{season}/{div}.csv"

# Ngân sách request API-Football mỗi lần chạy (free tier = 100/ngày)
MAX_API_CALLS = 85

# Số trận gần nhất dùng cho "form"
FORM_N = 5

# Nếu mùa hiện tại đá dưới ngưỡng này thì lấy số liệu mùa trước
MIN_PLAYED_CURRENT_SEASON = 5

# Alias tên đội: API-Football -> football-data.co.uk
TEAM_ALIASES = {
    "Manchester United": "Man United",
    "Manchester City": "Man City",
    "Newcastle": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Wolves": "Wolves",
    "Sheffield Utd": "Sheffield United",
    "Tottenham": "Tottenham",
    "West Ham": "West Ham",
    "Brighton": "Brighton",
    "Leeds": "Leeds",
    "Atletico Madrid": "Ath Madrid",
    "Athletic Club": "Ath Bilbao",
    "Real Sociedad": "Sociedad",
    "Real Betis": "Betis",
    "Celta Vigo": "Celta",
    "Deportivo Alaves": "Alaves",
    "Rayo Vallecano": "Vallecano",
    "Real Valladolid": "Valladolid",
    "Cadiz": "Cadiz",
    "Espanyol": "Espanol",
    "Inter": "Inter",
    "AC Milan": "Milan",
    "Hellas Verona": "Verona",
    "Bayern Munchen": "Bayern Munich",
    "Bayer Leverkusen": "Leverkusen",
    "Borussia Dortmund": "Dortmund",
    "Borussia Monchengladbach": "M'gladbach",
    "Eintracht Frankfurt": "Ein Frankfurt",
    "FC Koln": "FC Koln",
    "VfB Stuttgart": "Stuttgart",
    "Werder Bremen": "Werder Bremen",
    "1899 Hoffenheim": "Hoffenheim",
    "FSV Mainz 05": "Mainz",
    "Paris Saint Germain": "Paris SG",
    "Olympique Marseille": "Marseille",
    "Olympique Lyonnais": "Lyon",
    "Stade Rennais": "Rennes",
    "Stade Brestois 29": "Brest",
    "AS Monaco": "Monaco",
    "LOSC Lille": "Lille",
    "Saint Etienne": "St Etienne",
}
