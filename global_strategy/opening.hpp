#pragma once
#include <algorithm>
#include <cmath>
#include <deque>
#include <vector>
#include "map_recognition.hpp"
#include "ending.hpp"
#include "middle_game.hpp"

namespace global_strategy {

// Prefer a nearby distinguishing edge only while the map is ambiguous.
// Movement still passes the adapter's collision and short-horizon checks.
template<class Bot>
bool scoutUnknownMap(Bot& bot, std::vector<int>& action) {
    if (!bot.mapStatus.active || bot.mapStatus.opening.map || !bot.mapStatus.candidates ||
        bot.body.empty() || bot.round >= 24 || bot.actualLength >= 8) return false;
    int target=-1, distance=bot.n+1;
    for (const auto& s : signatures) {
        if (s.w!=bot.w || s.h!=bot.h) continue;
        int p=s.y*bot.w+s.x;
        if (bot.cells[p].edge[s.d]!=-2) continue;
        int d=bot.wrappedDistance(bot.body.front(),p);
        if (d<distance) { distance=d; target=p; }
    }
    return target>=0 && bot.moveOpeningToward(target,action);
}

template<class Bot, class Controller>
bool trophyOpening(Bot& bot, Controller&, std::vector<int>& action) {
    using State = typename Bot::SearchState;
        const int map = bot.mapStatus.active ? bot.mapStatus.opening.map : bot.identifiedMap();
        if (map != 10 || bot.trophyOpeningFinished || bot.body.empty()) return false;
        const bool upper = (bot.team == 'A' && bot.myid == 0) || (bot.team == 'B' && bot.myid == 1);
        const bool lower = (bot.team == 'A' && bot.myid == 2) || (bot.team == 'B' && bot.myid == 3);
        if (!upper && !lower) return false;
        if (bot.round >= 32 || bot.actualLength >= 12) {
            bot.trophyOpeningFinished = true; return false;
        }
        // Trophy reflects left/right: upper roles stay upper on both teams.
        const int target = upper ? 8 * bot.w + (bot.team == 'A' ? 5 : 19) : 22 * bot.w + 12;
        const int head = bot.body.front();
        if ((upper && head == target) || (lower && head / bot.w < 8)) {
            bot.trophyOpeningFinished = true; return false;
        }
        if (lower && head == target) {
            if (bot.cells[head].edge[0] <= 0) {
                bot.trophyOpeningFinished = true; return false;
            }
            State next, root; root.body = bot.body;
            if (bot.graph[head][0] >= 0) {
                if (!bot.advance(root, 0, next, 1) || bot.danger[next.body.front()] >= 80) return false;
                bot.body = next.body;
            } else if (bot.graph[head][0] == -2) {
                // Deliberate exploration of an observed portal. Its unseen
                // exit is not inserted into memory or assumed collision-free.
                if (bot.danger[head] >= 80) return false;
                bot.body.clear(); bot.complete = false;
            } else return false;
            bot.trophyOpeningFinished = true; action = {0}; return true;
        }
        return bot.moveOpeningToward(target, action);
    
}

template<class Bot>
bool moveOpeningToward(Bot& bot, int target, std::vector<int>& action) {
    using State = typename Bot::SearchState;
        const int head = bot.body.front();
        std::vector<std::vector<int>> incoming(bot.n);
        for (int p = 0; p < bot.n; ++p) for (int q : bot.graph[p])
            if (q >= 0 && !bot.fixed[q]) incoming[q].push_back(p);
        std::vector<int> distance(bot.n, bot.n + 1); distance[target] = 0;
        std::deque<int> queue{target};
        while (!queue.empty()) {
            int p = queue.front(); queue.pop_front();
            for (int q : incoming[p]) if (distance[q] > distance[p] + 1) {
                distance[q] = distance[p] + 1; queue.push_back(q);
            }
        }
        State root, selected; root.body = bot.body;
        int direction = -1;
        double best = -1e9;
        int preferred = head % bot.w < target % bot.w ? 1 : head % bot.w > target % bot.w ? 3 :
            head / bot.w > target / bot.w ? 0 : 2;
        for (int d = 0; d < 4; ++d) {
            State next;
            if (bot.cells[head].edge[d] == -2 || !bot.advance(root, d, next, 1)) continue;
            int q = next.body.front();
            if (distance[q] >= distance[head] || bot.danger[q] >= 80 || bot.search(next, 4).depth < 4) continue;
            double score = -100.0 * distance[q] - bot.danger[q] + (d == preferred ? 2 : 0);
            if (score > best) { best = score; direction = d; selected = next; }
        }
        if (direction < 0) return false;
        bot.body = selected.body; action = {direction}; return true;
    
}

template<class Bot>
int wrappedDistance(const Bot& bot, int p, int q) {
        int dx = std::abs(p % bot.w - q % bot.w), dy = std::abs(p / bot.w - q / bot.w);
        return std::min(dx, bot.w - dx) + std::min(dy, bot.h - dy);
    
}

template<class Bot, class Controller>
bool default_smallOpening(Bot& bot, Controller& ct, std::vector<int>& action) {
    using State = typename Bot::SearchState;
        const int map = bot.mapStatus.active ? bot.mapStatus.opening.map : bot.identifiedMap();
        if (map != 5 || bot.body.empty()) return false;
        const int head = bot.body.front();
        const bool initial = (bot.team == 'A' && (bot.myid == 0 || bot.myid == 2)) ||
            (bot.team == 'B' && (bot.myid == 1 || bot.myid == 3));
        if (!initial) {
            if (!bot.smallScoutChecked) {
                bot.smallScoutChecked = true;
                int x = head % bot.w, y = head / bot.w;
                // A newborn infers its assignment from its own first view.
                if (bot.myid >= 4 && bot.round < 140 && bot.actualLength <= 3 &&
                    ((x >= 10 && y <= 5) || (x <= 5 && y >= 10))) bot.smallScoutUntil = bot.round + 32;
            }
            const int center = bot.team == 'A' ? 7 * bot.w + 7 : 8 * bot.w + 8;
            if (bot.wrappedDistance(head, center) <= 2 || bot.actualLength >= 12) bot.smallScoutUntil = -1;
            return bot.round < bot.smallScoutUntil && bot.moveOpeningToward(center, action);
        }
        if (bot.round >= 140 || bot.actualLength >= 12) { bot.smallOpeningPhase = 3; return false; }
        int approach = bot.myid == 0 ? 13 * bot.w + 1 : bot.myid == 2 ? bot.w + 13 :
            bot.myid == 1 ? 2 * bot.w + 14 : 14 * bot.w + 2;
        bot.smallCornerHome = (bot.myid == 0 || bot.myid == 3) ? 13 * bot.w + 2 : 2 * bot.w + 13;
        bool onLane = bot.myid == 0 ? head % bot.w == 1 : bot.myid == 1 ? head % bot.w == 14 :
            bot.myid == 2 ? head / bot.w == 1 : head / bot.w == 14;
        if (bot.smallOpeningPhase == 0 && !onLane) bot.smallOpeningPhase = 1;
        if (bot.smallOpeningPhase == 0 && head == approach) bot.smallOpeningPhase = 1;
        if (bot.smallOpeningPhase == 1 && head == bot.smallCornerHome) bot.smallOpeningPhase = 2;
        if (bot.smallOpeningPhase == 0) {
            // Keep the initial heading; toroidal shortest paths would turn
            // back across the board edge instead of following the opening.
            int d = bot.myid == 0 ? 2 : bot.myid == 2 ? 1 : bot.myid == 1 ? 0 : 3;
            State root, next; root.body = bot.body;
            if (bot.cells[head].edge[d] == -2 || !bot.advance(root, d, next, 1) ||
                bot.danger[next.body.front()] >= 80 || bot.search(next, 4).depth < 4) return false;
            bot.body = next.body; action = {d}; return true;
        }
        if (bot.smallOpeningPhase == 1) return bot.moveOpeningToward(bot.smallCornerHome, action);
        if (bot.smallOpeningPhase == 2 && ct.can_split(2) && bot.complete &&
            bot.breedingExit(bot.body.front()) && bot.breedingExit(bot.body.back()) && bot.childRoom() >= 4) {
            bot.smallOpeningPhase = 3; bot.body.resize(bot.body.size() - 2); action = {-1}; return true;
        }
        if (bot.wrappedDistance(head, bot.smallCornerHome) > 4) return bot.moveOpeningToward(bot.smallCornerHome, action);
        int target = -1; double best = -1e9;
        for (int p = 0; p < bot.n; ++p) {
            if (!bot.visible[p] || !bot.cells[p].pearl || bot.fixed[p] || bot.contains(bot.body, p) ||
                bot.wrappedDistance(p, bot.smallCornerHome) > 4) continue;
            double value = 100.0 / (bot.wrappedDistance(head, p) + 1) - bot.danger[p];
            if (value > best) { best = value; target = p; }
        }
        return target >= 0 && bot.moveOpeningToward(target, action);
    
}

// Unknown maps explore for evidence; false hands control to middle-game.
template<class Bot, class Controller>
bool genericOpening(Bot& bot, Controller&, std::vector<int>& action) {
    return scoutUnknownMap(bot, action);
}

// Maps without a dedicated opening use the normal economy planner.
template<class Bot, class Controller>
bool arenaOpening(Bot& bot, Controller& ct, std::vector<int>& action) {
    return genericOpening(bot, ct, action);
}

template<class Bot, class Controller>
bool big_emptyOpening(Bot& bot, Controller& ct, std::vector<int>& action) {
    constexpr int populationTarget = 64;
    if (bot.w == 64 && bot.h == 64) {
        auto rescue = trappedHeadRescue(bot, ct);
        if (!rescue.empty()) { action = rescue; return true; }
        auto trade = headTradeAction(bot, ct);
        if (!trade.empty()) { action = trade; return true; }
    }
    if (bot.w == 64 && bot.h == 64 && ct.get_unit_count() < populationTarget && ct.can_split(2)) {
        // Two-segment children maximize population without waiting for longer bodies.
        if (bot.complete && bot.body.size() == static_cast<std::size_t>(ct.get_length()))
            bot.body.resize(bot.body.size() - 2);
        else {
            bot.body.clear();
            bot.complete = false;
        }
        action = {-1};
        return true;
    }
    if (bot.w == 64 && bot.h == 64 && ct.get_unit_count() < std::min(populationTarget, ct.unit_limit) &&
        bot.complete && ct.get_length() > 2 && bot.body.size() == static_cast<std::size_t>(ct.get_length())) {
        using State = typename Bot::SearchState;
        State root, selected; root.body = bot.body;
        double best = -1e12;
        std::vector<int> moves;
        for (int d=0;d<4;++d) {
            State first;
            if (bot.cells[root.body.front()].edge[d] == -2 || !bot.advance(root,d,first,1)) continue;
            for (int e=0;e<4;++e) {
                State second;
                if (!bot.advance(first,e,second,1,true)) continue;
                // Pay the sprint cost with food; do not delay an available next-turn split.
                if (second.body.size()<root.body.size() ||
                    (first.body.size()>=4 && second.body.size()<4)) continue;
                int head=second.body.front();
                if (bot.danger[head]>=80 || bot.search(second,4).depth<4) continue;
                double score=second.reward+bot.danger[first.body.front()]+
                    150.0/(bot.foodDist[head]+1)+4*std::min(bot.area(second),12);
                if (score>best) { best=score; selected=second; moves={d,e}; }
            }
        }
        if (!moves.empty()) { bot.body=selected.body; action=moves; return true; }
    }
    return genericOpening(bot, ct, action);
}

template<class Bot, class Controller>
bool colosseumOpening(Bot& bot, Controller& ct, std::vector<int>& action) {
    return genericOpening(bot, ct, action);
}

template<class Bot, class Controller>
bool defaultOpening(Bot& bot, Controller& ct, std::vector<int>& action) {
    return genericOpening(bot, ct, action);
}

template<class Bot, class Controller>
bool helpOpening(Bot& bot, Controller& ct, std::vector<int>& action) {
    return big_emptyOpening(bot, ct, action);
}

template<class Bot, class Controller>
bool queen_of_spadesOpening(Bot& bot, Controller& ct, std::vector<int>& action) {
    return genericOpening(bot, ct, action);
}

template<class Bot, class Controller>
bool queen_of_spades_but_she_agesOpening(Bot& bot, Controller& ct, std::vector<int>& action) {
    return queen_of_spadesOpening(bot, ct, action);
}

template<class Bot, class Controller>
bool schooltimeOpening(Bot& bot, Controller& ct, std::vector<int>& action) {
    return genericOpening(bot, ct, action);
}

// Compatibility entry point for existing adapters/tests.
template<class Bot, class Controller>
bool smallOpening(Bot& bot, Controller& ct, std::vector<int>& action) {
    return default_smallOpening(bot, ct, action);
}

template<class Bot, class Controller>
bool openingAction(Bot& bot, Controller& ct, std::vector<int>& action) {
    const int map = bot.mapStatus.active ? bot.mapStatus.opening.map : bot.identifiedMap();
    switch (map) {
    case 1: return arenaOpening(bot, ct, action);
    case 2: return big_emptyOpening(bot, ct, action);
    case 3: return colosseumOpening(bot, ct, action);
    case 4: return defaultOpening(bot, ct, action);
    case 5: return default_smallOpening(bot, ct, action);
    case 6: return helpOpening(bot, ct, action);
    case 7: return queen_of_spadesOpening(bot, ct, action);
    case 8: return queen_of_spades_but_she_agesOpening(bot, ct, action);
    case 9: return schooltimeOpening(bot, ct, action);
    case 10: return trophyOpening(bot, ct, action);
    default: return genericOpening(bot, ct, action);
    }
}

} // namespace global_strategy
