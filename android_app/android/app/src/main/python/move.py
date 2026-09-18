#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov 17 11:20:54 2024

@author: stereo
"""

# ███╗░░░███╗░█████╗░██╗░░░██╗███████╗
# ████╗░████║██╔══██╗██║░░░██║██╔════╝
# ██╔████╔██║██║░░██║╚██╗░██╔╝█████╗░░
# ██║╚██╔╝██║██║░░██║░╚████╔╝░██╔══╝░░
# ██║░╚═╝░██║╚█████╔╝░░╚██╔╝░░███████╗
# ╚═╝░░░░░╚═╝░╚════╝░░░░╚═╝░░░╚══════╝

from square import Square
from piece import *

class Move:
    
    def __init__(self, initial, final, piece=None):
        # initial and final are squares
        self.initial = initial
        self.final = final
        self.piece = piece
        
    def __eq__(self, other):
            return self.initial == other.initial and self.final == other.final
        
    def serialize(self):
        return {
            "initial": {"col": self.initial.col, "row": self.initial.row},
            "final": {"col": self.final.col, "row": self.final.row}
        }
    
    def serialize_for_firebase(self):
        # convert to Firebase-compatible dict
        return {
            'initial': {
                'col': self.initial.col,
                'row': self.initial.row,
                'piece': self._serialize_piece(self.piece)
            },
            'final': {
                'col': self.final.col,
                'row': self.final.row
            },
            'player': self.piece.color if self.piece else None,
            'timestamp': {'.sv': 'timestamp'}  # Firebase server timestamp
        }
    
    def _serialize_piece(self, piece):
        if not piece: return None
        return {
            'name': piece.name,
            'color': piece.color,
            'value': abs(piece.value)  # Remove color sign
        }

    @classmethod
    def deserialize_from_firebase(cls, data):
        # reconstruct move from Firebase data
        initial_sq = Square(data['initial']['col'], data['initial']['row'])
        final_sq = Square(data['final']['col'], data['final']['row'])
        
        # Recreate piece (simplified - adjust as needed)
        piece_data = data.get('initial', {}).get('piece')
        if piece_data:
            piece_class = {
                'raider': Raider,
                'knight': Knight,
                'rook': Rook,
                'bishop': Bishop,
                'queen': Queen,
                'king': King
            }[piece_data['name']]
            piece = piece_class(piece_data['color'])
        
        return cls(initial_sq, final_sq, piece)