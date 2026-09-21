# Phân tích replay Top Battles

Thời điểm phân tích (UTC): 2026-09-21T07:00:26.578790+00:00

10 trận; 2 nhóm series/match; 2 tên đội.

Mỗi hàng là một đội trong một trận. Sprint = lượt yêu cầu MOVE nhiều bước; split = sự kiện tách thành công. R ở bảng là vòng đếm từ 0. Đây là mô tả hành vi, không phải bằng chứng một chiến thuật gây ra chiến thắng.

| Match | Map | Đội | Kết quả | Số vòng | Split | Split đầu (R / độ dài trước) | Sprint / MOVE | Sonar | Rồng tối đa | Dài nhất cuối | Tổng dài cuối |
|---|---|---|---|---:|---:|---|---|---:|---:|---:|---:|
| [2931](https://game.battlecode.au/visualiser?match=2931) | Big Empty | Vibing++ | Thắng | 500 | 264 | 2 / 6 | 279 / 23878 | 0 | 64 | 46 | 738 |
| [2931](https://game.battlecode.au/visualiser?match=2931) | Big Empty | Sponge(Albert and Bob) | Thua | 500 | 230 | 2 / 6 | 0 / 25085 | 0 | 64 | 27 | 352 |
| [2934](https://game.battlecode.au/visualiser?match=2934) | Trophy | Vibing++ | Thắng | 464 | 202 | 10 / 4 | 68 / 11612 | 0 | 47 | 11 | 182 |
| [2934](https://game.battlecode.au/visualiser?match=2934) | Trophy | Sponge(Albert and Bob) | Thua | 464 | 130 | 17 / 4 | 0 / 3365 | 0 | 16 | 0 | 0 |
| [2930](https://game.battlecode.au/visualiser?match=2930) | Default | Vibing++ | Thua | 500 | 79 | 0 / 4 | 25 / 4816 | 0 | 16 | 13 | 23 |
| [2930](https://game.battlecode.au/visualiser?match=2930) | Default | Sponge(Albert and Bob) | Thắng | 500 | 125 | 0 / 4 | 0 / 7995 | 0 | 30 | 22 | 80 |
| [2933](https://game.battlecode.au/visualiser?match=2933) | Arena | Vibing++ | Thắng | 428 | 373 | 8 / 4 | 158 / 3697 | 0 | 15 | 14 | 41 |
| [2933](https://game.battlecode.au/visualiser?match=2933) | Arena | Sponge(Albert and Bob) | Thua | 428 | 273 | 9 / 4 | 0 / 2183 | 0 | 14 | 0 | 0 |
| [2932](https://game.battlecode.au/visualiser?match=2932) | Default Small | Vibing++ | Thua | 228 | 3 | 12 / 4 | 7 / 353 | 0 | 4 | 0 | 0 |
| [2932](https://game.battlecode.au/visualiser?match=2932) | Default Small | Sponge(Albert and Bob) | Thắng | 228 | 99 | 10 / 4 | 0 / 3491 | 0 | 26 | 3 | 53 |
| [2387](https://game.battlecode.au/visualiser?match=2387) | Default | Sponge(Albert and Bob) | Thắng | 500 | 209 | 0 / 4 | 0 / 14650 | 0 | 60 | 20 | 124 |
| [2387](https://game.battlecode.au/visualiser?match=2387) | Default | Vibing++ | Thua | 500 | 12 | 0 / 4 | 5 / 1133 | 0 | 8 | 5 | 5 |
| [2390](https://game.battlecode.au/visualiser?match=2390) | Queen Of Spades | Sponge(Albert and Bob) | Thua | 500 | 128 | 26 / 4 | 0 / 3250 | 0 | 20 | 3 | 7 |
| [2390](https://game.battlecode.au/visualiser?match=2390) | Queen Of Spades | Vibing++ | Thắng | 500 | 106 | 28 / 4 | 18 / 4825 | 0 | 19 | 16 | 93 |
| [2386](https://game.battlecode.au/visualiser?match=2386) | Trophy | Sponge(Albert and Bob) | Thua | 143 | 19 | 21 / 4 | 0 / 565 | 0 | 8 | 0 | 0 |
| [2386](https://game.battlecode.au/visualiser?match=2386) | Trophy | Vibing++ | Thắng | 143 | 39 | 13 / 4 | 3 / 1790 | 0 | 26 | 5 | 91 |
| [2389](https://game.battlecode.au/visualiser?match=2389) | Default Small | Sponge(Albert and Bob) | Thua | 171 | 40 | 14 / 4 | 0 / 702 | 0 | 8 | 0 | 0 |
| [2389](https://game.battlecode.au/visualiser?match=2389) | Default Small | Vibing++ | Thắng | 171 | 50 | 10 / 4 | 11 / 1312 | 0 | 16 | 5 | 47 |
| [2388](https://game.battlecode.au/visualiser?match=2388) | Arena | Sponge(Albert and Bob) | Thua | 112 | 70 | 8 / 4 | 0 / 482 | 0 | 10 | 0 | 0 |
| [2388](https://game.battlecode.au/visualiser?match=2388) | Arena | Vibing++ | Thắng | 112 | 88 | 8 / 4 | 39 / 940 | 0 | 16 | 20 | 70 |

## Các điểm cần xem lại trong viewer

Xem 5–10 vòng trước khi tách, sprint hoặc chết. So sánh vùng nhìn, lối thoát, pearl và vị trí đối thủ; không suy chiến thuật chỉ từ kết quả cuối.

- Match 2931 (Big Empty):
  - Vibing++ (A): số lần chết — hitHeadToHead: 171, hitSelf: 14, hitOtherBody: 18.
  - Sponge(Albert and Bob) (B): số lần chết — hitHeadToHead: 159, hitSelf: 29, hitOtherBody: 22.
- Match 2934 (Trophy):
  - Vibing++ (A): số lần chết — hitHeadToHead: 113, hitSelf: 31, hitOtherBody: 22.
  - Sponge(Albert and Bob) (B): số lần chết — hitWall: 14, hitHeadToHead: 91, hitSelf: 15, hitOtherBody: 12.
- Match 2930 (Default):
  - Vibing++ (A): số lần chết — hitHeadToHead: 66, hitSelf: 9, hitOtherBody: 6.
  - Sponge(Albert and Bob) (B): số lần chết — hitHeadToHead: 60, hitWall: 26, hitSelf: 16, hitOtherBody: 20.
- Match 2933 (Arena):
  - Vibing++ (A): số lần chết — hitHeadToHead: 269, hitOtherBody: 60, hitSelf: 37.
  - Sponge(Albert and Bob) (B): số lần chết — hitHeadToHead: 209, hitWall: 14, hitSelf: 22, hitOtherBody: 29.
- Match 2932 (Default Small):
  - Vibing++ (A): số lần chết — hitHeadToHead: 5.
  - Sponge(Albert and Bob) (B): số lần chết — hitHeadToHead: 5, hitWall: 31, hitSelf: 24, hitOtherBody: 19.
- Match 2387 (Default):
  - Sponge(Albert and Bob) (A): số lần chết — hitHeadToHead: 41, hitWall: 59, hitSelf: 56, hitOtherBody: 43.
  - Vibing++ (B): số lần chết — hitHeadToHead: 15.
- Match 2390 (Queen Of Spades):
  - Sponge(Albert and Bob) (A): số lần chết — hitSelf: 46, hitWall: 35, hitHeadToHead: 37, hitOtherBody: 9.
  - Vibing++ (B): số lần chết — hitHeadToHead: 43, hitSelf: 39, hitOtherBody: 11.
- Match 2386 (Trophy):
  - Sponge(Albert and Bob) (A): số lần chết — hitHeadToHead: 10, hitWall: 3, hitSelf: 4, hitOtherBody: 4.
  - Vibing++ (B): số lần chết — hitHeadToHead: 14, hitSelf: 1, hitOtherBody: 1.
- Match 2389 (Default Small):
  - Sponge(Albert and Bob) (A): số lần chết — hitHeadToHead: 29, hitOtherBody: 1, hitWall: 10, hitSelf: 2.
  - Vibing++ (B): số lần chết — hitHeadToHead: 31, hitSelf: 4, hitOtherBody: 1.
- Match 2388 (Arena):
  - Sponge(Albert and Bob) (A): số lần chết — hitHeadToHead: 55, hitOtherBody: 6, hitSelf: 7, hitWall: 3.
  - Vibing++ (B): số lần chết — hitHeadToHead: 59, hitSelf: 9, hitOtherBody: 10.

## Cách sử dụng

- Giữ cả thắng và thua để nghiên cứu điểm mạnh và cách khắc chế.
- Kiểm tra giả thuyết bằng bot đã sửa đối đầu bot gốc trên cùng map, seed và cả hai phía.
- Để các trận cùng series trong cùng tập train/validation/test. 10 trận có thể chỉ là 2 series.
- Kết quả/đối thủ/toàn bản đồ trong báo cáo chỉ phục vụ phân tích; không dùng làm input bot ngoài vision.
- File JSON đi kèm chứa từng split, từng lần chết và timeline theo vòng để phân tích sâu hơn.
