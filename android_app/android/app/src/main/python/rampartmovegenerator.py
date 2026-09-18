#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 26 12:07:05 2025

@author: stereo
"""

import numpy as np
from ai_casting import AiCastingArbiter


# ███╗░░░███╗░█████╗░██╗░░░██╗███████╗
# ████╗░████║██╔══██╗██║░░░██║██╔════╝
# ██╔████╔██║██║░░██║╚██╗░██╔╝█████╗░░
# ██║╚██╔╝██║██║░░██║░╚████╔╝░██╔══╝░░
# ██║░╚═╝░██║╚█████╔╝░░╚██╔╝░░███████╗
# ╚═╝░░░░░╚═╝░╚════╝░░░░╚═╝░░░╚══════╝

# ░██████╗░███████╗███╗░░██╗███████╗██████╗░░█████╗░████████╗░█████╗░██████╗░
# ██╔════╝░██╔════╝████╗░██║██╔════╝██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗
# ██║░░██╗░█████╗░░██╔██╗██║█████╗░░██████╔╝███████║░░░██║░░░██║░░██║██████╔╝
# ██║░░╚██╗██╔══╝░░██║╚████║██╔══╝░░██╔══██╗██╔══██║░░░██║░░░██║░░██║██╔══██╗
# ╚██████╔╝███████╗██║░╚███║███████╗██║░░██║██║░░██║░░░██║░░░╚█████╔╝██║░░██║
# ░╚═════╝░╚══════╝╚═╝░░╚══╝╚══════╝╚═╝░░╚═╝╚═╝░░╚═╝░░░╚═╝░░░░╚════╝░╚═╝░░╚═╝

class RampartMoveGenerator:
    def __init__(self):
        # tables for bitboard lookups
        self.KNIGHT_TABLE = [0] * 60
        self.ROOK_TABLE = [0] * 60  # basic reach (ignoring blockers)
        self.ROOK_RAYS = [[0]*4 for _ in range(60)] # 0:Up, 1:Down, 2:Left, 3:Right
        self.QUEEN_RAYS = [[0]*8 for _ in range(60)] # 4 orthogonal + 4 diagonal
        
        self._precompute_knights()
        self._precompute_rooks()
        self._precompute_queens()
        
        self.KING_TABLE = [0] * 60
        self._precompute_kings()
        
    def _precompute_queens(self):
        """Generates 8 rays for the Queen (Rule 33)."""
        directions = [(0, 1), (0, -1), (-1, 0), (1, 0),  # orthogonal
                      (-1, -1), (-1, 1), (1, -1), (1, 1)] # diagonal
        
        for col in range(10):
            for row in range(6):
                sq = row * 10 + col
                for i, (dc, dr) in enumerate(directions):
                    ray = 0
                    nc, nr = col + dc, row + dr
                    while 0 <= nc < 10 and 0 <= nr < 6:
                        ray |= (1 << (nr * 10 + nc))
                        nc += dc
                        nr += dr
                    self.QUEEN_RAYS[sq][i] = ray

    def get_knight_moves(self, sq, friendly_mask, valid_mask):
        """Returns legal knight moves (Rule 31) filtered by territory."""
        return self.KNIGHT_TABLE[sq] & ~friendly_mask & valid_mask

    def get_queen_moves(self, sq, occupied, friendly_mask, valid_mask):
        """
        Calculates sliding moves for a Queen at 'sq' (Rule 33).
        Uses ray-tracing and stops at the first blocker in 8 directions.
        """
        moves = 0
        for i in range(8): # 8 directions
            ray = self.QUEEN_RAYS[sq][i]
            blockers = ray & occupied
            if blockers:
                # down, right, down-left, down-right (increasing indices)
                if i in [0, 3, 5, 7]:
                    first_blocker_sq = (blockers & -blockers).bit_length() - 1
                # up, left, up-left, up-right (decreasing indices)
                else: 
                    first_blocker_sq = blockers.bit_length() - 1
                
                # truncate the ray at the blocker
                line_to_blocker = ray ^ self.QUEEN_RAYS[first_blocker_sq][i]
                moves |= line_to_blocker
            else:
                moves |= ray
        
        return moves & ~friendly_mask & valid_mask

    def get_bishop_moves(self, sq, occupied, friendly_mask, valid_mask):
        """
        Calculates sliding moves for a Bishop at 'sq'.
        Reuses the precomputed Queen diagonal rays (indices 4-7).
        """
        moves = 0
        for i in [4, 5, 6, 7]: # diagonal directions only
            ray = self.QUEEN_RAYS[sq][i]
            blockers = ray & occupied
            if blockers:
                if i in [0, 3, 5, 7]:
                    first_blocker_sq = (blockers & -blockers).bit_length() - 1
                else:
                    first_blocker_sq = blockers.bit_length() - 1

                line_to_blocker = ray ^ self.QUEEN_RAYS[first_blocker_sq][i]
                moves |= line_to_blocker
            else:
                moves |= ray

        return moves & ~friendly_mask & valid_mask

    def _precompute_knights(self):
        """Generates all legal L-moves for every square on a 10x6 grid."""
        offsets = [
            (1, 2), (2, 1), (2, -1), (1, -2),
            (-1, -2), (-2, -1), (-2, 1), (-1, 2)
        ]
        for col in range(10):
            for row in range(6):
                sq = row * 10 + col
                moves = 0
                for dc, dr in offsets:
                    nc, nr = col + dc, row + dr
                    if 0 <= nc < 10 and 0 <= nr < 6:
                        moves |= (1 << (nr * 10 + nc))
                self.KNIGHT_TABLE[sq] = moves

    def _precompute_rooks(self):
        """Generates rays for Rooks. Essential for sliding piece logic."""
        # directions: (d_col, d_row)
        directions = [(0, 1), (0, -1), (-1, 0), (1, 0)]
        
        for col in range(10):
            for row in range(6):
                sq = row * 10 + col
                for i, (dc, dr) in enumerate(directions):
                    ray = 0
                    nc, nr = col + dc, row + dr
                    while 0 <= nc < 10 and 0 <= nr < 6:
                        ray |= (1 << (nr * 10 + nc))
                        nc += dc
                        nr += dr
                    self.ROOK_RAYS[sq][i] = ray
                    self.ROOK_TABLE[sq] |= ray

    def get_rook_moves(self, sq, occupied, friendly_mask, valid_mask):
        """
        Calculates sliding moves for a Rook at 'sq' considering blockers 
        and the valid board boundary for non-raiders.
        """
        moves = 0
        for i in range(4): # 4 directions
            ray = self.ROOK_RAYS[sq][i]
            blockers = ray & occupied
            if blockers:
                if i in [0, 3]: # up or right
                    first_blocker_sq = (blockers & -blockers).bit_length() - 1
                else: # down or left
                    first_blocker_sq = blockers.bit_length() - 1
                
                line_to_blocker = ray ^ self.ROOK_RAYS[first_blocker_sq][i]
                moves |= line_to_blocker
            else:
                moves |= ray
        
        # APPLY MASKS: remove friendly pieces AND restricted house squares
        return moves & ~friendly_mask & valid_mask
    
    def _precompute_kings(self):
        """Standard 1-square range (Rule 34) neighbors for every square."""
        for col in range(10):
            for row in range(6):
                sq = row * 10 + col
                moves = 0
                for dc in [-1, 0, 1]:
                    for dr in [-1, 0, 1]:
                        if dc == 0 and dr == 0: continue
                        nc, nr = col + dc, row + dr
                        if 0 <= nc < 10 and 0 <= nr < 6:
                            moves |= (1 << (nr * 10 + nc))
                self.KING_TABLE[sq] = moves

    def get_king_moves(self, sq, friendly_mask, valid_mask):
        """Returns legal King moves filtered by the valid territory mask."""
        return self.KING_TABLE[sq] & ~friendly_mask & valid_mask
    
class RampartRaiderGenerator:
    def __init__(self):
        
        # basic 8-way movement for every square
        self.RAIDER_BASE_TABLE = [0] * 60
        self._precompute_base_raiders()
        
        self.WHITE_HOUSES = (1 << 2) | (1 << 3) | (1 << 4)      # squares 2,3,4
        self.BLACK_HOUSES = (1 << 55) | (1 << 56) | (1 << 57)   # squares 55,56,57
        self.ALL_HOUSES = self.WHITE_HOUSES | self.BLACK_HOUSES
        
    def _precompute_base_raiders(self):
        """Precomputes standard 1-square king-style moves."""
        for col in range(10):
            for row in range(6):
                sq = row * 10 + col
                moves = 0
                for dc in [-1, 0, 1]:
                    for dr in [-1, 0, 1]:
                        if dc == 0 and dr == 0: continue
                        nc, nr = col + dc, row + dr
                        if 0 <= nc < 10 and 0 <= nr < 6:
                            moves |= (1 << (nr * 10 + nc))
                self.RAIDER_BASE_TABLE[sq] = moves

    def get_raider_moves(self, sq, color, occupied, enemy_pieces, valid_mask):
        # immobilization check
        if (1 << sq) & self.ALL_HOUSES:
            return 0

        # base_moves are the 8 neighbors filtered by the territory mask
        base_moves = self.RAIDER_BASE_TABLE[sq] & valid_mask
        
        # moves 1 space in ANY direction to empty squares
        legal_steps = base_moves & ~occupied
        
        # captures ONLY in diagonal direction
        diag_mask = self._get_diagonal_neighbors(sq)
        vulnerable_enemies = enemy_pieces & ~self.ALL_HOUSES
        
        legal_captures = (base_moves & diag_mask) & vulnerable_enemies
        
        return legal_captures | legal_steps

    def _get_diagonal_neighbors(self, sq):
        """Helper to isolate diagonal bits from the 8-neighbor mask."""
        col, row = sq % 10, sq // 10
        diag = 0
        for dc, dr in [(-1,-1), (1,1), (-1,1), (1,-1)]:
            nc, nr = col + dc, row + dr
            if 0 <= nc < 10 and 0 <= nr < 6:
                diag |= (1 << (nr * 10 + nc))
        return diag
    
class RampartCastGenerator:
    
    def __init__(self):
        pass
    
    def get_cast_moves(self, bitboard, color):
        
        raw_moves = []
        bb = bitboard
        
        trigger_sq = 4 if color == 'white' else 55
        my_raiders = bb.white_pieces['raider'] if color == 'white' else \
            bb.black_pieces['raider']
            
        if not (my_raiders & (1 << trigger_sq)):
            return []
        
        # set up resources
        deck_mask = bb.white_deck if color == 'white' else bb.black_deck
        graveyard = bb.white_graveyard if color == 'white' else bb.black_graveyard
        
        # identify raiders
        valid_card_mask = bb.CARD_MASK & ~bb.ALL_HOUSES
        caster_raiders = my_raiders & valid_card_mask
        caster_squares = list(bb.get_set_bits(caster_raiders))

        # queen must be dead (in graveyard) AND a raider must have
        # infiltrated the enemy queen house (Rule: "Queen's House: Unlocks
        # spawning your Queen" - this was missing entirely; matches the
        # pygame board's own _enemy_queen_house_occupied check)
        enemy_queen_house_sq = 3 if color == 'white' else 56
        if graveyard['queen'] > 0 and (my_raiders & (1 << enemy_queen_house_sq)):

            # define spawn zones (Rows b,c for white; d,e for black)
            if color == 'white':
                spawn_zone_mask = 0x3FFFFC0000000 
            else:
                spawn_zone_mask = 0x3FFFFC00
                
            valid_spawn_mask = spawn_zone_mask & ~bb.get_occupied()
            spawn_squares = list(bb.get_set_bits(valid_spawn_mask))
            
            # only proceed if there is space to spawn her
            if spawn_squares:
                # pick the first valid square (or reuse scoring logic)
                target_sq = spawn_squares[0] 
                
                # respawn requires combo B (2 board cards + 1 deck card)
                # iterate through pairs of raiders to find board card combos
                n = len(caster_squares)
                for i in range(n):
                    for j in range(i + 1, n):
                        sq1, sq2 = caster_squares[i], caster_squares[j]
                        
                        # find valid deck cards that complete the sum to 21
                        combos = AiCastingArbiter.find_combos_B(sq1, sq2, deck_mask)
                        
                        for c1 in combos:
                            # add the specific "raise_queen" move type
                            raw_moves.append((sq1, target_sq, "raise_queen", [c1]))
        
        # generate raises
        if graveyard['raiders'] > 0:
            # white spawns: row b,c (30 - 49). black spawns: rows d,e (10-29)
            if color == 'white':
                spawn_zone_mask = 0x3FFFFC0000000
            else:
                spawn_zone_mask = 0x3FFFFC00
                
            valid_spawn_mask = spawn_zone_mask & ~bb.get_occupied()
            spawn_squares = list(bb.get_set_bits(valid_spawn_mask))
            
            if spawn_squares:
                
                # 1. setup data
                occupied = bb.get_occupied()
                if color == 'white':
                    enemy_pieces = bb.black_pieces
                    my_pieces = bb.white_pieces
                    
                    row_score_mult = -1
                else:
                    enemy_pieces = bb.white_pieces
                    my_pieces = bb.black_pieces
                    
                    row_score_mult = 1
                    
                # masks for fast lookup
                e_threats_adj = enemy_pieces['raider'] | enemy_pieces['king'] | \
                    enemy_pieces['queen']
                e_knights = enemy_pieces['knight']
                e_orth_sliders = enemy_pieces['rook'] | enemy_pieces['queen']
                e_diag_sliders = enemy_pieces['bishop'] | enemy_pieces['queen']

                my_protectors_adj = my_pieces['raider'] | my_pieces['king'] | \
                    my_pieces['queen']
                my_knights = my_pieces['knight']
                my_orth_sliders = my_pieces['rook'] | my_pieces['queen']
                my_diag_sliders = my_pieces['bishop'] | my_pieces['queen']
                
                best_sq = spawn_squares[0]
                best_score = -float('inf')
                
                # 2. evaluate candidates
                for sq in spawn_squares:
                    current_score = 0
                    col, row = sq % 10, sq // 10
                    
                    # A. strategy bonus
                    current_score += (row * row_score_mult) * 10
                    
                    # B. immediate threats and protection
                    for dc, dr in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                        idx = (row + dr) * 10 + (col + dc)
                        if 0 <= col + dc < 10 and 0 <= row + dr < 6:
                            bit = (1 << idx)
                            if bit & e_threats_adj: current_score -= 1000
                            if bit & my_protectors_adj: current_score += 50
                            
                    # C. ray casting
                    for dc, dr in [(0, 1), (0, -1), (1, 0), (-1, 0),
                                   (1, 1), (1, -1), (-1, 1), (-1, -1)]:
                        is_diag = dc != 0 and dr != 0
                        e_sliders = e_diag_sliders if is_diag else e_orth_sliders
                        my_sliders = my_diag_sliders if is_diag else my_orth_sliders

                        r, c = row + dr, col + dc
                        while 0 <= r < 6 and 0 <= c < 10:
                            idx = r * 10 + c
                            bit = (1 << idx)
                            if bit & occupied:
                                # friend or foe?
                                if bit & e_sliders:
                                    current_score -= 1000   # sniper
                                elif bit & my_sliders:
                                    current_score += 50 # covered
                                break # vision blocked
                            r += dr
                            c += dc
                            
                    # D. pick best one
                    if current_score > best_score:
                        best_score = current_score
                        best_sq = sq
                        
                # 3. generate move for best square
                primary_target = best_sq
                
                # combos A: 1 board card + 2 deck cards
                for sq in caster_squares:
                    combos = AiCastingArbiter.find_combos_A(sq, deck_mask)
                    for (c1, c2) in combos:
                        raw_moves.append((sq, primary_target, "raise", [c1, c2]))
                
                    # combos B: -- raise
                n = len(caster_squares)
                for i in range(n):
                    for j in range(i + 1, n):
                        sq1, sq2 = caster_squares[i], caster_squares[j]
                        # find 1 deck card that sums to 21 with these two board cards
                        combos = AiCastingArbiter.find_combos_B(sq1, sq2, deck_mask)
                        for c1 in combos:
                            raw_moves.append((sq1, primary_target, "raise", [c1]))
                        
        # generate strikes
        # white strikes d,e. black strikes b,c
        if color =='white':
            strike_zone_mask = 0x3FFFFC00
            enemy_raiders = bb.black_pieces['raider']
        else:
            strike_zone_mask = 0x3FFFFC0000000
            enemy_raiders = bb.white_pieces['raider']
            
        valid_targets = list(bb.get_set_bits(enemy_raiders & strike_zone_mask))
        
        if valid_targets:
            
            board_caster_squares = [
                sq for sq in caster_squares 
                if not ((1 << sq) & bb.ALL_HOUSES)
            ]
            
            # strike requires combos B (2 board cards)
            n = len(board_caster_squares)
            for i in range(n):
                for j in range(i + 1, n):
                    sq1, sq2 = board_caster_squares[i], board_caster_squares[j]
                    combos = AiCastingArbiter.find_combos_B(sq1, sq2, deck_mask)
                    for c1 in combos:
                        for target in valid_targets:
                            raw_moves.append((sq1, target, "strike", [c1]))
                            
        return raw_moves
                        
                        
