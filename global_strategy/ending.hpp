#pragma once
#include <algorithm>
#include <cmath>
#include <deque>
#include <vector>
#include "map_recognition.hpp"

namespace global_strategy {

template<class Policy>
bool breedingAllowed(int round, int units, bool confined, const Policy& plan) {
    return round < plan.stop || ((confined || plan.cautiousChild) &&
        round < plan.reserveStop && units < plan.reserve);
}

template<class Bot, class Controller>
std::vector<int> longBodyAction(Bot& bot, Controller& ct) {
    using State = typename Bot::SearchState;
    State root; root.body = bot.body;
        double best = -1e12; std::vector<int> action;
        State selected;
        int bestDepth = -1;
        const int horizon = bot.tuning().search_horizon + (bot.mapPlan()==MapPlan::Schooltime ? 4 : 0);
        for (int d = 0; d < 4; ++d) {
            State first;
            if (!bot.advance(root, d, first, 1)) continue;
            auto result = bot.search(first, horizon);
            int space = bot.area(first);
            double score = result.depth * 2000.0 + result.value +
                std::min(space, ct.get_length() + 8) * 1.5;
            if (space < ct.get_length()) score -= std::min(100, (ct.get_length() - space) * 3);
            if (bot.dirs[d] == ct.get_dir()) score += 1;
            if (score > best) { best = score; action = {d}; selected = first; bestDepth = result.depth; }
        }
        // A two-step escape can shorten our body and move out of a ram square.
        if (bot.complete && bot.body.size() > 2 && (bestDepth < horizon ||
            (!action.empty() && bot.danger[selected.body.front()] >= 80))) {
            for (int d = 0; d < 4; ++d) {
                State first; if (!bot.advance(root, d, first, 1)) continue;
                for (int e = 0; e < 4; ++e) {
                    State second; if (!bot.advance(first, e, second, 1, true)) continue;
                    // No enemy gets a turn on the intermediate sprint square.
                    second.reward += bot.danger[first.body.front()];
                    auto result = bot.search(second, horizon);
                    double score = result.depth * 2000.0 + result.value +
                        std::min(bot.area(second), ct.get_length() + 7) * 1.5;
                    if (score > best) { best = score; action = {d, e}; selected = second; bestDepth = result.depth; }
                }
            }
        }
        // Splitting keeps the parent stationary and buys time for a blocked
        // tail or lets a child survive when the parent has no escape.
        // Reverse the valuable rear body into a child, leaving only two
        // segments at the trapped old head. The child acts later this round.
        if (bestDepth < 8 && bot.complete && bot.body.size() >= 4 &&
            ct.can_split(ct.get_length() - 2)) {
            State child;
            child.body.assign(bot.body.rbegin(), bot.body.rend() - 2);
            int head = bot.body[0], neck = bot.body[1];
            int savedHead = bot.fixed[head], savedNeck = bot.fixed[neck];
            bot.fixed[head] = bot.fixed[neck] = 2;
            auto rescue = bot.search(child, horizon);
            bot.fixed[head] = savedHead; bot.fixed[neck] = savedNeck;
            // With no legal head move, even a short tail exit beats certain
            // death. A newborn acts now, so assess its escape, not danger at
            // the square it will immediately leave.
            bool emergency = action.empty() && rescue.depth >= 1;
            if (emergency || (rescue.depth >= std::max(8, bestDepth + 3) &&
                bot.danger[child.body.front()] < 80)) {
                int childSize = ct.get_length() - 2;
                bot.body.resize(2);
                return {-1, childSize};
            }
        }
        if (bestDepth < 3 && ct.can_split(2) && bot.complete) {
            State parent = root; parent.body.resize(parent.body.size() - 2);
            // Child still occupies the severed cells this turn.
            int a = bot.body.back(), b = bot.body[bot.body.size() - 2];
            bot.fixed[a] = bot.fixed[b] = 1;
            auto result = bot.search(parent, horizon);
            bool childExit = false;
            for (int q : bot.graph[a]) if (q >= 0 && !bot.fixed[q] && !bot.contains(bot.body, q)) childExit = true;
            bot.fixed[a] = bot.fixed[b] = 0;
            if (result.depth > bestDepth + 2 || (action.empty() && childExit)) {
                bot.body.clear(); bot.complete = false; return {-1};
            }
        }
        if (action.empty()) {
            // New children may not know their remote tail yet. Do not make
            // complete body memory a prerequisite for a last-chance rescue.
            // Keep only the trapped head/neck; the child observes its own exit.
            if (!bot.complete && ct.can_split(ct.get_length() - 2)) {
                int childSize = ct.get_length() - 2;
                bot.body.clear(); bot.complete = false;
                return {-1, childSize};
            }
            // Unknown portal is preferable to a proven collision.
            for (int d = 0; d < 4; ++d) if (bot.graph[bot.body.front()][d] == -2) {
                bot.body.clear(); bot.complete = false; return {d};
            }
            return {0};
        }
        bot.body = selected.body;
        return action;
    
}

} // namespace global_strategy
