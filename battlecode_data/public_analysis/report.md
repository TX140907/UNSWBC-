# Phân tích replay Top Battles

Thời điểm phân tích (UTC): 2026-09-21T09:59:40.731027+00:00

10 trận; 2 nhóm series/match; 2 tên đội.

Mỗi hàng là một đội trong một trận. Sprint = lượt yêu cầu MOVE nhiều bước; split = sự kiện tách thành công. R ở bảng là vòng đếm từ 0. Đây là mô tả hành vi, không phải bằng chứng một chiến thuật gây ra chiến thắng.

| Match | Map | Đội | Kết quả | Số vòng | Split | Split đầu (R / độ dài trước) | Sprint / MOVE | Sonar | Rồng tối đa | Dài nhất cuối | Tổng dài cuối |
|---|---|---|---|---:|---:|---|---|---:|---:|---:|---:|
| [4140](https://game.battlecode.au/visualiser?match=4140) | Arena | SHINK AI 6500 | Thắng | 29 | 26 | 8 / 4 | 6 / 178 | 84 | 21 | 4 | 51 |
| [4140](https://game.battlecode.au/visualiser?match=4140) | Arena | Vibing++ | Thua | 29 | 5 | 11 / 4 | 9 / 36 | 0 | 2 | 0 | 0 |
| [4141](https://game.battlecode.au/visualiser?match=4141) | Big Empty | SHINK AI 6500 | Thua | 500 | 270 | 6 / 6 | 68 / 23485 | 1609 | 64 | 29 | 219 |
| [4141](https://game.battlecode.au/visualiser?match=4141) | Big Empty | Vibing++ | Thắng | 500 | 327 | 2 / 6 | 508 / 24892 | 0 | 64 | 31 | 821 |
| [4142](https://game.battlecode.au/visualiser?match=4142) | Colosseum | SHINK AI 6500 | Thua | 43 | 6 | 0 / 4 | 4 / 106 | 0 | 4 | 0 | 0 |
| [4142](https://game.battlecode.au/visualiser?match=4142) | Colosseum | Vibing++ | Thắng | 43 | 25 | 0 / 4 | 2 / 318 | 0 | 20 | 3 | 47 |
| [4143](https://game.battlecode.au/visualiser?match=4143) | Default | SHINK AI 6500 | Thua | 449 | 54 | 0 / 4 | 11 / 4336 | 81 | 18 | 0 | 0 |
| [4143](https://game.battlecode.au/visualiser?match=4143) | Default | Vibing++ | Thắng | 449 | 166 | 0 / 4 | 31 / 9616 | 0 | 48 | 8 | 147 |
| [4144](https://game.battlecode.au/visualiser?match=4144) | Schooltime | SHINK AI 6500 | Thua | 500 | 121 | 0 / 4 | 24 / 11156 | 542 | 40 | 12 | 48 |
| [4144](https://game.battlecode.au/visualiser?match=4144) | Schooltime | Vibing++ | Thắng | 500 | 434 | 0 / 4 | 207 / 24375 | 0 | 64 | 23 | 409 |
| [5529](https://game.battlecode.au/visualiser?match=5529) | Arena | Vibing++ | Thua | 45 | 17 | 9 / 4 | 21 / 104 | 0 | 7 | 0 | 0 |
| [5529](https://game.battlecode.au/visualiser?match=5529) | Arena | SHINK AI 6500 | Thắng | 45 | 50 | 8 / 4 | 12 / 340 | 204 | 20 | 4 | 48 |
| [5530](https://game.battlecode.au/visualiser?match=5530) | Trophy | Vibing++ | Thắng | 121 | 64 | 8 / 4 | 6 / 2309 | 0 | 44 | 4 | 105 |
| [5530](https://game.battlecode.au/visualiser?match=5530) | Trophy | SHINK AI 6500 | Thua | 121 | 17 | 10 / 4 | 2 / 520 | 8 | 9 | 0 | 0 |
| [5531](https://game.battlecode.au/visualiser?match=5531) | Colosseum | Vibing++ | Thắng | 65 | 36 | 0 / 4 | 4 / 520 | 0 | 19 | 4 | 50 |
| [5531](https://game.battlecode.au/visualiser?match=5531) | Colosseum | SHINK AI 6500 | Thua | 65 | 17 | 0 / 4 | 7 / 245 | 5 | 7 | 0 | 0 |
| [5532](https://game.battlecode.au/visualiser?match=5532) | Default | Vibing++ | Thắng | 176 | 67 | 0 / 4 | 5 / 2813 | 0 | 41 | 4 | 93 |
| [5532](https://game.battlecode.au/visualiser?match=5532) | Default | SHINK AI 6500 | Thua | 176 | 19 | 0 / 4 | 3 / 824 | 13 | 8 | 0 | 0 |
| [5533](https://game.battlecode.au/visualiser?match=5533) | Default Small | Vibing++ | Thua | 263 | 18 | 10 / 4 | 11 / 515 | 0 | 5 | 0 | 0 |
| [5533](https://game.battlecode.au/visualiser?match=5533) | Default Small | SHINK AI 6500 | Thắng | 263 | 89 | 9 / 4 | 5 / 5003 | 2262 | 36 | 13 | 100 |

## Các điểm cần xem lại trong viewer

Xem 5–10 vòng trước khi tách, sprint hoặc chết. So sánh vùng nhìn, lối thoát, pearl và vị trí đối thủ; không suy chiến thuật chỉ từ kết quả cuối.

- Match 4140 (Arena):
  - SHINK AI 6500 (A): số lần chết — hitHeadToHead: 6, hitOtherBody: 1, hitWall: 1.
  - Vibing++ (B): số lần chết — hitHeadToHead: 6.
- Match 4141 (Big Empty):
  - SHINK AI 6500 (A): số lần chết — hitHeadToHead: 256, hitOtherBody: 7.
  - Vibing++ (B): số lần chết — hitHeadToHead: 256, hitOtherBody: 8, hitSelf: 3.
- Match 4142 (Colosseum):
  - SHINK AI 6500 (A): số lần chết — hitHeadToHead: 7.
  - Vibing++ (B): số lần chết — hitHeadToHead: 7.
- Match 4143 (Default):
  - SHINK AI 6500 (A): số lần chết — hitHeadToHead: 58.
  - Vibing++ (B): số lần chết — hitHeadToHead: 96, hitSelf: 18, hitOtherBody: 16.
- Match 4144 (Schooltime):
  - SHINK AI 6500 (A): số lần chết — hitHeadToHead: 110, hitOtherBody: 4, hitWall: 4.
  - Vibing++ (B): số lần chết — hitHeadToHead: 176, hitOtherBody: 83, hitSelf: 115.
- Match 5529 (Arena):
  - Vibing++ (A): số lần chết — hitHeadToHead: 18.
  - SHINK AI 6500 (B): số lần chết — hitHeadToHead: 28, hitOtherBody: 5, hitWall: 1.
- Match 5530 (Trophy):
  - Vibing++ (A): số lần chết — hitHeadToHead: 19, hitSelf: 3, hitOtherBody: 1.
  - SHINK AI 6500 (B): số lần chết — hitHeadToHead: 17, hitWall: 2.
- Match 5531 (Colosseum):
  - Vibing++ (A): số lần chết — hitHeadToHead: 18, hitSelf: 1.
  - SHINK AI 6500 (B): số lần chết — hitHeadToHead: 18.
- Match 5532 (Default):
  - Vibing++ (A): số lần chết — hitHeadToHead: 27, hitSelf: 2, hitOtherBody: 2.
  - SHINK AI 6500 (B): số lần chết — hitHeadToHead: 23.
- Match 5533 (Default Small):
  - Vibing++ (A): số lần chết — hitHeadToHead: 20.
  - SHINK AI 6500 (B): số lần chết — hitHeadToHead: 32, hitOtherBody: 10, hitWall: 21.

## Cách sử dụng

- Giữ cả thắng và thua để nghiên cứu điểm mạnh và cách khắc chế.
- Kiểm tra giả thuyết bằng bot đã sửa đối đầu bot gốc trên cùng map, seed và cả hai phía.
- Để các trận cùng series trong cùng tập train/validation/test. 10 trận có thể chỉ là 2 series.
- Kết quả/đối thủ/toàn bản đồ trong báo cáo chỉ phục vụ phân tích; không dùng làm input bot ngoài vision.
- File JSON đi kèm chứa từng split, từng lần chết và timeline theo vòng để phân tích sâu hơn.
