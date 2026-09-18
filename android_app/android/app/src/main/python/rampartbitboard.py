#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 26 11:48:44 2025

@author: stereo
"""

import numpy as np

from typing import Optional, List, Dict # Optional is required for get_piece_type_at
from const import *


# ██████╗░██╗████████╗██████╗░░█████╗░░█████╗░██████╗░██████╗░
# ██╔══██╗██║╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗
# ██████╦╝██║░░░██║░░░██████╦╝██║░░██║███████║██████╔╝██║░░██║
# ██╔══██╗██║░░░██║░░░██╔══██╗██║░░██║██╔══██║██╔══██╗██║░░██║
# ██████╦╝██║░░░██║░░░██████╦╝╚█████╔╝██║░░██║██║░░██║██████╔╝
# ╚═════╝░╚═╝░░░╚═╝░░░╚═════╝░░╚════╝░╚═╝░░╚═╝╚═╝░░╚═╝╚═════╝░

class RampartBitboard:
    
    def _gen_card_mask_static():
        # deliberately undecorated: called immediately below, while still
        # inside the class body, to compute CARD_SQUARES - a bare name
        # lookup here just calls the plain function, but if this were a
        # @staticmethod, calling it by name in the class body only works
        # on Python 3.10+ (staticmethod objects weren't callable before
        # that), which broke on Python 3.8 with
        # "TypeError: 'staticmethod' object is not callable".
        mask = 0
        for col, row in CARDSQS:
            mask |= (1 << ((row * 10) + col))
        return mask

    # static constants
    CARD_SQUARES = _gen_card_mask_static()
    RAMPART_BARRIER = 0x000000003FFFFC00 # Rows C and D
    WHITE_JACK_HOUSE = 1 << 55 # Square 5f [cite: 55]
    BLACK_JACK_HOUSE = 1 << 4  # Square 4a [cite: 4]
    
    # CARD MASK: all squares that are cards
    CARD_MASK = CARD_SQUARES
    
    # HOUSE BITS: corrected ownership
    # row 0 (2-4) are White's Diamonds; row 5 (55-57) are black's hearts 
    WHITE_HOUSES = (1 << 2) | (1 << 3) | (1 << 4)
    BLACK_HOUSES = (1 << 55) | (1 << 56) | (1 << 57)
    ALL_HOUSES = WHITE_HOUSES | BLACK_HOUSES
    
    # MASTER BOARD MASK: only middle rows + houses are playable
    # self.MIDDLE_ROWS_MASK = 0x0003FFFFFFFFFC00
    MIDDLE_ROWS_MASK = ((1 << 50) - 1) ^ ((1 << 10) - 1)
    
    # MASKS FOR THE BARRIER ROWS
    # row 3 (Index 30-39) - "top" side of the wall
    ROW_3_MASK = 0xFFC0000000
    # Row 2 (Index 20-29) - "bottom" side of the wall
    ROW_2_MASK = 0x003FF00000
    TOTAL_PLAYABLE_BOARD = MIDDLE_ROWS_MASK | ALL_HOUSES
    
    # SPECIFIC KING HOUSES
    BLACK_KING_HOUSE = 1 << 2
    WHITE_KING_HOUSE = 1 << 57
    
    # non-raiders can ONLY occupy the middle 4 rows
    NON_RAIDER_VALID_MASK = MIDDLE_ROWS_MASK
    
    # raiders can occupy the middle rows OR the houses
    RAIDER_VALID_MASK = MIDDLE_ROWS_MASK | ALL_HOUSES
    
    
    
    def __init__(self):
        # 10x6 Board = 60 bits used. 
        # square 0 is 1a, Square 59 is 10f.
        self.white_pieces = {
            'raider': 0, 'knight': 0, 'rook': 0, 'bishop': 0, 'king': 0, 'queen': 0
        }
        self.black_pieces = {
            'raider': 0, 'knight': 0, 'rook': 0, 'bishop': 0, 'king': 0, 'queen': 0
        }
        
        # RESOURCE STATE (anticipating casting)
        self.white_deck = 0b1111111111111 # 13 bits (A-K)
        self.black_deck = 0b1111111111111
        self.white_graveyard = {'raiders': 5, 'queen': 1}
        self.black_graveyard = {'raiders': 5, 'queen': 1}

        # NOTE: CARD_SQUARES/CARD_MASK are already precomputed once as class
        # attributes (see _gen_card_mask_static() above) - re-deriving a
        # per-instance copy here was pure waste, since nothing ever read it
        # and RampartBitboard() gets constructed on every single .copy(),
        # which happens on every candidate move during search.

    def get_occupied(self):
        white = 0
        for b in self.white_pieces.values(): white |= b
        black = 0
        for b in self.black_pieces.values(): black |= b
        return white | black

    # PRECOMPUTE MOVE GENERATION (for speed)
    # knight_moves[sq] = bitboard of 8 possible L-shapes
    KNIGHT_MOVES = [] 
    ROOK_MOVES = []
    
    def sync_from_board(self, board):
            """
            Clears current bitboards and populates them based on the 
            current state of the Pygame Board object.
            """
            # reset all piece bitboards to 0
            for piece_type in self.white_pieces:
                self.white_pieces[piece_type] = 0
                self.black_pieces[piece_type] = 0
    
            for col in range(10): # COLS
                for row in range(6): # ROWS
                    sq = board.squares[col][row]
                    if sq.has_piece():
                        piece = sq.piece
                        # bit Index = (Row * 10) + column
                        bit_idx = (row * 10) + col
                        
                        if piece.color == 'white':
                            # use piece.name which matches dictionary keys ('raider', 'rook', etc.)
                            # note: if piece name is 'raider', ensure bitboard key is 'raider' (not 'raiders')
                            self.white_pieces[piece.name] |= (1 << bit_idx)
                        else:
                            self.black_pieces[piece.name] |= (1 << bit_idx)
                            
            # 2. scan both decks
            self.white_deck = 0
            self.black_deck = 0
            
            # black deck (suit 0)
            for rank in range(13):
                card = board.cards[0][rank]
                if not card.is_cast():
                    self.black_deck |= (1 << rank)
                    
            # white deck (suit 1)
            for rank in range(13):
                card = board.cards[1][rank]
                if not card.is_cast():
                    self.white_deck |= (1 << rank)
                    
            # even if cards exist, AI must consider deck "locked" (0)
            # unless a raider currently occupies jack's house.
            # This forces the AI to move a Raider there to "Unlock" the value.
            
            # check white (needs raider at 55 or 4)
            white_unlocked = (self.white_pieces['raider'] & self.WHITE_JACK_HOUSE) or \
                             (self.white_pieces['raider'] & self.BLACK_JACK_HOUSE)
            if not white_unlocked:
                self.white_deck = 0  # force lock if no raider in house
                
            # check black (needs raider at 55 or 4)
            black_unlocked = (self.black_pieces['raider'] & self.WHITE_JACK_HOUSE) or \
                             (self.black_pieces['raider'] & self.BLACK_JACK_HOUSE)
            if not black_unlocked:
                self.black_deck = 0  # force lock if no raider in house
                    
            # 3. sync graveyards
            w_raiders = 0
            w_queens = 0
            b_raiders = 0
            b_queens = 0
            
            # white graves
            for row in range(9):
                grave = board.graves[1][row]
                if grave.has_piece():
                    if grave.piece.name == 'raider': w_raiders += 1
                    elif grave.piece.name == 'queen': w_queens += 1
                
            # black graves
            for row in range(9):
                grave = board.graves[0][row]
                if grave.has_piece():
                    if grave.piece.name == 'raider': b_raiders += 1
                    elif grave.piece.name == 'queen': b_queens += 1
                
            self.white_graveyard = {'raiders': w_raiders, 'queen': w_queens}
            self.black_graveyard = {'raiders': b_raiders, 'queen': b_queens}
            
                            
    def _get_house_eligibility_mask(self, player):
        """Helper for Raider house rules logic."""
        if player == 'white':
            jack_idx, queen_idx, king_idx = 2, 3, 4 
        else:
            jack_idx, queen_idx, king_idx = 55, 56, 57 
    
        eligible_mask = (1 << jack_idx)
        friendly_pieces = self.get_friendly_mask(player)
        
        if (1 << jack_idx) & friendly_pieces:
            eligible_mask |= (1 << queen_idx)
        if (1 << queen_idx) & friendly_pieces:
            eligible_mask |= (1 << king_idx)
            
        return eligible_mask
                            
    def get_raider_valid_mask(self, sq, color):
        row = sq // 10
        mask = self.TOTAL_PLAYABLE_BOARD
        
        if color == 'black':
            mask &= ~self.WHITE_HOUSES
        else:
            mask &= ~self.BLACK_HOUSES
        
        if color == 'white':
            # white starts at top (row 3). moves DOWN to bottom (row 2).
            # RULE: if we have crossed to bottom (row <= 2), we cannot go back to row 3.
            if row <= 2:
                mask &= ~self.ROW_3_MASK
            # (if we are at row 3, we do NOT apply the mask. we are free to enter row 2.)
                
        else: # black
            # black starts at bottom (row 2). moves UP to top (row 3).
            # RULE: if we have crossed to top (row >= 3), we cannot go back to row 2.
            if row >= 3:
                mask &= ~self.ROW_2_MASK
            # (if we are at row 2, we do NOT apply the mask. we are free to enter row 3.)
                
        return mask
    
    def get_king_valid_mask(self, color, occupied_bitboard):
        """
        Implements Rule 71: If your own King house is occupied,
        you are restricted to CARD squares only.
        """
        # determine if your own King House has an enemy raider
        own_house = self.WHITE_KING_HOUSE if color == 'white' else self.BLACK_KING_HOUSE
        
        if occupied_bitboard & own_house:
            # restricted to card squares within the playable middle rows
            return self.MIDDLE_ROWS_MASK & self.CARD_MASK
        
        # otherwise, standard non-raider territory (no houses)
        return self.NON_RAIDER_VALID_MASK
    
    def get_friendly_mask(self, color):
        pieces = self.white_pieces if color == 'white' else self.black_pieces
        result = 0
        for bitboard in pieces.values():
            result |= bitboard
        return result
    
    def get_enemy_mask(self, color):
        enemy_pieces = self.black_pieces if color == 'white' else self.white_pieces
        result = 0
        for bitboard in enemy_pieces.values():
            result |= bitboard
        return result
    
    def get_raider_capture_mask(self, from_sq, color):
        """
        Returns a bitmask of the 4 diagonal squares a raider can capture/defend.
        """
        mask = 0
        col = from_sq % 10
        row = from_sq // 10
        
        # diagonal offsets for capture 
        diagonals = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
        
        for dc, dr in diagonals:
            new_col, new_row = col + dc, row + dr
            # ensure the square is within the 10x6 board
            if 0 <= new_col < 10 and 0 <= new_row < 6:
                target_idx = new_row * 10 + new_col
                mask |= (1 << target_idx)
                
        return mask
    
    def copy(self):
        """Creates a deep copy of the bitboard state."""
        new_board = RampartBitboard()
        
        # copy Piece Maps (Dictionaries need explicit copying)
        new_board.white_pieces = self.white_pieces.copy()
        new_board.black_pieces = self.black_pieces.copy()
        
        # copy Graveyards
        new_board.white_graveyard = self.white_graveyard.copy()
        new_board.black_graveyard = self.black_graveyard.copy()
        
        # --- copy Resources ---
        new_board.white_deck = self.white_deck
        new_board.black_deck = self.black_deck
        # ------------------------------------
        
        return new_board

    def apply_move(self, from_sq, to_sq, piece_type, color):
        """Updates bitboards using XOR. Instant compared to object moves."""
        move_mask = (1 << from_sq) | (1 << to_sq)
        
        if color == 'white':
            self.white_pieces[piece_type] ^= move_mask
            # capture logic: clear target bit from all black piece bitboards
            target_mask = ~(1 << to_sq)
            for p in self.black_pieces:
                self.black_pieces[p] &= target_mask
        else:
            self.black_pieces[piece_type] ^= move_mask
            target_mask = ~(1 << to_sq)
            for p in self.white_pieces:
                self.white_pieces[p] &= target_mask
                
    def get_set_bits(self, bitboard):
        """Yields the bit index of every '1' in the integer."""
        # note: yield doesn't return and exit, it pauses the function and gives
        # one value. When you loop again (over .get_set_bits() from outside) 
        # it resumes where it left off
        while bitboard:
            # isolates the lowest set bit
            bit = bitboard & -bitboard
            # finds the index of that bit
            yield bit.bit_length() - 1
            # removes that bit to find the next
            bitboard ^= bit
            
    def get_piece_type_at(self, sq: int) -> Optional[str]:
        """Returns the piece type at a given bit index, or None if empty."""
        mask = (1 << sq)
        
        # check all white piece bitboards
        for p_type, p_mask in self.white_pieces.items():
            if p_mask & mask:
                return p_type
                
        # check all black piece bitboards
        for p_type, p_mask in self.black_pieces.items():
            if p_mask & mask:
                return p_type
                
        return None
    
    def get_king_pos(self, color: str) -> int:
        """Returns the bit index of the king for the given color."""
        mask = self.white_pieces['king'] if color == 'white' else self.black_pieces['king']
        if mask == 0: return -1 # Should not happen in a valid state
        # find index of the set bit (0-59)
        return (mask).bit_length() - 1
    
    def is_card_square(self, sq: int) -> bool:
        """Returns True if the bit index corresponds to a card square[cite: 14]."""
        # we can pre-calculate this mask based on CARDSQS in const.py
        col, row = sq % 10, sq // 10
        # card squares are the Jack/Queen/King houses and the middle board cards
        return (col, row) in CARDSQS # requires 'from const import CARDSQS'
    
    
    def get_state_hash(self):
        return hash((
            # pieces
            tuple(self.white_pieces.values()),
            tuple(self.black_pieces.values()),
            # resources
            self.white_deck, self.black_deck,
            self.white_graveyard['raiders'], self.white_graveyard['queen'],
            self.black_graveyard['raiders'], self.black_graveyard['queen']
            ))
        