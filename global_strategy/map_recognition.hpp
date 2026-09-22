#pragma once
#include <algorithm>
#include <cmath>
#include <deque>
#include <vector>

namespace global_strategy {

enum class MapPlan { Generic, Arena, Compact, Colosseum, DefaultSmall,
    Default, BigEmpty, Help, Queen, Schooltime, Trophy };

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
    if (bot.w == 64 && bot.h == 64) {
        bot.enclosedOrFastWater |= mapPlan(bot) == MapPlan::Help;
        bot.observedOpenWater = !bot.enclosedOrFastWater;
    }
}

} // namespace global_strategy
