# Battlecode: tải replay và tạo dataset

## Phân tích đội An IQ too high? và chấm hành động

Xem [báo cáo tổng hợp mới](coaching/README.md): 139 match ID từ dữ liệu công khai,
gồm 28 game của team 128; phân tích từng map, thắng/thua, quyết định trước khi
mất con dài/con cuối, bộ chấm điểm offline và hướng thử khắc chế.

```powershell
# Chạy từ thư mục gốc repository
python battlecode_data/download_team_public.py --team-id 128 --out battlecode_data/my_replays
python battlecode_data/coach_replays.py
python battlecode_data/decisive_positions.py
python battlecode_data/score_position.py --match 5910 --dragon 81
```

Trang đội công khai chỉ cung cấp các series đang liên kết, không thay thế xuất
toàn bộ My Battles riêng tư. Bộ chấm chưa được gắn vào Leviathan và không chứng
minh chiến thuật tối ưu; xem định nghĩa, tập kiểm định và giới hạn trong báo cáo.

Bộ công cụ Python cho UNSW Battlecode. Định dạng replay được kiểm tra với
toolkit `unswbc 0.3.5` ngày 21/09/2026.

## Top Battles và All Battles bằng một script

Chạy trong folder `battlecode_data`:

```powershell
# Chỉ các trận trên Top Battles
uv run download_public_battles.py --source top

# All Battles: đọc tối đa 5 trang, lấy tối đa 100 game đã hoàn thành
uv run download_public_battles.py --source all --pages 5 --limit 100

# Cả hai nguồn, gộp theo match ID
uv run download_public_battles.py --source both --pages 5 --limit 100
```

Chọn **một** lệnh phù hợp, không cần chạy cả ba. Dữ liệu cùng lưu ở `replays/`;
trận đã có file và checksum đúng được bỏ qua. Không cần API key.
`--limit` là số game độc nhất được xét trong lần chạy, **bao gồm game đã có**,
không phải số file mới tải. `--pages` chỉ áp dụng cho All Battles.

All Battles hiện hiển thị 25 dòng mỗi trang. Một dòng có thể là series gồm
nhiều game: script mở link Watch replay, đọc danh sách game, bỏ game pending/
running/failed và lấy các game completed. Khi đạt giới hạn game thì dừng,
kể cả còn trang chưa đọc. Cùng series vẫn có cùng group_id để tránh rò rỉ
giữa train và test.

Để đi tiếp các trang cũ hơn:

```powershell
uv run download_public_battles.py --source all --start-page 6 --pages 5 --limit 100
```

Danh sách có thể dịch chuyển khi có trận mới; đây là thu thập có giới hạn,
không bảo đảm chụp đủ toàn bộ lịch sử tại một thời điểm. Script đi theo link
trang kế tiếp thật, dừng nếu không còn trang, không dò các ID liên tiếp.
Nếu muốn xem ID trước khi tải file nhị phân, thêm `--list-only`.

Phân tích và tạo dataset từ thư mục chung:

```powershell
uv run analyze_replays.py replays --out public_analysis
uv run make_dataset.py replays --output public_dataset.jsonl.gz
```

ZIP vẫn kèm 10 replay Top Battles cũ ở `top_replays/`. Nếu muốn gom dữ liệu mới
ngay vào đó và dùng lại các file cũ, thêm `--out top_replays` vào lệnh tải,
rồi dùng thư mục `top_replays` làm đầu vào phân tích/dataset.

## Tải đúng các trận trên Top Battles (mới)

Bản ZIP cập nhật kèm sẵn **10 replay thật** trong `top_replays/` và báo cáo
`top_analysis/report.md`, lấy ngày 21/09/2026. Bạn có thể mở xem ngay.
Đây là 10 game thuộc 2 series, giữa Vibing++ và Sponge(Albert and Bob),
không phải 10 cặp đối thủ độc lập. Không cần tải lại các file mẫu này.

Trong Terminal của VS Code, vào folder `battlecode_data` rồi chạy:

```powershell
uv run download_top_battles.py
uv run analyze_replays.py top_replays --out top_analysis
```

**Không cần API key.** Script đọc liên kết `/visualiser?match=ID` đang hiện trên
https://game.battlecode.au/top-battles, lấy metadata công khai của từng trận,
rồi gọi `GET /api/matches/ID/replay` như viewer chính thức. Đây là đường tải
đã kiểm tra trên website ngày 21/09/2026, không phải API liệt kê trận của team.
Nếu website đổi, cần cập nhật script.

- `top_replays/`: các file `.replay`, metadata đội, map, submission ID và series ID.
- `top_analysis/report.md`: bảng so sánh split, sprint, sonar, độ dài và nguyên nhân chết.
- `top_analysis/report.json`: thêm từng sự kiện split/chết và timeline độ dài theo vòng.
- Mở file `.replay` bằng extension VS Code để xem tình huống trước mỗi sự kiện.

Chạy lại lệnh tải khi muốn cập nhật: trận đã có đúng checksum được bỏ qua;
script không xóa các trận cũ. Mỗi lần chỉ đọc danh sách hiện tại, không tự quét
ID, không lấy được các trận từng xuất hiện rồi rời khỏi trang mà chưa tải.

Top Battles hiện mô tả là 10 trận có Elo trung bình cao nhất trong 24 giờ qua.
10 trận có thể là 2 series của cùng 2 đội, chưa phải dataset đa dạng. Khi cần
bổ sung một trận công khai cụ thể, lấy số sau `match=` ở link Watch replay:

```powershell
uv run download_top_battles.py --ids 2931 2934
```

Hai ID này là trận thật được kiểm tra ngày 21/09/2026; hãy dùng ID hiện trên
trang của bạn. Có thể lấy link từ All battles khi muốn thêm đối thủ hoặc map.
Script tự nhóm theo **seriesId** để các game cùng một series không bị tách
sang train và test. Giữ cả đội thắng lẫn đội thua để phân tích cách khắc chế.

Tạo dataset từ các replay đã tải:

```powershell
uv run make_dataset.py top_replays --output top_dataset.jsonl.gz
```

Sau khi đã có đủ nhiều series độc lập ở cả train/validation/test mới chạy:

```powershell
uv run --with scikit-learn train_baseline.py top_dataset.jsonl.gz
```

Hai series chưa đủ để đánh giá khả năng khái quát. Decision Tree này chỉ học
hướng đi một bước; để tìm chiến thuật, ưu tiên report và xem replay, đề xuất
một thay đổi cụ thể rồi đấu bot mới với bot gốc trên nhiều map và cả hai phía.
Replay không chứa source code hoặc toàn bộ suy nghĩ của bot đối thủ.

### Từ replay đến thay đổi chiến thuật

1. Chọn một trận thắng và một trận thua trên cùng map. Mở chúng trong viewer.
2. Trong `report.json`, xem các trường `splits`, `deaths` và `timeline` để tìm
   đúng vòng đáng chú ý; quay lại 5–10 vòng trước đó trong replay.
3. Ghi một giả thuyết có thể kiểm tra, ví dụ: "tách ở độ dài 6 giúp thu pearl
   trên map thoáng", hoặc "sprint một bước bổ sung giúp né đầu đối phương".
   Kiểm tra vị trí, đường thoát của cả hai rồng và độ dài bị tiêu hao trước khi
   biến quan sát đó thành rule. Số lần split cao không tự chứng minh split tốt.
4. Chỉ thay một thành phần của Leviathan, giữ lại phiên bản cũ làm đối chứng.
   Chạy cả hai phía trên nhiều map, giữ cấu hình thử giống nhau. Ghi win/draw/loss,
   số lần tự đâm, số lần bị kẹt, độ dài con lớn nhất cuối trận và CPU points.
5. Sau khi chọn thay đổi tốt hơn trên tập thử, kiểm tra lại trên map/đối thủ
   chưa dùng để chỉnh chiến thuật. Bắt chước đúng replay không bảo đảm thắng.

Ví dụ đã kiểm tra: match 2931, map Big Empty, 500 vòng. Cả hai đội đều split
lần đầu ở vòng 2 (đếm từ 0), khi rồng dài 6. Vibing++ yêu cầu 279 lượt sprint;
Sponge không có lượt sprint nào. Đây là điểm để mở replay so sánh, chưa phải
kết luận rằng sprint là nguyên nhân thắng. Báo cáo phân biệt số lượt sprint
với tổng số bước di chuyển, và split thành công với lệnh split được yêu cầu.

Script tải công khai chờ tối thiểu 1,1 giây giữa các request, retry có giới hạn,
tôn trọng `Retry-After` và dừng khi bị từ chối truy cập. Nó xử lý gzip của máy
chủ lưu replay và không dùng cookie/API key. Nếu gặp 401/403, dùng nút
**Download replay** của website với quyền truy cập của bạn rồi đặt file vào
`top_replays`; không tìm cách vượt kiểm soát truy cập.

## 1. Lấy API key của team

Mở trang team trên website Battlecode và tạo API key bắt đầu bằng `bc_`.
Đây là **key Battlecode**, không phải key OpenAI/Codex.

Script hỏi key bằng một ô nhập ẩn trong Terminal. Không dán key vào chat hoặc
commit vào repo. Có thể dùng biến môi trường `UNSWBC_API_KEY` nếu đã cấu hình.
Script không đọc hoặc thay đổi thông tin đăng nhập Codex.

## 2. Tải trận về

Giải nén rồi mở folder `battlecode_data` trong VS Code. Bạn đã cài uv, chạy:

```powershell
uv run download_battles.py --recent 50
```

Lệnh lấy tối đa 50 trận gần nhất **của team ứng với key**. API cho phép giới hạn
tối đa 200. Không có tham số phân trang được xác nhận trong tài liệu đã đọc,
nên script không tự đoán page/cursor để quét toàn bộ lịch sử.

Để tải các trận cụ thể, kể cả trận team khác mà API cho phép bạn xem:

```powershell
uv run download_battles.py --ids 1201 1202 1203
```

Các số trên chỉ là ví dụ. Thay bằng ID thật lấy từ trang/link trận. Nếu chưa biết
cách lấy ID thì dùng `--recent` để bắt đầu với trận của team mình.

Cũng có thể tạo `ids.txt`, mỗi dòng một ID:

```powershell
uv run download_battles.py --ids-file ids.txt
```

Kết quả nằm trong `replays/`:

- `battle_....replay`: dữ liệu diễn biến trận.
- `battle_....json`: metadata API trả về.
- `battle_....meta.json`: ID nhóm, thời điểm tải và mã kiểm tra file.
- `recent.json`: nguyên bản response danh sách để đối chiếu nếu API thay đổi.
- `downloads.json`: danh sách tải thành công, giúp chạy lại mà không tải trùng.

Script chỉ gửi GET, không tạo scrim hoặc submit bot. Trận đang chờ/chưa có replay
có thể báo chưa tải được; chạy lại sau khi trận kết thúc. Lỗi 401 dừng chương
trình để bạn kiểm tra key; 403 là API không cho phép truy cập mục đó.

API giới hạn 120 request/phút/key. Script chờ ít nhất 0,65 giây giữa các request,
retry có giới hạn và tôn trọng `Retry-After`. Nếu nhiều người dùng cùng một team
key, tổng request của cả nhóm vẫn tính chung.

Replay thường được tải qua một URL chuyển hướng có chữ ký. Script bỏ
Authorization trên mọi redirect, không gửi key team tới máy chủ lưu replay.

**Giới hạn xác minh của `download_battles.py`:** chưa tải trận online bằng tài khoản của bạn. Downloader
dựa trên endpoint chính thức và được kiểm tra bằng HTTP giả lập; nếu schema
danh sách thực tế không nhận diện được, nó lưu response và yêu cầu dùng `--ids`.

## 3. Chuyển replay thành dataset

```powershell
uv run make_dataset.py replays --output dataset.jsonl.gz
```

Không cần thư viện bên ngoài cho bước tải và giải mã. `.replay` là Cap'n Proto
dạng packed, không phải video, CSV hoặc JSON thuần.

Một dòng dataset là **một lượt của một con rồng**:

```json
{
  "observation": {
    "round": 12,
    "position": [4, 5],
    "map": [11, 11],
    "length": 6,
    "facing": "E",
    "unit_count": 1,
    "unit_limit": 64,
    "sonar": [],
    "tiles": []
  },
  "action": {"kind": "move", "steps": "N"},
  "team_won": true,
  "died_this_turn": false,
  "split": "train"
}
```

Đây là ví dụ rút gọn. File thật có 49 hàng trong `tiles`, theo thứ tự từ góc
trên trái đến góc dưới phải, đầu rồng ở hàng số 24 (đếm từ 0).

Mỗi hàng tile có 11 giá trị:

| Chỉ số | Nội dung |
| --- | --- |
| 0 | Có pearl: 0/1 |
| 1 | Countdown pearl; -1 nếu ô không tự sinh pearl |
| 2 | Vật chiếm ô, theo bảng dưới |
| 3, 4 | Loại cạnh Bắc, portal ID |
| 5, 6 | Loại cạnh Đông, portal ID |
| 7, 8 | Loại cạnh Nam, portal ID |
| 9, 10 | Loại cạnh Tây, portal ID |

| Occupant | Nghĩa |
| --- | --- |
| 0 | Trống |
| 1 | Thân chính mình |
| 2 | Thân đồng đội |
| 3 | Thân đối phương |
| 4 | Đầu đồng đội |
| 5 | Đầu đối phương |
| 6 | Đầu chính mình |

Loại cạnh: 0 trống, 1 kelp, 2 portal. Portal ID bằng -1 khi không phải portal.
Vùng nhìn nối vòng đúng kích thước map. Feature này giữ một phần input bot;
chưa giữ hướng của từng đoạn thân hay bộ nhớ tích lũy qua nhiều lượt.

Trạng thái được chụp ngay trước hành động của rồng, theo thứ tự event/ID trong
replay, không lấy một ảnh chung đầu vòng cho mọi rồng. Sonar inbox được cập nhật
và xóa theo lượt. Toàn bộ bản đồ chỉ dùng nội bộ để dựng lại diễn biến; dataset
không đưa các ô ngoài vision vào observation.

`team_won`, `died_this_turn`, `death_reason`, tên bot và ID trận là nhãn/metadata,
không được đưa vào input dự đoán. Các bước di chuyển nhiều ô và split được giữ
nguyên trong dataset: không tự chia một sprint thành nhiều quyết định giả.

## 4. Train thử một model chọn hướng

```powershell
uv run --with scikit-learn train_baseline.py dataset.jsonl.gz
```

Model là Decision Tree, đầu vào 352 feature từ observation, đầu ra một trong
N/E/S/W. Cấu hình ban đầu: `max_depth=10`, `min_samples_leaf=20`, `random_state=42`.
Đây là lựa chọn khởi đầu để hạn chế cây quá lớn, chưa tối ưu cho thi đấu.

Baseline chỉ học các nước đi một bước của đội thắng và loại các lượt chết ngay.
Nước đi của đội thắng vẫn có thể kém; đây không phải nhãn "nước đi tối ưu".
Chưa học split, sprint, chiến lược dùng sonar hoặc trạng thái có bộ nhớ.

Kết quả ghi trong `move_policy.json`, cùng accuracy, balanced accuracy và
confusion matrix trên train/validation/test. `predict()` trong `train_baseline.py`
có thể đọc cây JSON bằng Python chuẩn để trả các hướng theo điểm dự đoán.

**File model chưa phải bot hoàn chỉnh để nộp.** Cần nối input helper với feature,
lọc nước đi nguy hiểm và có chiến thuật dự phòng, sau đó chạy nhiều trận thực tế
và đo CPU points trong sandbox. Accuracy là mức bắt chước nước đi, không phải
tỉ lệ thắng. Không có đảm bảo model này mạnh hơn Pearl Bot hiện tại.

## Chia dữ liệu và chọn trận

- Hash `group_id` để gán khoảng 80% nhóm cho train, 10% validation, 10% test;
  toàn bộ lượt trong cùng nhóm luôn ở một tập. Tỉ lệ thực tế có thể lệch khi ít trận.
- Mặc định các replay cùng ID tải về có cùng nhóm. Nếu nhiều ID thuộc cùng một
  series, đặt cùng `group_id` trong các file `.meta.json` trước khi convert.
- Không random từng lượt rồi chia train/test: hai trạng thái liền nhau quá giống.
- Nên dành thêm các map/đối thủ chưa dùng để chỉnh model làm bài kiểm tra cuối.
- Nếu một tập không có mẫu hợp lệ, trainer dừng và yêu cầu thêm trận; không tự
  chuyển sang chia theo lượt để tạo chỉ số đẹp.
- Nên bắt đầu với vài chục trận từ nhiều map và đối thủ; lọc trùng, trận lỗi và
  xem lại các thất bại điển hình trước khi tăng số lượng.

Train ở đây là **học bắt chước (imitation learning)** từ observation → action.
RL cần thêm môi trường để bot tự hành động, nhận reward và cập nhật chính sách;
chỉ tải replay về chưa tạo thành một vòng train RL.

## Thử ngay với file mẫu

```powershell
uv run make_dataset.py example_replays --output example_dataset.jsonl.gz
```

Hai replay mẫu dùng để kiểm tra định dạng, không phải dataset đủ để train bot
mạnh. Trong đó `portal_split_sonar.replay` là trận kiểm tra nhân tạo. Không trộn
nó vào dữ liệu học chiến thuật.

## Nguồn và xác minh

- API: https://game.battlecode.au/docs/api
- Vision: https://game.battlecode.au/docs/vision
- Thứ tự lượt: https://game.battlecode.au/docs/execution-order
- Wire protocol: https://game.battlecode.au/docs/protocol
- Cap'n Proto encoding: https://capnproto.org/encoding.html

Offsets schema replay được đối chiếu với viewer chính thức trong package
`unswbc 0.3.5`. Xem `VALIDATION.md` để biết phạm vi kiểm tra. Nếu toolkit thay
đổi format, cần cập nhật parser; không đổi tên file nhị phân thành JSON để đọc.
