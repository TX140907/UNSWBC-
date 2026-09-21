# Vòng lặp huấn luyện Leviathan

Đợt hiện tại: **3 vòng, tối đa tổng 20 game unranked**, chia 7–7–6,
đối thủ cách hạng hiện tại không quá 12. Không phải 20 game mỗi vòng.

```powershell
# Chạy từ thư mục gốc; chạy lại cùng lệnh để tiếp tục tiến trình đã lưu.
python battlecode_data/learning_loop.py --run
```

Script dùng key đã lưu bằng toolkit, `UNSWBC_API_KEY` hoặc `UNSWBC_KEY`;
nếu chưa có thì hỏi qua ô nhập ẩn. Không ghi key vào báo cáo.

## Mỗi vòng làm gì?

1. Đọc replay của chính team 128, giữ metadata map, submission, series và checksum.
2. Ước lượng trọng số rủi ro khi vùng nhìn có ít nhất hai đầu rồng địch hoặc
   tám đốt rồng địch. Chia theo kích thước map và độ dài bản thân dưới/từ 8.
   Điểm đích là điểm giữ mạng/chiều dài dòng con sau 10 vòng của hành động đã chơi.
3. Giữ các series nguyên vẹn ở train hoặc holdout; thiếu bằng chứng thì không
   đề xuất trọng số mới. Loại game có `noValidAction` khỏi tập fit.
4. Build ?ng vi?n, ch?y test chi?n thu?t v? protocol, r?i ??i ch?ng tr??c/sau tr?n **to?n b? map, c? A/B, v?i Kraken, mybot v? NamBot ???c ??ng b?ng** (120 tr?n khi c? 10 map). M?i map ???c ch?m ri?ng: th?ng 1, h?a 0,5, thua 0; ?i?m t?ng l? trung b?nh ??u gi?a c?c map. Thi?u b?t k? c?p ??i ch?ng n?o th? kh?ng c? ?i?m t?ng h?p l?. Lo?i ?ng vi?n l?m gi?m k?t qu? ? b?t k? ??i th?/map/ph?a n?o; k?t qu? ngang baseline c?ng kh?ng ?? ?? t? submit. Ph?i c? ?t nh?t m?t c?i thi?n th?c s?. `full-gate/map_scores.md` ghi ?i?m t?ng map v? th? t? ?u ti?n s?a.
5. Chỉ ứng viên qua gate mới được submit. Chờ server build và active, đối chiếu
   source trên server. Server tự active bản mới sau khi build thành công.
6. Tạo tối đa số game còn lại của vòng, chờ kết quả, tải replay và viết báo cáo.
   Dữ liệu mới được đưa vào lần fit tiếp theo. Ứng viên bị loại thì đấu tiếp
   bằng bản đang active để lấy thêm dữ liệu.

Vòng này chỉ train **tham số rủi ro trước áp lực nhìn thấy**, chưa tự viết lại
thuật toán split hoặc suy ra source đối phương. Thống kê replay không chứng minh
một hành động thay thế sẽ tốt hơn; local gate cũng không bảo đảm thắng online.
Không đọc thông tin ngoài vision vào bot. Hai map cùng kích thước có thể chia sẻ
trọng số; `mapPlan` nền vẫn giữ nguyên.

## Theo dõi

- `training_loop/campaign/report.md`: tiến trình tổng, phiên bản và ID battle.
- `training_loop/campaign/roundN/fit.json`: bằng chứng và trọng số đề xuất.
- `roundN/before`, `roundN/after`: đối chứng local, log và replay khi có ứng viên.
- `roundN/replays/report.md`: kết quả online riêng vòng đó.
- `loop_replays`: dữ liệu riêng team, có metadata để tránh nhầm phiên bản.
- `experiments/128/state.json`: sổ request dùng chung với `challenge_cycle.py`.

Script lưu ý định trước POST và không tự gửi lại khi kết quả POST không rõ.
Riêng HTTP 429 là yêu cầu đã bị từ chối: vòng lặp chờ `Retry-After` (hoặc 60 giây
nếu server không cung cấp) rồi thử lại yêu cầu đó; không gửi lại các game đã tạo.
Tổng thời gian chờ giới hạn trong một lần chạy là tối đa một giờ, sau đó giữ
checkpoint để tiếp tục sau. Hạn mức 60 game/giờ của server còn tính các yêu cầu
đội đã gửi bên ngoài script, nên đợt 20 game vẫn có thể phải chờ.
Đợt đã đủ 3 vòng thì chạy lại không tạo thêm game. Khi một tiến trình bị đóng
cưỡng bức, chỉ gỡ `experiments/128/cycle.lock` sau khi xác nhận nó đã dừng.
Lỗi build, thay đổi phiên bản bên ngoài, lỗi game hoặc schema API lạ đều dừng
để xem log; không âm thầm học dữ liệu bị gắn sai phiên bản.

## ??i ch?ng l?i ??t train c?

```powershell
python tests/paired_training.py
```

L?u ngu?n, executable, map v? checksum tr??c khi ch?y; kh?ng g?i API hay submit.
B?o c?o: `benchmark-results/training-paired/report.md` v? `map_scores.md`.
Vi?c so v?i bot local ch? s?ng l?c h?i quy, ch?a ch?ng minh th?ng c?c ??i online.
?i?m replay c? l? t?n hi?u ch?n v?n ?? ?? th? s?a, kh?ng thay th? ?i?m ??i ch?ng t?ng map.

## Campaign theo map (phi?n b?n 3)

L?nh ??t ???c y?u c?u: `python battlecode_data/learning_loop.py --run --map-campaign map-campaign-573-20260921`.
Ba v?ng, t?ng 20 game unranked (7/7/6), rank ?12. Ch?y l?i c?ng t?n ch? ti?p t?c checkpoint.
M?i v?ng t?o gi? thuy?t policy ri?ng t? c?c map c? tr?n thua trong replay c?a ??i.
Old/new ??u c?ng Kraken, mybot, NamBot ?? ??ng b?ng, ?? map v? hai ph?a.
Map c? ?i?m new cao h?n l?y policy new; b?ng/th?p h?n gi? old. C? th? ??i k?t qu? t?ng ph?a
n?u t?ng ?i?m c?a ch?nh map ?? t?ng. Kh?ng d?ng ?i?m t?ng c?c map ?? b? map b? y?u ?i.
B?n gh?p ???c ??u l?i to?n b?; ch? submit khi kh?ng map n?o gi?m v? c? map t?ng ?i?m.
Big Empty/help v? hai Queen t?m kh?ng ?? xu?t m?i do ??nh danh map c?n m? h?.
C?c ?? xu?t l? t?m ki?m tham s? c? gi?i h?n, kh?ng ph?i t? suy ra thu?t to?n t?i ?u t? replay.
Theo d?i `training_loop/map-campaign-573-20260921/roundN/map_scores.md`, `selection.json`,
`merged/map_scores.md`, `replays/report.md` v? `state.json` c?a campaign.
