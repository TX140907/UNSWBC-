# Thư viện chiến thuật và graph khắc chế theo map

Baseline đang giữ: **573**. Campaign chọn một policy thắng điểm cho mỗi map đã
được đặt `HOLD.json`; chưa gửi game online hoặc submit từ campaign này.

## Dữ liệu đã triển khai

- `strategy_library/strategies/<SHA256>/`: bản source bất biến của generic,
  proposal và đối thủ. Thêm strat mới không xóa strat cũ.
- `strategy_library/legacy_matchups.json`: các trận local đã hoàn thành, có map,
  checksum map, bản đối thủ, phía A/B, phiên bản engine và nguồn kết quả.
- `strategy_library/map_graphs.json`: graph riêng theo **map + checksum + phase**.
  Cạnh `A → B` là lợi thế trực tiếp quan sát được của A trước B trên map đó.
  Không tính bắc cầu; chu trình A → B → C → A được giữ nguyên.
- `strategy_library/counter_graphs/index.json`: danh sách file graph riêng của từng
  map/context. `weight` = điểm đối đầu trung bình (thắng 1, hòa 0,5, thua 0).
- `CounterSelector.update`: mỗi lần có nhận diện đối phương mới, tìm các cạnh
  đi **vào** node đối phương trong đúng map/checksum/phase rồi chọn trọng số lớn
  nhất. Chỉ chọn strat thuộc danh sách bot có thể thực thi; không lấy source của
  đối thủ làm strat của mình. Bằng trọng số giữ strat hiện tại nếu còn hợp lệ.
  Mất độ tin cậy hoặc không có cạnh hợp lệ thì trở về generic. Mặc định không
  dùng cạnh `runtime_enabled=false`; tùy chọn offline chỉ phục vụ phân tích.
- `strategy_library.py::select_counter`: chỉ chọn từ đối chứng trực tiếp giữa
  generic và ứng viên trong cùng map, phase và tín hiệu đối phương quan sát được.
  Cần đủ cặp A/B, ít nhất hai bản đối thủ; thiếu dữ liệu hoặc bằng điểm giữ generic.

Kết quả một game được khử trùng theo fixture; không tăng độ tin cậy bằng cách
chạy lại cùng game xác định. Cạnh ít dữ liệu được ghi là lợi thế quan sát, chưa
coi là counter chắc chắn. Không gán nhãn chiến thuật chỉ từ tên đội hay số quân
cuối trận. Một graph khác map không được dùng để bù điểm hoặc suy ra counter.

## Nhận diện khi chơi

Prototype `tests/strategy_adaptation.hpp` giữ trạng thái theo từng rồng, chỉ nhận
các tín hiệu có thể thấy trong vision: số đầu địch và số đoạn thân địch thấy được.
Nó bắt đầu Unknown, cần bốn quan sát liên tiếp để xác nhận, có cooldown 12 vòng
và bỏ nhận định sau tám vòng không có tín hiệu đủ rõ. Vì vậy nó có thể nhận ra
đối thủ chuyển từ nhiều đầu nhỏ sang thân dài, thay vì khóa nhãn từ đầu trận.
Đây là tín hiệu cục bộ, chưa phải bằng chứng chắc chắn về chiến thuật toàn đội.

## Phần chưa đủ bằng chứng để bật trên bot thi đấu

Các graph hiện tại là kết quả **cả trận**, chưa có nhãn đối phương theo cửa sổ
quan sát và phase. `runtime_enabled` vì thế đang false; không dùng dữ liệu nhìn
toàn replay để giả làm thông tin bot biết lúc ra quyết định. Source thi đấu vẫn
giữ 573. Cần thu thập/đối chứng từng strat trước cùng các nhóm hành vi đối phương,
kiểm tra nhận diện trên cửa sổ vision, rồi test bot chuyển strat giữa trận trước
khi bật tự submit trở lại. Generic luôn là phương án dự phòng.

Trong graph triển khai sau này, các phase/nhóm hành vi khác nhau là context riêng;
đổi map hoặc đối phương đổi hành vi phải chọn lại cạnh thích hợp. Các tham số và
ngưỡng prototype cần được kiểm chứng, không được coi là đã train xong.
