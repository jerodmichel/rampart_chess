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
TIME_LIMIT = 5.0  # seconds per move - was INFINITY, which meant the
                  # TimeoutError check in negamax() could never fire

# transposition-table bound flags
TT_EXACT = 0
TT_LOWERBOUND = 1
TT_UPPERBOUND = 2

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

    def is_square_attacked(self, bitboard, square, by_color):
        """STEP 1 of the legality-check speedup: a cheap, targeted 'is this
        one square attacked' query, reusing the same precomputed tables
        the move generators already use (KNIGHT_TABLE, ROOK_RAYS/QUEEN_RAYS,
        raider diagonal pattern), instead of building a full board-wide
        attack map (get_attack_map) just to answer one square's yes/no
        question.

        Deliberately mirrors get_attack_map's existing masking exactly, so
        it can be validated square-for-square against it:
          - king attacks are allowed onto house squares (get_attack_map
            uses TOTAL_PLAYABLE_BOARD for the king)
          - knight/rook/bishop/queen attacks only ever land within
            NON_RAIDER_VALID_MASK (get_attack_map masks these with it)
          - raiders capture diagonally only, can never attack INTO a house
            square (mirrors get_raider_moves' vulnerable_enemies mask),
            and a raider currently SITTING on a house square is
            immobilized and contributes no attacks at all (mirrors
            get_raider_moves' own immobilization check)

        Not yet used anywhere - this is the primitive itself, to be
        validated on its own before anything is built on top of it.
        """
        bb = bitboard
        pieces = bb.white_pieces if by_color == 'white' else bb.black_pieces
        occupied = bb.get_occupied()
        sq_mask = 1 << square

        # get_attack_map is built from real move destinations, and every
        # move generator excludes the mover's own pieces (~friendly_mask) -
        # so a square occupied by a by_color piece is never "attacked" by
        # that same color, regardless of what any of its pieces' raw
        # patterns would otherwise cover.
        if sq_mask & sum(pieces.values()):
            return False

        # king - get_king_valid_mask (Rule 71) restricts the king to
        # NON_RAIDER_VALID_MASK normally, or to card-squares-within-middle-
        # rows if its own king house is occupied - houses are excluded
        # either way, contrary to what the & TOTAL_PLAYABLE_BOARD in
        # get_attack_map's king branch looks like at a glance (that
        # intersection is a no-op since get_king_valid_mask's result is
        # already a subset of the middle rows in both branches).
        king_valid_mask = bb.get_king_valid_mask(by_color, occupied)
        if sq_mask & king_valid_mask:
            if self.gen.KING_TABLE[square] & pieces['king']:
                return True

        # knight/rook/bishop/queen only ever threaten non-house squares
        if sq_mask & bb.NON_RAIDER_VALID_MASK:
            if self.gen.KNIGHT_TABLE[square] & pieces['knight']:
                return True

            for i in range(8):
                ray = self.gen.QUEEN_RAYS[square][i]
                blockers = ray & occupied
                if not blockers:
                    continue
                if i in [0, 3, 5, 7]:
                    first_blocker_sq = (blockers & -blockers).bit_length() - 1
                else:
                    first_blocker_sq = blockers.bit_length() - 1
                blocker_mask = 1 << first_blocker_sq

                if i < 4:
                    if blocker_mask & (pieces['rook'] | pieces['queen']):
                        return True
                else:
                    if blocker_mask & (pieces['bishop'] | pieces['queen']):
                        return True

        # raiders: diagonal-only, can't attack INTO a house square, a
        # raider sitting IN a house square is immobilized, and (Rule: can't
        # cross back over the rampart) a raider that has already crossed
        # the rampart can't attack back across it either - this last one
        # is per-raider (depends on THAT raider's own row), so it's
        # checked via get_raider_valid_mask directly rather than
        # re-derived here, to guarantee it can't diverge from the real
        # move generator's rule.
        if not (sq_mask & self.raider_gen.ALL_HOUSES):
            diag_neighbors = self.raider_gen._get_diagonal_neighbors(square)
            candidate_raiders = pieces['raider'] & diag_neighbors & ~self.raider_gen.ALL_HOUSES
            for r_sq in bb.get_set_bits(candidate_raiders):
                if sq_mask & bb.get_raider_valid_mask(r_sq, by_color):
                    return True

        return False

    def get_checkers(self, bitboard, king_color):
        """STEP 3 of the legality-check speedup: returns a bitmask of every
        enemy square currently attacking king_color's king (0 if not in
        check). A separate function from is_square_attacked (rather than
        sharing code with it) so Step 1/2's already-validated logic stays
        completely untouched - this mirrors it closely, but accumulates
        every attacker instead of stopping at the first one, since knowing
        WHICH square(s) check the king is needed for check-evasion
        filtering (capture-the-checker / block-the-line) in a later step,
        and a position with 2+ simultaneous checkers ('double check') can
        only be escaped by moving the king - never by blocking or
        capturing.

        Not yet used anywhere - dormant until validated, like Step 1 was.
        """
        bb = bitboard
        king_bb = bb.white_pieces['king'] if king_color == 'white' else bb.black_pieces['king']
        if king_bb == 0:
            return 0
        king_sq = king_bb.bit_length() - 1

        enemy_color = 'black' if king_color == 'white' else 'white'
        pieces = bb.white_pieces if enemy_color == 'white' else bb.black_pieces
        occupied = bb.get_occupied()
        sq_mask = 1 << king_sq

        checkers = 0

        # king (Rule 71 masking, same as is_square_attacked)
        king_valid_mask = bb.get_king_valid_mask(enemy_color, occupied)
        if sq_mask & king_valid_mask:
            checkers |= (pieces['king'] & self.gen.KING_TABLE[king_sq])

        # knight/rook/bishop/queen only ever threaten non-house squares
        if sq_mask & bb.NON_RAIDER_VALID_MASK:
            checkers |= (pieces['knight'] & self.gen.KNIGHT_TABLE[king_sq])

            for i in range(8):
                ray = self.gen.QUEEN_RAYS[king_sq][i]
                blockers = ray & occupied
                if not blockers:
                    continue
                if i in [0, 3, 5, 7]:
                    first_blocker_sq = (blockers & -blockers).bit_length() - 1
                else:
                    first_blocker_sq = blockers.bit_length() - 1
                blocker_mask = 1 << first_blocker_sq

                if i < 4:
                    if blocker_mask & (pieces['rook'] | pieces['queen']):
                        checkers |= blocker_mask
                else:
                    if blocker_mask & (pieces['bishop'] | pieces['queen']):
                        checkers |= blocker_mask

        # raiders: diagonal-only, can't attack INTO a house square, a
        # raider sitting IN a house square is immobilized, and the anti-
        # backcrossing rule applies per-raider via get_raider_valid_mask
        if not (sq_mask & self.raider_gen.ALL_HOUSES):
            diag_neighbors = self.raider_gen._get_diagonal_neighbors(king_sq)
            candidate_raiders = pieces['raider'] & diag_neighbors & ~self.raider_gen.ALL_HOUSES
            for r_sq in bb.get_set_bits(candidate_raiders):
                if sq_mask & bb.get_raider_valid_mask(r_sq, enemy_color):
                    checkers |= (1 << r_sq)

        return checkers

    def get_pinned_pieces(self, bitboard, king_color):
        """STEP 4 of the legality-check speedup: for each friendly piece
        that sits ALONE between the king and an enemy slider (rook/bishop/
        queen) along one of the 8 ray directions, returns a dict mapping
        that piece's square -> the bitmask of squares it may still legally
        move to without exposing the king (the pin line itself: every
        square from the king outward to and including the pinning piece's
        own square, so the pinned piece may still slide along that same
        line, or capture the pinner, without ever being fully immobile).
        Pieces not present in this dict are not pinned by anything.

        Uses the exact same first-blocker-then-second-blocker ray-walk the
        move generators already use for sliding pieces (see get_rook_moves/
        get_queen_moves in rampartmovegenerator.py), just carried one
        blocker further, so it can't diverge from geometry those already
        rely on.

        Not yet used anywhere - dormant until validated, like Steps 1-3.
        """
        bb = bitboard
        king_bb = bb.white_pieces['king'] if king_color == 'white' else bb.black_pieces['king']
        if king_bb == 0:
            return {}
        king_sq = king_bb.bit_length() - 1

        friendly_pieces = bb.white_pieces if king_color == 'white' else bb.black_pieces
        friendly_mask = sum(friendly_pieces.values())
        enemy_color = 'black' if king_color == 'white' else 'white'
        enemy_pieces = bb.white_pieces if enemy_color == 'white' else bb.black_pieces
        occupied = bb.get_occupied()

        pins = {}

        for i in range(8):
            ray = self.gen.QUEEN_RAYS[king_sq][i]
            blockers = ray & occupied
            if not blockers:
                continue
            if i in [0, 3, 5, 7]:
                first_blocker_sq = (blockers & -blockers).bit_length() - 1
            else:
                first_blocker_sq = blockers.bit_length() - 1
            first_mask = 1 << first_blocker_sq

            if not (first_mask & friendly_mask):
                continue  # nearest piece in this direction isn't ours - no pin here

            remainder = self.gen.QUEEN_RAYS[first_blocker_sq][i]
            blockers2 = remainder & occupied
            if not blockers2:
                continue  # nothing beyond our piece - no pin

            if i in [0, 3, 5, 7]:
                second_blocker_sq = (blockers2 & -blockers2).bit_length() - 1
            else:
                second_blocker_sq = blockers2.bit_length() - 1
            second_mask = 1 << second_blocker_sq

            if i < 4:
                is_pinning = second_mask & (enemy_pieces['rook'] | enemy_pieces['queen'])
            else:
                is_pinning = second_mask & (enemy_pieces['bishop'] | enemy_pieces['queen'])

            if is_pinning:
                pin_line = ray ^ self.gen.QUEEN_RAYS[second_blocker_sq][i]
                pins[first_blocker_sq] = pin_line

        return pins

    def get_check_resolution_mask(self, bitboard, king_color, checkers):
        """STEP 5 helper: given a nonzero `checkers` bitmask (from
        get_checkers - caller must have already confirmed it's truthy),
        returns (in_double_check, resolution_mask):
          - in_double_check=True means only a king move can escape (two or
            more simultaneous checkers can never both be blocked/captured
            by a single move); resolution_mask is 0 and unused in that case.
          - otherwise resolution_mask is the set of squares a non-king move
            must land on to resolve the check: capturing the checker
            itself, or (only possible against a sliding checker) blocking
            its line to the king. Non-sliding checkers (knight, raider)
            can only be resolved by capture, since there's no line to block.

        Not yet used anywhere - dormant until validated, like Steps 1-4.
        """
        checker_count = bin(checkers).count('1')
        if checker_count >= 2:
            return True, 0

        checker_sq = checkers.bit_length() - 1

        king_bb = bitboard.white_pieces['king'] if king_color == 'white' else bitboard.black_pieces['king']
        king_sq = king_bb.bit_length() - 1

        enemy_color = 'black' if king_color == 'white' else 'white'
        enemy_pieces = bitboard.white_pieces if enemy_color == 'white' else bitboard.black_pieces

        is_slider = checkers & (enemy_pieces['rook'] | enemy_pieces['bishop'] | enemy_pieces['queen'])
        if not is_slider:
            return False, checkers  # capture is the only resolution

        for i in range(8):
            ray = self.gen.QUEEN_RAYS[king_sq][i]
            if ray & checkers:
                # ray from king up to and including the checker's square -
                # covers both "capture the checker" and "block the line"
                resolution_mask = ray ^ self.gen.QUEEN_RAYS[checker_sq][i]
                return False, resolution_mask

        # shouldn't happen if checkers/king are geometrically consistent,
        # but fall back to "capture only" defensively rather than crash
        return False, checkers

    def would_removal_expose_check(self, bitboard, king_color, removed_sq):
        """Would removing WHATEVER piece currently sits at removed_sq
        expose king_color's king to a NEW check from an enemy slider?

        This is for STRIKE cast moves specifically: a strike removes an
        ENEMY raider, and blocking is about occupancy, not ownership - an
        enemy raider sitting between an enemy slider and your own king is
        still blocking that slider's line (regardless of whose piece it
        is), so striking it can create a genuine discovered check against
        yourself. (Confirmed concretely: king + enemy rook aimed at it +
        enemy raider directly between them - checkers is 0 before, becomes
        nonzero if that raider is removed.) RAISE/RAISE_QUEEN never need
        this check, since they only ever ADD a piece to an empty square,
        which can only add a blocker, never remove one.

        Mirrors get_pinned_pieces' ray-walk, but doesn't require the first
        blocker to be a friendly piece - it specifically checks what
        happens if THIS square's occupant (whoever it is) goes away.

        Not yet used anywhere - dormant until validated.
        """
        bb = bitboard
        king_bb = bb.white_pieces['king'] if king_color == 'white' else bb.black_pieces['king']
        if king_bb == 0:
            return False
        king_sq = king_bb.bit_length() - 1

        enemy_color = 'black' if king_color == 'white' else 'white'
        enemy_pieces = bb.white_pieces if enemy_color == 'white' else bb.black_pieces
        occupied = bb.get_occupied()
        removed_mask = 1 << removed_sq

        for i in range(8):
            ray = self.gen.QUEEN_RAYS[king_sq][i]
            if not (ray & removed_mask):
                continue  # removed_sq isn't even on this ray from the king

            blockers = ray & occupied
            if i in [0, 3, 5, 7]:
                first_blocker_sq = (blockers & -blockers).bit_length() - 1
            else:
                first_blocker_sq = blockers.bit_length() - 1

            if first_blocker_sq != removed_sq:
                continue  # something else already blocks this ray first -
                          # removing removed_sq changes nothing here

            remainder = self.gen.QUEEN_RAYS[removed_sq][i]
            blockers2 = remainder & occupied
            if not blockers2:
                continue

            if i in [0, 3, 5, 7]:
                second_blocker_sq = (blockers2 & -blockers2).bit_length() - 1
            else:
                second_blocker_sq = blockers2.bit_length() - 1
            second_mask = 1 << second_blocker_sq

            if i < 4:
                if second_mask & (enemy_pieces['rook'] | enemy_pieces['queen']):
                    return True
            else:
                if second_mask & (enemy_pieces['bishop'] | enemy_pieces['queen']):
                    return True

        return False

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
                
        # STEP 2 of the legality-check speedup: king moves use the cheap
        # targeted check from Step 1 instead of rebuilding a full board-wide
        # attack map, since we already know exactly which one square needs
        # checking - the king's own destination (which is where the king's
        # bitboard now sits, post-move, on temp_bb). Every other piece type
        # is untouched for now and still goes through is_king_in_check.
        if move.piece_type == 'king':
            enemy_color = 'black' if player_color == 'white' else 'white'
            return not self.is_square_attacked(temp_bb, move.to_sq, enemy_color)

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

        # STEP 5 of the legality-check speedup: compute checkers/pins ONCE
        # per node (Steps 3-4), instead of a full make/unmake + attack-map
        # rebuild for every single candidate move. Only applies to the
        # "standard move" branch below (king moves already use the Step 2
        # fast path inside ai_self_in_check; cast moves and the
        # enter_queen_house branch are untouched, out of scope for this pass).
        checkers = self.attack_gen.get_checkers(self.bitboard, self.current_player)
        if checkers:
            in_double_check, resolution_mask = self.attack_gen.get_check_resolution_mask(
                self.bitboard, self.current_player, checkers)
        else:
            in_double_check, resolution_mask = False, None
        pins = self.attack_gen.get_pinned_pieces(self.bitboard, self.current_player)

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

                        if p_type == 'king':
                            # king moves already use the Step 2 fast path
                            # inside ai_self_in_check
                            is_safe = self.attack_gen.ai_self_in_check(self.bitboard, mv, self.current_player)
                        elif in_double_check:
                            # only a king move can ever escape a double check
                            is_safe = False
                        else:
                            is_safe = True
                            if from_sq in pins and not (pins[from_sq] & (1 << to_sq)):
                                is_safe = False
                            if is_safe and checkers and not (resolution_mask & (1 << to_sq)):
                                is_safe = False

                        if is_safe:
                            moves.append(mv)
                        
        # cast moves
        raw_casts = self.cast_gen.get_cast_moves(self.bitboard, self.current_player)
        
        # wrap in engine objects
        for (src, tgt, m_type, cards) in raw_casts:
            # notation (and apply_move's own move_type-driven dispatch) should
            # reflect which piece is actually being raised - a queen for
            # raise_queen, a raider otherwise - not a hardcoded placeholder
            cast_piece_type = 'queen' if m_type == 'raise_queen' else 'raider'
            mv = EngineMove(src, tgt, cast_piece_type, self.current_player, m_type, cards)

            # cast moves never involve a friendly piece leaving a square it
            # occupies (raise/raise_queen only ADD a piece to an empty
            # square; strike only REMOVES an enemy piece) so ai_self_in_check
            # - built around "a piece relocates from A to B" - doesn't apply
            # here at all (it also wasn't correct for these move shapes; see
            # apply_move's cast branch above for the real semantics).
            #
            # Adding a friendly piece can only ever block a ray, never
            # create a new discovered check against yourself - confirmed
            # both by reasoning and empirically (1000+ real raise/raise_queen
            # moves applied via apply_move: the only ones that end in check
            # were already in check beforehand and didn't happen to resolve
            # it - zero cases of a raise creating a NEW exposure).
            #
            # Removing an enemy piece (strike) is different: blocking is
            # about occupancy, not ownership, so an enemy raider sitting
            # between an enemy slider and your own king is still blocking
            # that slider - striking it can genuinely discover a check
            # against yourself. Confirmed concretely (king + enemy rook
            # aimed at it + enemy raider directly between them: checkers is
            # 0 before, nonzero once that raider is removed).
            if m_type in ('raise', 'raise_queen'):
                if not checkers:
                    is_safe = True
                elif in_double_check:
                    is_safe = False
                else:
                    is_safe = bool(resolution_mask & (1 << tgt))
            else:  # strike
                exposes = self.attack_gen.would_removal_expose_check(
                    self.bitboard, self.current_player, tgt)
                if not checkers:
                    is_safe = not exposes
                elif in_double_check:
                    is_safe = False
                else:
                    is_safe = bool(resolution_mask & (1 << tgt)) and not exposes

            if is_safe:
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
        if move.move_type in ["raise", "strike", "raise_queen"]:
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
        self.max_depth = 6 # defaults to medium
        self.time_limit = TIME_LIMIT # per-instance so difficulty can vary it
        self.transposition_table = {}
        self.quiescence_max_depth = 4 # cap on capture-chain extension

    def get_best_move(self, pygame_board, player_color, history, debug=False):
        # self.start_time = time.time()

        if debug:
            self.start_time = time.time() + 999999

        else:
            self.start_time = time.time()

        self.nodes_explored = 0

        # fresh per move-decision: keeps memory bounded over a long game and
        # avoids any risk of a stale entry from an earlier, unrelated position
        self.transposition_table = {}

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
        # (was range(1, self.max_depth), which never actually reached
        # max_depth itself - e.g. "Medium" (max_depth=5) only ever searched
        # to depth 4)
        for depth in range(1, self.max_depth + 1):
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
            if time.time() - self.start_time > self.time_limit:
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

            if state.is_terminal():
                return color * evaluate_board(state), None

            # depth 0, not checkmate: resolve captures before settling on a
            # static evaluation, so we don't misjudge a position that's mid-
            # exchange right at the search horizon (the "horizon effect").
            return self.quiescence(state, alpha, beta, color, state_history, 0), None

        legal_moves = state.get_legal_moves()

        # checkmate / stalemate check
        if not legal_moves:
            in_check = state.attack_gen.is_king_in_check(state.bitboard, \
                    state.current_player)
            if in_check:
                return -CHECKMATE_SCORE + depth, None
            else:
                return 0, None

        # --- transposition table lookup ---
        # keyed on (hash, current_player) rather than hash alone, since
        # get_state_hash() doesn't encode whose turn it is - the same raw
        # board/deck/graveyard state could in principle be reached with
        # either side to move, and a negamax score is only meaningful for
        # the side it was computed for.
        tt_key = (current_hash, state.current_player)
        tt_entry = self.transposition_table.get(tt_key)
        tt_move = None
        if tt_entry is not None:
            tt_depth, tt_score, tt_flag, tt_move = tt_entry
            if tt_depth >= depth:
                if tt_flag == TT_EXACT:
                    return tt_score, tt_move
                elif tt_flag == TT_LOWERBOUND:
                    alpha = max(alpha, tt_score)
                elif tt_flag == TT_UPPERBOUND:
                    beta = min(beta, tt_score)
                if alpha >= beta:
                    return tt_score, tt_move

        # move ordering: try the cached best move from a previous search of
        # this same position first, then captures, then everything else -
        # alpha-beta prunes far more when strong moves are tried first.
        tt_move_key = (tt_move.from_sq, tt_move.to_sq, tt_move.move_type) \
            if tt_move is not None else None

        enemy_pieces = state.bitboard.black_pieces if state.current_player == 'white' \
            else state.bitboard.white_pieces
        enemy_occupied = 0
        for b in enemy_pieces.values():
            enemy_occupied |= b

        def move_sort_key(mv):
            if tt_move_key is not None and \
                (mv.from_sq, mv.to_sq, mv.move_type) == tt_move_key:
                return 0
            return 1 if (enemy_occupied & (1 << mv.to_sq)) else 2

        legal_moves.sort(key=move_sort_key)

        orig_alpha = alpha
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

        # --- transposition table store ---
        if max_eval <= orig_alpha:
            flag = TT_UPPERBOUND
        elif max_eval >= beta:
            flag = TT_LOWERBOUND
        else:
            flag = TT_EXACT
        self.transposition_table[tt_key] = (depth, max_eval, flag, best_move)

        return max_eval, best_move

    def quiescence(self, state, alpha, beta, color, state_history, qdepth):
        """Extends the search past the depth-0 horizon through captures
        only (raises/strikes/normal captures all reduce material, so this
        always terminates), so the static eval isn't taken mid-exchange.
        Deliberately does NOT special-case "in check" (that's a separate,
        pre-existing limitation left untouched here) and does NOT use the
        transposition table (its "depth" isn't comparable to negamax's)."""
        if self.nodes_explored & 1023 == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
        self.nodes_explored += 1

        stand_pat = color * evaluate_board(state)

        if qdepth >= self.quiescence_max_depth or state.is_terminal():
            return stand_pat

        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        enemy_pieces = state.bitboard.black_pieces if state.current_player == 'white' \
            else state.bitboard.white_pieces
        enemy_occupied = 0
        for b in enemy_pieces.values():
            enemy_occupied |= b

        def captured_value(mv):
            # most-valuable-victim ordering, reusing PIECE_VALUES purely to
            # order search - doesn't touch evaluation at all
            for p_type, p_bb in enemy_pieces.items():
                if p_bb & (1 << mv.to_sq):
                    return PIECE_VALUES.get(p_type, 0)
            return 0

        capture_moves = [mv for mv in state.get_legal_moves()
                          if enemy_occupied & (1 << mv.to_sq)]
        capture_moves.sort(key=captured_value, reverse=True)

        for move in capture_moves:
            new_state, _ = state.apply_move(move)
            score = -self.quiescence(new_state, -beta, -alpha, -color, \
                state_history, qdepth + 1)

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha