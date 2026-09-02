#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan  1 19:33:56 2025

@author: stereo
"""

# ░█████╗░░█████╗░███╗░░██╗███████╗██╗░██████╗░
# ██╔══██╗██╔══██╗████╗░██║██╔════╝██║██╔════╝░
# ██║░░╚═╝██║░░██║██╔██╗██║█████╗░░██║██║░░██╗░
# ██║░░██╗██║░░██║██║╚████║██╔══╝░░██║██║░░╚██╗
# ╚█████╔╝╚█████╔╝██║░╚███║██║░░░░░██║╚██████╔╝
# ░╚════╝░░╚════╝░╚═╝░░╚══╝╚═╝░░░░░╚═╝░╚═════╝░

import pygame
import os

from sound import Sound
from theme import Theme
from const import *



class Config:
    
    def __init__(self):
        
        pygame.mixer.quit()  # Reset mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        self.themes = []
        self._add_themes()
        self.emblems = []
        self._add_emblems()
        self.dead_cards = []
        self._add_dead_cards()
        # self.texturEs = []
        # self._add_texturEs()
        self.idx = 0
        self.idx1 = 0
        self.idx2 = 0
        self.idx3 = 0
        self.theme = self.themes[self.idx]
        self.emblem = self.emblems[self.idx1]
        self.dead_card = self.dead_cards[self.idx2]
        #self.texturE = self.texturEs[self.idx3]
        
        self.font = pygame.font.SysFont('monospace', 18, bold=True)
        
        self.move_sound = Sound(
                os.path.join('assets/sounds/move.wav'))
        self.capture_sound = Sound(
                os.path.join('assets/sounds/capture.wav'))
        self.card_click_sound = Sound(
                os.path.join('assets/sounds/card_click.mp3'))
        self.strike_sound = Sound(
                os.path.join('assets/sounds/thunder_strike.wav'))
        self.raise_sound = Sound(
                os.path.join('assets/sounds/thunder_raise.mp3'))
        
        # rampart image
        self.rampart_img = pygame.image.load('assets/images/rampart.png').convert_alpha()
        self.rampart_img = pygame.transform.scale(self.rampart_img, (RWIDTH * COLS, RAMPART_HEIGHT))
    
    
    def change_theme(self):
        self.idx += 1
        self.idx %= len(self.themes)
        self.theme = self.themes[self.idx]
    
    
    def _add_themes(self):
        green = Theme((234, 235, 200), (119, 154, 88), (244, 247, 116), \
                      (172, 195, 51), '#C86464', '#C84646')
        brown = Theme((235, 209, 166), (165, 117, 80), (245, 234, 100), \
                      (209, 185, 59), '#C86464', '#C84646')
        blue = Theme((229, 228, 200), (60, 95, 135), (123,187, 227), \
                     (43, 119, 191), '#C86464', '#C84646')
        gray = Theme((120, 119, 118), (86, 85, 84), (99, 126, 143), \
                     (82, 102, 128), '#C86464', '#C84646')
        
        self.themes = [green, brown, blue, gray]
        
    def change_emblem(self):
        self.idx1 += 1
        self.idx1 %= len(self.emblems)
        print(f"Changing emblem to index {self.idx1}, paths: {self.emblems[self.idx1]}")  # debug
        self.emblem = self.emblems[self.idx1]
        print("emblem", self.emblem)
        
    def _add_emblems(self):
        print("Loading emblem paths...")  # debug
        alpha_omega = [r'assets/images/alpha_omega88.png', 'assets/images/alpha_omega88.png']
        
        alpha_omega2 = [r'assets/images/alpha-omega1.png', 'assets/images/alpha-omega1.png']
        
        alpha_omega1 = [r'assets/images/alpha_omega.png', 'assets/images/alpha_omega.png']
        
        alpha_omega3 = [r'assets/images/alpha-omega2.png', 'assets/images/alpha-omega2.png']
        self.emblems = [alpha_omega, alpha_omega2, alpha_omega1, alpha_omega3]
        
    def change_dead_card(self):
        self.idx2 += 1
        self.idx2 %= len(self.dead_cards)
        self.dead_card = self.dead_cards[self.idx2]
        
    def _add_dead_cards(self):
        dead_card1 = r'assets/images/card_back.png'
        dead_card2 = r'assets/images/dead_card0.png'
        dead_card3 = r'assets/images/card_back.png'
        dead_card4 = r'assets/images/dead_card0.png'
        
        self.dead_cards = [dead_card1, dead_card2, dead_card3, dead_card4]
        
    # def change_texturE(self):
    #     self.idx3 += 1
    #     self.idx3 %= len(self.texturEs)
    #     self.texturE = self.texturEs[self.idx3]
        
    # def _add_texturEs(self):
    #     texture1 = [f'assets/images/imgs-{size}px/{self.color}_{self.name}.png', \
    #                 f'assets/images/dead_{self.color}_{self.name}.png']
    #     texture2 = [f'assets/images/new_black_set/{self.color}_{self.name}.png', \
    #                 f'assets/images/new_black_set/dead_{self.color}_{self.name}.png']
            
    #     self.texturEs = [texture1, texture2]
    