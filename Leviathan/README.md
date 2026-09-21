# Leviathan — UNSW Battlecode

Bot C++20. Mã nguồn nằm trong `main.cpp`; `helper.hpp` lấy từ toolkit unswbc 0.3.5. Các bot `mybot` và `NamBot` ban đầu được giữ nguyên.

## Chạy local

Từ thư mục gốc dự án:

```powershell
unswbc run maps/arena.map Leviathan NamBot
unswbc run maps/Colosseum.map NamBot Leviathan
```

Hiện đang phát triển và đánh giá local. Chưa push GitHub hoặc upload bot. ZIP tạo ở đợt trước là bản v1, không được cập nhật trong đợt này. Chạy bằng thư mục `Leviathan` để CLI biên dịch mã nguồn hiện tại.

## Chiến thuật

- Ghi nhớ địa hình, ngọc và vị trí thân của chính mình qua các lượt, kể cả phần thân ngoài tầm nhìn.
- Con dài vừa được tách giữ lại đoạn thân đã lần ra qua từng lượt, nối thêm khi quan sát được và giới hạn mô phỏng theo chiều dài thật; không xóa toàn bộ lịch sử chỉ vì chưa nhìn thấy hết đuôi.
- Dựng đồ thị đường đi có wrap và portal hai chiều; dùng BFS để tính khoảng cách tới ngọc thay vì chỉ dùng khoảng cách tọa độ.
- Trên bản đồ tối đa 256 ô: sinh sản sớm, giới hạn số rồng; rồng nhỏ ưu tiên thu ngọc và chừa lối thoát. Từ vòng 350 chuyển sang ưu tiên chiều dài.
- Với rồng dài và bản đồ lớn: beam search rộng 24, nhìn trước 14 bước sau nước đi đầu; mô phỏng va chạm, thân di chuyển và ngọc đã ăn. Xét cả diện tích có thể đi tới và nguy cơ đối đầu với đầu rồng khác.
- Chấm thêm không gian và lối thoát tại cuối cây tìm kiếm, tránh chọn đường có ngọc nhưng bị kẹt ngay sau giới hạn nhìn trước. Trên bản đồ nhỏ, đầu rồng đối phương chỉ có một lối đi được đánh giá nguy hiểm hơn đầu có nhiều lối thoát.
- Tăng tốc hai bước khi có thể giúp thoát hiểm; phân thân khẩn cấp khi đường đi sắp hết. Không coi ô đuôi hiện tại là trống.
- Với thân dài, đánh giá khả năng tìm đường về phía đuôi. Khi đầu cũ bị nhốt, thử tách `length - 2` đốt: đầu cũ còn 2 đốt, phần thân dài đảo chiều thành con mới ở đuôi cũ. Chỉ chọn khi mô phỏng con mới có đường sống tốt hơn, còn hạn mức rồng và phía đuôi không có nguy cơ đối đầu cao.
- Portal chưa biết đầu ra chỉ dùng khi không có nước đi đã biết an toàn.
- Buffer stdout, một lần flush tại `ENDTURN`; xử lý cả EOF và `ENDGAME`.

## Kiểm tra

Có bộ chạy và báo cáo tự động: `python tests/run_tests.py --suite quick`. Xem [hướng dẫn test](../tests/README.md) và [kết quả mới nhất](../benchmark-results/LATEST.md). Trong VS Code chọn task **Battlecode: local tests**.

```powershell
g++ -std=c++20 -O2 -Wall -Wextra -pedantic Leviathan/main.cpp -o Leviathan/Leviathan.exe
g++ -std=c++20 -O2 -Wall -Wextra -pedantic tests/strategy.cpp -o tests/strategy.exe
./tests/strategy.exe
python tests/protocol_smoke.py
python tests/benchmark.py --output benchmark-results/my-run
```

`tests/strategy.cpp` kiểm tra va chạm đuôi, tăng trưởng, không ăn hai lần cùng một ngọc, chi phí sprint, vật cản, wrap, portal, dựng lại thân, tránh ngõ cụt và chính sách phân thân đầu/cuối trận. Kiểm tra protocol chạy executable thật và xác nhận phản hồi cùng kết thúc sạch.

Các test cứu thân dài kiểm tra trường hợp tách 8 thành 2+6, đuôi không có lối thoát, đội đã đạt giới hạn rồng và tính hợp lệ của lệnh `SPLIT 6`. Mã nguồn v2 trước thay đổi này được giữ ở `tests/baselines/leviathan-v2`.

Kết quả phiên bản local mới nằm trong `benchmark-results/local-v2-nambot`, `local-v2-mybot` và `local-v2-vs-v1`. Mỗi thư mục có `results.json`, `metadata.json` ghi SHA-256 của executable và map, cùng log và replay. Benchmark đổi cả hai phía. CLI không cung cấp tùy chọn seed; đây không phải một khảo sát nhiều seed ngẫu nhiên.

Bản v1 trước đợt này thắng 24/26 trận, lưu ở `benchmark-results/release-*`. Mã nguồn v1 được giữ tại `tests/baselines/leviathan-v1` để đối chiếu, không trộn kết quả các phiên bản. Có thể chọn riêng phía bằng `--sides B` và bản đồ bằng `--maps arena` khi cần tái hiện một trận.

Bản local v2 thắng **25/26** trước NamBot (19/20) và mybot (6/6). Đấu trực tiếp v1 trên ba map, đổi phía: 3 thắng/3 thua. V2 vẫn thua NamBot trên `help` phía B; xem `benchmark-results/README.md` để đối chiếu các hồi quy. Đây là ứng viên để test tiếp, không phải kết luận mạnh hơn toàn diện.

Giới hạn: mô hình tìm kiếm giữ nguyên thân đối phương trong tương lai nên có thể đánh giá thận trọng quá mức khi đông quân; thông tin ngoài tầm nhìn có thể lỗi thời. Đấu native chưa đo ngân sách WASM 100 triệu CPU points của máy chấm: toolkit 0.3.5 chỉ hỗ trợ `--sandbox` cho Python. Kết quả trước hai bot cục bộ không chứng minh thứ hạng trên ladder.

## Luật đã đối chiếu

- [Structure / chấm điểm](https://game.battlecode.au/docs/structure): sống sót trước, rồi rồng dài nhất, tiếp theo tổng chiều dài.
- [Movement](https://game.battlecode.au/docs/movement) và [execution order](https://game.battlecode.au/docs/execution-order): va chạm kiểm tra trước khi đuôi dịch chuyển; mỗi bước sprint bổ sung mất một đốt.
- [Portals](https://game.battlecode.au/docs/kelp-and-portals), [splitting](https://game.battlecode.au/docs/splitting), [pearls](https://game.battlecode.au/docs/pearls).
- [Timeouts](https://game.battlecode.au/docs/timeouts) và [định dạng nộp](https://game.battlecode.au/docs/submitting).
