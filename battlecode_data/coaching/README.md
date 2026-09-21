# Phân tích trận và hướng khắc chế cho Leviathan

## Phạm vi đã làm

- Đợt crawl công khai xét 100 game từ Top Battles/All Battles: 90 file mới, 10 đã có; cả 100 được kiểm tra checksum. Có 9 lỗi in tên Unicode trên terminal sau khi file đã lưu thành công; đã kiểm tra riêng file và sửa cách in của downloader. Xem `../replays/download_verification.json`.
- Tải 28 game thuộc 6 series đang được liên kết ở trang công khai team 128 — **An IQ too high?**. Đây không phải cam kết đã xuất hết lịch sử My Battles riêng tư. Không dùng API key/cookie.
- Gộp với dữ liệu có sẵn: **139 match ID, 135 nội dung replay khác nhau, 30 series, 8 map**. Dựng lại trạng thái cuối và đối chiếu với kết quả replay.
- 4 cặp replay của đội bạn giống hệt nội dung: 5584/5710, 5586/5712, 5587/5709, 5588/5713. Giữ đủ dòng trận để đối chiếu, chỉ lấy mẫu hành động một lần cho mỗi nội dung.
- **Mọi trận của đội bạn trong bộ này dùng submission 372.** Không coi đây là kiểm định bản mã local mới nhất.

## Đọc kết quả

- [Từng trận của bạn, nguyên nhân chết và các mốc mất quân](my_battles.md).
- [So sánh bên thắng theo từng map](maps.md).
- [Ba quyết định trước các lần mất con dài nhất/con cuối](decisive_positions.md).
- [Hàng đợi hành động cần xem lại, có điểm thực tế và điểm ước lượng](review_actions.md).
- [Định nghĩa điểm và kiểm định](action_scoring.md); dữ liệu máy đọc trong `matches.json`, `decisive_positions.json`, `scored_actions.jsonl.gz`, `action_model.json`.

## My Battles: thắng/thua vì đâu?

**15 thắng / 13 thua.** Bốn thắng trước risq-v kết thúc sau một vòng vì đối thủ chết với `noValidAction`; không dùng chúng để kết luận chiến thuật mạnh. Bỏ bốn trận này còn 11 thắng / 13 thua, vẫn có các replay trùng nội dung đã nêu trên.

| Map | Thắng / thua | Kết luận trong mẫu của đội bạn |
|---|---|---|
| Arena | 4 / 0 | Thắng bằng loại hết đối thủ, giữ được quân thay thế dù chết nhiều. |
| Colosseum | 3 / 1 | Sinh quân có ích nhưng chưa đủ: vẫn thua Peanut Butter #5808. |
| Default Small | 1 / 0 | Thắng Peanut Butter #5909 bằng loại đối thủ; mẫu chỉ một trận. |
| Queen Of Spades | 1 / 2 | #5711/#5910 mất con dài rồi bị loại; #6244 thắng bằng dài 65 so với 11 dù ít quân hơn. |
| Big Empty | 1 / 3 | Trận thắng là đối thủ không có hành động hợp lệ. Hai trận trùng nội dung mất con dài 37 do đầu đối đầu; #5911 thua chiều dài 51–55. |
| Schooltime | 2 / 4 | Một thắng do đối thủ lỗi; #6247 thắng thật khi còn 63 quân/dài nhất 20. Các trận thua bị loại sạch. |
| Trophy | 1 / 2 | Trận thắng do đối thủ lỗi; hai trận thua bị loại sau các va chạm đầu/thân. |
| Default | 2 / 1 | Một thắng do đối thủ lỗi; #6246 thắng dài 53–15, #5809 bị Peanut Butter loại sạch. |

### Ba thất bại khác nhau cần ba cách xử lý

1. **Ít quân + mất con chủ lực:** #5586/#5712 Big Empty, con 37 chết R105 do `hitHeadToHead`, khi lượt cuối chỉ còn một quân. #5711 Queen Of Spades, con 21 chết R298; lúc R297 còn hai quân. Cần dự phòng trước khi giao tranh, không đợi con chủ lực chết mới cứu.
2. **Bị ép vào hành lang không còn lựa chọn:** #5910, con 19 ở R263 chỉ có hướng N trống, nhưng ô N nằm trong tầm đi thường của đầu địch đang nhìn thấy. Con cuối dài 2 ở R303 bị khóa cả bốn hướng bởi tường/thân. Đổi hướng tại nước chết không giải quyết được; cần kiểm tra ngõ cụt và lựa chọn split/sprint từ trước.
3. **Sống nhưng thua điểm chiều dài:** #5911 Big Empty vẫn còn 10 quân, dài nhất 51; Peanut Butter còn 64 quân, dài nhất 55. Tránh chết chưa đủ; cần cân bằng mở rộng vùng lấy ngọc và giữ con dài tới cuối trận.

Một số con chết do đầu đối đầu dù quyết định cuối không có đe dọa một bước trong vùng nhìn. Chưa kết luận là sprint: cần kiểm tra chuỗi hành động đối phương, thứ tự lượt và portal. Bộ kiểm tra hiện chỉ liệt kê đe dọa đi thường một bước, không chứng minh ô đó an toàn tuyệt đối.

### Các trận thắng cũng chỉ ra điều không nên sửa quá tay

- #6244 Queen Of Spades: đội bạn **4 quân/dài 65**, đối thủ **18 quân/dài 11** — ít quân vẫn thắng nếu giữ được con dài tới giới hạn vòng.
- #6246 Default: đội bạn **4 quân/dài 53**, đối thủ **36 quân/dài 15**. Vì vậy không biến mọi cá thể dài thành đàn con nhỏ chỉ để tăng số quân.
- Arena/Colosseum thắng dù có nhiều lần tự đâm/đâm tường: thắng không đồng nghĩa từng hành động tốt. Xem các lỗi đó trong hàng đợi hành động, nhưng cũng phải kiểm tra liệu đã hết nước đi từ trước.

## Theo map: chiến thuật nào đáng thử nhất?

Các số dưới đây là trung vị của **bên thắng trong mẫu**, loại nội dung trùng và các trận một vòng có `noValidAction`. Đây là tương quan mô tả, **không chứng minh tối ưu** và không phải trần quân được đề xuất cứng.

| Map | Số trận | Đỉnh quân trung vị bên thắng | Dài nhất cuối trung vị | Thắng bằng loại đối thủ |
|---|---:|---:|---:|---:|
| Arena | 19 | 20 | 4 | 19/19 |
| Colosseum | 14 | 26 | 6 | 13/14 |
| Default Small | 13 | 21 | 5 | 9/13 |
| Queen Of Spades | 16 | 20 | 11 | 5/16 |
| Trophy | 17 | 39 | 6 | 12/17 |
| Default | 18 | 33,5 | 9 | 8/18 |
| Big Empty | 15 | 64 | 27 | 2/15 |
| Schooltime | 19 | 64 | 18 | 5/19 |

- **Arena/Colosseum/Default Small:** sinh quân nhỏ, bảo vệ lối ra và đối phó đầu địch; mục tiêu sớm là tránh bị loại, không tối đa chiều dài một con.
- **Queen Of Spades:** giữ quân dự phòng nhưng kiểm tra không gian con mới sinh; để các con dài an toàn tiếp tục lớn. Kiểm tra hành lang phía trước và tầm tấn công qua wrap/portal/sprint.
- **Trophy:** tăng quân khi có lối thoát, tiếp tục bù quân trong trận kéo dài; ít quân đã khiến bản 372 dễ bị loại.
- **Big Empty/Schooltime:** mở rộng sớm trên vùng thoáng có thức ăn, tăng quân theo không gian; giữ một nhóm con chủ lực thay vì chia nhỏ tất cả. Dữ liệu không ủng hộ việc chỉ sinh sản trên map nhỏ/nhiều tường.
- **Default:** cần cả hai chế độ: sinh quân để sống qua giao tranh và giữ con dài để thắng cuối trận. Chuyển theo tình trạng đội, không cùng một mốc R350 cho mọi cá thể.

Chưa có replay `help` và `queen_of_spades_but_she_ages` trong tập crawl này.

## Khắc chế từng đối thủ đã gặp

| Đối thủ | Kết quả của bạn | Hướng khắc chế cần thử |
|---|---|---|
| All Roads Lead to Makuhari | 4 thắng / 6 thua; gồm các cặp replay trùng | Trên map lớn/hẹp, tạo dự phòng trước và bảo vệ con dài khỏi giao tranh; không sao chép toàn bộ chiến thuật Arena vốn đã thắng. |
| Peanut Butter | 2 thắng / 7 thua | Ưu tiên đối chứng đối thủ này: chống khóa hành lang, giữ nhiều hướng thoát, mở rộng thu ngọc trên Big Empty; đừng chỉ tăng phạt va chạm ở nước cuối. |
| Quant Merch Trader | 5 thắng / 0 thua | Giữ lợi thế nuôi dài trên Queen/Default; dùng làm bộ kiểm tra hồi quy khi tăng split. |
| risq-v | 4 thắng / 0 thua, đều `noValidAction` ở vòng đầu | Không rút chiến thuật khắc chế từ các thắng này. |

Replay không chứa mã nguồn đối thủ. Không thể phát các nước đi cũ để giả làm đối thủ phản ứng đúng sau khi Leviathan đổi nước. Muốn xác nhận khắc chế cần bot đối chứng có hành vi tương tự hoặc trận ranked mới.

## Chấm điểm hành động đã làm

Điểm thực tế sau **10 vòng**:

`60 × dòng con còn sống + 30 × tỷ lệ giữ chiều dài con dài nhất (tối đa 1) + 10 × tăng tổng chiều dài/4 (chặn 0..1)`.

Con sinh ra sau hành động vẫn được tính nếu con mẹ chết; không lấy công của con đã sinh trước hành động. Loại các hành động không còn đủ 10 vòng để quan sát. Đây là mục tiêu tự chọn phục vụ review, không phải điểm chính thức của game.

Bộ ước lượng điều kiện theo kích thước map, mật độ tường nhìn thấy, giai đoạn trận, chiều dài/quân của mình, áp lực địch trong vùng nhìn và loại hành động. Không dùng đội thắng, sự kiện tương lai hay vị trí địch khuất làm input. Đặc trưng áp lực địch không tương đương biết chính xác thuật toán đối thủ.

- Học trên **105.450 hành động mẫu, 19 series công khai**.
- Kiểm định trên **31.249 mẫu, 5 series khác**; 30.753 mẫu đủ độ hỗ trợ để dự đoán.
- Sai số tuyệt đối trung bình: **14,91/100**, baseline đoán trung bình: **18,55/100** trên cùng mẫu được phủ.
- Toàn bộ **6 series của đội bạn bị loại khỏi tập học**.
- Chỉ dự đoán khi ngữ cảnh có ít nhất 30 mẫu từ 3 series; thiếu dữ liệu thì không chấm. Chưa có khoảng tin cậy hay chứng minh mức cải thiện này tăng win rate.

Đây là ước lượng kết quả của **loại hành động đã từng thấy**, không đánh giá hoàn chỉnh mọi hướng đi. Hai hướng có cùng đặc trưng có thể cùng điểm dù tương lai khác nhau. Không nạp trực tiếp vào Leviathan để điều khiển bot.

So sánh các lựa chọn ở một tình huống đã lưu:

```powershell
python battlecode_data/score_position.py --match 5910 --dragon 81
```

Công cụ loại nước đâm ngay vào tường/thân nhìn thấy, trả điểm khi đủ mẫu cho các lựa chọn còn lại. Lối ra portal/đuôi sau split và phản ứng địch vẫn cần bộ mô phỏng kiểm tra. Nó không khẳng định một nước chưa được chơi sẽ thắng.

## Kiểm chứng tiếp theo trước khi thay chính sách bot

1. Kiểm tra rủi ro **địch đi hai bước/sprint**, đặc biệt với con dài và lúc đội ít quân; giữ test chống sprint mù qua portal.
2. Thử sinh sản trên vùng thoáng giàu thức ăn, có quân dự phòng, giữ con dài theo vai trò; đối chứng cả map rộng lẫn các trận đang thắng bằng chiều dài.
3. Khi chọn split, đo vùng trống ở đầu con và dự báo bị khóa hành lang; theo dõi tỷ lệ con sống được 10 vòng, không chỉ số lần split.
4. Chạy cùng map/cả hai phía với bản hiện tại và bot đối chứng; dùng thắng/thua và chiều dài cuối làm tiêu chí chính, điểm 10 vòng là phụ. Giữ riêng tập map/đối thủ chưa dùng để chỉnh tham số.

**Trong lượt này chưa sửa `Leviathan/main.cpp` hoặc thay executable.** Đã hoàn thành crawl, đối chiếu thắng/thua, tạo bộ chấm offline và xác định các thử nghiệm khắc chế; chưa gọi một chiến thuật là tối ưu hay tuyên bố đánh bại đội top.

## Chạy lại

```powershell
python battlecode_data/download_public_battles.py --source both --pages 5 --limit 100 --out battlecode_data/replays
python battlecode_data/download_team_public.py --team-id 128 --out battlecode_data/my_replays
python battlecode_data/coach_replays.py
python battlecode_data/decisive_positions.py
python -m unittest discover -s tests -p test_coach.py
```

Downloader lấy danh sách tại thời điểm chạy, có giới hạn và có lưu manifest; `--pages 5` là giới hạn tối đa, không có nghĩa luôn đọc đủ 5 trang nếu đã đủ 100 game. Pipeline dùng cache theo checksum; dữ liệu replay không bị sửa.
