# Football Collector — cào dữ liệu bóng đá tự động

Thay thế task **"Collector new"** đang chạy trong Cowork.
Toàn bộ việc nặng chuyển sang **GitHub Actions** (miễn phí), Cowork chỉ đọc kết quả.

| | Trước | Sau |
|---|---|---|
| Nơi cào | Cowork (Sonnet, 50-60 lần WebSearch) | GitHub Actions (script Python) |
| Token/ngày | ~200.000-400.000 | ~3.000-5.000 |
| Dữ liệu góc | Hay `THIẾU DỮ LIỆU` | Có đủ 5 giải châu Âu |
| Chi phí tiền | 0 | 0 |

---

## Cần chuẩn bị (làm hết trên trình duyệt, KHÔNG cài gì lên máy công ty)

### 1. Tài khoản GitHub — 2 phút
- Vào https://github.com/signup, đăng ký bằng email.
- Ghi nhớ **username** (ví dụ `khadeptrai021`).

### 2. API key bóng đá miễn phí — 3 phút
- Vào https://dashboard.api-football.com/register
- Đăng ký gói **Free** (100 request/ngày — dư dùng, script chỉ tốn ~26).
- Vào mục **Account** → copy chuỗi **API Key** (dài ~32 ký tự).
- ⚠️ Đây là mật khẩu — không paste công khai ở đâu.

### 3. Tạo repo và dán key
- Vào https://github.com/new → tên repo `football-collector` → chọn **Private** → **Create**.
- Upload toàn bộ file trong thư mục này lên repo (nút **uploading an existing file**).
- Vào **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
  - Name: `API_FOOTBALL_KEY`
  - Secret: dán API key vừa copy
  - → **Add secret**

### 4. Chạy thử
- Tab **Actions** → chọn *Cao du lieu bong da hang ngay* → **Run workflow**.
- Đợi ~1 phút → vào thư mục `data/` xem file `latest.md`.

Xong. Từ đó mỗi ngày **06:30 giờ VN** nó tự chạy và tự cập nhật `data/latest.md`.

---

## Cowork lấy dữ liệu thế nào

Chỉ 1 lệnh, không tốn WebSearch:

```
curl -s https://raw.githubusercontent.com/<username>/football-collector/main/data/latest.md
```

Nếu repo để **Private** thì cần thêm token đọc; để **Public** thì lệnh trên chạy thẳng.
(Repo public không lộ API key — key nằm trong Secrets, không nằm trong code.)

---

## Cấu trúc

```
src/config.py     ← sửa giải đấu, ngưỡng, alias tên đội ở đây
src/collect.py    ← script cào chính
tests/            ← kiểm thử logic tính toán (chạy không cần mạng/key)
.github/workflows/daily.yml  ← lịch chạy 06:30 VN
data/latest.md    ← kết quả mới nhất (file Cowork sẽ đọc)
data/YYYY-MM-DD.md ← lưu trữ theo ngày
```

## Nguồn dữ liệu

| Trường | Nguồn |
|---|---|
| Lịch thi đấu, H2H, chấn thương, trọng tài | API-Football (free) |
| Bàn thắng/thủng tách sân, O2.5, BTTS, **góc**, thắng ≥2 bàn | football-data.co.uk (free, không cần key) |

Ô nào không có nguồn thật → ghi đúng chuỗi `THIẾU DỮ LIỆU`, **không bịa số**.

## Lưu ý mùa giải mới

Tháng 8 mùa mới chưa đá đủ trận → script **tự động lấy số liệu mùa trước**
và ghi rõ trong dòng `Bối cảnh`. Đây là lỗi mà prompt Collector cũ hay mắc
(đòi số `x/19`, `x/38` trong khi mùa mới mới đá 1-2 vòng).
