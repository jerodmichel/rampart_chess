#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 14 17:47:11 2025

@author: stereo
"""


# ██████╗░██╗░░░░░░█████╗░██╗░░░██╗███████╗██████╗░
# ██╔══██╗██║░░░░░██╔══██╗╚██╗░██╔╝██╔════╝██╔══██╗
# ██████╔╝██║░░░░░███████║░╚████╔╝░█████╗░░██████╔╝
# ██╔═══╝░██║░░░░░██╔══██║░░╚██╔╝░░██╔══╝░░██╔══██╗
# ██║░░░░░███████╗██║░░██║░░░██║░░░███████╗██║░░██║
# ╚═╝░░░░░╚══════╝╚═╝░░╚═╝░░░╚═╝░░░╚══════╝╚═╝░░╚═╝

class Player:
    
    def __init__(self, color):
        self.color = color
        self.cast_moved = False
        self.cast_moves = []
        
        
        
    def clear_cast_moves(self):
        self.cast_moves = []
        
    def add_cast_move(self, move):
        self.cast_moves.append(move)
        
        
        
class Black(Player):
    
    def __init__(self, color):
        super().__init__('black')
                
class White(Player):
        
    def __init__(self, color):
        super().__init__('white')