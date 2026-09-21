#include "helper.hpp"
#include <vector>
#include <cmath>
#include <algorithm>
#include <unordered_map>
#include <unordered_set>
#include <queue>

using namespace unswbc;

static std::unordered_map<int, std::vector<Position>> position_history;
static std::vector<Position> reserved_positions_this_turn;
static int last_processed_id = 999999;

Tile* get_portal_destination(Controller& ct, int portal_id, Direction move_dir, Position current_pos) {
    for (const auto& tile : ct.get_tiles()) {
        for (Direction d : Direction::get_direction_list()) {
            Edge pe = tile.get_edge(d);
            if (pe.is_portal() && pe.get_portal_id() == portal_id) {
                if (tile.get_position() == current_pos && d == move_dir) continue;
                Position exit_pos = (d == move_dir.get_opposite()) 
                                    ? tile.get_position() 
                                    : tile.get_position().add_dir(move_dir);
                return ct.get_tile(exit_pos);
            }
        }
    }
    return nullptr;
}

Position get_next_actual_pos(Controller& ct, Position current_pos, Direction dir, bool& is_portal_jump) {
    Tile* current_tile = ct.get_tile(current_pos);
    is_portal_jump = false;
    if (current_tile && current_tile->get_edge(dir).is_portal()) {
        Tile* dest = get_portal_destination(ct, current_tile->get_edge(dir).get_portal_id(), dir, current_pos);
        if (dest) {
            is_portal_jump = true;
            return dest->get_position();
        } else {
            is_portal_jump = true;
        }
    }
    return current_pos.add_dir(dir);
}

bool is_safe(Controller& ct, Direction dir, bool allow_blind_portal = true) {
    Position my_pos = ct.get_position();
    Tile* here = ct.get_tile(my_pos);
    if (here == nullptr) return false;

    Edge edge = here->get_edge(dir);
    if (edge.get_edge_type() == EdgeType::KELP) return false;

    if (edge.is_portal()) {
        Tile* dest_tile = get_portal_destination(ct, edge.get_portal_id(), dir, my_pos);
        if (dest_tile == nullptr) return allow_blind_portal; 
        
        if (dest_tile->get_edge(dir).get_edge_type() == EdgeType::KELP) return false;
        if (dest_tile->get_dragon() != nullptr) return false;
        
        for (const auto& pos : reserved_positions_this_turn) {
            if (pos == dest_tile->get_position()) return false;
        }
        return true;
    }

    Position next_pos = my_pos.add_dir(dir);
    Tile* next_tile = ct.get_tile(next_pos);
    if (next_tile == nullptr) return false;
    if (next_tile->get_dragon() != nullptr) return false;

    for (const auto& pos : reserved_positions_this_turn) {
        if (pos == next_pos) return false;
    }
    return true;
}

// Chống chui ngõ cụt (Nhìn xa 2 bước)
int count_safe_exits(Controller& ct, Position pos) {
    int exits = 0;
    Tile* t = ct.get_tile(pos);
    if (!t) return 1; 
    
    for (Direction d : Direction::get_direction_list()) {
        Edge e = t->get_edge(d);
        if (e.get_edge_type() == EdgeType::KELP) continue;
        
        bool is_portal;
        Position next_p = get_next_actual_pos(ct, pos, d, is_portal);
        Tile* next_t = ct.get_tile(next_p);
        
        if (next_t) {
            if (next_t->get_dragon() == nullptr) exits++;
        } else {
            exits++; 
        }
    }
    return exits;
}

// Tận dụng 40MB RAM để quét không gian sống 120 ô!
int evaluate_open_space(Controller& ct, Position start) {
    std::queue<Position> q;
    std::unordered_set<Position, PositionHash> visited;
    
    q.push(start);
    visited.insert(start);
    int space_count = 0;
    int MAX_SEARCH = 120; // Nâng giới hạn loang cực rộng vì RAM dư dả
    
    while (!q.empty() && space_count < MAX_SEARCH) {
        Position curr = q.front();
        q.pop();
        space_count++;
        
        Tile* t = ct.get_tile(curr);
        if (!t) continue;
        
        for (Direction d : Direction::get_direction_list()) {
            Edge e = t->get_edge(d);
            if (e.get_edge_type() == EdgeType::KELP || e.is_portal()) continue; 
            
            Position next_p = curr.add_dir(d);
            Tile* next_t = ct.get_tile(next_p);
            
            if (next_t && next_t->get_dragon() == nullptr && visited.find(next_p) == visited.end()) {
                bool is_reserved = false;
                for (const auto& pos : reserved_positions_this_turn) {
                    if (pos == next_p) { is_reserved = true; break; }
                }
                if (!is_reserved) {
                    visited.insert(next_p);
                    q.push(next_p);
                }
            }
        }
    }
    return space_count;
}

std::optional<Direction> bfs_find_pearl(Controller& ct, Position start) {
    std::queue<std::pair<Position, Direction>> q;
    std::unordered_set<Position, PositionHash> visited;
    visited.insert(start);

    for (Direction d : Direction::get_direction_list()) {
        if (is_safe(ct, d, false)) {
            bool dummy;
            Position next_p = get_next_actual_pos(ct, start, d, dummy);
            q.push({next_p, d});
            visited.insert(next_p);
        }
    }

    while (!q.empty()) {
        auto [curr, first_dir] = q.front();
        q.pop();

        Tile* t = ct.get_tile(curr);
        if (t == nullptr) continue; 

        if (t->has_pearl() || (t->get_pearl_time() >= 0 && t->get_pearl_time() <= 2)) return first_dir;

        for (Direction d : Direction::get_direction_list()) {
            Edge e = t->get_edge(d);
            if (e.get_edge_type() == EdgeType::KELP) continue;
            
            Position next_p = curr.add_dir(d);
            if (e.is_portal()) {
                Tile* dest = get_portal_destination(ct, e.get_portal_id(), d, curr);
                if (dest) next_p = dest->get_position();
                else continue; 
            }

            Tile* next_t = ct.get_tile(next_p);
            if (next_t && next_t->get_dragon() == nullptr && visited.find(next_p) == visited.end()) {
                visited.insert(next_p);
                q.push({next_p, first_dir});
            }
        }
    }
    return std::nullopt;
}

void run_bot(Controller& ct, Game& game) {
    int my_id = ct.get_id();
    int my_len = ct.get_length();
    Position my_pos = ct.get_position();
    Direction current_facing = ct.get_dir();
    auto [map_w, map_h] = game.get_map_size();

    if (my_id <= last_processed_id) reserved_positions_this_turn.clear();
    last_processed_id = my_id;
    auto& hist = position_history[my_id];
    ct.send_sonar(static_cast<uint64_t>(my_id));

    // [THEO Ý TƯỞNG CỦA BẠN] Bầy Đàn Virus - Đẻ ngay khi đạt 4, cap số lượng cực khủng
    int max_dragons_allowed = std::max(20, (map_w * map_h) / 8); 
    if (my_len >= 4 && ct.can_split(2) && ct.get_unit_count() < max_dragons_allowed) {
        ct.do_split(2);
        hist.push_back(my_pos);
        if (hist.size() > 16) hist.erase(hist.begin());
        return;
    }

    std::vector<Direction> safe_dirs;
    for (Direction d : Direction::get_direction_list()) if (is_safe(ct, d, false)) safe_dirs.push_back(d);
    if (safe_dirs.empty()) for (Direction d : Direction::get_direction_list()) if (is_safe(ct, d, true)) safe_dirs.push_back(d);
    if (safe_dirs.empty()) {
        hist.push_back(my_pos);
        if (hist.size() > 16) hist.erase(hist.begin());
        return; 
    }

    std::optional<Direction> bfs_best_dir = bfs_find_pearl(ct, my_pos);
    Direction best_dir = safe_dirs[0];
    double min_dir_score = 999999.0;

    for (Direction d : safe_dirs) {
        double score = 0.0;
        bool is_portal_move = false;
        bool is_blind_portal = false;
        Position next_pos = my_pos.add_dir(d);

        Tile* current_tile = ct.get_tile(my_pos);
        if (current_tile && current_tile->get_edge(d).is_portal()) {
            is_portal_move = true;
            Tile* dest = get_portal_destination(ct, current_tile->get_edge(d).get_portal_id(), d, my_pos);
            if (dest) next_pos = dest->get_position();
            else is_blind_portal = true;
        }

        // Ưu tiên đi ăn ngọc, nhưng lực kéo không quá mù quáng để tránh bẫy
        if (bfs_best_dir.has_value() && d == bfs_best_dir.value()) score -= 4000.0; 

        // Tăng động lực đi thẳng (Lawnmower) để bù đắp việc rồng bị chia nhỏ, cần nhanh chóng bung map
        if (d == current_facing) score -= 150.0;
        else if (d == current_facing.get_opposite()) score += 300.0;

        if (!is_blind_portal) {
            // [CỰC KỲ QUAN TRỌNG VỚI RỒNG NHỎ] NẾU CÓ 0 HOẶC 1 LỐI THOÁT -> CHẠY NGAY!
            int exits = count_safe_exits(ct, next_pos);
            if (exits == 0) score += 30000.0; // Tử địa chắc chắn chết
            else if (exits == 1) score += 4000.0; // Nút thắt cổ chai, rồng size 2 chui vào rất dễ bị địch nắp hầm

            // Quét Flood-Fill xem khu vực phía trước to cỡ nào
            int open_space = evaluate_open_space(ct, next_pos);
            if (open_space < my_len + 2) score += 10000.0; 
            else score -= open_space * 8.0; // Kéo cực mạnh về các quảng trường lớn

            // Sợ đầu địch kinh hoàng (Vì mình size 2, đụng đầu ai cũng chết)
            int enemy_danger = 0;
            int ally_cluster = 0;
            for (Direction adj_d : Direction::get_direction_list()) {
                bool dummy;
                Position adj_pos = get_next_actual_pos(ct, next_pos, adj_d, dummy);
                Tile* adj_tile = ct.get_tile(adj_pos);
                
                if (adj_tile && adj_tile->get_dragon() != nullptr) {
                    const DragonPart* dp = adj_tile->get_dragon();
                    if (dp->get_team() != ct.get_team()) {
                        if (dp->is_head()) enemy_danger += 4000.0; // Điểm tránh né cực khủng
                        else enemy_danger += 200.0;
                    } else {
                        // Tản nhau ra để lấp bản đồ
                        if (dp->is_head()) ally_cluster += 300.0;
                        else ally_cluster += 50.0; 
                    }
                }
            }
            score += enemy_danger + ally_cluster;
        }

        // Chống lặp lại lịch sử đi vòng tròn
        int visit_count = 0;
        for (const auto& pos : hist) if (!is_blind_portal && next_pos == pos) visit_count++;
        score += visit_count * 500.0;

        // Xáo trộn nhẹ nhịp đi bước chân
        score += ((my_id + next_pos.x * 2 + next_pos.y * 3) % 5) * 3.0; 

        if (score < min_dir_score) {
            min_dir_score = score;
            best_dir = d;
        }
    }

    bool dummy;
    Position chosen_next_pos = get_next_actual_pos(ct, my_pos, best_dir, dummy);
    reserved_positions_this_turn.push_back(chosen_next_pos);

    hist.push_back(my_pos);
    if (hist.size() > 16) hist.erase(hist.begin());

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