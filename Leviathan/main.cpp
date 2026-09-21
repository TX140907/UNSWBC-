#include "helper.hpp"
#include <algorithm>
#include <cmath>
#include <deque>
#include <limits>

using namespace unswbc;

#ifndef LEVIATHAN_HORIZON
#define LEVIATHAN_HORIZON 14
#endif
#ifndef LEVIATHAN_BEAM_WIDTH
#define LEVIATHAN_BEAM_WIDTH 24
#endif

// All memory is private to this dragon. Never assume unseen enemies stayed put.
struct Cell {
    std::array<int, 4> edge{-2, -2, -2, -2}; // -2 unknown, -1 kelp, 0 open, id+1 portal
    int seen = -10000, due = -1;
    bool pearl = false;
};
struct State {
    std::vector<int> body, eaten;
    double reward = 0, rank = 0;
    int first = -1;
};
class Leviathan {
public:
    int w = 0, h = 0, n = 0, round = 0, myid = 0;
    std::vector<Cell> cells;
    std::vector<std::array<int, 4>> graph;
    std::vector<int> fixed, visible, foodDist, visits, body;
    std::vector<double> danger;
    bool complete = false;
    int actualLength = 0;
    const std::array<Direction, 4> dirs = Direction::get_direction_list();

    int index(Position p) const { return p.y * w + p.x; }
    int adjacent(int p, int d) const {
        int x = p % w, y = p / w;
        if (d == 0) y = (y + h - 1) % h;
        if (d == 1) x = (x + 1) % w;
        if (d == 2) y = (y + 1) % h;
        if (d == 3) x = (x + w - 1) % w;
        return y * w + x;
    }
    static bool contains(const std::vector<int>& v, int p) {
        return std::find(v.begin(), v.end(), p) != v.end();
    }
    void observe(Controller& ct, Game& game) {
        if (!n) {
            std::tie(w, h) = game.get_map_size(); n = w * h;
            cells.resize(n); graph.resize(n); visits.resize(n);
        }
        round = game.get_round_num(); myid = ct.get_id();
        actualLength = ct.get_length();
        fixed.assign(n, 0); visible.assign(n, 0); danger.assign(n, 0);
        std::vector<int> own(n, 0), predecessor(n, -1);
        for (auto const& tile : ct.get_tiles()) {
            int p = index(tile.get_position()); visible[p] = 1;
            auto& c = cells[p]; c.seen = round; c.pearl = tile.has_pearl();
            c.due = tile.get_pearl_time() < 0 ? -1 : round + tile.get_pearl_time();
            for (int d = 0; d < 4; ++d) {
                auto e = tile.get_edge(dirs[d]);
                c.edge[d] = e.is_portal() ? e.get_portal_id() + 1 :
                    e.get_edge_type() == EdgeType::KELP ? -1 : 0;
                cells[adjacent(p, d)].edge[(d + 2) % 4] = c.edge[d];
            }
            if (auto part = tile.get_dragon()) {
                if (part->get_id() == myid) own[p] = 1;
                else fixed[p] = 1;
            }
        }
        // A directed portal side has one matching side at the partner edge.
        std::unordered_map<int, std::vector<int>> portalSides;
        for (int p = 0; p < n; ++p) for (int d = 0; d < 4; ++d)
            if (cells[p].edge[d] > 0) portalSides[cells[p].edge[d] * 4 + d].push_back(p);
        for (int p = 0; p < n; ++p) for (int d = 0; d < 4; ++d) {
            int e = cells[p].edge[d];
            graph[p][d] = e == -1 ? -1 : adjacent(p, d);
            if (e > 0) {
                graph[p][d] = -2;
                auto const& sides = portalSides[e * 4 + d];
                if (sides.size() == 2) graph[p][d] = adjacent(sides[0] == p ? sides[1] : sides[0], d);
            }
        }
        int head = index(ct.get_position()); ++visits[head];
        // Retain the full body across turns, including sections beyond vision.
        std::vector<char> bodyMask(n, 0);
        for (int p : body) bodyMask[p] = 1;
        bool valid = !body.empty() && body.front() == head && int(body.size()) <= actualLength;
        if (complete && int(body.size()) != actualLength) valid = false;
        for (int p = 0; p < n && valid; ++p)
            if (visible[p] && ((bodyMask[p] && !own[p]) || (complete && own[p] && !bodyMask[p]))) valid = false;
        {
            for (auto const& tile : ct.get_tiles()) if (auto part = tile.get_dragon()) {
                if (part->get_id() != myid || part->is_head()) continue;
                int p = index(tile.get_position());
                for (int d = 0; d < 4; ++d) if (dirs[d] == part->get_dir()) {
                    int next = graph[p][d];
                    if (next >= 0) predecessor[next] = p;
                }
            }
            if (!valid) body = {head};
            while (int(body.size()) < actualLength && predecessor[body.back()] >= 0 &&
                   !contains(body, predecessor[body.back()]))
                body.push_back(predecessor[body.back()]);
            complete = int(body.size()) == actualLength;
        }
        std::fill(bodyMask.begin(), bodyMask.end(), 0);
        for (int p : body) bodyMask[p] = 1;
        for (int p = 0; p < n; ++p) if (own[p] && !bodyMask[p]) fixed[p] = 2;
        for (auto const& tile : ct.get_tiles()) if (auto part = tile.get_dragon()) {
            if (!part->is_head() || part->get_id() == myid) continue;
            int p = index(tile.get_position());
            int options = 0;
            for (int q : graph[p]) if (q >= 0 && !fixed[q] && !bodyMask[q]) ++options;
            // Higher ids can ram our new head immediately. Lower ids act before
            // our next turn, so their reachable squares are dangerous as well.
            for (int d = 0; d < 4; ++d) {
                int q = graph[p][d];
                if (q < 0 || fixed[q] || bodyMask[q]) continue;
                // A forced head is much more dangerous than a head with three
                // alternative exits. Avoid surrendering every contested pearl.
                double risk = part->get_team() == ct.get_team() ? 85 : 125;
                if (n <= 256) risk = (part->get_team() == ct.get_team() ? 250.0 : 300.0)
                    / (options * options);
                else risk *= std::clamp(ct.get_length() / 8.0, 1.0, 4.0);
                danger[q] += risk;
                for (int dd = 0; dd < 4; ++dd) {
                    int r = graph[q][dd];
                    if (r >= 0 && !fixed[r] && !bodyMask[r]) danger[r] += 6;
                }
            }
        }
        // Reverse BFS: true walking distance, including remembered portals.
        std::vector<std::vector<int>> incoming(n);
        for (int p = 0; p < n; ++p) for (int q : graph[p])
            if (q >= 0 && !fixed[q] && !bodyMask[q]) incoming[q].push_back(p);
        foodDist.assign(n, n + 1); std::deque<int> queue;
        for (int p = 0; p < n; ++p) if (cells[p].pearl && round - cells[p].seen <= 20 && !fixed[p]) {
            foodDist[p] = 0; queue.push_back(p);
        }
        while (!queue.empty()) {
            int p = queue.front(); queue.pop_front();
            for (int q : incoming[p]) if (foodDist[q] > foodDist[p] + 1) {
                foodDist[q] = foodDist[p] + 1; queue.push_back(q);
            }
        }
    }
    bool growAt(int p, const State& s) const {
        return cells[p].pearl && round - cells[p].seen <= 20 && !contains(s.eaten, p);
    }
    bool advance(const State& s, int d, State& next, int depth, bool sprint = false) const {
        int p = s.body.front(), q = graph[p][d];
        // Collision is checked BEFORE the tail moves, including for sprints.
        if (q < 0 || fixed[q] || contains(s.body, q)) return false;
        if (sprint && s.body.size() <= 2) return false;
        next = s; next.body.insert(next.body.begin(), q);
        bool grows = growAt(q, s);
        if (grows) next.eaten.push_back(q);
        else if (complete || (actualLength > 0 && int(next.body.size()) > actualLength + int(next.eaten.size())))
            next.body.pop_back();
        if (sprint && complete) next.body.pop_back();
        if (s.first < 0) next.first = d;
        double discount = std::pow(0.91, depth - 1);
        double gain = grows ? (visible[q] ? 100 : 65) : 0;
        if (sprint) gain -= 125;
        gain -= visible[q] ? 0 : cells[q].seen < 0 ? 11 : 3;
        if (cells[p].edge[d] == -2) gain -= 15;
        if (depth <= 2) gain -= danger[q] * (depth == 1 ? 1.0 : 0.35);
        gain -= std::min(visits[q], 12) * 0.45;
        if (cells[q].due == round + 1 && !grows && depth == 1) gain -= 12;
        next.reward += discount * gain;
        next.rank = next.reward + 38.0 / (foodDist[q] + 1);
        return true;
    }
    // Space is a soft preference: a corridor may open as our own tail advances.
    int area(const State& s) const {
        std::vector<char> blocked(n, 0);
        for (int p : s.body) blocked[p] = 1;
        std::deque<int> queue{s.body.front()}; int result = 0;
        while (!queue.empty() && result < 100) {
            int p = queue.front(); queue.pop_front(); ++result;
            for (int q : graph[p]) if (q >= 0 && !blocked[q] && !fixed[q]) {
                blocked[q] = 1; queue.push_back(q);
            }
        }
        return result;
    }
    // A long dragon needs a route back toward its moving tail, not just many
    // nearby empty cells. Crossing the tail is never allowed on the real move.
    double escapeValue(const State& s) const {
        if (!complete || s.body.size() < 8) return 0;
        std::vector<char> blocked(n, 0);
        for (int p : s.body) blocked[p] = 1;
        int tail = s.body.back();
        std::deque<int> queue{s.body.front()};
        int space = 0;
        while (!queue.empty() && space < int(s.body.size()) + 20) {
            int p = queue.front(); queue.pop_front(); ++space;
            for (int q : graph[p]) {
                if (q == tail) return 40;
                if (q < 0 || blocked[q] || fixed[q]) continue;
                blocked[q] = 1; queue.push_back(q);
            }
        }
        return space >= int(s.body.size()) + 8 ? 0 : -160;
    }
    struct Evaluation { int depth = 0; double value = -1e9; };
    Evaluation search(State start, int horizon = LEVIATHAN_HORIZON) const {
        std::vector<State> beam{std::move(start)};
        Evaluation out;
        constexpr int WIDTH = LEVIATHAN_BEAM_WIDTH;
        for (int depth = 1; depth <= horizon; ++depth) {
            std::vector<State> next; next.reserve(WIDTH * 3);
            for (auto const& s : beam) for (int d = 0; d < 4; ++d) {
                State candidate;
                if (advance(s, d, candidate, depth + 1)) next.push_back(std::move(candidate));
            }
            if (next.empty()) break;
            auto better = [](State const& a, State const& b) { return a.rank > b.rank; };
            if (next.size() > WIDTH) {
                std::nth_element(next.begin(), next.begin() + WIDTH, next.end(), better);
                next.resize(WIDTH);
            }
            out.depth = depth;
            out.value = std::max_element(next.begin(), next.end(),
                [](State const& a, State const& b) { return a.rank < b.rank; })->rank;
            if (depth == horizon) {
                out.value = -1e9;
                for (auto const& leaf : next) {
                    int exits = 0;
                    for (int d = 0; d < 4; ++d) {
                        State successor;
                        if (advance(leaf, d, successor, depth + 2)) ++exits;
                    }
                    double value = leaf.rank + 2.0 * std::min(area(leaf), int(leaf.body.size()) + 8);
                    if (n > 256) value += escapeValue(leaf);
                    if (!exits) value -= 500;
                    out.value = std::max(out.value, value);
                }
            }
            beam = std::move(next);
        }
        return out;
    }
    std::vector<int> choose(Controller& ct) {
        State root; root.body = body;
        // Crowded small boards reward early reproduction. Switch to the
        // long-body planner for the final 150 rounds, when length decides ties.
        if (n <= 256 && round < 350 && ct.get_unit_count() < std::min(32, n / 3) && ct.can_split(2)) {
            if (complete) body.resize(body.size() - 2);
            else body.clear();
            return {-1};
        }
        if (n <= 256 && round < 350 && ct.get_length() <= 5) {
            double best = -1e9; int direction = -1; State chosen;
            for (int d = 0; d < 4; ++d) {
                State next; if (!advance(root, d, next, 1)) continue;
                int p = next.body.front(), exits = 0;
                for (int e = 0; e < 4; ++e) {
                    State after; if (advance(next, e, after, 2)) ++exits;
                }
                double score = (growAt(p, root) ? 250 : 0) + 150.0 / (foodDist[p] + 1)
                    + 8 * std::min(area(next), 10) + 25 * exits - 0.7 * danger[p]
                    - 0.5 * std::min(visits[p], 12);
                if (!exits && next.body.size() < 4) score -= 500;
                if (dirs[d] == ct.get_dir()) score += 2;
                if (score > best) { best = score; direction = d; chosen = next; }
            }
            if (direction >= 0) { body = chosen.body; return {direction}; }
        }
        double best = -1e12; std::vector<int> action;
        State selected;
        int bestDepth = -1;
        const int horizon = LEVIATHAN_HORIZON;
        for (int d = 0; d < 4; ++d) {
            State first;
            if (!advance(root, d, first, 1)) continue;
            auto result = search(first, horizon);
            int space = area(first);
            double score = result.depth * 2000.0 + result.value +
                std::min(space, ct.get_length() + 8) * 1.5;
            if (space < ct.get_length()) score -= std::min(100, (ct.get_length() - space) * 3);
            if (dirs[d] == ct.get_dir()) score += 1;
            if (score > best) { best = score; action = {d}; selected = first; bestDepth = result.depth; }
        }
        // A two-step escape can shorten our body and move out of a ram square.
        if (complete && body.size() > 2 && (bestDepth < horizon ||
            (!action.empty() && danger[selected.body.front()] >= 80))) {
            for (int d = 0; d < 4; ++d) {
                State first; if (!advance(root, d, first, 1)) continue;
                for (int e = 0; e < 4; ++e) {
                    State second; if (!advance(first, e, second, 1, true)) continue;
                    // No enemy gets a turn on the intermediate sprint square.
                    second.reward += danger[first.body.front()];
                    auto result = search(second, horizon);
                    double score = result.depth * 2000.0 + result.value +
                        std::min(area(second), ct.get_length() + 7) * 1.5;
                    if (score > best) { best = score; action = {d, e}; selected = second; bestDepth = result.depth; }
                }
            }
        }
        // Splitting keeps the parent stationary and buys time for a blocked
        // tail or lets a child survive when the parent has no escape.
        // Reverse the valuable rear body into a child, leaving only two
        // segments at the trapped old head. The child acts later this round.
        if (bestDepth < 8 && complete && body.size() >= 6 &&
            ct.can_split(ct.get_length() - 2)) {
            State child;
            child.body.assign(body.rbegin(), body.rend() - 2);
            int head = body[0], neck = body[1];
            int savedHead = fixed[head], savedNeck = fixed[neck];
            fixed[head] = fixed[neck] = 2;
            auto rescue = search(child, horizon);
            fixed[head] = savedHead; fixed[neck] = savedNeck;
            if (rescue.depth >= std::max(8, bestDepth + 3) &&
                danger[child.body.front()] < 80) {
                int childSize = ct.get_length() - 2;
                body.resize(2);
                return {-1, childSize};
            }
        }
        if (bestDepth < 3 && ct.can_split(2) && complete) {
            State parent = root; parent.body.resize(parent.body.size() - 2);
            // Child still occupies the severed cells this turn.
            int a = body.back(), b = body[body.size() - 2];
            fixed[a] = fixed[b] = 1;
            auto result = search(parent, horizon);
            bool childExit = false;
            for (int q : graph[a]) if (q >= 0 && !fixed[q] && !contains(body, q)) childExit = true;
            fixed[a] = fixed[b] = 0;
            if (result.depth > bestDepth + 2 || (action.empty() && childExit)) {
                body.clear(); complete = false; return {-1};
            }
        }
        if (action.empty()) {
            // Unknown portal is preferable to a proven collision.
            for (int d = 0; d < 4; ++d) if (graph[body.front()][d] == -2) {
                body.clear(); complete = false; return {d};
            }
            return {0};
        }
        body = selected.body;
        return action;
    }
};

#ifndef LEVIATHAN_TEST
int main() {
    auto [ct, game] = unswbc::init();
    Leviathan bot;
    // The engine closes stdin at game end; EOF is not a malformed round.
    while (std::cin >> std::ws && std::cin.peek() != std::char_traits<char>::eof()) {
        if (!unswbc::update(ct, game)) break;
        bot.observe(ct, game);
        auto action = bot.choose(ct);
        if (action[0] < 0) ct.do_split(action.size() > 1 ? action[1] : 2);
        else {
            std::vector<Direction> moves;
            for (int d : action) moves.push_back(bot.dirs[d]);
            ct.make_moves(moves);
        }
        unswbc::end_turn();
    }
}
#endif
