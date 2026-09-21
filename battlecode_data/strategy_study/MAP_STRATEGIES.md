# Học chiến thuật theo từng map

Phân tích 21 replay hoàn chỉnh đang có trong `top_replays`, `replays`, `all_replays`: 8 map, 5 series/nhóm, 5 tên đội. Riêng thư mục `top_replays` chỉ có 10 trận của Vibing++ và Sponge. Không coi tất cả replay tải về là bằng chứng các đội đang đứng top hiện tại. Các submission khác nhau được giữ riêng trong [bảng số liệu](measurements.md).

Đã đọc lại sự kiện, dựng lại trạng thái cuối và đối chiếu kết quả trong replay; kiểm tra SHA-256 theo metadata. Vòng dưới đây đếm từ 0. Đây là hành vi quan sát được; phần đề xuất cho Leviathan là giả thuyết cần đấu thử, không phải mã nguồn hay ý đồ đã biết của đối thủ.

## Queen Of Spades — chất lượng con tách ra quan trọng hơn số lần split

**Dữ liệu: 1 trận, match 2390.** Vibing++ submission 98 thắng Sponge submission 177 ở giới hạn 500 vòng.

- Vibing++ split 106 lần, Sponge 128 lần; quân tối đa tương ứng 19 và 20. Không phải bên đẻ nhiều hơn thắng.
- Con mới sống ít nhất 10 vòng: Vibing++ 74/106 (69,8%), Sponge 57/127 (44,9%). Những con sinh trong 10 vòng cuối không tính vào mẫu này.
- Vibing++ chỉ split 6 lần trong vòng 0–99, sau đó 69 lần trong 100–349 và 31 lần từ 350 trở đi. Sponge split 29 lần trong 100 vòng đầu.
- Vibing++ có 6 quân/dài nhất 3 ở cuối R99; 17 quân/dài nhất 4 ở R349; 15 quân/dài nhất 16 khi hết trận. Vừa tăng chiều dài cuối trận vừa tiếp tục sinh quân.
- Vibing++ có 18 lệnh sprint trong 4.825 lệnh MOVE; Sponge không sprint. Không đủ dữ liệu để quy chiến thắng cho sprint.

**Đề xuất:** kiểm tra lối ra và vùng trống ở đuôi trước khi sinh, tránh tách con vào ngăn chật. Duy trì quân dự phòng và một số con dài; không đặt mục tiêu cố đạt 64 quân trên map này. Không ngừng mọi sinh sản ngay R350.

**Xem lại:** [replay 2390](../top_replays/match_2390.replay), B: R28 bắt đầu split, R88 có lệnh `NE` ở (5,0); so sánh R99, R349, R449 và R499. Chỉ một trận nên chưa chốt được ngưỡng quân tối ưu.

## Big Empty — mở rộng mạnh, vẫn giữ con dài

**Dữ liệu: 2 trận, 2931 và 4141.** Vibing++ thắng cả hai, nhưng dùng submission 98 và 242 khác nhau.

- Cả hai lần split đầu ở R2, khi rồng dài 6. Kiểu `6 -> 4 + 2` cho phép vừa giữ thân chính vừa tạo con nhỏ; riêng trận 2931 kiểu này xuất hiện 100 lần.
- R99 bên thắng đã có 47 và 48 quân. Cả hai đạt đỉnh 64 quân; cuối trận còn 64 và 63 quân, dài nhất 46 và 31.
- Sau R350 vẫn có 67 và 70 split. Đối thủ có 16 và 6 split ở giai đoạn này, cuối trận còn 23 và 10 quân.
- Lệnh sprint của bên thắng chiếm khoảng 1,17% và 2,04% MOVE: có dùng nhưng không phải sprint liên tục.

**Đề xuất:** vùng mở nhiều thức ăn cần tăng quân sớm, không đợi thấy nhiều tường mới sinh sản. Thử tách con 2 từ thân dài 6 để giữ con mẹ dài 4. Cho phép tiến gần giới hạn quân khi còn không gian, bổ sung quân tới cuối trận, đồng thời bảo vệ các con dài.

**Xem lại:** [2931](../top_replays/match_2931.replay) A và [4141](../replays/match_4141.replay) B: R2, R49, R99, R349, R499. Cả hai đối thủ cũng từng đạt 64 quân: đạt giới hạn một lần chưa đủ.

## Arena — giao tranh sớm, sinh quân và khả năng sống phải đi cùng nhau

**Dữ liệu: 5 trận, 2388, 2933, 4140, 5529, 6125.** Tất cả kết thúc bằng loại hết một đội, sau 29–428 vòng.

- Bên thắng bắt đầu split R8–9 khi dài 4; số quân tối đa 15–21.
- SHINK thắng Vibing++ submission 242 ở cả hai phía trong 4140/5529; cuối trận còn 19/17 quân, dài nhất đều 4.
- All Roads Lead to Makuhari thắng Stockfish ở 6125 sau 41 vòng, còn 18 quân, dài nhất 3. Có 51 lệnh sprint/274 MOVE (18,6%), cao hơn nhiều mẫu Big Empty.
- Ở trận dài 2933, Vibing++ vẫn duy trì khoảng 10 quân ở R49, R99, R199, R349 dù đã split rất nhiều. Đẻ nhiều có thể chỉ bù tổn thất giao tranh.

**Đề xuất:** ưu tiên sống qua giao tranh đầu trận, đẻ từ chiều dài 4 và có sprint thoát va chạm khi thật sự hợp lệ. Không sao chép tỷ lệ sprint 18,6% thành quy tắc cố định: đây là lệnh yêu cầu, không đảm bảo mọi bước đều được thực hiện.

**Xem lại:** [6125](../all_replays/match_6125.replay) A, R9 split đầu, R11 lệnh `EE` từ (5,1); [5529](../replays/match_5529.replay) B, R8–20; [2933](../top_replays/match_2933.replay) A cho trận kéo dài.

## Colosseum — quân nhỏ thắng bằng loại đối thủ sớm

**Dữ liệu: 2 trận, 4142 và 5531.** Vibing++ submission 242 thắng SHINK ở cả hai phía sau 43 và 65 vòng.

- Split ngay R0 từ chiều dài 4. Tất cả 25/36 split của bên thắng đều là `4 -> 2 + 2`.
- Bên thắng còn 19/18 quân, dài nhất chỉ 3/4. SHINK chỉ đạt tối đa 4/7 quân.
- Chỉ 2/4 lệnh sprint: mẫu này không cần sprint nhiều để thắng.

**Đề xuất:** ưu tiên có nhiều con sống được sớm, không giữ một thân dài khi có thể tạo hai con có lối thoát. Đánh giá an toàn con mới sinh và hướng tránh đầu đối thủ; chưa cần tối ưu chiều dài cuối 500 vòng trong các thế giao tranh này.

**Xem lại:** [4142](../replays/match_4142.replay) B và [5531](../replays/match_5531.replay) A, từ R0 đến lúc loại hết đội kia.

## Default — tăng quân đầu/giữa trận, chuyển dần sang nuôi dài

**Dữ liệu: 4 trận, 2387, 2930, 4143, 5532.** Tất cả bên thắng split đầu R0, chiều dài 4; phần lớn split là `4 -> 2 + 2`.

- Sponge thắng 2387/2930 khi hết 500 vòng: cuối trận dài nhất 20/22, còn 14/7 quân.
- Trận 2387: R349 có 52 quân, dài nhất 3; R449 còn 17 quân, dài nhất 12; cuối trận dài nhất 20. Có chuyển đổi rõ từ nhiều con nhỏ sang con dài, nhưng không thể biết chỉ từ số liệu đó việc giảm quân là chủ động hay do bị giết.
- Vibing++ thắng 4143/5532 bằng loại đối thủ, cuối trận đều còn 40 quân, dài nhất 8/4.

**Đề xuất:** không dùng một mục tiêu duy nhất cho mọi trận Default. Tạo lực lượng trước; nếu giao tranh kéo dài thì giữ con dài trong khi bổ sung tổn thất. Không dừng sinh sản toàn đội chỉ vì đã qua R350.

**Xem lại:** [2387](../top_replays/match_2387.replay) A tại R349–499; [5532](../replays/match_5532.replay) A để đối chiếu kiểu thắng loại hết đối thủ.

## Default Small — tránh rơi xuống quá ít quân

**Dữ liệu: 3 trận, 2389, 2932, 5533.** Tất cả thắng bằng loại đối thủ sau 171, 228, 263 vòng.

- Bên thắng split đầu ở R9–10 khi dài 4; đạt đỉnh 16, 26, 36 quân. Bên thua đạt đỉnh 8, 4, 5 quân.
- Vibing++ thắng 2389 nhưng thua 2932; không thể lấy tên đội làm đại diện cho một chiến thuật luôn thắng.
- SHINK trong 5533 có split `5 -> 2 + 3` ở R152, `6 -> 2 + 4` ở R231: có giữ phần đuôi dài hơn đầu cũ, nhưng hình dạng split không tự chứng minh đó là một nước cứu khỏi ngõ cụt.

**Đề xuất:** ưu tiên tránh tuyệt chủng và phục hồi quân sớm. Giữ nhánh đảo phần thân dài làm con khi bị kẹt, nhưng không coi đó là thay thế cho sinh sản đầu trận.

**Xem lại:** [5533](../replays/match_5533.replay) B R152/R231 và [2932](../top_replays/match_2932.replay) để thấy đội ít quân bị loại dù có dùng sprint.

## Trophy — áp lực từ nhiều con sống được

**Dữ liệu: 3 trận, 2386, 2934, 5530.** Vibing++ thắng bằng loại đối thủ ở cả ba; submission 98/242 khác nhau.

- Quân cuối của bên thắng là 25, 38, 43; dài nhất 5, 11, 4. Đỉnh quân của đối thủ chỉ 8, 16, 9.
- Submission 98 thường giữ mẹ dài 3–4 rồi tách con 2: trong 2934 có 79 split `5 -> 3 + 2`, 68 split `6 -> 4 + 2`.
- Submission 242 ở 5530 lại có toàn bộ 64 split là `4 -> 2 + 2`. Không có một ngưỡng split duy nhất chung cho mọi bản bot.
- Trận dài 2934 vẫn có 56 split từ R350 trở đi.

**Đề xuất:** mở rộng quân khi lối ra còn tốt, không giữ trần 32 cứng trên mọi địa hình. Thử ngưỡng split 4 so với 5–6 bằng đối chứng; kiểm tra lối ra quan trọng hơn chỉ tăng số quân tối đa.

## Schooltime — nhiều quân và dài cùng lúc

**Dữ liệu: 1 trận, 4144.** Vibing++ submission 242 thắng SHINK ở giới hạn 500 vòng.

- R99 có 47 quân, dài nhất 6; R349 có 61 quân, dài nhất 18; cuối trận còn 63 quân, dài nhất 23. Đối thủ còn 6 quân, dài nhất 12.
- Split 434 lần, trong đó 138 lần từ R350. SHINK split 121 lần và chỉ 3 lần ở giai đoạn cuối.
- Có 207 sprint/24.375 MOVE (0,85%): nhiều quân không đồng nghĩa phải sprint nhiều.

**Đề xuất:** duy trì đội đông và tăng chiều dài đồng thời; không chuyển cả đội sang ngừng sinh sản vào cùng một vòng. Một trận chưa đủ chốt trần quân hay ngưỡng chiều dài.

**Xem lại:** [4144](../replays/match_4144.replay) B, R99/R349/R499.

## Điều cần thử ở Leviathan, theo thứ tự

1. **Queen Of Spades:** đo khả năng con tách sống được 10 vòng; kiểm tra không gian ở đuôi, không chỉ một ô thoát. Đây là mục tiêu sát vấn đề map hẹp nhất.
2. **Big Empty/Schooltime:** thêm sinh sản ở vùng mở có thức ăn; thử trần quân 48–64 khi có không gian. Code hiện tại chỉ bật sinh sản thường xuyên trên map nhỏ hoặc nhiều tường và giữ trần 32.
3. **Trophy/Default:** thay chuyển chế độ đồng loạt ở R350 bằng quyết định theo số quân, chiều dài cá thể, thức ăn và nguy hiểm. Dữ liệu cho thấy bên thắng vẫn tách muộn.
4. **Arena/Colosseum/Default Small:** dùng test tình huống đầu đối đầu, sprint hợp lệ và con mới sinh; tránh đánh đổi tỷ lệ sống chỉ để tăng số lần split.

Đây là các ứng viên để thử, chưa thay vào bot chỉ dựa trên replay. Không có mã đối thủ nên không thể chạy lại họ như một bot phản ứng được; phát lại các nước đi cũ cũng không tương đương đấu với họ.

**Thiếu dữ liệu:** chưa có replay cho `help` và `queen_of_spades_but_she_ages` trong ba thư mục đã đọc. Không áp nguyên chiến thuật Queen Of Spades sang bản biến thể khi chưa kiểm chứng.

Tái tạo số liệu: `python battlecode_data/study_strategies.py`. [JSON chi tiết](measurements.json) có hình dạng split, phân bố số quân lúc split, ví dụ sprint/split, timeline và submission ID cho từng trận. Script chỉ phân tích file local, không tải thêm hay sửa bot.
