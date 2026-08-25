#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  2 00:49:23 2026

@author: stereo
"""

# ░█████╗░██╗  ███████╗███╗░░██╗░██████╗░██╗███╗░░██╗███████╗
# ██╔══██╗██║  ██╔════╝████╗░██║██╔════╝░██║████╗░██║██╔════╝
# ███████║██║  █████╗░░██╔██╗██║██║░░██╗░██║██╔██╗██║█████╗░░
# ██╔══██║██║  ██╔══╝░░██║╚████║██║░░╚██╗██║██║╚████║██╔══╝░░
# ██║░░██║██║  ███████╗██║░╚███║╚██████╔╝██║██║░╚███║███████╗
# ╚═╝░░╚═╝╚═╝  ╚══════╝╚═╝░░╚══╝░╚═════╝░╚═╝╚═╝░░╚══╝╚══════╝

import time
import math
from rampartbitboard import RampartBitboard
from rampartmovegenerator import RampartMoveGenerator, RampartRaiderGenerator, \
    RampartCastGenerator

# --- GLOBAL LOG BUFFER ---
LOG_BUFFER = []

def debug_log(message, mode="ai"):
    """Logging to memory."""
    timestamp = time.strftime('%H:%M:%S')
    LOG_BUFFER.append(f"[{timestamp}] [{mode}] {message}")

def flush_debug_log():
    """Writes all buffered logs to disk."""
    if not LOG_BUFFER: return
    try:
        with open('ai_debug.txt', 'a', encoding='utf-8') as f:
            f.write('\n'.join(LOG_BUFFER) + '\n')
        LOG_BUFFER.clear()
    except Exception as e:
        print(f"LOG FLUSH FAILED: {e}")
        

# █░█ █▀▀ █░█ █▀█ █ █▀ ▀█▀ █ █▀▀ █▀
# █▀█ ██▄ █▄█ █▀▄ █ ▄█ ░█░ █ █▄▄ ▄█

# --- 1. CONSTANTS & CONFIGURATION ---
INFINITY = 10000000
CHECKMATE_SCORE = 1000000
TIME_LIMIT = INFINITY  # seconds per move

# heuristic values
PIECE_VALUES = {
    'raider': 100,
    'knight': 320,
    'bishop': 330,
    'rook': 500,
    'queen': 900,
    'king': 20000
}


# ╔══╦═╗╔══╦╦═╗╔══╗
# ║║═╣╔╗╣╔╗╠╣╔╗╣║═╣
# ║║═╣║║║╚╝║║║║║║═╣
# ╚══╩╝╚╩═╗╠╩╝╚╩══╝
# ──────╔═╝║
# ──────╚══╝

# --- 2. THE MOVE OBJECT ---
class EngineMove:
    """
    Represents a move in the bitboard engine.
    (Formerly AI_Move)
    """
    def __init__(self, from_sq, to_sq, piece_type, color, move_type="normal", \
                 deck_cards=None, spawn_sq=None):
        self.from_sq = from_sq   # integer 0-59
        self.to_sq = to_sq       # integer 0-59
        self.piece_type = piece_type
        self.color = color
        self.move_type = move_type
        self.deck_cards = deck_cards if deck_cards else []
        self.spawn_sq = spawn_sq
    
    def __repr__(self):
        if self.move_type == "normal":
            f_col, f_row = self.from_sq % 10, self.from_sq // 10
            t_col, t_row = self.to_sq % 10, self.to_sq // 10
            return f"Move({f_col},{f_row} -> {t_col},{t_row} | {self.piece_type})"
        elif self.move_type == "enter_queen_house":
            return f"QueenUnlock({self.from_sq}->{self.to_sq}, Spawn@{self.spawn_sq})"
        else:
            return f"Cast({self.move_type} | Cards:{self.deck_cards})"

    
# ╱╱╱╭╮╱╭╮╱╱╱╱╱╱╭╮
# ╱╱╭╯╰┳╯╰╮╱╱╱╱╱┃┃
# ╭━┻╮╭┻╮╭╋━━┳━━┫┃╭╮
# ┃╭╮┃┃╱┃┃┃╭╮┃╭━┫╰╯╯
# ┃╭╮┃╰╮┃╰┫╭╮┃╰━┫╭╮╮
# ╰╯╰┻━╯╰━┻╯╰┻━━┻╯╰╯
    
class RampartAttackGenerator:
    def __init__(self):
        self.gen = RampartMoveGenerator()
        self.raider_gen = RampartRaiderGenerator()
        
    def get_attack_map(self, bitboard, attacker_color):
        # return bitboard of all squares under attack by given color
        attacks = 0
        bb = bitboard
        
        # get team pieces
        if attacker_color == 'white':
            pieces = bb.white_pieces
            friendly_mask = bb.get_friendly_mask('white')
        else:
            pieces = bb.black_pieces  
            friendly_mask = bb.get_friendly_mask('black')

        occupied = bb.get_occupied()
        
        # generate attacks for each piece type
        for p_type, bitboard_map in pieces.items():
            for from_sq in bb.get_set_bits(bitboard_map):
                if p_type == 'knight':
                    attacks |= self.gen.get_knight_moves(from_sq, friendly_mask, bb.NON_RAIDER_VALID_MASK)
                elif p_type == 'rook':
                    attacks |= self.gen.get_rook_moves(from_sq, occupied, friendly_mask, bb.NON_RAIDER_VALID_MASK)
                elif p_type == 'bishop':
                    attacks |= self.gen.get_bishop_moves(from_sq, occupied, friendly_mask, bb.NON_RAIDER_VALID_MASK)
                elif p_type == 'queen':
                    attacks |= self.gen.get_queen_moves(from_sq, occupied, friendly_mask, bb.NON_RAIDER_VALID_MASK)
                elif p_type == 'king':
                    v_mask = bb.get_king_valid_mask(attacker_color, occupied)
                    attacks |= self.gen.get_king_moves(from_sq, friendly_mask, v_mask & bb.TOTAL_PLAYABLE_BOARD)
                elif p_type == 'raider':
                    v_mask = bb.get_raider_valid_mask(from_sq, attacker_color)
                    house_eligibility = bb._get_house_eligibility_mask(attacker_color)
                    
                    all_houses_mask = (1 << 2) | (1 << 3) | (1 << 4) | (1 << 55) | (1 << 56) | (1 << 57)
                    v_mask &= ~all_houses_mask
                    v_mask |= house_eligibility
                    enemy_mask = occupied ^ friendly_mask
                    attacks |= self.raider_gen.get_raider_moves(from_sq, attacker_color, occupied, enemy_mask, v_mask)
        
        return attacks
    
    def is_king_in_check(self, bitboard, king_color):
        # fast check detection for king of given color
        
        # find king's square
        king_bitboard = bitboard.white_pieces['king'] if king_color == 'white' else bitboard.black_pieces['king']
        
        if king_bitboard == 0:
            return False # no king? should not happen
        
        king_sq = king_bitboard.bit_length() - 1
        
        # get squares attacked by enemy
        enemy_color = 'black' if king_color == 'white' else 'white'
        enemy_attacks = self.get_attack_map(bitboard, enemy_color)
        
        # king is in check if enemy attacks its square
        return (enemy_attacks & (1 << king_sq)) != 0
    
    def ai_self_in_check(self, bitboard, move, player_color):
        # fast check for whether a move puts own king in check
        
        # create temp bitboard
        temp_bb = bitboard.copy()
        
        # apply the move
        from_mask = (1 << move.from_sq)
        to_mask = (1 << move.to_sq)
        move_mask = from_mask | to_mask
        
        if player_color == 'white':
            temp_bb.white_pieces[move.piece_type] ^= move_mask
            # handle capture
            target_mask = ~to_mask
            for p in temp_bb.black_pieces:
                temp_bb.black_pieces[p] &= target_mask
        else:
            temp_bb.black_pieces[move.piece_type] ^= move_mask
            target_mask = ~to_mask
            for p in temp_bb.white_pieces:
                temp_bb.white_pieces[p] &= target_mask
                
        # check if this move leaves king in check
        return not self.is_king_in_check(temp_bb, player_color)


# ┏┓╋╋┏┓┏┓╋╋╋╋╋╋╋╋╋╋╋┏┓╋╋╋┏┓╋╋╋┏┓
# ┃┃╋┏┛┗┫┃╋╋╋╋╋╋╋╋╋╋╋┃┃╋╋┏┛┗┓╋┏┛┗┓
# ┃┗━╋┓┏┫┗━┳━━┳━━┳━┳━┛┃┏━┻┓┏╋━┻┓┏╋━━┓
# ┃┏┓┣┫┃┃┏┓┃┏┓┃┏┓┃┏┫┏┓┃┃━━┫┃┃┏┓┃┃┃┃━┫
# ┃┗┛┃┃┗┫┗┛┃┗┛┃┏┓┃┃┃┗┛┃┣━━┃┗┫┏┓┃┗┫┃━┫
# ┗━━┻┻━┻━━┻━━┻┛┗┻┛┗━━┛┗━━┻━┻┛┗┻━┻━━┛

# --- 3. THE STATE WRAPPER ---
class BitboardGameState:
    """
    Manages game state using bitboards.
    Handles move generation, application, and basic rules.
    """
    # static generators to avoid re-initializing every frame
    gen = RampartMoveGenerator()
    raider_gen = RampartRaiderGenerator()
    attack_gen = RampartAttackGenerator()
    cast_gen = RampartCastGenerator()
    
    def __init__(self, bitboard, current_player: str):
        self.bitboard = bitboard
        self.current_player = current_player
        
    def get_legal_moves(self):
        """
        Generates all legal moves for current player using bitboards.
        """
        moves = []
        bb = self.bitboard
        
        occupied = bb.get_occupied()
        pieces = bb.white_pieces if self.current_player == 'white' else bb.black_pieces
        friendly_mask = sum(pieces.values())
        enemy_mask = occupied ^ friendly_mask
        
        # define targets for queen house
        enemy_queen_house = 3 if self.current_player == 'white' else 56
        
        # iterate through each piece type
        for p_type, bitboard_map in pieces.items():
            for from_sq in bb.get_set_bits(bitboard_map):
                targets = 0
                
                if p_type == 'knight':
                    targets = self.gen.get_knight_moves(from_sq, friendly_mask, bb.NON_RAIDER_VALID_MASK)
                elif p_type == 'rook':
                    targets = self.gen.get_rook_moves(from_sq, occupied, friendly_mask, bb.NON_RAIDER_VALID_MASK)
                elif p_type == 'bishop':
                    targets = self.gen.get_bishop_moves(from_sq, occupied, friendly_mask, bb.NON_RAIDER_VALID_MASK)
                elif p_type == 'queen':
                    targets = self.gen.get_queen_moves(from_sq, occupied, friendly_mask, bb.NON_RAIDER_VALID_MASK)
                elif p_type == 'king':
                    # rule: King restricted to card squares if own house occupied
                    v_mask = bb.get_king_valid_mask(self.current_player, occupied)
                    targets = self.gen.get_king_moves(from_sq, friendly_mask, v_mask & bb.TOTAL_PLAYABLE_BOARD)
                elif p_type == 'raider':
                    # raider Logic (complex masks for houses/walls)
                    v_mask = bb.get_raider_valid_mask(from_sq, self.current_player)
                    house_eligibility = bb._get_house_eligibility_mask(self.current_player)
                    
                    # strip houses from mask, then add back eligible ones
                    all_houses_mask = (1 << 2) | (1 << 3) | (1 << 4) | (1 << 55) | (1 << 56) | (1 << 57)
                    v_mask &= ~all_houses_mask
                    v_mask |= house_eligibility
                    
                    targets = self.raider_gen.get_raider_moves(from_sq, self.current_player, occupied, enemy_mask, v_mask)
                    
                # process targets
                for to_sq in bb.get_set_bits(targets):
                    
                    if p_type == 'raider' and to_sq == enemy_queen_house:
                        # entering queen house
                        
                        # 1. define valid spawn territory
                        if self.current_player == 'white':
                            spawn_mask = 0x3FFFFC0000000
                        else:
                            spawn_mask = 0x3FFFFC00
                            
                        # 2. find empty square
                        
                        valid_spawns = list(bb.get_set_bits(spawn_mask & ~occupied))
                        
                        if valid_spawns:
                            # branch for valid spawn
                            for spawn_sq in valid_spawns:
                                mv = EngineMove(from_sq, to_sq, 'raider', \
                                    self.current_player, \
                                    move_type="enter_queen_house", spawn_sq=spawn_sq)
                                
                                # check if this spawn variation is safe
                                moves.append(mv)
                                
                        else:
                            # rare case: no space to spawn queen
                            mv = EngineMove(from_sq, to_sq, 'raider', self.current_player)
                            moves.append(mv)
                            
                    else:
                        # standard move
                        mv = EngineMove(from_sq, to_sq, p_type, self.current_player)
                        
                        # 1. calculate Safety ONCE
                        is_safe = self.attack_gen.ai_self_in_check(self.bitboard, mv, self.current_player)
                        
                        # 2. Probe (Now Safe to use!)
                        # if p_type == 'raider' and (to_sq == 55 or to_sq == 4):
                        #      debug_log(f"Raider Probe {from_sq}->{to_sq}: Safe={is_safe}")

                        # 3. add to list if safe
                        if is_safe:
                            moves.append(mv)
                        
        # cast moves
        raw_casts = self.cast_gen.get_cast_moves(self.bitboard, self.current_player)
        
        # wrap in engine objects
        for (src, tgt, m_type, cards) in raw_casts:
            mv = EngineMove(src, tgt, 'raider', self.current_player, m_type, cards)
            if self.attack_gen.ai_self_in_check(self.bitboard, mv, self.current_player):
                moves.append(mv)
            
        return moves

    def apply_move(self, move: EngineMove):
        """
        Returns NEW BitboardGameState with move applied.
        Does NOT modify the current instance.
        """
        from square import Square
        
        new_bb = self.bitboard.copy()
        notation = ""
        
        # handle cast moves
        if move.move_type in ["raise", "strike"]:
            # 1. update deck and graveyard counts
            deck_mask = new_bb.white_deck if move.color == 'white' else \
                new_bb.black_deck
            
            # remove cards used
            for card_idx in move.deck_cards:
                deck_mask &= ~(1 << card_idx)
                
            # commit changes back to state
            if move.color == 'white':
                new_bb.white_deck = deck_mask
                if move.move_type == 'raise':
                    new_bb.white_graveyard['raiders'] -= 1
                elif move.move_type == 'raise_queen':
                    new_bb.white_graveyard['queen'] -= 1
            else:
                new_bb.black_deck = deck_mask
                if move.move_type == 'raise':
                    new_bb.black_graveyard['raiders'] -= 1
                elif move.move_type == 'raise_queen': 
                    new_bb.black_graveyard['queen'] -= 1
                    
            # 2. execute spawn or capture
            if move.move_type == "raise":
                target_map = new_bb.white_pieces if move.color == 'white' else \
                    new_bb.black_pieces
                target_map['raider'] |= (1 << move.to_sq)
            elif move.move_type == "raise_queen":
                target_map = new_bb.white_pieces if move.color == 'white' else \
                    new_bb.black_pieces
                target_map['queen'] |= (1 << move.to_sq)
                    
            elif move.move_type == "strike":
                # capture the raider at to_sq
                target_mask = ~(1 << move.to_sq)
                if move.color == 'white':
                    new_bb.black_pieces['raider'] &= target_mask
                else:
                    new_bb.white_pieces['raider'] &= target_mask
                    
        else:
            # standard move
            # Apply XOR move logic
            from_mask = (1 << move.from_sq)
            to_mask = (1 << move.to_sq)
            move_mask = from_mask | to_mask
            
            pieces = new_bb.white_pieces if move.color =='white' else \
                new_bb.black_pieces
            pieces[move.piece_type] ^= move_mask
            
            enemy_pieces = new_bb.black_pieces if move.color == 'white' else \
                new_bb.white_pieces
            enemy_graveyard = new_bb.black_graveyard if move.color == 'white' else \
                new_bb.white_graveyard
            
            # capture
            target_mask = ~to_mask
            for p_name, p_bb in enemy_pieces.items():
                if p_bb & to_mask:
                    # capture detected
                    enemy_pieces[p_name] &= target_mask
                    
                    # add to graveyard if raider or queen
                    if p_name == 'raider':
                        enemy_graveyard['raiders'] += 1
                    elif p_name == 'queen':
                        enemy_graveyard['queen'] += 1
                        
                    break
                
            # 2. handle queen spawn
            if move.move_type == "enter_queen_house" and move.spawn_sq is not None:
                
                # standard move part
                f_col, f_row = move.from_sq % 10, move.from_sq // 10
                t_col, t_row = move.to_sq % 10, move.to_sq // 10
                src = f"{f_col + 1}{Square.get_alpharow(5 - f_row)}"
                dst = f"{t_col + 1}{Square.get_alpharow(5 - t_row)}"
                
                # spawn part
                s_col, s_row = move.spawn_sq % 10, move.spawn_sq // 10
                s_dst = f"{s_col + 1}{Square.get_alpharow(5 - s_row)}"
                
                notation = f"{move.piece_type[0].upper()}{src}>{dst}/Q@{s_dst}"
                
                # this tells where to place queen
                if move.color == 'white':
                    new_bb.white_pieces['queen'] |= (1 << move.spawn_sq)
                    new_bb.white_graveyard['queen'] -= 1
                else:
                    new_bb.black_pieces['queen'] |= (1 << move.spawn_sq)
                    new_bb.black_graveyard['queen'] -= 1
                    
            # if a Raider enters the Jack House (Square 4 or 55), the deck refills.
            # must simulate this so AI sees "reward" (Full Deck) in future state.
            if move.piece_type == 'raider' and (move.to_sq == 55 or move.to_sq == 4):
                # 0xFFFFF represents 20 cards (bits 0-19 set). 
                # ensures evaluate_board sees (>0) and awards massive bonus.
                full_deck_simulation = 0xFFFFF 
                
                if move.color == 'white':
                    new_bb.white_deck = full_deck_simulation
                else:
                    new_bb.black_deck = full_deck_simulation
                    
        # generate notaton for AI steps
        if move.move_type in ["raise", "strike", "raise_queen"]:
            action = "++" if "raise" in move.move_type else "__"
            p_char = move.piece_type[0].upper()
            t_col, t_row = move.to_sq % 10, move.to_sq // 10
            dst = f"{t_col + 1}{Square.get_alpharow(5 - t_row)}"
            # convert deck card indices back to RN format if desired
            notation = f"{action}{p_char}@{dst}({move.deck_cards})"
        else:
            # standard AI move notation
            f_col, f_row = move.from_sq % 10, move.from_sq // 10
            t_col, t_row = move.to_sq % 10, move.to_sq // 10
            src = f"{f_col + 1}{Square.get_alpharow(5 - f_row)}"
            dst = f"{t_col + 1}{Square.get_alpharow(5 - t_row)}"
            
            if move.move_type == "enter_queen_house" and move.spawn_sq is not None:
                s_col, s_row = move.spawn_sq % 10, move.spawn_sq // 10
                s_dst = f"{s_col + 1}{Square.get_alpharow(5 - s_row)}"
                notation = f"{move.piece_type[0].upper()}{src}>{dst}/Q@{s_dst}"
            else:
                notaton = f"{move.piece_type[0].upper()}{src}>{dst}"
                    
        next_player = 'black' if self.current_player == 'white' else 'white'
        return BitboardGameState(new_bb, next_player), notation

    def is_terminal(self):
        """Game over if a king is missing."""
        if self.bitboard.white_pieces['king'] == 0: return True
        if self.bitboard.black_pieces['king'] == 0: return True
        return False
                
# ╱╱╱╱╱╱╱╱╱╭╮╱╱╱╱╱╱╭╮╱╱╱╱╭╮╱╱╱╱╱╱╱╱╱╱╱╭╮
# ╱╱╱╱╱╱╱╱╱┃┃╱╱╱╱╱╭╯╰╮╱╱╱┃┃╱╱╱╱╱╱╱╱╱╱╱┃┃
# ╭━━┳╮╭┳━━┫┃╭╮╭┳━┻╮╭╋━━╮┃╰━┳━━┳━━┳━┳━╯┃
# ┃┃━┫╰╯┃╭╮┃┃┃┃┃┃╭╮┃┃┃┃━┫┃╭╮┃╭╮┃╭╮┃╭┫╭╮┃
# ┃┃━╋╮╭┫╭╮┃╰┫╰╯┃╭╮┃╰┫┃━┫┃╰╯┃╰╯┃╭╮┃┃┃╰╯┃
# ╰━━╯╰╯╰╯╰┻━┻━━┻╯╰┻━┻━━╯╰━━┻━━┻╯╰┻╯╰━━╯

# --- 4. THE EVALUATION FUNCTION ---
def evaluate_board(state):
    """
    Returns score from WHITE's perspective.
    Positive = White winning, Negative = Black winning.
    """
    bb = state.bitboard
    attack_gen = state.attack_gen
    
    # 1. King Safety (immediate terminal check)
    if bb.white_pieces['king'] == 0: return -CHECKMATE_SCORE
    if bb.black_pieces['king'] == 0: return CHECKMATE_SCORE

    score = 0
    
    # 2. material counting
    for p_type, val in PIECE_VALUES.items():
        w_count = bb.white_pieces[p_type].bit_count()
        b_count = bb.black_pieces[p_type].bit_count()
        score += (w_count - b_count) * val
        
    # 3. threat detection: genenate attack maps
    white_attacks = attack_gen.get_attack_map(bb, 'white')
    black_attacks = attack_gen.get_attack_map(bb, 'black')
    
    # detects whether opponent is pinned/helpless on the field.
    w_board_raiders = bb.white_pieces['raider'] & ~bb.ALL_HOUSES
    b_board_raiders = bb.black_pieces['raider'] & ~bb.ALL_HOUSES
    
    b_hunting = (w_board_raiders == 0) or (bb.white_deck < 2) or \
       (bb.black_pieces['raider'] & (1 << 56))
       
    w_hunting = (b_board_raiders == 0) or (bb.black_deck < 2) or \
       (bb.white_pieces['raider'] & (1 << 3))
    
    # penalize white pieces occupying squares attacked by black
    for p_type, bitboard_map in bb.white_pieces.items():
        
        # king handles threats via checkmate detection.
        # we penalize the king here, the AI panics.
        if p_type == 'king':
            if bitboard_map & black_attacks:
                score -= 50
            continue
        
        # bitwise AND to find pieces under attack
        threatened_pieces = bitboard_map & black_attacks
        if threatened_pieces:
            count = threatened_pieces.bit_count()
            if not b_hunting:
                if bb.white_deck == 0:
                    # penalty is 60 % of piece value
                    mult = 1.1 if p_type == 'raider' else 0.75
                    
                else:
                    mult = 1.5 if p_type == 'raider' else 0.9
            else:
                mult = 1.05 if p_type == 'raider' else 0.55
                
            score -= count * (PIECE_VALUES[p_type] * mult)
            
    # penalize black pieces occupying squares attacked by white
    for p_type, bitboard_map in bb.black_pieces.items():
        
        # king handles threats via checkmate detection.
        # we penalize the king here, the AI panics.
        if p_type == 'king':
            if bitboard_map & white_attacks:
                score += 50
            continue
        
        threatened_pieces = bitboard_map & white_attacks
        if threatened_pieces:
            count = threatened_pieces.bit_count()
            if not w_hunting:
                if bb.black_deck == 0:
                    # penalty is 60 % of piece value
                    mult = 1.1 if p_type == 'raider' else 0.75
                    
                    
                else:
                    mult = 1.5 if p_type == 'raider' else 0.9
            else:
                mult = 1.05 if p_type == 'raider' else 0.55
                
            score += count * (PIECE_VALUES[p_type] * mult)
            
    # 4. positional bonus
    # black raiders: when in row 5, aim for columns 5-7
    black_raiders = bb.black_pieces['raider']
    
    target_col, target_row = 5, 5
    
    if black_raiders & (1 << 55):
        target_col, target_row = 6, 5
    elif black_raiders & (1 << 56):
        target_col, target_row = 7, 5
    else:
        pass
    
    for sq in bb.get_set_bits(bb.black_pieces['raider']):
        row = sq // 10
        col = sq % 10
        
        if sq in [55, 56, 57]:
            score -= 2000
            continue
        
        distance = abs(col - target_col) + abs(row - target_row)
        if not b_hunting:
            if bb.black_deck == 0:
                house_bonus = 275 - (distance * 27.5)
            else:
                house_bonus = 250 - (distance * 25)
        else:
            if bb.black_pieces['raider'] & (1 << 57):
                house_bonus = 0
            else:
                house_bonus = 240 - (distance * 24)
        
        score -= house_bonus
        
    # white raiders: When in row 0, aim for columns 2-4
    for sq in bb.get_set_bits(bb.white_pieces['raider']):
        row = sq // 10
        col = sq % 10
        
        min_distance = float('inf')
        for (h_col, h_row) in [(4, 0), (3, 0), (2, 0)]:
            distance = abs(col - h_col) + abs(row - h_row)
            min_distance = min(min_distance, distance)
        
        if not w_hunting:
            if bb.white_deck == 0:
                house_bonus = 275 - (min_distance * 27.5)
            else:
                house_bonus = 250 - (min_distance * 25)
        else:
            if bb.white_pieces['raider'] & (1 << 2):
                house_bonus = 0
            else:
                house_bonus = 240 - (min_distance * 24)
        
        score += house_bonus
        
        if min_distance == 0:
            score += 2000
            
    # if w_hunting:
    #     b_king_sq = bb.get_king_pos('black')
    #     if b_king_sq != -1:
    #         bk_r, bk_c = b_king_sq // 10, b_king_sq % 10
    #         # check all white raiders
    #         for sq in bb.get_set_bits(bb.white_pieces['raider']):
    #             r, c = sq // 10, sq % 10
    #             dist = abs(r - bk_r) + abs(c - bk_c)
    #             # ADD score for White getting closer
    #             score += (15 - dist) * 30 

    # if b_hunting:
    #     w_king_sq = bb.get_king_pos('white')
    #     if w_king_sq != -1:
    #         wk_r, wk_c = w_king_sq // 10, w_king_sq % 10
    #         # check all black raiders
    #         for sq in bb.get_set_bits(bb.black_pieces['raider']):
    #             r, c = sq // 10, sq % 10
    #             dist = abs(r - wk_r) + abs(c - wk_c)
    #             # SUBTRACT score for Black getting closer
    #             score -= (15 - dist) * 30
            
    # lone raider check: do not award deck bonus if we can't cast (need 2 raiders)
    w_raiders = bb.white_pieces['raider'].bit_count()
    b_raiders = bb.black_pieces['raider'].bit_count()
            
    if bb.white_deck > 0 and w_raiders >= 2:
        score += 2000  # reward for having an unlocked deck
        
    if bb.black_deck > 0 and b_raiders >= 2:
        score -= 2000  # penalty if Black has an unlocked deck
            
    return score

# ╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╭━╮╭━┳━╮╭━╮
# ╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╰╮╰╯╭┻╮╰╯╭╯
# ╭━╮╭━━┳━━┳━━┳╮╭┳━━╮╰╮╭╯╱╰╮╭╯
# ┃╭╮┫┃━┫╭╮┃╭╮┃╰╯┃╭╮┃╭╯╰╮╱╭╯╰╮
# ┃┃┃┃┃━┫╰╯┃╭╮┃┃┃┃╭╮┣╯╭╮╰┳╯╭╮╰╮
# ╰╯╰┻━━┻━╮┣╯╰┻┻┻┻╯╰┻━╯╰━┻━╯╰━╯
# ╱╱╱╱╱╱╭━╯┃
# ╱╱╱╱╱╱╰━━╯

# --- 5. SEARCH ENGINE (Negamax) ---
class NegamaxEngine:
    def __init__(self):
        self.nodes_explored = 0
        self.start_time = 0
        self.max_depth = 5 # defaults to medium
    
    def get_best_move(self, pygame_board, player_color, history, debug=False):
        # self.start_time = time.time()
        
        if debug:
            self.start_time = time.time() + 999999
            
        else:
            self.start_time = time.time()
            
        self.nodes_explored = 0
        
        # sync bitboard
        bitboard = RampartBitboard()
        bitboard.sync_from_board(pygame_board)
        root_state = BitboardGameState(bitboard, player_color)
        
        legal_moves = root_state.get_legal_moves()
        if not legal_moves:
            return None

        color_multiplier = 1 if player_color == 'white' else -1
        best_move_found = None
        current_depth_score = -INFINITY

        # iterative deepening
        for depth in range(1, self.max_depth):
            try:
                
                if debug:
                    debug_log(f"--- Scanning All Root Moves at Depth {depth} ---")
                    for mv in legal_moves:
                        # test every move individually to see its exact score
                        next_state = root_state.apply_move(mv)
                        # we pass color_multiplier because perspective flips
                        move_score = -self.negamax(next_state, depth - 1, -INFINITY, INFINITY, \
                                                    -color_multiplier, history)[0]
                        debug_log(f"  > Move: {mv} | Score: {move_score}")
                
                # run standard negamax
                score, move = self.negamax(root_state, depth, -INFINITY, INFINITY, \
                    color_multiplier, history)
                
                # print(f"[AI] Depth {depth} done. Score: {score}. Move: {move}")

                if move:
                    best_move_found = move
                    current_depth_score = score
                
                # stop if we found the winning house move (High Score)
                if score > 4000: 
                    break

            except TimeoutError:
                print(f"[AI] Time limit reached at Depth {depth}.")
                break
        
        # --- DEBUG: SANITY CHECK ROOT MOVES ---
        # if the search results strange, this loop forces check of immediate move values
        # if best_move_found:
        #     print(f"[AI] FINAL SELECTION: {best_move_found}")
            
        #     # double check: Does the selected move actually have the high score?
        #     test_state = root_state.apply_move(best_move_found)
        #     static_eval = evaluate_board(test_state) * color_multiplier
        #     print(f"[AI] Static Eval of Selected Move: {static_eval}")
            
        #     # if we found a huge score (5000) but selected move is weak (<1000), 
        #     # something is wrong. Let's scan all root moves to find the 5000 one.
        #     if current_depth_score > 4000 and static_eval < 1000:
        #         print("[AI] !!! MISMATCH DETECTED. Scanning all root moves for the 5000 pointer...")
        #         for mv in legal_moves:
        #             next_s = root_state.apply_move(mv)
        #             s_score = evaluate_board(next_s) * color_multiplier
        #             if s_score > 4000:
        #                 print(f"[AI] FOUND IT! Correct move is: {mv} (Score: {s_score})")
        #                 best_move_found = mv
        #                 break
        
        # flush_debug_log()
        return best_move_found

    def negamax(self, state, depth, alpha, beta, color, state_history):
        # time Check
        # using bitwise '&' here with integer 1023 (has 10 1's in binary)
        if self.nodes_explored & 1023 == 0:
            if time.time() - self.start_time > TIME_LIMIT:
                raise TimeoutError()
                
        current_hash = state.bitboard.get_state_hash()
        
        if current_hash in state_history:
            # apply massive penalty
            return -500, None
                
        self.nodes_explored += 1

        # base Case
        if depth == 0 or state.is_terminal():
            
            if state.attack_gen.is_king_in_check(state.bitboard, state.current_player):
                # Only NOW do we spend CPU time generating moves
                if not state.get_legal_moves():
                    return -CHECKMATE_SCORE + depth, None
            
            return color * evaluate_board(state), None

        legal_moves = state.get_legal_moves()
        
        # checkmate / stalemate check
        if not legal_moves:
            in_check = state.attack_gen.is_king_in_check(state.bitboard, \
                    state.current_player)
            if in_check:
                return -CHECKMATE_SCORE + depth, None
            else:
                return 0, None

        # move ordering (optimization: prioritize captures by guess)
        # simple heuristic: prioritize moves to squares that have enemies
        # (for now, we just rely on standard order)

        max_eval = -INFINITY
        best_move = None

        for move in legal_moves:
            
            # if this move is 
            new_state, _ = state.apply_move(move)
            
            # recurse
            eval_score, _ = self.negamax(new_state, depth - 1, -beta, -alpha, \
                -color, state_history)
            eval_score = -eval_score
            
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move
            
            alpha = max(alpha, eval_score)
            if alpha >= beta:
                break

        return max_eval, best_move