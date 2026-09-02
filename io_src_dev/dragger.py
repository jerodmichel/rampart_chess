#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 13 20:17:34 2024

@author: stereo
"""

# ██████╗░██████╗░░█████╗░░██████╗░░██████╗░███████╗██████╗░
# ██╔══██╗██╔══██╗██╔══██╗██╔════╝░██╔════╝░██╔════╝██╔══██╗
# ██║░░██║██████╔╝███████║██║░░██╗░██║░░██╗░█████╗░░██████╔╝
# ██║░░██║██╔══██╗██╔══██║██║░░╚██╗██║░░╚██╗██╔══╝░░██╔══██╗
# ██████╔╝██║░░██║██║░░██║╚██████╔╝╚██████╔╝███████╗██║░░██║
# ╚═════╝░╚═╝░░╚═╝╚═╝░░╚═╝░╚═════╝░░╚═════╝░╚══════╝╚═╝░░╚═╝

import pygame

from const import *

class Dragger:
    
    def __init__(self):
        self.piece = None
        self.dragging = False
        self.mouseX = 0
        self.mouseY = 0
        self.initial_row = 0
        self.initial_col = 0
        
    # blit method
        
    def update_blit(self, surface):
        # texture
        self.piece.set_texture(size=128)
        texture = self.piece.texture
        
        # img
        img = pygame.image.load(texture)
        if img.get_size() != (128, 128):
            img = pygame.transform.scale(img, (128, 128))

        # rect
        img_center = (self.mouseX, self.mouseY)
        self.piece.texture_rect = img.get_rect(center=img_center)
        
        # blit
        surface.blit(img, self.piece.texture_rect)
        
    # other methods
        
    def update_mouse(self, pos):
        self.mouseX, self.mouseY = pos # (x, y)
        
    def save_initial(self, col, row):  # change parameter to take coordinates directly
        self.initial_col = col
        self.initial_row = row
        
    def drag_piece(self, piece):
        self.piece = piece
        self.dragging = True
        
    def undrag_piece(self):
        self.piece = None
        self.dragging = False
        
        