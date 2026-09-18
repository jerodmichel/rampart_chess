#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  8 10:35:00 2026

@author: stereo
"""


# ░█████╗░██╗  ░█████╗░░█████╗░░██████╗████████╗██╗███╗░░██╗░██████╗░
# ██╔══██╗██║  ██╔══██╗██╔══██╗██╔════╝╚══██╔══╝██║████╗░██║██╔════╝░
# ███████║██║  ██║░░╚═╝███████║╚█████╗░░░░██║░░░██║██╔██╗██║██║░░██╗░
# ██╔══██║██║  ██║░░██╗██╔══██║░╚═══██╗░░░██║░░░██║██║╚████║██║░░╚██╗
# ██║░░██║██║  ╚█████╔╝██║░░██║██████╔╝░░░██║░░░██║██║░╚███║╚██████╔╝
# ╚═╝░░╚═╝╚═╝  ░╚════╝░╚═╝░░╚═╝╚═════╝░░░░╚═╝░░░╚═╝╚═╝░░╚══╝░╚═════╝░

from const import *

class AiCastingArbiter:
    
    @staticmethod
    def get_card_values_at_square(sq_index):
        
        col = sq_index % 10
        row = sq_index // 10
        
        entry = TABLE_DICT.get((col, row))
        
        if not entry or entry == ('', ''):
            return []
        
        rank_idx, suit_idx = entry
        
        # base value from const file: (0->1, 12->10, etc.)
        base_val = CARD_VAL[rank_idx]
        
        # rule for aces at val 1 or 11
        if rank_idx == 0:
            return [1, 11]
        
        return [base_val]
    
    @staticmethod
    def get_deck_card_values(rank_idx):
        
        base_val = CARD_VAL[rank_idx]
        if rank_idx == 0:
            return [1, 11]
        
        return [base_val]
    
    @staticmethod
    def get_available_deck_ranks(deck_mask):
        """
        Returns a list of rank indices (0-12) available in the provided deck bitmask.
        """
        available = []
        for i in range(13):
            # Check if the i-th bit is set
            if deck_mask & (1 << i):
                available.append(i)
        return available
    
    @staticmethod
    def find_combos_A(board_sq_index, deck_mask):
        
        valid_combos = []
        
        # get card value for board square
        board_vals = AiCastingArbiter.get_card_values_at_square(board_sq_index)
        if not board_vals:
            return []
        
        available_ranks = AiCastingArbiter.get_available_deck_ranks(deck_mask)
        n = len(available_ranks)
        
        # iterate all unique pairs of deck cards
        for i in range(n):
            for j in range(i + 1, n):
                r1 = available_ranks[i]
                r2 = available_ranks[j]
                
                vals_1 = AiCastingArbiter.get_deck_card_values(r1)
                vals_2 = AiCastingArbiter.get_deck_card_values(r2)
                
                # check all math permutations
                match_found = False
                for v_b in board_vals:
                    for v1 in vals_1:
                        for v2 in vals_2:
                            if v_b + v1 + v2 == 21:
                                valid_combos.append((r1, r2))
                                match_found = True
                                break
                        if match_found: break
                    if match_found: break
                
        return valid_combos
    
    @staticmethod
    def find_combos_B(sq_index_1, sq_index_2, deck_mask):
        
        valid_combos = []
        
        vals_b1 = AiCastingArbiter.get_card_values_at_square(sq_index_1)
        vals_b2 = AiCastingArbiter.get_card_values_at_square(sq_index_2)
        
        if not vals_b1 or not vals_b2:
            return []
        
        available_ranks = AiCastingArbiter.get_available_deck_ranks(deck_mask)
        
        for r_deck in available_ranks:
            vals_d = AiCastingArbiter.get_deck_card_values(r_deck)
            
            # board1 + board2 + deck = 21
            match_found = False
            for v1 in vals_b1:
                for v2 in vals_b2:
                    for vd in vals_d:
                        if v1 + v2 + vd == 21:
                            valid_combos.append(r_deck)
                            match_found = True
                            break
                    if match_found: break
                if match_found: break
            
        return valid_combos
    
    
    