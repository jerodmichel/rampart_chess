#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 17:02:01 2024

@author: stereo
"""

#  ██████╗   ██████╗   █████╗   ██████╗   ██████╗
#  ██╔══██╗  ██╔══██╗  ██╔══██╗  ██╔══██╗  ██╔══██╗
#  ██████╔╝  ██║  ██║  ███████║  ██████╔╝  ██║  ██║
#  ██╔══██╗  ██║  ██║  ██╔══██║  ██╔══██╗  ██║  ██║
#  ██████╔╝  ██████╔╝  ██║  ██║  ██║  ██║  ██████╔╝
#  ╚═════╝   ╚═════╝   ╚═╝  ╚═╝   ╚═╝  ╚═╝   ╚═════╝
#  ┌────┐    ┌────┐    ┌───┐    ┌────┐    ┌────┐
#  │ ██║    │ ██║    │╭─╮│    │ ╭─╮│    │ ██║
#  │ ██║    │ ██║    │╰─╯│    │ ╰─╯│    │ ██║
#  └────┘    └────┘    └───┘    └────┘    └────┘

from const import *
from grave import Grave
from card import Card
from cast_button import Cast_button
from square import Square
from piece import *
from clicker import Clicker
from player import Player
from move import Move
from cast_move import Cast_move
from comprehensiveCastCache import *

import time
import copy

class Board:
    
    def __init__(self, flipped):
        self.flipped = flipped
        self.players = [0, 0]
        self.squares = [[0, 0, 0, 0, 0, 0] for col in range(COLS)]
        self.cards = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] for col in range(4)]
        self.graves = [[0, 0, 0, 0, 0, 0, 0, 0, 0] for col in range(2)]
        self.cast_buttons = [0, 0]
        self.last_move = None
        self.last_player_color = None # networked
        self.king_mated = False
        self.king_stalemated = False
        self.clicker = Clicker()
        self._create()
        self._add_cards()
        self._add_pieces('white')
        self._add_pieces('black')
        self._add_dead_pieces('white')
        self._add_dead_pieces('black')
        self.cast_cache = ComprehensiveCastCache()
        
    def print_debug(self):
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[col][row].piece
                print(f"[{'W' if piece and piece.color=='white' else 'B' if piece else ' '}]", end="")
            print()  # newline after each row
            

# █▄░█ █▀▀ ▀█▀ █░█░█ █▀█ █▀█ █▄▀ █ █▄░█ █▀▀
# █░▀█ ██▄ ░█░ ▀▄▀▄▀ █▄█ █▀▄ █░█ █ █░▀█ █▄█
            
    def get_serialized_state(self):
        # serialize the current board state for Firebase
        state = {
            'squares': [],
            'graves': [],
            'players': {
                'white': {
                    'cast_moved': self.players[1].cast_moved,
                },
                'black': {
                    'cast_moved': self.players[0].cast_moved,
                }
            },
            'flipped': self.flipped,
            'king_mated': self.king_mated
        }
        
        # serialize squares
        for col in range(COLS):
            for row in range(ROWS):
                square = self.squares[col][row]
                square_data = {
                    'col': col,
                    'row': row,
                    'has_piece': square.has_piece(),
                    'has_card': square.is_card()
                }
                
                if square.has_piece():
                    piece = square.piece
                    square_data['piece'] = {
                        'name': piece.name,
                        'color': piece.color,
                        'moved': piece.moved
                    }
                    
                if square.is_card():
                    card = square.card
                    square_data['card'] = {
                        'suit': card.suit,
                        'rank': card.rank,
                        'cast': card.is_cast()
                    }
                    
                state['squares'].append(square_data)
        
        # serialize graves
        for col in range(2):  # 0=black, 1=white
            for row in range(GRAVES):
                grave = self.graves[col][row]
                grave_data = {
                    'col': col,
                    'row': row,
                    'has_piece': grave.has_piece()
                }
                
                if grave.has_piece():
                    piece = grave.piece
                    grave_data['piece'] = {
                        'name': piece.name,
                        'color': piece.color
                    }
                    
                state['graves'].append(grave_data)
        
        return state
    
    def get_card(self, suit, rank):
        # get card by suit/rank, whether in deck or on table
        # sheck main deck (suits 0-1)
        if suit in [0, 1]:
            return self.cards[suit][rank]
        
        else:
            return Card(suit, rank)
        
        raise ValueError(f"Card not found: suit={suit}, rank={rank}")
            
    def apply_networked_move(self, move):
        initial_sq = self.squares[move.initial.col][move.initial.row]
        piece = initial_sq.piece
        
        if not piece:
            raise ValueError("No piece at start position")
        
        # RECALCULATE moves for this piece (exactly like when clicked)
        self.calc_moves(piece, move.initial.col, move.initial.row, bool=True)
        
        # now validate against the freshly calculated moves
        if move in piece.moves:
            return self.move(piece, move)
        else:
            raise ValueError("Move not in valid moves")
            
    def apply_networked_cast_move(self, player, piece, card, move):
        if move.cast_type not in [0, 1]:  # ensure it's an int
            raise ValueError(f"Invalid cast_type: {move.cast_type}")
            
        # recalculate cast moves for this call
        self.calc_cast_moves(player, piece)
        
        # validate move
        if move in player.cast_moves:
            return self.cast_move(player, piece, card, move)
        else:
            raise ValueError("Cast move not a valid cast move")


# ╭━╮╭━┳━━━┳╮╱╱╭┳━━━╮╭╮╱╭┳━━━┳━╮╱╭┳━━━┳╮╱╱╭━━┳━╮╱╭┳━━━╮
# ┃┃╰╯┃┃╭━╮┃╰╮╭╯┃╭━━╯┃┃╱┃┃╭━╮┃┃╰╮┃┣╮╭╮┃┃╱╱╰┫┣┫┃╰╮┃┃╭━╮┃
# ┃╭╮╭╮┃┃╱┃┣╮┃┃╭┫╰━━╮┃╰━╯┃┃╱┃┃╭╮╰╯┃┃┃┃┃┃╱╱╱┃┃┃╭╮╰╯┃┃╱╰╯
# ┃┃┃┃┃┃┃╱┃┃┃╰╯┃┃╭━━╯┃╭━╮┃╰━╯┃┃╰╮┃┃┃┃┃┃┃╱╭╮┃┃┃┃╰╮┃┃┃╭━╮
# ┃┃┃┃┃┃╰━╯┃╰╮╭╯┃╰━━╮┃┃╱┃┃╭━╮┃┃╱┃┃┣╯╰╯┃╰━╯┣┫┣┫┃╱┃┃┃╰┻━┃
# ╰╯╰╯╰┻━━━╯╱╰╯╱╰━━━╯╰╯╱╰┻╯╱╰┻╯╱╰━┻━━━┻━━━┻━━┻╯╱╰━┻━━━╯
        
    def move(self, piece, move):
        initial = move.initial
        final = move.final
        
        # generate notation
        notation = f"{piece.name[0].upper()}{initial.col + 1}{Square.get_alpharow(5 - initial.row)}>{final.col + 1}{Square.get_alpharow(5 - final.row)}"
        
        # console board move update
        self.squares[initial.col][initial.row].piece = None
        self.squares[final.col][final.row].piece = piece
        
        # move
        piece.moved = True
        
        # clear valid moves
        piece.clear_moves()
        
        self.last_player_color = piece.color # networked
        self.last_move = move
        
        return notation
        
    def valid_move(self, piece, move):
        if self.flipped:
            # convert flipped display coords back to internal coords if needed
            initial = Square(move.initial.col, move.initial.row)
            final = Square(move.final.col, move.final.row)
        else:
            initial, final = move.initial, move.final 
             
        return move in piece.moves
        
    def cast_move(self, player, piece, card, cast_move):
        
        # generate notation
        prefix = "++" if cast_move.cast_type == 1 else "--"
        p_char = piece.name[0].upper()
        target = f"{cast_move.final.col + 1}{Square.get_alpharow(5 - cast_move.final.row)}"
        cards_str = ",".join([RANKS[c.rank] for c in cast_move.cards])
        notation = f"{prefix}{p_char}@{target}({cards_str})"
        
        if cast_move.cast_type == 0:
            col = cast_move.final.col
            row = cast_move.final.row
            self._send_to_grave(self.squares[col][row].piece)
            self.squares[col][row].piece = None
            
        elif cast_move.cast_type == 1:
            if piece.name == 'raider':
                self._raise_raider(cast_move.final.col, cast_move.final.row, player.color, card)
            elif piece.name == 'queen':
                self._raise_queen(cast_move.final.col, cast_move.final.row, player.color, card)
        
        player.cast_moved = True
        
        player.clear_cast_moves()
        
        self.last_player_color = player.color # networked
        self.last_move = cast_move
        
        return notation
        
    def valid_cast_move(self, player, move):
        return move in player.cast_moves
    
    def is_eligible(self, col, row):
        if (col == 3 and row == 0) and self.squares[4][0].has_piece():
            return True
        elif (col == 6 and row == 5) and self.squares[5][5].has_piece():
            return True
        elif (col == 2 and row == 0) and self.squares[3][0].has_piece():
            return True
        elif (col == 7 and row == 5) and self.squares[6][5].has_piece():
            return True
        elif (col == 4 and row == 0) or (col == 5 and row == 5) or \
            not self.squares[col][row].is_house():
            return True
        else:
            return False
                

# ╭━━━┳╮╱╭┳━━━┳━━━┳╮╭━┳━━━╮
# ┃╭━╮┃┃╱┃┃╭━━┫╭━╮┃┃┃╭┫╭━╮┃
# ┃┃╱╰┫╰━╯┃╰━━┫┃╱╰┫╰╯╯┃╰━━╮
# ┃┃╱╭┫╭━╮┃╭━━┫┃╱╭┫╭╮┃╰━━╮┃
# ┃╰━╯┃┃╱┃┃╰━━┫╰━╯┃┃┃╰┫╰━╯┃
# ╰━━━┻╯╱╰┻━━━┻━━━┻╯╰━┻━━━╯
    
    def in_check(self, piece, move):
        temp_board = copy.deepcopy(self)
        
        # clear all cached moves in temp_board
        for col in range(COLS):
            for row in range(ROWS):
                if temp_board.squares[col][row].has_piece():
                    temp_board.squares[col][row].piece.clear_moves()
        
        # apply move
        temp_piece = temp_board.squares[move.initial.col][move.initial.row].piece
        temp_board.move(temp_piece, move)
        
        # find the king's position
        king_pos = None
        for col in range(COLS):
            for row in range(ROWS):
                sq = temp_board.squares[col][row]
                if sq.has_team_piece(piece.color) and isinstance(sq.piece, King):
                    king_pos = (col, row)
                    break
            if king_pos:
                break
        
        if not king_pos:
            return False
        
        # force enemy pieces to recalc moves
        for col in range(COLS):
            for row in range(ROWS):
                square = temp_board.squares[col][row]
                if square.has_rival_piece(piece.color):
                    temp_board.calc_moves(square.piece, col, row, bool=False)
        
        # check if any opponent piece attacks the king
        for col in range(COLS):
            for row in range(ROWS):
                square = temp_board.squares[col][row]
                if square.has_rival_piece(piece.color):
                    # defensive check:
                    if not hasattr(square, 'piece') or square.piece is None:
                        continue  # skip if no piece exists
                        
                    pc = square.piece
                    
                    if isinstance(pc, Queen):
                        directions = [
                        (-1, 1),   # up-right
                        (-1, -1),  # up-left
                        (1, 1),    # down-right
                        (1, -1),   # down-left
                        (-1, 0),   # up
                        (0, 1),    # right
                        (1, 0),    # down
                        (0, -1)    # left
                        ]
                
                        for dcol, drow in directions:
                            step = 1
                            while True:
                                check_col = col + (dcol * step)
                                check_row = row + (drow * step)
                                
                                if not Square.in_range(check_col, check_row):
                                    break
                                    
                                check_sq = temp_board.squares[check_col][check_row]
                                
                                # found king - check is valid
                                if (check_col, check_row) == king_pos:
                                    return True
                                    
                                # hit another piece - stop checking in this direction
                                if check_sq.has_piece():
                                    break
                                    
                                step += 1
                    else:
                        temp_board.calc_moves(pc, col, row, bool=False)
                        for mv in pc.moves:
                            if (mv.final.col, mv.final.row) == king_pos:
                                return True
        return False
                        
    def cast_in_check(self, player, piece, cast_move):
        temp_player = copy.deepcopy(player)
        temp_piece = copy.deepcopy(piece) if piece else None
        temp_card = copy.deepcopy(self.squares[cast_move.final.col][cast_move.final.row].card)
        temp_board = copy.deepcopy(self)
        temp_board.cast_move(temp_player, temp_piece, temp_card, cast_move)
        
        for col in range(COLS):
            for row in range(ROWS):
                if temp_board.squares[col][row].has_rival_piece(player.color):
                    pc = temp_board.squares[col][row].piece
                    temp_board.calc_moves(pc, col, row, bool=False)
                    for mv in pc.moves:
                        if isinstance(mv.final.piece, King):
                            return True
                        
        return False
    
    def king_in_check(self, player):
        print(f"\n[Check Detection] Checking {player.color} king")
        temp_board = copy.deepcopy(self)
        
        print("[Initial Board State]")
        temp_board.print_debug()
        
        # clear all cached moves
        for col in range(COLS):
            for row in range(ROWS):
                if temp_board.squares[col][row].has_piece():
                    temp_board.squares[col][row].piece.clear_moves()
        
        for col in range(COLS):
            for row in range(ROWS):
                if temp_board.squares[col][row].has_rival_piece(player.color):
                    pc = temp_board.squares[col][row].piece
                    print(f"[Checking Piece] {pc.name} at {col},{row}")
                    temp_board.calc_moves(pc, col, row, bool=False)
                    
                    for mv in pc.moves:
                        if isinstance(mv.final.piece, King):
                            print(f"[Check Found] {pc.name} at {col},{row} can attack king")
                            return True
        print("[No Check Found]")                
        return False
    
    
    def has_no_valid_move(self, color):
        temp_board = copy.deepcopy(self)
        
        for col in range(COLS):
            for row in range(ROWS):
                if temp_board.squares[col][row].has_team_piece(color):
                    pc = temp_board.squares[col][row].piece
                    temp_board.calc_moves(pc, col, row, bool=True)
                    if len(pc.moves) != 0:
                        for mv in pc.moves:
                            return False
                
        return True
    
    
    def has_no_valid_cast_move(self, player):
        temp_board = copy.deepcopy(self)
        
        for piece in [None, Raider(player.color), Queen(player.color)]:
             temp_board.calc_cast_moves(player, piece, booL=True)   
             if len(player.cast_moves) != 0:
                 return False
                 
        return True
                
        
    def _king_mated(self, player):
        auX = self.has_no_valid_move(player.color) and self.has_no_valid_cast_move(player)
            
        if auX and self.king_in_check(player):
            self.king_mated = True
        elif auX and not self.king_in_check(player):
            self.king_stalemated = True
            
        return auX
        

# ╭━━━┳━━━┳╮╱╱╭━━━╮╭━╮╭━┳━━━┳╮╱╱╭┳━━━┳━━━╮
# ┃╭━╮┃╭━╮┃┃╱╱┃╭━╮┃┃┃╰╯┃┃╭━╮┃╰╮╭╯┃╭━━┫╭━╮┃
# ┃┃╱╰┫┃╱┃┃┃╱╱┃┃╱╰╯┃╭╮╭╮┃┃╱┃┣╮┃┃╭┫╰━━┫╰━━╮
# ┃┃╱╭┫╰━╯┃┃╱╭┫┃╱╭╮┃┃┃┃┃┃┃╱┃┃┃╰╯┃┃╭━━┻━━╮┃
# ┃╰━╯┃╭━╮┃╰━╯┃╰━╯┃┃┃┃┃┃┃╰━╯┃╰╮╭╯┃╰━━┫╰━╯┃
# ╰━━━┻╯╱╰┻━━━┻━━━╯╰╯╰╯╰┻━━━╯╱╰╯╱╰━━━┻━━━╯    


# █▀▀ ▄▀█ █░░ █▀▀   █▀▀ ▄▀█ █▀ ▀█▀   █▀▄▀█ █▀█ █░█ █▀▀ █▀
# █▄▄ █▀█ █▄▄ █▄▄   █▄▄ █▀█ ▄█ ░█░    █░▀░█ █▄█ ▀▄▀ ██▄ ▄█


    def calc_cast_moves(self, player, piece, booL=True):
        state_hash = self._get_state_hash(player.color)
        
        # Try cache first
        cached_moves = self.cast_cache.get_cached_moves(player.color, state_hash)
        if cached_moves is not None:
            # Use cache but still validate check conditions
            valid_moves = []
            for move in cached_moves:
                if not bool or not self.cast_in_check(player, piece, move):
                    valid_moves.append(move)
            player.cast_moves = valid_moves
            return
        
        # Cache miss - run original logic
        self._original_calc_cast_moves(player, piece, booL)
        
        # Cache the results
        self.cast_cache.store_moves(player.color, state_hash, player.cast_moves)

    def _original_calc_cast_moves(self, player, piece, booL=True):
        
        color = player.color
        possible_hand = []
        possible_hand2 = []
        
        for col in range(COLS):
            for row in range(1, 5):
                if self.squares[col][row].has_piece():
                    sq = self.squares[col][row]
                    if sq.piece.name == 'raider' and sq.piece.color == color \
                        and sq.is_card():
                        possible_hand.append(sq.card)
                        
                        
        deck = self.cards[1] if color == 'white' else self.cards[0]
                            
        if len(possible_hand) > 2:
            
            possible_hand = self._sift_cards(possible_hand, deck)
            possible_hand2 = self._sift_cards2(possible_hand, deck)
            print(f"possible_hand2 combos: {possible_hand2}")
            print(f"valid_sum: {self.clicker.has_sum_21(possible_hand2)}")
            
            
        elif len(possible_hand) == 2:
            
            possible_hand2 = self._sift_cards2(possible_hand, deck)
            print(f"possible_hand2 combos: {possible_hand2}")
            print(f"valid_sum: {self.clicker.has_sum_21(possible_hand2)}")
            
            for crd in deck:
                auX = possible_hand.copy()
                auX.append(crd)
                
                if not crd.is_cast() and self.clicker.has_sum_21(auX):
                    possible_hand.append(crd)
                    break
                
            else:
                for crd in possible_hand:
                    for crd1 in deck:
                        auX = [crd]
                        auX.append(crd1)
                        if not crd1.is_cast() and self.clicker.has_sum_21(auX):
                            possible_hand.append(crd1)
                            break
                            
                    else:
                        for crd1 in deck:
                            for crd2 in deck:
                                if crd1 != crd2:
                                    auX = possible_hand.copy()
                                    auX.extend([crd1, crd2])
                                    if not crd1.is_cast() and not crd2.is_cast() and \
                                        self.clicker.has_sum_21(auX):
                                        possible_hand = [crd, crd1, crd2]
                                        break
                        break
                        
                else:
                    possible_hand = []
                    
            
        elif len(possible_hand) == 1:
            for crd1 in deck:
                auX = possible_hand.copy()
                auX.append(crd1)
                if not crd1.is_cast() and self.clicker.has_sum_21(auX):
                    possible_hand.append(crd1)
                    break
                    
            else:
                for crd1 in deck:
                    for crd2 in deck:
                        if crd1 != crd2:
                            auX = possible_hand.copy()
                            auX.extend([crd1, crd2])
                            if not crd1.is_cast() and not crd2.is_cast() and \
                                self.clicker.has_sum_21(auX):
                                possible_hand.extend([crd1, crd2])
                                break
                
        else:
            possible_hand = []
            
        
        if self._enemy_jack_house_occupied(color):
            if self.clicker.has_2_raider_cards(possible_hand):
                for col in range(COLS):
                    rAnge = range(1, 3) if color == 'white' else range(3, 5)
                    for row in rAnge:
                        sq = self.squares[col][row]
                        if sq.has_rival_piece(color) and sq.piece.name == 'raider':
                            final = sq
                            move = Cast_move(possible_hand, final, 0)
                            if booL:
                                if not self.cast_in_check(player, None, move):
                                    # append new valid move
                                    player.add_cast_move(move)
                            else:
                                # append new valid move
                                player.add_cast_move(move)
                                
                        
                    rangE = range(3, 5) if color == 'white' else range(1, 3)
                    for row in rangE:
                        sq = self.squares[col][row]
                        if sq.is_empty():
                            final = sq
                            move = Cast_move(possible_hand, final, 1)
                            if self._queen_isdead(color) and self._enemy_queen_house_occupied(color):
                                for piece in [Raider(color), Queen(color)]:
                                    if booL:
                                        if not self.cast_in_check(player, piece, move):
                                            # append new valid move
                                            player.add_cast_move(move)
                                    else:
                                        # append new valid move
                                        player.add_cast_move(move)
                            else:
                                piece = Raider(color)
                                if booL:
                                    if not self.cast_in_check(player, piece, move):
                                        # append new valid move
                                        player.add_cast_move(move)
                                else:
                                    # append new valid move
                                    player.add_cast_move(move)
                          
                for col in range(COLS):
                    for row in rangE:
                        sq = self.squares[col][row]
                        if sq.is_empty():
                            final = sq
                            move = Cast_move(possible_hand2, final, 1)
                            piece = Raider(color)
                            if booL:
                                if not self.cast_in_check(player, piece, move):
                                    # append new valid move
                                    player.add_cast_move(move)
                            else:
                                # append new valid move
                                player.add_cast_move(move)
                 
                
            elif len(possible_hand) > 0 and not self.clicker.has_2_raider_cards(possible_hand):
                for col in range(COLS):
                    rangE = range(3, 5) if color == 'white' else range(1, 3)
                    for row in rangE:
                        sq = self.squares[col][row]
                        if sq.is_empty():
                            final = sq
                            move = Cast_move(possible_hand, final, 1)
                            piece = Raider(color)
                            if booL:
                                if not self.cast_in_check(player, piece, move):
                                    # append new valid move
                                    player.add_cast_move(move)
                            else:
                                # append new valid move
                                player.add_cast_move(move)
                                
                for col in range(COLS):
                    for row in rangE:
                        sq = self.squares[col][row]
                        if sq.is_empty():
                            final = sq
                            print(f"possible_hand2 combos: {possible_hand2}")
                            print(f"valid_sum: {self.clicker.has_sum_21(possible_hand2)}") 
                            move = Cast_move(possible_hand2, final, 1)
                            piece = Raider(color)
                            if booL:
                                if not self.cast_in_check(player, piece, move):
                                    # append new valid move
                                    player.add_cast_move(move)
                            else:
                                # append new valid move
                                player.add_cast_move(move)
                                

# █▀▀ ▄▀█ █░░ █▀▀   █▀▄▀█ █▀█ █░█ █▀▀ █▀
# █▄▄ █▀█ █▄▄ █▄▄   █░▀░█ █▄█ ▀▄▀ ██▄ ▄█           
        
    def calc_moves(self, piece, col, row, bool=True):
        # calculate all possible valid moves of specific piece on specific
        # position
        
        def raider_moves():
            # 8 possible moves
            possible_moves = [
                    (col+1, row-1),
                    (col+1, row),
                    (col+1, row+1),
                    (col, row-1),
                    (col, row+1),
                    (col-1, row+1),
                    (col-1, row),
                    (col-1, row-1),
                    ]
            initial = Square(col, row)
            if not initial.is_house():
                for possible_move in possible_moves:
                    possible_move_col, possible_move_row = possible_move
                    if Square.in_board_range(possible_move_col, possible_move_row):
                        if self.squares[possible_move_col][possible_move_row].\
                            raider_in_range(piece.color, possible_move_col, \
                                    possible_move_row):
                            if (piece.color == 'white' and row < 3 and \
                                possible_move_row < 3) or (piece.color == 'black' and \
                                             row > 2 and possible_move_row > 2):
                                # diagonal moves
                                if col != possible_move_col and row != possible_move_row:
                                    if self.squares[possible_move_col][possible_move_row].\
                                        isempty_or_rival(piece.color):
                                        if self.is_eligible(possible_move_col, possible_move_row):
                                            # create squares of new move
                                            # initial = Square(col, row)
                                            final_piece = self.squares[possible_move_col]\
                                                [possible_move_row].piece
                                            final = Square(possible_move_col, possible_move_row, \
                                                   final_piece)
                                            # create new move
                                            move = Move(initial, final)
                                    
                                            # check potential checks
                                            if bool:
                                                if not self.in_check(piece, move):
                                                    # append new valid move
                                                    piece.add_move(move)
                                            else:
                                                # append new valid move
                                                piece.add_move(move)
                                    
                                        
                                # non-diagonal
                                else:
                                    if self.squares[possible_move_col][possible_move_row].\
                                        is_empty():
                                        if self.is_eligible(possible_move_col, possible_move_row):
                                            # create squares of new move
                                            # initial = Square(col, row)
                                            final = Square(possible_move_col, possible_move_row)
                                            # create new move
                                            move = Move(initial, final)
                                        
                                            # check potential checks
                                            if bool:
                                                if not self.in_check(piece, move):
                                                    # append new valid move
                                                    piece.add_move(move)
                                            else:
                                                # append new valid move
                                                piece.add_move(move)
                                    
                            elif (piece.color == 'white' and row > 2) or \
                                (piece.color == 'black' and row < 3):
                                # diagonal moves
                                if col != possible_move_col and row != possible_move_row:
                                    if self.squares[possible_move_col][possible_move_row].\
                                        isempty_or_rival(piece.color):
                                        if self.is_eligible(possible_move_col, possible_move_row):
                                            # create squares of new move
                                            # initial = Square(col, row)
                                            final_piece = self.squares[possible_move_col]\
                                                [possible_move_row].piece
                                            final = Square(possible_move_col, possible_move_row, \
                                               final_piece)
                                            # create new move
                                            move = Move(initial, final)
                                
                                            # check potential checks
                                            if bool:
                                                if not self.in_check(piece, move):
                                                    # append new valid move
                                                    piece.add_move(move)
                                            else:
                                                # append new valid move
                                                piece.add_move(move)
                                                
                                                    
                                # non-diagonal
                                else:
                                    if self.squares[possible_move_col][possible_move_row].\
                                        is_empty():
                                        if self.is_eligible(possible_move_col, possible_move_row):
                                            # create squares of new move
                                            # initial = Square(col, row)
                                            final = Square(possible_move_col, possible_move_row)
                                            # create new move
                                            move = Move(initial, final)
                                    
                                            # check potential checks
                                            if bool:
                                                if not self.in_check(piece, move):
                                                    # append new valid move
                                                    piece.add_move(move)
                                            else:
                                                # append new valid move
                                                piece.add_move(move)

                            
        def knight_moves():
            # 8 possible moves
            possible_moves = [
                    (col+1, row-2),
                    (col+2, row-1),
                    (col+2, row+1),
                    (col+1, row+2),
                    (col-1, row+2),
                    (col-2, row+1),
                    (col-2, row-1),
                    (col-1, row-2)
                    ]
            # print(possible_moves)
            for possible_move in possible_moves:
                possible_move_col, possible_move_row = possible_move
                if Square.in_range(possible_move_col, possible_move_row):
                    # print(possible_move_col, possible_move_row)
                    if self.squares[possible_move_col][possible_move_row].\
                        isempty_or_rival(piece.color):
                        # create squares of new move
                        initial = Square(col, row)
                        final_piece = self.squares[possible_move_col]\
                                                [possible_move_row].piece
                        final = Square(possible_move_col, possible_move_row, final_piece)
                        # create new move
                        move = Move(initial, final)
                        
                        # check potential checks
                        if bool:
                            if not self.in_check(piece, move):
                                # append new valid move
                                piece.add_move(move)
                        else:
                            # append new valid move
                            piece.add_move(move)
                    
                        
        def straightline_moves(incrs):
            for incr in incrs:
                col_incr, row_incr = incr
                possible_move_col = col + col_incr
                possible_move_row = row + row_incr
                
                while True:
                    if Square.in_range(possible_move_col, possible_move_row):
                        # create new move
                        initial = Square(col, row)
                        final_piece = self.squares[possible_move_col]\
                                                [possible_move_row].piece
                        final = Square(possible_move_col, possible_move_row, final_piece)
                        # create possible new move
                        move = Move(initial, final)
                        
                        # empty = continue loop
                        if self.squares[possible_move_col][possible_move_row].\
                            is_empty():
                            # check potential checks
                            if bool:
                                if not self.in_check(piece, move):
                                    # append new valid move
                                    piece.add_move(move)
                            else:
                                # append new valid move
                                piece.add_move(move)

                        # has rival piece + add move + break
                        elif self.squares[possible_move_col][possible_move_row].\
                            has_rival_piece(piece.color):
                            # check potential checks
                            if bool:
                                if not self.in_check(piece, move):
                                    # append new valid move
                                    piece.add_move(move)
                            else:
                                # append new valid move
                                piece.add_move(move)
                            
                            break
                        
                        # has team piece + add move + break
                        elif self.squares[possible_move_col][possible_move_row].\
                            has_team_piece(piece.color):
                            # break loop
                            break
                        
                    # not in range
                    else:
                        break
                    
                    # incrementing incrs
                    possible_move_col = possible_move_col + col_incr
                    possible_move_row = possible_move_row + row_incr
                    
        def king_moves():
            adjs = [
                    (col-1, row),
                    (col-1, row+1),
                    (col, row+1),
                    (col+1, row+1),
                    (col+1, row),
                    (col+1, row-1),
                    (col, row-1),
                    (col-1, row-1)
                    ]
            
            for possible_move in adjs:
                possible_move_col, possible_move_row = possible_move
                
                if Square.in_range(possible_move_col, possible_move_row):
                    if self.squares[possible_move_col][possible_move_row].\
                        isempty_or_rival(piece.color):
                        if not self._own_king_house_occupied(piece.color):
                            # create squares of new move
                            initial = Square(col, row)
                            final = Square(possible_move_col, possible_move_row)
                            # create new move
                            move = Move(initial, final)
                            
                            # check potential checks
                            if bool:
                                if not self.in_check(piece, move):
                                    # append new valid move
                                    piece.add_move(move)
                            else:
                                # append new valid move
                                piece.add_move(move)
                                
                        else:
                            if self.squares[col][row].is_card():
                                if self.squares[possible_move_col][possible_move_row].is_card():
                                    # create squares of new move
                                    initial = Square(col, row)
                                    final = Square(possible_move_col, possible_move_row)
                                    # create new move
                                    move = Move(initial, final)
                                    
                                    # check potential checks
                                    if bool:
                                        if not self.in_check(piece, move):
                                            # append new valid move
                                            piece.add_move(move)
                                    else:
                                        # append new valid move
                                        piece.add_move(move)
                            else:
                                self.king_mated = True
                 
                
                            
        if isinstance(piece, Raider):
            raider_moves()
        
        elif isinstance(piece, Knight):
            knight_moves()
        
        elif isinstance(piece, Rook):
            straightline_moves([
                    (-1, 0), # up
                    (0, 1), # left
                    (1, 0), # down
                    (0, -1) # right
                    ])
        
        elif isinstance(piece, Queen):
            straightline_moves([
                    (-1, 1), # up-right
                    (-1, -1), # up-left
                    (1, 1), # down-right
                    (1, -1), # down-left
                    (-1, 0), # up
                    (0, 1), # left
                    (1, 0), # down
                    (0, -1) # right
                    ])

        elif isinstance(piece, Bishop):
            straightline_moves([
                    (-1, 1), # up-right
                    (-1, -1), # up-left
                    (1, 1), # down-right
                    (1, -1), # down-left
                    ])

        elif isinstance(piece, King):
            king_moves()
            

# ╭━━━┳━━━┳━━━┳━━━┳━━━━┳━━━╮
# ┃╭━╮┃╭━╮┃╭━━┫╭━╮┃╭╮╭╮┃╭━━╯
# ┃┃╱╰┫╰━╯┃╰━━┫┃╱┃┣╯┃┃╰┫╰━━╮
# ┃┃╱╭┫╭╮╭┫╭━━┫╰━╯┃╱┃┃╱┃╭━━╯
# ┃╰━╯┃┃┃╰┫╰━━┫╭━╮┃╱┃┃╱┃╰━━╮
# ╰━━━┻╯╰━┻━━━┻╯╱╰╯╱╰╯╱╰━━━╯
    
    def _create(self):
        
        self.players[0] = Player('black')
        self.players[1] = Player('white')
        
        # print(self.squares)
        for row in range(ROWS):
            for col in range(COLS):
                self.squares[col][row] = Square(col, row)
                
        for suit in range(2):
            for rank in range(DECK):
                self.cards[suit][rank] = Card(suit, rank)
                
        for col in range(2):
            for row in range(GRAVES):
                self.graves[col][row] = Grave(col, row)
                
        for btn in CASTBUTTONS:
            self.cast_buttons[btn] = Cast_button(btn)
            
    def _add_cards(self):
        
        for sq in CARDSQS:
            card = Card(TABLE_DICT[(sq[0], sq[1])][1], TABLE_DICT[(sq[0], sq[1])][0])
            self.squares[sq[0]][sq[1]] = Square(sq[0], sq[1], None, card)
     
    def _add_pieces(self, color):
        # back rank, corner to center: bishop, king, knight, rook
        # raiders sit in front of each back-rank piece

        # raiders
        if color == 'white':
            for col in [6, 7, 8, 9]:
                card = self.squares[col][3].card if (col,3) in CARDSQS else None
                self.squares[col][3] = Square(col, 3, Raider(color), card)

        else:
            for col in range(4):
                card = self.squares[col][2].card if (col,2) in CARDSQS else None
                self.squares[col][2] = Square(col, 2, Raider(color), card)

        # rooks
        if color == 'white':
            self.squares[6][4] = Square(6, 4, Rook(color))
        else:
            self.squares[3][1] = Square(3, 1, Rook(color))

        # knights
        if color == 'white':
            card = self.squares[7][4].card
            self.squares[7][4] = Square(7, 4, Knight(color), card)
        else:
            card = self.squares[2][1].card
            self.squares[2][1] = Square(2, 1, Knight(color), card)

        # queen
        # self.squares[row_other][2] = Square(row_other, 2, Queen(color))

        # king
        if color == 'white':
            self.squares[8][4] = Square(8, 4, King(color))
        else:
            card = self.squares[1][1].card
            self.squares[1][1] = Square(1, 1, King(color), card)

        # bishops
        if color == 'white':
            card = self.squares[9][4].card
            self.squares[9][4] = Square(9, 4, Bishop(color), card)
        else:
            card = self.squares[0][1].card
            self.squares[0][1] = Square(0, 1, Bishop(color), card)
            

# ╭━━━┳━━━━┳╮╱╭┳━━━┳━━━╮╭━╮╭━┳━━━┳━━━━┳╮╱╭┳━━━┳━━━┳━━━╮
# ┃╭━╮┃╭╮╭╮┃┃╱┃┃╭━━┫╭━╮┃┃┃╰╯┃┃╭━━┫╭╮╭╮┃┃╱┃┃╭━╮┣╮╭╮┃╭━╮┃
# ┃┃╱┃┣╯┃┃╰┫╰━╯┃╰━━┫╰━╯┃┃╭╮╭╮┃╰━━╋╯┃┃╰┫╰━╯┃┃╱┃┃┃┃┃┃╰━━╮
# ┃┃╱┃┃╱┃┃╱┃╭━╮┃╭━━┫╭╮╭╯┃┃┃┃┃┃╭━━╯╱┃┃╱┃╭━╮┃┃╱┃┃┃┃┃┣━━╮┃
# ┃╰━╯┃╱┃┃╱┃┃╱┃┃╰━━┫┃┃╰╮┃┃┃┃┃┃╰━━╮╱┃┃╱┃┃╱┃┃╰━╯┣╯╰╯┃╰━╯┃
# ╰━━━╯╱╰╯╱╰╯╱╰┻━━━┻╯╰━╯╰╯╰╯╰┻━━━╯╱╰╯╱╰╯╱╰┻━━━┻━━━┻━━━╯
            
    def _raise_raider(self, col, row, color, card):
        if color == 'white':
            for roW in range(GRAVES):
                if self.graves[1][roW].has_piece() and \
                    self.graves[1][roW].piece.name == 'raider':
                    self.graves[1][roW] = Grave(1, roW, None)
                    new_piece = Raider(color)
                    new_piece.idx3 = self._get_current_texture_idx()
                    new_piece.set_texture()
                    new_piece.set_dead_texture()
                    self.squares[col][row] = Square(col, row, new_piece, card)
                    break
                
        else:
            for roW in range(GRAVES):
                if self.graves[0][roW].has_piece() and \
                    self.graves[0][roW].piece.name == 'raider':
                    self.graves[0][roW] = Grave(0, roW, None)
                    new_piece = Raider(color)
                    new_piece.idx3 = self._get_current_texture_idx()
                    new_piece.set_texture()
                    new_piece.set_dead_texture()
                    self.squares[col][row] = Square(col, row, new_piece, card)
                    break
                
    def _raise_queen(self, col, row, color, card):
        if color == 'white':
            for roW in range(GRAVES):
                if self.graves[1][roW].has_piece() and \
                    self.graves[1][roW].piece.name == 'queen':
                    self.graves[1][roW] = Grave(1, roW, None)
                    new_piece = Queen(color)
                    new_piece.idx3 = self._get_current_texture_idx()
                    new_piece.set_texture()
                    new_piece.set_dead_texture()
                    self.squares[col][row] = Square(col, row, new_piece, card)
                    break
                
        else:
            for roW in range(GRAVES):
                if self.graves[0][roW].has_piece() and \
                    self.graves[0][roW].piece.name == 'queen':
                    self.graves[0][roW] = Grave(0, roW, None)
                    new_piece = Queen(color)
                    new_piece.idx3 = self._get_current_texture_idx()
                    new_piece.set_texture()
                    new_piece.set_dead_texture()
                    self.squares[col][row] = Square(col, row, new_piece, card)
                    break
                
    def _queen_isdead(self, color):
        auX = False
        if color == 'white':
            for roW in range(GRAVES):
                if self.graves[1][roW].has_piece() and \
                    self.graves[1][roW].piece.name == 'queen':
                    auX = True
                
        else:
            for roW in range(GRAVES):
                if self.graves[0][roW].has_piece() and \
                    self.graves[0][roW].piece.name == 'queen':
                    auX = True
                    
        return auX
    
    def _enemy_jack_house_occupied(self, color):
        if color == 'white':
            return self.squares[4][0].has_piece()
        else:
            return self.squares[5][5].has_piece()
    
    def _enemy_queen_house_occupied(self, color):
        if color == 'white':
            return self.squares[3][0].has_piece()
        else:
            return self.squares[6][5].has_piece()
            
    def _own_king_house_occupied(self, color):
        if color == 'white':
            return self.squares[7][5].has_piece()
        else:
            return self.squares[2][0].has_piece()
        
    def _opponent_king_on_noncard(self, color):
        # check if opponent's king is on non-card square
        opponent_color = 'black' if color == 'white' else 'white'
        
        for col in range(COLS):
            for row in range(ROWS):
                square = self.squares[col][row]
                if (not square.is_card() and 
                    square.has_team_piece(opponent_color) and 
                    isinstance(square.piece, King)):
                    return True
        return False
                     
    def _send_to_grave(self, piece):
        if piece:
            if piece.color == 'white':
                for row in range(GRAVES):
                    if not self.graves[1][row].has_piece():
                        self.graves[1][row] = Grave(1, row, piece)
                        break
                    
            else:
                for row in range(GRAVES):
                    if not self.graves[0][row].has_piece():
                        self.graves[0][row] = Grave(0, row, piece)
                        break
        else:
            pass
            
            
    def _add_dead_pieces(self, color):
        
        if color == 'white':
            for row in range(GRAVES-4):
                self.graves[1][row] = Grave(1, row, Raider(color))
        else:
            for row in range(4, GRAVES):
                self.graves[0][row] = Grave(0, row, Raider(color))
                
                
        if color == 'white':
            self.graves[1][5] = Grave(1, 5, Queen(color))
        else:
            self.graves[0][3] = Grave(0, 3, Queen(color))
            
    def change_all_piece_textures(self):
        # board pieces
        for row in self.squares:
            for square in row:
                if square.has_piece():
                    square.piece.change_texture()
                    square.piece.set_texture()
                    square.piece.set_dead_texture()
                    
        # graveyard pieces
        for grave_col in range(2):
            for grave_row in range(GRAVES):
                if self.graves[grave_col][grave_row].has_piece():
                    self.graves[grave_col][grave_row].piece.change_texture()
                    
    def _get_current_texture_idx(self):
        # returns the dominant texture index used by existing pieces
        indices = [sq.piece.idx3 for col in self.squares for sq in col if sq.has_piece()]
        return max(set(indices), key=indices.count) if indices else 0
            
    def _sift_cards(self, possible_hand, deck):
        for crD1 in possible_hand:
            for crD2 in possible_hand:
                if crD1 != crD2:
                    for crd in deck:
                        auX = [crD1, crD2]
                        auX.append(crd)
                        
                        if not crd.is_cast() and self.clicker.has_sum_21(auX):
                            possible_hand = [crD1, crD2, crd]
                            return possible_hand
                        
    def _sift_cards2(self, possible_hand, deck):
        for crd in possible_hand:
            for crd1 in deck:
                if not crd1.is_cast():
                    for crd2 in deck:
                        if crd1 != crd2:
                            if not crd2.is_cast():
                                if self.clicker.has_sum_21([crd, crd1, crd2]):
                                    return [crd, crd1, crd2]
                                
        return []
    

# ░██████╗████████╗░█████╗░████████╗███████╗
# ██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝██╔════╝
# ╚█████╗░░░░██║░░░███████║░░░██║░░░█████╗░░
# ░╚═══██╗░░░██║░░░██╔══██║░░░██║░░░██╔══╝░░
# ██████╔╝░░░██║░░░██║░░██║░░░██║░░░███████╗
# ╚═════╝░░░░╚═╝░░░╚═╝░░╚═╝░░░╚═╝░░░╚══════╝

# ███████╗██╗███╗░░██╗░██████╗░███████╗██████╗░██████╗░██████╗░██╗███╗░░██╗████████╗
# ██╔════╝██║████╗░██║██╔════╝░██╔════╝██╔══██╗██╔══██╗██╔══██╗██║████╗░██║╚══██╔══╝
# █████╗░░██║██╔██╗██║██║░░██╗░█████╗░░██████╔╝██████╔╝██████╔╝██║██╔██╗██║░░░██║░░░
# ██╔══╝░░██║██║╚████║██║░░╚██╗██╔══╝░░██╔══██╗██╔═══╝░██╔══██╗██║██║╚████║░░░██║░░░
# ██║░░░░░██║██║░╚███║╚██████╔╝███████╗██║░░██║██║░░░░░██║░░██║██║██║░╚███║░░░██║░░░
# ╚═╝░░░░░╚═╝╚═╝░░╚══╝░╚═════╝░╚══════╝╚═╝░░╚═╝╚═╝░░░░░╚═╝░░╚═╝╚═╝╚═╝░░╚══╝░░░╚═╝░░░



    def _get_comprehensive_state_fingerprint(self, player_color):
        """Create fingerprint that includes ALL cast move dependencies"""
        fingerprint = {}
        
        # 1. Deck card availability
        deck_suit = 1 if player_color == 'white' else 0
        available_cards = []
        for rank in range(DECK):
            if not self.cards[deck_suit][rank].is_cast():
                available_cards.append(rank)
        fingerprint['deck_cards'] = tuple(sorted(available_cards))
        
        # 2. Graveyard contents
        grave_col = 1 if player_color == 'white' else 0
        grave_pieces = []
        for row in range(GRAVES):
            if self.graves[grave_col][row].has_piece():
                piece = self.graves[grave_col][row].piece
                grave_pieces.append((piece.name, row))
        fingerprint['graveyard'] = tuple(sorted(grave_pieces))
        
        # 3. Board card availability (cards with raiders that can be used)
        board_cards = []
        for col in range(COLS):
            for row in range(1, 5):  # Rows where raiders can be on cards
                sq = self.squares[col][row]
                if (sq.has_piece() and sq.piece.name == 'raider' and 
                    sq.piece.color == player_color and sq.is_card()):
                    board_cards.append((sq.card.suit, sq.card.rank))
        fingerprint['board_cards'] = tuple(sorted(board_cards))
        
        # 4. Critical piece positions (for check detection)
        critical_pieces = []
        for col in range(COLS):
            for row in range(ROWS):
                sq = self.squares[col][row]
                if sq.has_piece():
                    # Track kings and pieces that can deliver check
                    if (isinstance(sq.piece, King) or
                        sq.piece.name in ['queen', 'rook', 'bishop']):  # Long-range pieces
                        critical_pieces.append((col, row, sq.piece.name, sq.piece.color))
        fingerprint['critical_pieces'] = tuple(sorted(critical_pieces))
        
        # 5. Enemy piece positions that affect cast move validity
        enemy_threats = []
        for col in range(COLS):
            for row in range(ROWS):
                sq = self.squares[col][row]
                if sq.has_rival_piece(player_color):
                    # Pieces that can threaten cast move destinations
                    if sq.piece.name in ['queen', 'rook', 'raider', 'knight', 'bishop']:
                        enemy_threats.append((col, row, sq.piece.name))
        fingerprint['enemy_threats'] = tuple(sorted(enemy_threats))
        
        return fingerprint
    
    def _get_state_hash(self, player_color):
        """Create a hashable key from the comprehensive state"""
        fingerprint = self._get_comprehensive_state_fingerprint(player_color)
        return hash(tuple(fingerprint.items()))


            
                
