# Kiểm tra ngày 21/09/2026

- Parser đối chiếu với decoder JavaScript của viewer chính thức: 519 event có
  cùng loại và các payload được kiểm tra (ID, round, countdown, facing, text,
  action và các tọa độ), cùng map text.
- Replay arena thật: 52 observation trích ra khớp từng giá trị với input engine
  gửi cho bot khi chạy lại các action đã ghi. Bao gồm multi-step moves.
- Replay tự đấu 500 vòng: 24.506 observation khớp input engine; bao gồm tạo nhiều
  rồng con. Tổng độ dài, độ dài lớn nhất và số rồng cuối trận khớp result.
- Trận kiểm tra portal/split/sonar: 33 observation khớp input engine; xác nhận
  teleport, split và nhận sonar trong cùng vòng theo thứ tự ID.
- Tổng cộng **24.591 observation** được đối chiếu với engine chính thức.
- HTTP giả lập xác nhận Authorization và Origin không đi theo redirect sang
  kho replay; nhận diện response danh sách; ZIP dùng tên file do script tạo,
  không dùng đường dẫn nhúng trong archive.
- Trainer và inference JSON chạy thử thành công trên dữ liệu nhân tạo. Chỉ
  kiểm tra đường chạy; không công bố accuracy đó như chất lượng thi đấu.

## Bổ sung: dữ liệu công khai Top Battles

- Đọc trực tiếp HTML Top Battles và link `/visualiser?match=ID` ngày 21/09/2026.
- Đối chiếu đường `GET /api/matches/ID/replay` trong JavaScript của viewer
  chính thức; tải được replay thật mà không gửi API key hoặc cookie.
- Kho replay gửi gzip qua HTTP. Cả hai downloader đã được sửa để giải nén
  có giới hạn kích thước; kiểm tra gzip bằng response giả lập cho cả hai.
- Trích metadata thật của match 2931 và series ID; các trận cùng series có
  cùng `group_id`. Không thực thi JavaScript nhúng trong HTML.
- Match 2931: giải mã đầy đủ 500 vòng, tạo được 49.457 observation/action.
  Trạng thái cuối tự dựng khớp số rồng, độ dài tối đa và tổng độ dài trong result.
  Đây là kiểm tra replay thực tế và trạng thái cuối; không gọi đó là đối chiếu
  từng observation với input engine như 24.591 observation ở phần trước.
- Các thống kê split/sprint/chết trong report được lấy từ event thật; không
  suy luận hoặc tuyên bố đã khôi phục thuật toán/source code của đối thủ.
- Tải thành công 10/10 game Top Battles: 2931, 2934, 2930, 2933, 2932,
  2387, 2390, 2386, 2389, 2388; thuộc 2 series. Giải mã toàn bộ event và
  dựng lại trạng thái cuối của cả 10 game, khớp result. Report kèm ZIP.
- Kiểm tra resume với 2931/2934: checksum đúng, không gửi request nào để tải lại.

## Bổ sung: All Battles và hai nguồn chung

- Đọc trực tiếp `/battles` và `/battles?page=2`: mỗi trang có 25 link series,
  xác nhận link trang kế tiếp thật và việc danh sách dịch chuyển khi có game mới.
- Link `/battles/6061` chuyển tới viewer; đọc được đủ 5 game completed
  6061–6065 trong series, thay vì chỉ tải game đầu.
- Kiểm tra bằng fixture hai trang: khử trùng giữa Top/All, khử trùng series
  lặp giữa các trang, bỏ game pending, dừng đúng giới hạn trước trang tiếp theo.
- Chạy thực tế `download_public_battles.py --source all --pages 1 --limit 1`:
  tải thành công game 6125, All Roads Lead to Makuhari vs Stockfish, map Arena.
  File thật và metadata có trong `all_replays/`. Toàn bộ event giải mã hợp lệ.
- Chưa quét toàn bộ lịch sử website; các ví dụ 5 trang/100 game là giới hạn
  người dùng có thể chọn, không phải tuyên bố đã tải 100 game trong lần kiểm tra.

Các kiểm tra chạy trên Linux; chưa thử trực tiếp trên Windows. Script dùng
Python và đường dẫn portable. API riêng của team (`download_battles.py`) chưa
được kiểm tra với key người dùng; đường tải công khai Top Battles đã tải thật.
Chưa train model hoặc kiểm chứng một chiến thuật mới thắng trên ladder.
