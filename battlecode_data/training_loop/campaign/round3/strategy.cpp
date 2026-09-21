#define LEVIATHAN_TEST
#include "candidate/main.cpp"
#include <cassert>
#include <iostream>

Leviathan board() {
    Leviathan bot;
    bot.w = bot.h = 11; bot.n = 121; bot.round = 1;
    bot.cells.resize(bot.n); bot.graph.resize(bot.n);
    bot.fixed.assign(bot.n, 0); bot.visible.assign(bot.n, 1);
    bot.foodDist.assign(bot.n, 20); bot.visits.assign(bot.n, 0);
    bot.danger.assign(bot.n, 0); bot.complete = true;
    for (int p = 0; p < bot.n; ++p) {
        bot.cells[p].seen = 1; bot.cells[p].edge.fill(0);
        for (int d = 0; d < 4; ++d) bot.graph[p][d] = bot.adjacent(p, d);
    }
    return bot;
}
int main() {
    // Profiles only use dimensions and observations, never hidden map files.
    auto profiles=board();
    assert(profiles.mapPlan()==Leviathan::MapPlan::Arena);
    assert(profiles.policy(false).continuation>0);
    profiles.w=profiles.h=16; profiles.n=256;
    profiles.cells.resize(256); profiles.visible.resize(256,0);
    assert(profiles.mapPlan()==Leviathan::MapPlan::Compact);
    profiles.cells[0].due=1000;
    assert(profiles.mapPlan()==Leviathan::MapPlan::DefaultSmall);
    profiles.cells[0].edge[1]=8;
    assert(profiles.mapPlan()==Leviathan::MapPlan::Colosseum);
    profiles.cells[0].edge[1]=0; profiles.cells[0].due=-1;
    profiles.w=profiles.h=64; profiles.n=4096;
    profiles.cells.resize(4096); profiles.visible.resize(4096,0);
    assert(profiles.mapPlan()==Leviathan::MapPlan::BigEmpty);
    assert(!profiles.policy(false).expand);
    for(int p=0;p<12;++p) profiles.cells[p].due=profiles.round+15;
    assert(profiles.mapPlan()==Leviathan::MapPlan::Help);
    assert(profiles.policy(false).expand && profiles.policy(false).cautiousChild);
    profiles.w=profiles.h=25;
    assert(profiles.mapPlan()==Leviathan::MapPlan::Trophy);
    assert(profiles.policy(true).expand);
    profiles.h=35;
    assert(profiles.mapPlan()==Leviathan::MapPlan::Queen);
    profiles.w=60; profiles.h=40;
    assert(profiles.mapPlan()==Leviathan::MapPlan::Schooltime);
    auto bot = board(); State s, next;
    s.body = {60, 59, 70, 71};
    assert(!bot.advance(s, 2, next, 1)); // own tail is fatal before it moves
    assert(bot.advance(s, 1, next, 1));
    assert((next.body == std::vector<int>{61, 60, 59, 70}));
    bot.cells[61].pearl = true;
    assert(bot.advance(s, 1, next, 1) && next.body.size() == 5);
    assert(!bot.growAt(61, next)); // same pearl cannot be eaten twice
    bot.cells[61].pearl = false;
    assert(bot.advance(s, 1, next, 1, true) && next.body.size() == 3);
    State tiny; tiny.body = {60, 59};
    assert(!bot.advance(tiny, 1, next, 1, true));
    bot.fixed[61] = 1; assert(!bot.advance(s, 1, next, 1));
    bot.fixed[61] = 0; bot.graph[60][1] = -1;
    assert(!bot.advance(s, 1, next, 1));
    assert(bot.adjacent(0, 3) == 10 && bot.adjacent(0, 0) == 110);

    Game game(11, 11, 64); unswbc::game = &game;
    Controller ct(0, Team::A, Direction::EAST, Vision{}, 64);
    ct.head.position = Position(5, 5); ct.length = 3;
    std::vector<Tile> tiles;
    for (int y = 0; y < 11; ++y) for (int x = 0; x < 11; ++x)
        tiles.emplace_back(Position(x,y));
    auto part = [&](int x, int y, bool head) {
        tiles[y*11+x].dragon_part = DragonPart(Position(x,y),0,Team::A,Direction::EAST,head);
    };
    part(5,5,true); part(4,5,false); part(3,5,false);
    // Portal between (5,5)/(6,5) and (8,8)/(9,8).
    for (auto [p,d] : std::vector<std::pair<int,int>>{{60,1},{61,3},{96,1},{97,3}})
        tiles[p].edges[d] = Edge(false,EdgeType::PORTAL,7);
    ct.vision = Vision(tiles);
    Leviathan observed; observed.observe(ct, game);
    assert(observed.graph[60][1] == 97);
    assert(observed.graph[97][3] == 60);
    assert(observed.complete && observed.body.size() == 3);
    // Portal topology and walls survive a later observation elsewhere.
    tiles[97].edges[1] = Edge(false,EdgeType::KELP);
    tiles[98].edges[3] = Edge(false,EdgeType::KELP);
    ct.vision = Vision(tiles); observed.observe(ct,game);
    ct.vision = Vision(std::vector<Tile>{tiles[60],tiles[59],tiles[58]});
    observed.observe(ct,game);
    assert(observed.graph[60][1] == 97 && observed.graph[97][1] == -1);
    // Never chain a blind sprint through the unknown wall beyond a portal.
    auto portalSprint = board(); portalSprint.body = {60,59,58,57};
    portalSprint.graph[60][1] = 97; portalSprint.cells[60].edge[1] = 8;
    portalSprint.cells[97].edge.fill(-2); portalSprint.visible[97] = 0;
    State beforePortal; beforePortal.body = portalSprint.body;
    State landed, afterPortal;
    assert(portalSprint.advance(beforePortal,1,landed,1));
    assert(!portalSprint.advance(landed,1,afterPortal,1,true));
    portalSprint.cells[97].edge[0] = 0; // remembered safe turn is allowed
    assert(portalSprint.advance(landed,0,afterPortal,1,true));
    // On arrival, forward is a wall and back is occupied: choose a side.
    auto turnAtExit = board(); turnAtExit.round = 400;
    turnAtExit.body = {97,96,95}; turnAtExit.graph[97][1] = -1;
    auto exitAction = turnAtExit.choose(ct);
    assert(exitAction[0] == 0 || exitAction[0] == 2);
    tiles[63].dragon_part = DragonPart(Position(8,5),1,Team::B,Direction::EAST,true);
    ct.vision = Vision(tiles); observed.observe(ct,game);
    double openThreat = observed.danger[64];
    for (int d : {0,2,3}) {
        auto wall = Edge(d != 3,EdgeType::KELP);
        tiles[63].edges[d] = wall;
        tiles[observed.adjacent(63,d)].edges[(d+2)%4] = wall;
    }
    ct.vision = Vision(tiles); observed.observe(ct,game);
    assert(observed.danger[64] > openThreat * 4);
    tiles[63].edges[1] = Edge(false,EdgeType::KELP);
    tiles[64].edges[3] = Edge(false,EdgeType::KELP);
    ct.vision = Vision(tiles); observed.observe(ct,game);
    assert(observed.danger[64] == 0); // no outgoing route, no division by zero
    // A sealed destination must lose to a route with continuing mobility.
    auto trapped = board(); trapped.body = {60,59,58};
    trapped.graph[61].fill(-1);
    auto action = trapped.choose(ct);
    assert(action[0] != 1);
    auto swarm = board(); swarm.body = {60,59,58,57};
    ct.length = 4;
    assert(swarm.choose(ct) == std::vector<int>{-1});
    assert(swarm.body.size() == 2);
    auto late = board(); late.body = {60,59,58,57}; late.round = 400;
    assert(late.choose(ct).front() >= 0);
    // Large but compartmentalized boards need reserves too; open boards do not.
    auto corridors = board(); corridors.w = corridors.h = 20; corridors.n = 400;
    corridors.cells.resize(400); corridors.graph.resize(400);
    corridors.fixed.resize(400); corridors.visible.resize(400,1);
    corridors.foodDist.resize(400,20); corridors.visits.resize(400);
    corridors.danger.resize(400); corridors.body = {210,209,208,207};
    for (int p = 0; p < 400; ++p) {
        corridors.cells[p].seen = 1; corridors.cells[p].edge.fill(0);
        for (int d = 0; d < 4; ++d) corridors.graph[p][d] = corridors.adjacent(p,d);
    }
    assert(!corridors.crowdedTerrain());
    for (int p = 0; p < 400; ++p) {
        corridors.cells[p].edge[0] = corridors.cells[p].edge[2] = -1;
        corridors.graph[p][0] = corridors.graph[p][2] = -1;
    }
    assert(corridors.crowdedTerrain()); ct.length = 4; ct.unit_count = 1;
    auto reserve = corridors;
    assert(reserve.choose(ct).front() == -1);
    auto depleted = corridors; depleted.round = 400;
    assert(depleted.choose(ct).front() == -1); // replenish depleted team late
    auto enough = corridors; enough.round = 400; ct.unit_count = 10;
    assert(enough.choose(ct).front() >= 0); // enough reserves: grow instead
    auto sealedTail = corridors; sealedTail.graph[207].fill(-1);
    assert(!sealedTail.breedingExit(207));
    assert(sealedTail.choose(ct).front() >= 0); // never breed into a sealed tail
    ct.unit_count = 1;
    // The tempting food corridor ends exactly beyond the old lookahead. The
    // alternative cycle remains navigable after the horizon and must win.
    auto horizonTrap = board(); horizonTrap.round = 400;
    horizonTrap.body = {60,59,58}; ct.length = 3;
    for (int p = 0; p < horizonTrap.n; ++p) {
        horizonTrap.graph[p].fill(-1); horizonTrap.cells[p].seen = 400;
    }
    horizonTrap.graph[60][1] = 61;
    for (int p = 61; p < 75; ++p) horizonTrap.graph[p][1] = p + 1;
    horizonTrap.cells[61].pearl = true;
    horizonTrap.graph[60][0] = 0;
    for (int p = 0; p < 20; ++p) horizonTrap.graph[p][0] = (p + 1) % 20;
    assert(horizonTrap.choose(ct).front() == 0);
    // Tail accessibility is a planning signal, never permission to collide
    // with the tail on the current step.
    auto escape = board(); State loop;
    loop.body = {60,59,58,57,68,69,70,71};
    assert(escape.escapeValue(loop) > 0);
    assert(!escape.advance(loop,2,next,1));
    for (auto& edges : escape.graph) edges.fill(-1);
    escape.graph[60][1] = 61;
    assert(escape.escapeValue(loop) < 0);
    escape.complete = false;
    assert(escape.escapeValue(loop) == 0);
    auto rescue = board(); rescue.round = 400; rescue.body = loop.body;
    rescue.graph[60].fill(-1); ct.length = 8; ct.unit_count = 1;
    assert((rescue.choose(ct) == std::vector<int>{-1,6}));
    assert((rescue.body == std::vector<int>{60,59}));
    // A short tail exit still saves a child when the old head is doomed.
    auto shortExit = board(); shortExit.round = 400; shortExit.body = loop.body;
    for (auto& edges : shortExit.graph) edges.fill(-1);
    shortExit.graph[71][2] = 82; shortExit.graph[82][2] = 93;
    shortExit.danger[71] = 200; // child leaves this square on its birth turn
    assert((shortExit.choose(ct) == std::vector<int>{-1,6}));
    auto tinyRescue = board(); tinyRescue.round = 400;
    tinyRescue.body = {60,59,58,57}; tinyRescue.graph[60].fill(-1);
    ct.length = 4;
    assert((tinyRescue.choose(ct) == std::vector<int>{-1,2}));
    // A partial body must not force a wall collision when splitting is legal.
    auto unseenTail = board(); unseenTail.round = 400; unseenTail.complete = false;
    unseenTail.body = {60,59,58}; unseenTail.actualLength = 20;
    unseenTail.graph[60].fill(-1); ct.length = 20;
    assert((unseenTail.choose(ct) == std::vector<int>{-1,18}));
    auto unseenLimit = board(); unseenLimit.round = 400; unseenLimit.complete = false;
    unseenLimit.body = {60,59,58}; unseenLimit.actualLength = 20;
    unseenLimit.graph[60].fill(-1); ct.unit_count = 64;
    assert(unseenLimit.choose(ct).front() >= 0);
    ct.length = 8; ct.unit_count = 1;
    auto noExit = board(); noExit.round = 400; noExit.body = loop.body;
    noExit.graph[60].fill(-1); noExit.graph[71].fill(-1);
    assert(noExit.choose(ct).front() >= 0);
    auto unitLimit = board(); unitLimit.round = 400; unitLimit.body = loop.body;
    unitLimit.graph[60].fill(-1); ct.unit_count = 64;
    assert(unitLimit.choose(ct).front() >= 0);
    // A new long child must retain its accumulated prefix even when the rear
    // of that prefix is outside current vision, and extend it when seen again.
    Leviathan memory; memory.body = {61,60,59,58,57}; memory.complete = false;
    ct.length = 8; ct.unit_count = 1; ct.head.position = Position(6,5);
    auto observeParts = [&](std::vector<int> positions) {
        std::vector<Tile> view;
        for (int p : positions) {
            Position pos(p%11,p/11);
            view.emplace_back(pos, DragonPart(pos,0,Team::A,Direction::EAST,p==61));
        }
        ct.vision = Vision(view); memory.observe(ct,game);
    };
    observeParts({61,60,59});
    assert(memory.body.size() == 5 && !memory.complete);
    observeParts({61,60,59,58,57,56,55,65});
    assert(memory.body.size() == 8 && memory.complete);
    auto partial = board(); partial.complete = false; partial.actualLength = 8;
    State history; history.body = {61,60,59,58,57};
    for (int step = 0; step < 5; ++step) {
        State future; assert(partial.advance(history,1,future,step+1));
        assert(future.body.size() <= 8); history = future;
    }
    Game largeGame(32,32,64); unswbc::game = &largeGame;
    std::vector<Tile> heads;
    heads.emplace_back(Position(6,5), DragonPart(Position(6,5),0,Team::A,Direction::EAST,true));
    heads.emplace_back(Position(8,5), DragonPart(Position(8,5),1,Team::B,Direction::WEST,true));
    ct.vision = Vision(heads); ct.length = 8;
    Leviathan protection; protection.observe(ct,largeGame);
    double shortRisk = protection.danger[5*32+9];
    ct.length = 32; protection.observe(ct,largeGame);
    assert(protection.danger[5*32+9] > shortRisk);
    std::cout << "PASS: collision, growth, sprint, wrap, portals, body reconstruction, forced-head danger, splitting, horizon trap\n";
}
