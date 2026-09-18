#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  6 16:43:31 2025

@author: stereo
"""

# ░█████╗░░█████╗░░██████╗████████╗███╗░░░███╗░█████╗░██╗░░░██╗███████╗
# ██╔══██╗██╔══██╗██╔════╝╚══██╔══╝████╗░████║██╔══██╗██║░░░██║██╔════╝
# ██║░░╚═╝███████║╚█████╗░░░░██║░░░██╔████╔██║██║░░██║╚██╗░██╔╝█████╗░░
# ██║░░██╗██╔══██║░╚═══██╗░░░██║░░░██║╚██╔╝██║██║░░██║░╚████╔╝░██╔══╝░░
# ╚█████╔╝██║░░██║██████╔╝░░░██║░░░██║░╚═╝░██║╚█████╔╝░░╚██╔╝░░███████╗
# ░╚════╝░╚═╝░░╚═╝╚═════╝░░░░╚═╝░░░╚═╝░░░░░╚═╝░╚════╝░░░░╚═╝░░░╚══════╝

from clicker import *


class Cast_move:
    
    def __init__(self, cards, final, cast_type):
        # initial and final are squares
        self.cards = cards
        self.final = final
        self.cast_type = cast_type
        self.clicker = Clicker()
        
    def __eq__(self, other):
        return self.cast_equiv(self.cards, other.cards) and self.final == other.final \
            and self.cast_type == other.cast_type
                
                
    def cast_equiv(self, hand1, hand2):
        auX1 = []
        auX2 = []
        for card in hand1:
            if card.suit not in [0,1]:
                auX1.append(card)
                
        for card in hand2:
            if card.suit not in [0,1]:
                auX2.append(card)
                
        return len(auX1) == len(auX2) and self.clicker.has_sum_21(hand1) \
                and self.clicker.has_sum_21(hand2)
                
    