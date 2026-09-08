#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 15 20:07:20 2025

@author: stereo
"""

# ░█████╗░██╗░░░░░██╗░█████╗░██╗░░██╗███████╗██████╗░
# ██╔══██╗██║░░░░░██║██╔══██╗██║░██╔╝██╔════╝██╔══██╗
# ██║░░╚═╝██║░░░░░██║██║░░╚═╝█████═╝░█████╗░░██████╔╝
# ██║░░██╗██║░░░░░██║██║░░██╗██╔═██╗░██╔══╝░░██╔══██╗
# ╚█████╔╝███████╗██║╚█████╔╝██║░╚██╗███████╗██║░░██║
# ░╚════╝░╚══════╝╚═╝░╚════╝░╚═╝░░╚═╝╚══════╝╚═╝░░╚═╝

import pygame

from const import *
from card import Card
from grave import Grave

class Clicker:
    
    def __init__(self):
        self.card = None
        self.clicked = False
        self.clicked_cards = []
        self.clicked_btn = None
        self.clicked_grv = None
        self.mouseX = 0
        self.mouseY = 0
        self.initial_suit = None
        self.initial_rank = None

        
    # other methods
        
    def update_mouse(self, pos):
        self.mouseX, self.mouseY = pos # (x, y)
        
    def save_card(self, pos):
        if pos[0] >= 2 and pos[0] <= 2 + CWIDTH:
            self.clicked_suit = 0
            if pos[1] <= 800 - CEM_HEIGHT:
                self.clicked_rank = pos[1] // CHEIGHT
        
        elif pos[0] >= 902 and pos[0] <= 902 + CWIDTH:
            self.clicked_suit = 1
            if pos[1] <= 800 and pos[1] >= CEM_HEIGHT:
                self.clicked_rank = 12 - ((pos[1] - CEM_HEIGHT) // CHEIGHT)
                
    def explic_save_card(self, card):
        self.clicked_suit = card.suit
        self.clicked_rank = card.rank
                
    def explic_save_grv(self, grv):
        self.clicked_col = grv.col
        self.clickded_row = grv.row
        
    def click_btn(self, btn):
        self.clicked_btn = btn
        
    def unclick_btn(self):
        if self.clicked_btn != None:
            self.clicked_btn = None
            
    def click_grv(self, grv):
        self.clicked_grv = grv
            
    def unclick_grv(self):
        if self.clicked_grv != None:
            self.clicked_grv = None
        
    def click_card(self, card):
        self.card = card
        self.clicked = True
        if len(self.clicked_cards) <= 2:
            self.clicked_cards.append(card)
        
    def unclick_card(self, card):
        if len(self.clicked_cards) > 0:
            self.clicked_cards.remove(card)
        else:
            self.card = None
            self.clicked = False

    def unclick_all_cards(self):
        self.clicked_cards = []
        self.card = None
        self.clicked = False


    def has_board_card(self):
        aux = []
        for card in self.clicked_cards:
            aux.append(card.suit)
        
        if 2 in aux or 3 in aux:
            return True
        else:
            return False
        
    def is_clicked(self, card):
        return card in self.clicked_cards
    
    def has_sum_21(self, hand):
        # Create local immutable copy of cards to prevent race conditions
        hand_copy = [(card.rank, card.suit) for card in hand] 
        
        aux = 0
        ace_present = False
        
        for rank, suit in hand_copy:
            val = CARD_VAL[rank]
            aux += val
            if rank == 0:  # Direct Ace check
                ace_present = True
        
        # Debugging that will survive races
        # print(f"Validating hand: {hand_copy}")
        # print(f"Sum: {aux}, Ace: {ace_present}")
        
        return aux == 21 or (aux == 11 and ace_present)
    
    # def has_sum_21(self, hand):
    #     aux = 0
    #     auX = []
    #     for card in hand:
    #         aux += CARD_VAL[card.rank]
    #         auX.append(card.rank)
        
    #     if aux == 21:
    #         return True
    #     elif aux == 11 and 0 in auX:
    #         return True
    #     else:
    #         return False
        
    def has_2_raider_cards(self, hand):
        auX = []
        for card in hand:
            if card.suit not in [0,1]:
                auX.append(card)
                
        return True if len(auX) > 1 else False

            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
    
    