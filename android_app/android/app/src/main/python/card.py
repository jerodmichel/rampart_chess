#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jan  5 10:50:32 2025

@author: stereo
"""


# ░█████╗░░█████╗░██████╗░██████╗░
# ██╔══██╗██╔══██╗██╔══██╗██╔══██╗
# ██║░░╚═╝███████║██████╔╝██║░░██║
# ██║░░██╗██╔══██║██╔══██╗██║░░██║
# ╚█████╔╝██║░░██║██║░░██║██████╔╝
# ░╚════╝░╚═╝░░╚═╝╚═╝░░╚═╝╚═════╝░

class Card:
    
    def __init__(self, suit, rank, cast=False):
        self.suit = suit
        self.rank = rank
        self.cast = cast
        
    def __eq__(self, other):
        return self.suit == other.suit and self.rank == other.rank
        
    def is_cast(self):
        return self.cast != False
    
    
    
    