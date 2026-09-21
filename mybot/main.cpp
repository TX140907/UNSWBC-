#include "helper.hpp"
#include <vector>
#include <cmath>
#include <algorithm>

using namespace unswbc;

struct Displacement {
    int dx, dy;
    int manhattan_dist() const { return std::abs(dx) + std::abs(dy); }
};

Displacement get_displacement(Position from, Position to, int map_w, int map_h) {
    int dx = ((to.x - from.x) % map_w + map_w) % map_w;
    if (dx > map_w / 2) dx -= map_w;

    int dy = ((to.y - from.y) % map_h + map_h) % map_h;
    if (dy > map_h / 2) dy -= map_h;

    return {dx, dy};
}

bool is_border_tile(Position pos, int map_w, int map_h) {
    return (pos.x == 0 || pos.x == map_w - 1 || pos.y == 0 || pos.y == map_h - 1);
}

// Tìm ô đích phía bên kia Portal nếu Portal đối ứng nằm trong Vision
Tile* get_portal_destination(Controller& ct, int portal_id, Direction move_dir, Position current_pos) {
    for (const auto& tile : ct.get_tiles()) {
        for (Direction d : Direction::get_direction_list()) {
            Edge pe = tile.get_edge(d);
            if (pe.is_portal() && pe.get_portal_id() == portal_id) {
                // Bỏ qua cạnh Portal tại vị trí hiện tại
                if (tile.get_position() == current_pos && d == move_dir) continue;

                // Xác định ô lối ra dựa vào hướng d của Portal đối ứng
                Position exit_pos = (d == move_dir.get_opposite()) 
                                    ? tile.get_position() 
                                    : tile.get_position().add_dir(move_dir);
                
                return ct.get_tile(exit_pos);
            }
        }
    }
    return nullptr; // Portal đối ứng nằm ngoài tầm nhìn (ô mù)
}

// Kiểm tra hướng đi an toàn (Xử lý cả Kelp và Portal)
bool is_safe(Controller& ct, Direction dir) {
    Position my_pos = ct.get_position();
    Tile* here = ct.get_tile(my_pos);
    if (here == nullptr) return false;

    Edge edge = here->get_edge(dir);

    // 1. Chạm vào Kelp -> Chết ngay lập tức
    if (edge.get_edge_type() == EdgeType::KELP) return false;

    // 2. Đi vào Portal
    if (edge.get_edge_type() == EdgeType::PORTAL) {
        int pid = edge.get_portal_id();
        Tile* dest_tile = get_portal_destination(ct, pid, dir, my_pos);

        if (dest_tile != nullptr) {
            // Kiểm tra xem ngay sau Portal có bị vách Kelp hay Rồng chặn không
            Edge exit_edge = dest_tile->get_edge(dir);
            if (exit_edge.get_edge_type() == EdgeType::KELP) return false;
            if (dest_tile->get_dragon() != nullptr) return false;
        }
        return true; // Nếu mù tầm nhìn vẫn cho phép đi (sẽ tính rủi ro sau)
    }

    // 3. Ô di chuyển thông thường
    Position next_pos = my_pos.add_dir(dir);
    Tile* next_tile = ct.get_tile(next_pos);
    if (next_tile == nullptr) return false;

    if (next_tile->get_dragon() != nullptr) return false;

    return true;
}

// Đếm số lối thoát an toàn từ 1 vị trí (Tránh chui vào ngõ cụt do Kelp tạo ra)
int count_safe_exits(Controller& ct, Position pos) {
    int exits = 0;
    Tile* t = ct.get_tile(pos);
    if (!t) return 0;

    for (Direction d : Direction::get_direction_list()) {
        Edge e = t->get_edge(d);
        if (e.get_edge_type() == EdgeType::KELP) continue;

        Position next_p = pos.add_dir(d);
        Tile* next_t = ct.get_tile(next_p);
        if (next_t && next_t->get_dragon() == nullptr) {
            exits++;
        }
    }
    return exits;
}

void run_bot(Controller& ct, Game& game) {
    int my_id = ct.get_id();
    int my_len = ct.get_length();
    Position my_pos = ct.get_position();
    auto [map_w, map_h] = game.get_map_size();

    // =============================================================
    // 1. TẬN DỤNG SONAR (Sonar đi xuyên qua cả Portal)
    // =============================================================
    ct.send_sonar(static_cast<uint64_t>(my_id));

    // =============================================================
    // 2. PHÂN THÂN (GIỚI HẠN = SỐ Ô TRUNG TÂM / 3)
    // =============================================================
    int inner_tiles = std::max(0, (map_w - 2) * (map_h - 2));
    int max_dragons_allowed = inner_tiles / 3;

    if (my_len >= 4 && ct.can_split(2) && ct.get_unit_count() < max_dragons_allowed) {
        ct.do_split(2);
        return;
    }

    // =============================================================
    // 3. LỌC CÁC HƯỚNG ĐI AN TOÀN
    // =============================================================
    std::vector<Direction> safe_dirs;
    for (Direction d : Direction::get_direction_list()) {
        if (is_safe(ct, d)) {
            safe_dirs.push_back(d);
        }
    }

    if (safe_dirs.empty()) {
        ct.make_move(Direction::NORTH);
        return;
    }

    // Lọc hướng không đi vào biên
    std::vector<Direction> non_border_dirs;
    for (Direction d : safe_dirs) {
        Position next_pos = my_pos.add_dir(d);
        if (!is_border_tile(next_pos, map_w, map_h)) {
            non_border_dirs.push_back(d);
        }
    }

    const auto& candidate_dirs = non_border_dirs.empty() ? safe_dirs : non_border_dirs;

    // Lọc tiếp các hướng KHÔNG rơi vào ngõ cụt (Có ít nhất 2 lối thoát)
    std::vector<Direction> best_candidate_dirs;
    for (Direction d : candidate_dirs) {
        Position next_pos = my_pos.add_dir(d);
        if (count_safe_exits(ct, next_pos) >= 2) {
            best_candidate_dirs.push_back(d);
        }
    }

    const auto& final_dirs = best_candidate_dirs.empty() ? candidate_dirs : best_candidate_dirs;

    // =============================================================
    // 4. TÌM NGỌC & ĐÓN ĐẦU PEARL TIME
    // =============================================================
    auto const& tiles = ct.get_tiles();
    Position target_pos = my_pos;
    bool has_target = false;
    double best_score = 999999.0;

    for (const auto& tile : tiles) {
        Position tile_pos = tile.get_position();
        Displacement disp = get_displacement(my_pos, tile_pos, map_w, map_h);
        int dist = disp.manhattan_dist();
        int p_time = tile.get_pearl_time();

        if (tile.has_pearl()) {
            double score = dist * 1.0;
            if (score < best_score) {
                best_score = score;
                target_pos = tile_pos;
                has_target = true;
            }
        } 
        else if (p_time >= 0 && p_time <= 2) {
            double score = dist * 1.0 + (p_time * 1.5) + 2.0;
            if (score < best_score) {
                best_score = score;
                target_pos = tile_pos;
                has_target = true;
            }
        }
    }

    // =============================================================
    // 5. VÂY TRUNG TÂM PHÂN TÁN THEO ID
    // =============================================================
    if (!has_target) {
        int base_cx = map_w / 2;
        int base_cy = map_h / 2;

        int offset_x = (my_id % 7) - 3;
        int offset_y = ((my_id / 7) % 7) - 3;

        int target_x = (base_cx + offset_x + map_w) % map_w;
        int target_y = (base_cy + offset_y + map_h) % map_h;

        target_pos = Position(target_x, target_y);
    }

    // =============================================================
    // 6. CHỌN HƯỚNG ĐI TỐI ƯU TRONG CÁC HƯỚNG ĐÃ LỌC
    // =============================================================
    Direction best_dir = final_dirs[0];
    int min_resulting_dist = 9999;

    for (Direction d : final_dirs) {
        Position next_pos = my_pos.add_dir(d);
        
        // Nếu là Portal, lấy vị trí đầu ra để tính khoảng cách tới target
        Tile* here = ct.get_tile(my_pos);
        if (here && here->get_edge(d).is_portal()) {
            Tile* dest = get_portal_destination(ct, here->get_edge(d).get_portal_id(), d, my_pos);
            if (dest) next_pos = dest->get_position();
        }

        Displacement next_disp = get_displacement(next_pos, target_pos, map_w, map_h);
        int d_dist = next_disp.manhattan_dist();

        if (d_dist < min_resulting_dist) {
            min_resulting_dist = d_dist;
            best_dir = d;
        }
    }

    ct.make_move(best_dir);
}

int main() {
    auto [ct, game] = unswbc::init();

    while (unswbc::update(ct, game)) {
        run_bot(ct, game);
        unswbc::end_turn();
    }

    return 0;
}