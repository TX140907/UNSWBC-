#pragma once
#include <algorithm>
#include <cmath>
#include <deque>
#include <vector>
#include "map_recognition.hpp"
#include "ending.hpp"

namespace global_strategy {

// A head collision kills both dragons, irrespective of length. Count only
// currently visible segments: this is a lower bound, not an enemy length oracle.
template<class Bot, class Controller>
std::vector<int> headTradeAction(Bot& bot, Controller& ct) {
    if (bot.round < 40 || ct.get_unit_count() <= 1 || ct.get_length() > 8 ||
        !bot.complete || bot.body.size() != static_cast<std::size_t>(ct.get_length())) return {};
    int bestLength = 0;
    std::vector<int> best;
    using State = typename Bot::SearchState;
    State root; root.body = bot.body;
    for (const auto& tile : ct.get_tiles()) {
        const auto* head = tile.get_dragon();
        if (!head || !head->is_head() || head->get_team() == ct.get_team()) continue;
        int length = 0;
        for (const auto& other : ct.get_tiles()) {
            const auto* part = other.get_dragon();
            if (part && part->get_team() == head->get_team() && part->get_id() == head->get_id()) ++length;
        }
        if (length < std::max(6, ct.get_length() + 2) || length <= bestLength) continue;
        const int target = bot.index(tile.get_position());
        std::vector<int> attack;
        for (int d = 0; d < 4; ++d) {
            const int start = root.body.front();
            if (bot.cells[start].edge[d] == -2) continue;
            if (bot.graph[start][d] == target) { attack = {d}; break; }
            if (ct.get_length() <= 2) continue;
            State first;
            if (!bot.advance(root, d, first, 1) || first.body.size() <= 2) continue;
            for (int e = 0; e < 4; ++e)
                if (bot.cells[first.body.front()].edge[e] != -2 &&
                    bot.graph[first.body.front()][e] == target) attack = {d, e};
        }
        if (!attack.empty()) { bestLength = length; best = attack; }
    }
    // No survivor memory to update: these actions deliberately end at a head.
    return best;
}

struct Policy {
    bool expand=false, workers=false, cautiousChild=false;
    int target=32, splitLength=4, stop=350, reserve=6, reserveStop=470;
    double continuation=0;
};
struct PatrolPolicy {
    int radius, holdRounds, pearlWait;
    double entranceWeight, centerWeight;
};

template<class Bot>
PatrolPolicy patrolPolicy(const Bot& bot) {
        if (bot.identifiedMap()) {
            const auto p = bot.tuning();
            return {p.patrol_radius, p.patrol_hold, p.patrol_wait,
                    p.patrol_entrance / 100.0, p.patrol_center / 100.0};
        }
        switch (bot.mapPlan()) {
        case MapPlan::Colosseum: return {3, 40, 32, 0.30, 0.0};
        case MapPlan::DefaultSmall: return {2, 20, 16, 0.10, 0.05};
        case MapPlan::Help: return {3, 32, 20, 0.20, 0.0};
        case MapPlan::Queen: return bot.seasonalFood
            ? PatrolPolicy{3, 24, 16, 0.20, 0.05}
            : PatrolPolicy{4, 48, 32, 0.30, 0.10};
        case MapPlan::Schooltime: return {3, 32, 24, 0.25, 0.05};
        case MapPlan::Trophy: return {4, 32, 24, 0.15, 0.10};
        case MapPlan::BigEmpty: return {5, 24, 16, 0.0, 0.05};
        default: return {3, 32, 24, 0.15, 0.10};
        }
    
}

template<class Bot>
int patrolWaypoint(Bot& bot, const std::vector<int>& anchors) {
        const auto tuning = bot.patrolPolicy();
        // Refresh the patrol area periodically; never stay for a whole match.
        if (bot.patrolAnchor < 0 || bot.round >= bot.patrolUntil || bot.fixed[bot.patrolAnchor]) {
            bot.patrolAnchor = -1;
            int bestDistance = bot.n + 1;
            for (int p : anchors) {
                int dx = std::abs(p % bot.w - bot.body.front() % bot.w);
                int dy = std::abs(p / bot.w - bot.body.front() / bot.w);
                int distance = std::min(dx, bot.w - dx) + std::min(dy, bot.h - dy);
                if (distance < bestDistance) { bestDistance = distance; bot.patrolAnchor = p; }
            }
            bot.patrolUntil = bot.round + tuning.holdRounds;
        }
        if (bot.patrolAnchor < 0) return -1;
        std::vector<int> distance(bot.n, -1);
        std::deque<int> queue{bot.patrolAnchor}; distance[bot.patrolAnchor] = 0;
        int target = -1; double best = -1;
        while (!queue.empty()) {
            int p = queue.front(); queue.pop_front();
            int exits = 0; bool entrance = false;
            for (int d = 0; d < 4; ++d) {
                int q = bot.graph[p][d];
                entrance |= bot.cells[p].edge[d] > 0;
                if (q >= 0 && !bot.fixed[q]) ++exits;
                if (bot.cells[p].edge[d] != 0 || q < 0 || bot.fixed[q] || bot.cells[q].seen < 0 ||
                    distance[q] >= 0 || distance[p] >= tuning.radius) continue;
                distance[q] = distance[p] + 1; queue.push_back(q);
            }
            if (exits < 2 || bot.fixed[p] || bot.contains(bot.body, p)) continue;
            double score = std::min(32, bot.round - bot.lastVisit[p]) / 32.0
                + tuning.entranceWeight * entrance + 0.05 * distance[p];
            if (score > best) { best = score; target = p; }
        }
        return target;
    
}

template<class Bot, class Controller>
void planOuterPearls(Bot& bot, Controller const& ct) {
        bot.outerPearls.assign(bot.n, 0); bot.forageCluster = -1;
        if (bot.identifiedMap() != 5 || bot.body.empty() || bot.actualLength >= 12 ||
            bot.round >= bot.tuning().outer_pearl_stop || !bot.tuning().outer_pearl_weight ||
            bot.myid % 4 != (bot.team == 'A' ? 2 : 3)) return;
        // Static spawn-rate priors, not knowledge of unseen live pearls.
        const std::array<int, 6> upper{43, 44, 45, 60, 61, 77};
        std::vector<std::vector<int>> incoming(bot.n);
        for (int p = 0; p < bot.n; ++p) for (int q : bot.graph[p])
            if (q >= 0 && !bot.fixed[q]) incoming[q].push_back(p);
        double best = -1;
        // Opening regions rotate 180 degrees with the team's spawn positions.
        const int homeCluster = bot.team == 'A' ? 0 : 1;
        for (int cluster = homeCluster; cluster <= homeCluster; ++cluster) {
            int anchor = cluster ? 195 : 60, neighbors = 0;
            for (auto const& tile : ct.get_tiles()) if (auto part = tile.get_dragon()) {
                if (!part->is_head() || part->get_id() == bot.myid || part->get_team() != ct.get_team()) continue;
                int p = bot.index(tile.get_position());
                int dx = std::abs(p % bot.w - anchor % bot.w), dy = std::abs(p / bot.w - anchor / bot.w);
                neighbors += std::min(dx, bot.w - dx) + std::min(dy, bot.h - dy) <= 3;
            }
            if (neighbors >= 2) continue;
            std::vector<int> distance(bot.n, bot.n + 1); std::deque<int> queue;
            double food = 0;
            for (int top : upper) {
                int p = cluster ? 255 - top : top;
                if (bot.fixed[p]) continue;
                bool recent = bot.cells[p].seen >= bot.round - 15;
                if (recent && !bot.cells[p].pearl && (bot.cells[p].due < bot.round || bot.cells[p].due > bot.round + 8)) continue;
                food += recent && bot.cells[p].pearl ? 2.0 : 1.0;
                distance[p] = 0; queue.push_back(p);
            }
            while (!queue.empty()) {
                int p = queue.front(); queue.pop_front();
                for (int q : incoming[p]) if (distance[q] > distance[p] + 1) {
                    distance[q] = distance[p] + 1; queue.push_back(q);
                }
            }
            if (distance[bot.body.front()] > bot.n || food == 0) continue;
            double score = food / (distance[bot.body.front()] + 2.0);
            if (score <= best) continue;
            best = score; bot.forageCluster = cluster;
            for (int p = 0; p < bot.n; ++p)
                bot.outerPearls[p] = distance[p] <= bot.n ? 1.0 / (distance[p] + 1) : 0;
        }
    
}

template<class Bot, class Controller>
void planTerritory(Bot& bot, Controller const& ct) {
        if (bot.mapStatus.active && !bot.mapStatus.middle.map) {
            bot.outerPearls.assign(bot.n, 0);
            bot.territory.assign(bot.n, 0);
            bot.territoryWeight = 0;
            bot.forageCluster = -1;
            return;
        }
        bot.planOuterPearls(ct);
        const auto patrol = bot.patrolPolicy();
        const bool mobilePatrol = bot.identifiedMap() ? bot.tuning().patrol_enabled : (bot.w == 16 && bot.h == 16) ||
            (bot.w == 25 && bot.h == 35 && bot.team == 'B' && bot.observedQueenSlowFood) ||
            (bot.w == 25 && bot.h == 25 && bot.team == 'B');
        bot.territory.assign(bot.n, 0);
        bot.territoryWeight = Bot::territoryOverride >= 0 ? Bot::territoryOverride
            : bot.tuning().territory_weight;
        if (!bot.identifiedMap() && bot.w == 16 && bot.h == 16 && bot.team == 'B' && bot.compactSlowFood) bot.territoryWeight = 0;
        if (bot.territoryWeight == 0 || bot.body.empty()) return;
        // Components exclude portals and unseen edges: never invent a room.
        std::vector<int> region(bot.n, -1), size;
        std::vector<bool> sealed;
        bool portals = false;
        for (auto const& cell : bot.cells) {
            for (int e : cell.edge) portals |= e > 0;
            if (portals) break;
        }
        // Only long dragons use component capacity to choose an exit.
        if (portals && bot.actualLength >= 12) for (int p = 0; p < bot.n; ++p) {
            if (bot.cells[p].seen < 0 || region[p] >= 0) continue;
            int id = int(size.size()); size.push_back(0); sealed.push_back(true);
            std::deque<int> queue{p}; region[p] = id;
            while (!queue.empty()) {
                int q = queue.front(); queue.pop_front(); ++size[id];
                for (int d = 0; d < 4; ++d) {
                    int r = bot.graph[q][d], e = bot.cells[q].edge[d];
                    if (e == -2 || (e == 0 && (r < 0 || bot.cells[r].seen < 0))) sealed[id] = false;
                    if (e != 0 || r < 0 || bot.cells[r].seen < 0 || region[r] >= 0) continue;
                    region[r] = id; queue.push_back(r);
                }
            }
        }
        int home = region[bot.body.front()];
        bool evacuate = portals && bot.actualLength >= 12 && home >= 0 && sealed[home]
            && size[home] < bot.actualLength * 4;
        // IDs distribute provisional roles, not a claim of global coordination.
        bool guard = bot.actualLength < 12 && bot.myid % 4 == 0;
        std::vector<int> targets;
        if (evacuate) {
            for (int p = 0; p < bot.n; ++p)
                if (region[p] >= 0 && size[region[p]] > size[home] && !bot.fixed[p]) targets.push_back(p);
        } else if (guard) {
            for (int p = 0; p < bot.n; ++p) {
                if (!bot.visible[p] || bot.fixed[p] || bot.cells[p].due < bot.round ||
                    bot.cells[p].due > bot.round + (mobilePatrol ? patrol.pearlWait : 24)) continue;
                int exits = 0, neighbors = 0;
                for (int q : bot.graph[p]) exits += q >= 0 && !bot.fixed[q];
                for (auto const& tile : ct.get_tiles()) if (auto part = tile.get_dragon())
                    if (part->is_head() && part->get_id() != bot.myid && part->get_team() == ct.get_team()) {
                        int q = bot.index(tile.get_position());
                        int dx = std::abs(q % bot.w - p % bot.w), dy = std::abs(q / bot.w - p / bot.w);
                        neighbors += std::min(dx, bot.w - dx) + std::min(dy, bot.h - dy) <= 4;
                    }
                if (exits >= 2 && neighbors < 2) targets.push_back(p);
            }
            if (mobilePatrol) {
                int waypoint = bot.patrolWaypoint(targets);
                targets.clear();
                if (waypoint >= 0) targets.push_back(waypoint);
            }
        }
        if (!targets.empty()) {
            std::vector<std::vector<int>> incoming(bot.n);
            for (int p = 0; p < bot.n; ++p) for (int q : bot.graph[p])
                if (q >= 0 && !bot.fixed[q] && bot.cells[p].seen >= 0 && bot.cells[q].seen >= 0) incoming[q].push_back(p);
            std::vector<int> distance(bot.n, bot.n + 1);
            std::deque<int> queue;
            for (int p : targets) { distance[p] = 0; queue.push_back(p); }
            while (!queue.empty()) {
                int p = queue.front(); queue.pop_front();
                for (int q : incoming[p]) if (distance[q] > distance[p] + 1) {
                    distance[q] = distance[p] + 1; queue.push_back(q);
                }
            }
            for (int p = 0; p < bot.n; ++p) if (distance[p] <= bot.n)
                bot.territory[p] = 1.0 / (distance[p] + 1);
        } else if (!portals && !guard) {
            for (int p = 0; p < bot.n; ++p) {
                if (bot.cells[p].seen < 0 || bot.fixed[p]) continue;
                int exits = 0;
                for (int q : bot.graph[p]) exits += q >= 0 && !bot.fixed[q];
                if (exits < 3) continue;
                double central = 1.0 - (std::abs(2 * (p % bot.w) - (bot.w - 1))
                    + std::abs(2 * (p / bot.w) - (bot.h - 1))) / double(bot.w + bot.h);
                bot.territory[p] = (bot.identifiedMap() || mobilePatrol ? patrol.centerWeight : 0.25) * central;
            }
        }
    
}

template<class Bot>
Policy policy(const Bot& bot, bool confined) {
        if (bot.mapStatus.active && !bot.mapStatus.middle.map) {
            Policy generic;
            generic.expand = generic.workers = bot.n <= 256 || confined;
            return generic;
        }
        Policy p; p.expand=p.workers=(bot.n<=256 || confined);
        switch (bot.mapPlan()) {
        case MapPlan::Arena: p.continuation=0.20; break;
        case MapPlan::DefaultSmall: break; // retain the winning baseline; tested alternatives regressed B
        case MapPlan::Help:
            p.expand=p.workers=true; p.splitLength=6; p.cautiousChild=true;
            p.stop=320; p.reserve=10; break;
        case MapPlan::Trophy: break; // retain long-body baseline until both sides improve
        // Preserve the established length advantage on these maps first.
        case MapPlan::BigEmpty: p.expand=p.workers=false; break;
        case MapPlan::Colosseum: case MapPlan::Compact: case MapPlan::Default:
        case MapPlan::Queen: case MapPlan::Schooltime: case MapPlan::Generic: break;
        }
        const auto tuning = bot.tuning();
        const bool help = bot.mapPlan() == MapPlan::Help;
        int food = 0;
        for (int i = 0; i < bot.n; ++i)
            if (bot.visible[i] && bot.cells[i].pearl && !bot.fixed[i]) ++food;
        p.target = bot.n <= 256 ? tuning.small_target :
            confined ? tuning.confined_target : tuning.open_target;
        p.splitLength = bot.n <= 256 ? tuning.small_split_length :
            (confined ? tuning.confined_split_length :
             food >= 5 ? tuning.rich_split_length : tuning.split_length) + (help ? 2 : 0);
        // Preserve Help's earlier growth phase and larger reserve at defaults.
        p.stop = bot.n <= 256 ? tuning.small_stop_round : tuning.growth_round - (help ? 30 : 0);
        p.reserveStop = tuning.stop_round;
        p.reserve = tuning.reserve + (help ? 4 : 0);
        p.continuation += tuning.worker_continuation / 100.0;
        // Favor continuing workers when observed food replenishes in dense waves.
        if (bot.w == 25 && bot.h == 35 && bot.team == 'A' && bot.seasonalFood) p.continuation = 1.0;
        if (tuning.open_expand) p.expand = p.workers = true;
        if (bot.identifiedMap() && tuning.long_growth) {
            p.expand = true; p.workers = false;
        } else if (!bot.identifiedMap() && bot.w == 25 && bot.h == 35 && bot.team == 'A' && bot.observedQueenFastFood) {
            p.expand = true; p.workers = false;
            p.splitLength = 6; p.target = 24; p.stop = 250;
        }
        return p;
    
}

template<class Bot, class Controller>
std::vector<int> workerAction(Bot& bot, Controller& ct) {
    using State = typename Bot::SearchState;
        State root; root.body = bot.body;
        const bool confined = bot.crowdedTerrain();
        const Policy plan=bot.policy(confined);
        // Board dimensions alone miss large maps made of narrow compartments.
        // Build a reserve there, and replenish a depleted team before endgame.
        const bool breeding = global_strategy::breedingAllowed(bot.round, ct.get_unit_count(), confined, plan);
        // Crowded small boards reward early reproduction. Switch to the
        // long-body planner for the final 150 rounds, when length decides ties.
        // Preserve a trapped long body before adding another tiny Arena worker.
        const bool openingOwnsExpansion = bot.identifiedMap() == 5 &&
            ((bot.myid < 4 && bot.smallOpeningPhase < 3 && bot.round < 140) || bot.round < bot.smallScoutUntil);
        if (!openingOwnsExpansion && plan.expand && breeding && !bot.arenaLongBodyTrapped() && ct.get_length() >= plan.splitLength &&
            ct.get_unit_count() < std::min(plan.target, bot.n / 3) && ct.can_split(2) &&
            (!plan.cautiousChild || (bot.childRoom()>=bot.tuning().nursery && (ct.get_length()<12 || ct.get_unit_count()<plan.reserve))) &&
            (bot.n <= 256 || (bot.complete && bot.breedingExit(bot.body.front()) && bot.breedingExit(bot.body.back())))) {
            if (bot.complete) bot.body.resize(bot.body.size() - 2);
            else bot.body.clear();
            return {-1};
        }
        if (plan.workers && breeding && ct.get_length() <= 5) {
            double best = -1e9; int direction = -1; State chosen;
            for (int d = 0; d < 4; ++d) {
                State next; if (!bot.advance(root, d, next, 1)) continue;
                int p = next.body.front(), exits = 0;
                double continuation=-300;
                for (int e = 0; e < 4; ++e) {
                    State after; if (bot.advance(next, e, after, 2)) {
                        ++exits;
                        int q=after.body.front();
                        continuation=std::max(continuation,(bot.growAt(q,next)?100.0:0.0)-
                            0.7*bot.danger[q]+4*std::min(bot.area(after),8));
                    }
                }
                double score = (bot.growAt(p, root) ? 250 : 0) + 150.0 / (bot.foodDist[p] + 1)
                    + 8 * std::min(bot.area(next), 10) + 25 * exits - 0.7 * bot.danger[p]
                    - 0.5 * std::min(bot.visits[p], 12) + plan.continuation*continuation
                    + (bot.outerPearls.empty() ? 0.0 : bot.tuning().outer_pearl_weight * bot.outerPearls[p])
                    + ((bot.identifiedMap() ? (bot.tuning().worker_patrol == 2 ||
                        (bot.tuning().worker_patrol == 1 && bot.myid % 4 == 0)) :
                        ((bot.w == 16 && bot.h == 16 && ((bot.team == 'B' && !bot.compactSlowFood) ||
                        (bot.team == 'A' && bot.myid % 4 == 0))) ||
                        (bot.w == 25 && bot.h == 35 && bot.team == 'B' && bot.observedQueenSlowFood && bot.myid % 4 == 0) ||
                        (bot.w == 25 && bot.h == 25 && bot.team == 'B' && bot.myid % 4 == 0))) && !bot.territory.empty()
                        ? bot.territoryWeight * bot.territory[p] : 0.0);
                if (!exits && next.body.size() < 4) score -= 500;
                if (bot.dirs[d] == ct.get_dir()) score += 2;
                if (score > best) { best = score; direction = d; chosen = next; }
            }
            if (direction >= 0) { bot.body = chosen.body; return {direction}; }
        }

    return {};
}

// Named entry points retain shared mechanics and per-map/side tuning.
// Add map-specific decisions here without duplicating the safety planner.
template<class Bot, class Controller>
std::vector<int> genericMiddleGame(Bot& bot, Controller& ct) {
    return workerAction(bot, ct);
}

template<class Bot, class Controller>
std::vector<int> arenaMiddleGame(Bot& bot, Controller& ct) {
    return workerAction(bot, ct);
}

template<class Bot, class Controller>
std::vector<int> big_emptyMiddleGame(Bot& bot, Controller& ct) {
    auto rescue = trappedHeadRescue(bot, ct);
    if (!rescue.empty()) return rescue;
    auto trade = headTradeAction(bot, ct);
    if (!trade.empty()) return trade;
    return workerAction(bot, ct);
}

template<class Bot, class Controller>
std::vector<int> colosseumMiddleGame(Bot& bot, Controller& ct) {
    return workerAction(bot, ct);
}

template<class Bot, class Controller>
std::vector<int> defaultMiddleGame(Bot& bot, Controller& ct) {
    return workerAction(bot, ct);
}

template<class Bot, class Controller>
std::vector<int> default_smallMiddleGame(Bot& bot, Controller& ct) {
    return workerAction(bot, ct);
}

template<class Bot, class Controller>
std::vector<int> helpMiddleGame(Bot& bot, Controller& ct) {
    return big_emptyMiddleGame(bot, ct);
}

template<class Bot, class Controller>
std::vector<int> queen_of_spadesMiddleGame(Bot& bot, Controller& ct) {
    return workerAction(bot, ct);
}

template<class Bot, class Controller>
std::vector<int> queen_of_spades_but_she_agesMiddleGame(Bot& bot, Controller& ct) {
    return queen_of_spadesMiddleGame(bot, ct);
}

template<class Bot, class Controller>
std::vector<int> schooltimeMiddleGame(Bot& bot, Controller& ct) {
    return workerAction(bot, ct);
}

template<class Bot, class Controller>
std::vector<int> trophyMiddleGame(Bot& bot, Controller& ct) {
    return workerAction(bot, ct);
}

template<class Bot, class Controller>
std::vector<int> middleGameAction(Bot& bot, Controller& ct) {
    const int map = bot.mapStatus.active ? bot.mapStatus.middle.map : bot.identifiedMap();
    switch (map) {
    case 1: return arenaMiddleGame(bot, ct);
    case 2: return big_emptyMiddleGame(bot, ct);
    case 3: return colosseumMiddleGame(bot, ct);
    case 4: return defaultMiddleGame(bot, ct);
    case 5: return default_smallMiddleGame(bot, ct);
    case 6: return helpMiddleGame(bot, ct);
    case 7: return queen_of_spadesMiddleGame(bot, ct);
    case 8: return queen_of_spades_but_she_agesMiddleGame(bot, ct);
    case 9: return schooltimeMiddleGame(bot, ct);
    case 10: return trophyMiddleGame(bot, ct);
    default: return genericMiddleGame(bot, ct);
    }
}

} // namespace global_strategy
