#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 16:59:09 2024

@author: stereo
"""

# ░██████╗░██████╗░██╗░░░██╗░█████╗░██████╗░███████╗
# ██╔════╝██╔═══██╗██║░░░██║██╔══██╗██╔══██╗██╔════╝
# ╚█████╗░██║██╗██║██║░░░██║███████║██████╔╝█████╗░░
# ░╚═══██╗╚██████╔╝██║░░░██║██╔══██║██╔══██╗██╔══╝░░
# ██████╔╝░╚═██╔═╝░╚██████╔╝██║░░██║██║░░██║███████╗
# ╚═════╝░░░░╚═╝░░░░╚═════╝░╚═╝░░╚═╝╚═╝░░╚═╝╚══════╝

from const import *

class Square:

    ALPHAROWS = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g'}
    
    def __init__(self, col, row, piece=None, card=None):
        self.col = col
        self.row = row
        self.piece = piece
        self.card = card
        self.alpharow = self.ALPHAROWS[row]
        
    def __eq__(self, other):
        # print(self.col, self.row, other.col, other.row)
        return self.col == other.col and self.row == other.row
        
    def has_piece(self):
        return self.piece != None
    
    def is_empty(self):
        return not self.has_piece()
    
    def has_team_piece(self, color):
        return self.has_piece() and self.piece.color == color
    
    def has_rival_piece(self, color):
        return self.has_piece() and self.piece.color != color
    
    def isempty_or_rival(self, color):
        return self.is_empty() or self.has_rival_piece(color)
    
    def raider_in_range(self, color, col, row):
        if col < 0 or col > 9:
            return False
        elif color == 'white' and row > 4 or \
            (row < 1 and col not in [2, 3, 4]):
            return False
        elif color == 'black' and row < 1 or \
            (row > 4 and col not in [5, 6, 7]):
            return False
        else:
            return True
        
    def is_house(self):
        if self.row == 0 or self.row == 5:
            return True
        else:
            return False
        
    def is_enemy_jack_house(self, color):
        if (self.col == 4 and self.row == 0 and color == 'white') or \
            (self.col == 5 and self.row == 5 and color == 'black'):
            return True
        
    def is_enemy_queen_house(self, color):
        if (self.col == 3 and self.row == 0 and color == 'white') or \
            (self.col == 6 and self.row == 5 and color == 'black'):
            return True

    def is_enemy_king_house(self, color):
        if (self.col == 2 and self.row == 0 and color == 'white') or \
            (self.col == 7 and self.row == 5 and color == 'black'):
            return True
        
    def is_own_king_house(self, color):
        if (self.col == 2 and self.row == 0 and color == 'black') or \
            (self.col == 7 and self.row == 5 and color == 'white'):
            return True
        
    def is_card(self):
        if (self.col, self.row) in CARDSQS:
            return True
        else:
            return False
            
                
    @staticmethod
    def in_range(col, row):
        if col < 0 or col > 9:
            return False
        elif row < 1 or row > 4:
            return False
            
        return True
    
    @staticmethod
    def in_board_range(col, row):
        if col < 0 or col > 9:
            return False
        elif row < 0 or row > 5:
            return False
            
        return True
    
    @staticmethod
    def get_alpharow(row):
        ALPHAROWS = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g'}
        return ALPHAROWS[row]
    
