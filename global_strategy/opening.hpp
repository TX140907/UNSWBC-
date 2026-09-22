#pragma once
#include <algorithm>
#include <cmath>
#include <deque>
#include <vector>

namespace global_strategy {

template<class Bot, class Controller>
bool trophyOpening(Bot& bot, Controller&, std::vector<int>& action) {
    using State = typename Bot::SearchState;
        if (bot.identifiedMap() != 10 || bot.trophyOpeningFinished || bot.body.empty()) return false;
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
bool smallOpening(Bot& bot, Controller& ct, std::vector<int>& action) {
    using State = typename Bot::SearchState;
        if (bot.identifiedMap() != 5 || bot.body.empty()) return false;
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

} // namespace global_strategy
