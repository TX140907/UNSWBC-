#pragma once
#include <algorithm>
#include <cmath>
#include <deque>
#include <vector>

namespace global_strategy {

enum class MapPlan { Generic, Arena, Compact, Colosseum, DefaultSmall,
    Default, BigEmpty, Help, Queen, Schooltime, Trophy };

enum class MapEvidence { Unknown, Dimensions, Geometry, Timer, Conflict, InitialCount, InitialSpawn };
struct StageMapStatus {
    int map = 0;
    MapPlan plan = MapPlan::Generic;
    int updatedRound = -1;
};
struct MapStatus {
    bool active = false;
    unsigned candidates = 0;
    int map = 0, firstIdentifiedRound = -1;
    MapEvidence evidence = MapEvidence::Unknown;
    int initialMapHint = 0;
    MapEvidence initialEvidence = MapEvidence::Unknown;
    StageMapStatus opening, middle, ending;
};

inline MapPlan planForMap(int map) {
    switch (map) {
    case 1: return MapPlan::Arena; case 2: return MapPlan::BigEmpty;
    case 3: return MapPlan::Colosseum; case 4: return MapPlan::Default;
    case 5: return MapPlan::DefaultSmall; case 6: return MapPlan::Help;
    case 7: case 8: return MapPlan::Queen;
    case 9: return MapPlan::Schooltime; case 10: return MapPlan::Trophy;
    default: return MapPlan::Generic;
    }
}

inline unsigned dimensionCandidates(int w, int h) {
    if (w==11 && h==11) return 1u<<1;
    if (w==32 && h==32) return 1u<<4;
    if (w==60 && h==40) return 1u<<9;
    if (w==25 && h==25) return 1u<<10;
    if (w==16 && h==16) return (1u<<3)|(1u<<5);
    if (w==64 && h==64) return (1u<<2)|(1u<<6);
    if (w==25 && h==35) return (1u<<7)|(1u<<8);
    return 0;
}

template<class Bot>
void observeInitialRoster(Bot& bot, int units, int x, int y) {
    if (bot.w!=64 || bot.h!=64 || bot.round!=0 || bot.mapStatus.active) return;
    auto& status=bot.mapStatus;
    // The first three originals per team act before any newborn. At most two
    // earlier allies can split: Big Empty stays <=5. Help assumes no early deaths
    // in its protected opening. Restrict this rule to the known round-0 roster.
    if (bot.myid>=0 && bot.myid<6 && bot.team==(bot.myid%2?'B':'A') && units>0) {
        status.initialMapHint=units<=5?2:6;
        status.initialEvidence=MapEvidence::InitialCount;
        return;
    }
    // Original dragons can recognize their own unchanged spawn even after
    // earlier dragons split. Newborns and displaced dragons must use observations.
    struct Spawn { int x,y,length; };
    constexpr Spawn empty[]={{13,14,6},{50,49,6},{18,17,6},{45,46,6},{8,11,6},{55,52,6}};
    constexpr Spawn help[]={{3,5,5},{60,58,5},{61,5,5},{2,58,5},{16,24,5},{47,39,5},
        {39,25,14},{24,38,14},{34,13,9},{29,50,9},{45,12,9},{18,51,9}};
    int id=bot.myid;
    if (id<0 || bot.team!=(id%2?'B':'A')) return;
    auto matches=[&](const Spawn& s) {return x==s.x && y==s.y && bot.actualLength==s.length;};
    if (id<6 && matches(empty[id])) status.initialMapHint=2;
    else if (id<12 && matches(help[id])) status.initialMapHint=6;
    if (status.initialMapHint) status.initialEvidence=MapEvidence::InitialSpawn;
}

// Signatures distinguish the repository catalogue. Compare observed edge types,
// never portal IDs/colors. Arbitrary custom maps are outside this closed set.
struct EdgeSignature { int w,h,x,y,d,first,second,firstType,secondType; };
inline constexpr EdgeSignature signatures[] = {
    {16,16,15,1,1,5,3,-1,0}, {16,16,12,8,1,5,3,0,1},
    {16,16,5,14,0,5,3,-1,0}, {16,16,12,11,1,5,3,0,-1},
    {64,64,17,14,1,2,6,0,-1}, {64,64,42,44,3,2,6,0,-1},
    {64,64,7,13,1,2,6,0,1}, {64,64,55,50,1,2,6,0,1}
};

inline bool seasonalFoodDensity(int mediumTimers, int longTimers) {
        return mediumTimers >= 8 && mediumTimers >= 3 * longTimers;
    
}

inline int queenTimerCeiling(int p) {
        // Known Queen variants share geometry; only a visible timer above the
        // aged variant's bound is positive evidence for the slow-food variant.
        p = std::min(p, 874 - p);
        switch (p) {
        case 87: case 94: case 110: case 111: case 112: case 113: case 114:
        case 115: case 116: case 117: case 118: case 119: case 120: return 80;
        case 135: case 136: case 137: case 143: case 144: case 145:
        case 159: case 160: case 161: case 169: case 170: case 171: return 160;
        case 184: case 185: case 186: case 194: case 195: case 196: case 197:
        case 208: case 209: case 210: case 220: case 221: case 222: return 240;
        case 232: case 233: case 234: case 235: case 245: case 246: case 247:
        case 257: case 258: case 259: case 260: case 269: case 270: case 271: case 272: return 320;
        case 282: case 283: case 284: case 285: case 286: case 293: case 294:
        case 295: case 296: case 297: case 308: case 309: case 310: case 311:
        case 312: case 317: case 318: case 319: case 320: case 321: case 322: return 400;
        case 333: case 334: case 335: case 342: case 343: case 344:
        case 345: case 346: case 359: case 360: case 370: return 480;
        default: return 0;
        }
    
}

template<class Bot>
int identifiedMap(const Bot& bot) {
        if (bot.mapStatus.active) return bot.mapStatus.middle.map;
        if (bot.w == 11 && bot.h == 11) return 1;
        if (bot.w == 32 && bot.h == 32) return 4;
        if (bot.w == 60 && bot.h == 40) return 9;
        if (bot.w == 25 && bot.h == 25) return 10;
        if (bot.w == 16 && bot.h == 16) {
            if (bot.compactSlowFood) return 5;
            for (const auto& cell : bot.cells)
                for (int edge : cell.edge) if (edge > 0) return 3;
        }
        if (bot.w == 64 && bot.h == 64) {
            if (bot.enclosedOrFastWater) return 6;
            if (bot.observedOpenWater) return 2;
        }
        if (bot.w == 25 && bot.h == 35) {
            if (bot.observedQueenSlowFood) return 7;
            if (bot.observedQueenFastFood) return 8;
        }
        return 0;
    
}

template<class Bot>
MapPlan mapPlan(const Bot& bot) {
        if (bot.mapStatus.active) return bot.mapStatus.middle.plan;
        int walls=0, portals=0, shortTimers=0, longTimers=0;
        for (int p=0;p<bot.n;++p) {
            for (int e:bot.cells[p].edge) { walls += e == -1; portals += e > 0; }
            if (!bot.visible[p] || bot.cells[p].due < bot.round) continue;
            if (bot.cells[p].due-bot.round <= 20) ++shortTimers; else ++longTimers;
        }
        if (bot.w==11 && bot.h==11) return MapPlan::Arena;
        if (bot.w==16 && bot.h==16) {
            if (portals) return MapPlan::Colosseum;
            for (int p=0;p<bot.n;++p)
                if (bot.visible[p] && bot.cells[p].due-bot.round > 250) return MapPlan::DefaultSmall;
            return MapPlan::Compact; // these maps cannot always be distinguished yet
        }
        if (bot.w==32 && bot.h==32) return MapPlan::Default;
        if (bot.w==64 && bot.h==64)
            return walls || portals || (shortTimers>=12 && !longTimers) ? MapPlan::Help : MapPlan::BigEmpty;
        if (bot.w==25 && bot.h==35) return MapPlan::Queen;
        if (bot.w==60 && bot.h==40) return MapPlan::Schooltime;
        if (bot.w==25 && bot.h==25) return MapPlan::Trophy;
        return MapPlan::Generic;
    
}

template<class Bot>
void observePearlTimer(Bot& bot, int p, int timer) {
    if (bot.w == 16 && bot.h == 16 && timer > 250) bot.compactSlowFood = true;
    if (bot.w == 25 && bot.h == 35 && queenTimerCeiling(p) > 0 &&
        timer > queenTimerCeiling(p)) bot.observedQueenSlowFood = true;
    if (bot.w == 25 && bot.h == 35 && bot.round < 20 &&
        queenTimerCeiling(p) > 0 && !bot.queenSampled[p] && timer >= 0) {
        bot.queenSampled[p] = 1;
        int upper = queenTimerCeiling(p), lower = upper == 80 ? 40 : upper - 80;
        int initialDue = timer + bot.round;
        if (initialDue < lower - 1 || initialDue > upper + 1) bot.queenFastRejected = true;
        else ++bot.queenFastSamples;
    }
}

template<class Bot>
void finishObservation(Bot& bot, int mediumTimers, int longTimers) {
    bot.seasonalFood = seasonalFoodDensity(mediumTimers, longTimers);
    bot.observedQueenFastFood = !bot.observedQueenSlowFood && !bot.queenFastRejected && bot.queenFastSamples >= 4;
    auto& status = bot.mapStatus;
    if (!status.active) {
        status.active = true;
        status.candidates = dimensionCandidates(bot.w, bot.h);
        status.evidence = MapEvidence::Dimensions;
    }
    auto retain = [&](unsigned allowed, MapEvidence evidence) {
        auto previous = status.candidates;
        status.candidates &= allowed;
        if (previous != status.candidates) status.evidence = evidence;
    };
    if (status.initialMapHint) retain(1u<<status.initialMapHint, status.initialEvidence);
    for (const auto& s : signatures) {
        if (bot.w != s.w || bot.h != s.h) continue;
        int edge = bot.cells[s.y*bot.w+s.x].edge[s.d];
        if (edge == -2) continue;
        int type = edge > 0 ? 1 : edge;
        unsigned allowed = 0;
        if (type == s.firstType) allowed |= 1u << s.first;
        if (type == s.secondType) allowed |= 1u << s.second;
        retain(allowed, MapEvidence::Geometry);
    }
    if (bot.w==16 && bot.h==16 && bot.compactSlowFood)
        retain(1u<<5, MapEvidence::Timer);
    if (bot.w==25 && bot.h==35 && bot.observedQueenSlowFood)
        retain(1u<<7, MapEvidence::Timer);
    if (bot.w==64 && bot.h==64) {
        for (int p=0;p<bot.n;++p) {
            for (int edge : bot.cells[p].edge)
                if (edge == -1 || edge > 0) retain(1u<<6, MapEvidence::Geometry);
            if (bot.visible[p] && bot.cells[p].due-bot.round > 20)
                retain(1u<<2, MapEvidence::Timer);
        }
    }
    status.map = 0;
    if (status.candidates && !(status.candidates & (status.candidates-1)))
        for (int id=1;id<=10;++id) if (status.candidates & (1u<<id)) status.map=id;
    if (!status.candidates) status.evidence = MapEvidence::Conflict;
    if (status.map && status.firstIdentifiedRound < 0) status.firstIdentifiedRound=bot.round;
    // Exact variant may remain unknown; both Queen candidates share one strategy.
    const unsigned queens = (1u<<7)|(1u<<8);
    const unsigned largeMaps = (1u<<2)|(1u<<6);
    const int strategy = status.candidates && !(status.candidates & ~queens) ? 7 :
        status.candidates && !(status.candidates & ~largeMaps) ? 2 : status.map;
    StageMapStatus stage{strategy, planForMap(strategy), bot.round};
    status.opening = status.middle = status.ending = stage;
    bot.enclosedOrFastWater = status.map==6;
    bot.observedOpenWater = status.map==2;
}

} // namespace global_strategy
