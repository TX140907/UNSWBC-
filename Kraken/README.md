# Kraken

Automated replay-guided training: [TRAINING.md](TRAINING.md).

```powershell
python battlecode_data/train_kraken.py --cycles 10 --pages 5 --limit 100
```

Kraken là nhánh phát triển trực tiếp từ Leviathan hiện tại. Giữ bộ beam search,
nhớ địa hình/thân, portal, tránh sprint mù và split cứu thân; chỉ thử thêm quy tắc
chiến thuật dựa trên [báo cáo replay](../battlecode_data/coaching/README.md).
Không sửa Leviathan, không sao chép mã đội khác, không dùng thông tin khuất trong
replay làm đầu vào khi thi đấu. Bộ chấm điểm offline chưa được gắn vào bot.

## Khác biệt đang thử

| Bằng chứng từ báo cáo | Thay đổi trong Kraken |
|---|---|
| Big Empty/Schooltime: đội thắng thường có đông quân và vẫn giữ con dài | Sinh sản cả ở vùng thoáng; thường tách con 2 khi dài 6. Nếu nhiều ngọc đang thấy và đội còn ít quân, có thể tách từ dài 4. |
| Queen Of Spades: số lần split không quyết định thắng; con mới phải sống được | Trên map lớn, kiểm tra cả đầu/đuôi có lối thoát và ít nhất 6 ô địa hình đã biết quanh đầu con mới, coi thân mẹ vẫn chiếm chỗ. |
| My Battles: mất con dài khi đội chỉ còn 1–2 con dẫn tới bị loại | Tăng thận trọng khi con dài và đội ít quân; thêm mức phạt đe dọa hai bước. Đây chỉ là xấp xỉ tầm sprint, chưa mô phỏng mọi sprint của địch. |
| Thắng Queen/Default bằng chiều dài dù ít quân hơn | Khi đủ 12 quân, một phần con dài giữ vai trò nuôi dài (`id % 4 == 0`); các con khác có thể tiếp tục bổ sung quân. |
| Đội thắng còn split cuối trận | Map lớn cho sinh quân tới trước vòng 420; nếu dưới 12 quân thì bổ sung tới trước vòng 480. |

Các ngưỡng 6 ô, 12 quân, 40/56 quân và mốc vòng là tham số thử nghiệm, không phải
giá trị tối ưu suy ra chắc chắn từ replay. Map nhỏ giữ chính sách sinh sản gốc
của Leviathan; đối chứng cần kiểm tra cả những map vốn đang thắng.

## Solo local

Chạy từ thư mục gốc repository. CLI tự build khi đưa tên thư mục:

```powershell
unswbc run maps/queen_of_spades.map Kraken Leviathan
unswbc run maps/queen_of_spades.map Leviathan Kraken
```

Bot viết trước là A, bot sau là B. Mở replay tạo ra bằng viewer Battlecode.

Kiểm tra protocol với executable đã build:

```powershell
g++ -std=c++20 -O2 Kraken/main.cpp -o Kraken/Kraken.exe
g++ -std=c++20 -O2 tests/kraken_strategy.cpp -o tests/kraken_strategy.exe
./tests/kraken_strategy.exe
python tests/protocol_smoke.py Kraken/Kraken.exe
```

Đợt đối chứng đầu tiên dùng Leviathan biên dịch từ mã hiện tại vào executable
riêng, thử đủ 10 map × A/B: **Kraken thắng 6, thua 14**, không hòa/lỗi/timeout.
Test chiến thuật Kraken và 12 test protocol đạt. Bản này chưa mạnh hơn Leviathan.

| Map | Kraken A | Kraken B |
|---|---|---|
| arena | Thua | Thắng |
| big_empty | Thua | Thua |
| Colosseum | Thua | Thua |
| default | Thua | Thua |
| default_small | Thua | Thắng |
| help | Thắng | Thắng |
| queen_of_spades | Thua | Thua |
| queen_of_spades_but_she_ages | Thua | Thua |
| schooltime | Thắng | Thua |
| trophy | Thua | Thắng |

Trên Big Empty, Kraken có tổng chiều dài cao hơn nhưng thua con dài nhất
(60–68 và 56–62). Mở rộng quân hoạt động, nhưng chưa cân bằng tốt việc nuôi
con chủ lực. Kết quả này không chứng minh riêng một quy tắc là nguyên nhân;
cần thử bỏ từng thay đổi để đối chiếu trước khi chọn bản tiếp theo.

[Báo cáo trận](../benchmark-results/kraken-v1-vs-leviathan/report.md) và
[quân số/chiều dài cuối](../benchmark-results/kraken-v1-vs-leviathan/standings.md);
`sources.json` ghi hash nguồn và executable. Không dùng
kết quả với bot cũ trên server thay cho đối chứng này. Chưa zip/push/upload.
