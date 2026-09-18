#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 11 13:14:42 2025

@author: stereo
"""

# ░██████╗░██████╗░░█████╗░██╗░░░██╗███████╗
# ██╔════╝░██╔══██╗██╔══██╗██║░░░██║██╔════╝
# ██║░░██╗░██████╔╝███████║╚██╗░██╔╝█████╗░░
# ██║░░╚██╗██╔══██╗██╔══██║░╚████╔╝░██╔══╝░░
# ╚██████╔╝██║░░██║██║░░██║░░╚██╔╝░░███████╗
# ░╚═════╝░╚═╝░░╚═╝╚═╝░░╚═╝░░░╚═╝░░░╚══════╝

from piece import Piece

class Grave:
    
    def __init__(self, col, row, piece=None):
        self.col = col
        self.row = row
        self.piece = piece
        
    def has_piece(self):
        return self.piece != None
    
    def is_empty(self):
        return not self.has_piece()
    
    

        
    
        