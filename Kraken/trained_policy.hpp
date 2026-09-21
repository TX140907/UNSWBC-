#pragma once

struct KrakenPolicy {
    int split_length = 6;
    int rich_split_length = 4;
    int confined_split_length = 4;
    int open_target = 56;
    int confined_target = 40;
    int reserve = 12;
    int nursery = 6;
    int growth_round = 420;
    int stop_round = 480;
    int small_stop_round = 350;
    int worker_continuation = 0;
    int risk_percent = 100;
    int search_horizon = 14;
    int small_target = 32;
    int small_split_length = 4;
    int open_expand = 1;
    int food_percent = 100;
};


inline KrakenPolicy kraken_policy(int w, int h, char side = '?') {
    if (w == 32 && h == 32 && side == 'A') return {4, 4, 4, 56, 40, 12, 6, 420, 480, 350, 0, 75, 14, 32, 4, 1, 100};
    if (w == 60 && h == 40 && side == 'B') return {6, 4, 4, 56, 40, 12, 6, 420, 480, 350, 10, 75, 14, 32, 4, 1, 100};
    if (w == 64 && h == 64 && side == 'A') return {8, 4, 4, 56, 40, 12, 6, 420, 480, 350, 0, 75, 14, 32, 4, 1, 100};
    if (w == 11 && h == 11) return {6, 4, 4, 56, 40, 12, 6, 420, 480, 350, 40, 100, 14, 32, 4, 1, 100};
    if (w == 16 && h == 16) return {6, 4, 4, 56, 40, 12, 6, 420, 480, 350, 10, 100, 14, 32, 4, 1, 100};
    if (w == 25 && h == 25) return {10, 4, 4, 56, 40, 12, 6, 420, 480, 350, 0, 100, 14, 32, 4, 1, 100};
    if (w == 25 && h == 35) return {4, 4, 4, 56, 40, 12, 6, 420, 480, 350, 0, 75, 14, 32, 4, 1, 100};
    if (w == 32 && h == 32) return {4, 4, 4, 56, 40, 12, 6, 420, 480, 350, 0, 100, 14, 32, 4, 1, 100};
    if (w == 60 && h == 40) return {6, 4, 4, 56, 40, 12, 6, 420, 480, 350, 0, 75, 14, 32, 4, 1, 100};
    if (w == 64 && h == 64) return {8, 4, 4, 56, 40, 12, 6, 420, 480, 350, 0, 100, 14, 32, 4, 1, 100};
    return {};
}
