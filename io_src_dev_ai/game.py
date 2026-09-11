#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 11 12:05:17 2024

@author: stereo
"""

#  ██████     █████     ██  ██     ███████
#  ██        ██   ██   ██████     ██
#  ██  ███   ███████   ██ ███     █████
#  ██    ██  ██   ██   ██  ██     ██
#  ██████    ██   ██   ██  ██     ███████
#  ┌────┐    ┌───┐    ┌┐┌┌┐    ┌─────┐
#  │ ██ │    │███│    │││││    │ ███ │
#  │ ██ │    │   │    │└┴┘│    │     │
#  └────┘    └───┘    └───┘    └─────┘

import pygame
import json
import os
import re

from const import *
from board import Board
from dragger import Dragger
from clicker import Clicker
from config import Config
from square import Square
from card import Card
from effects import Lightning_effect, Hourglass_effect
from piece import Raider, Knight, Rook, Bishop, Queen, King

from move import Move
from cast_move import Cast_move


class Game:
    
    def __init__(self):
        # ensure Pygame font is available
        if not pygame.font.get_init():
            pygame.font.init()
        # self.turn_lock = threading.Lock()
        self.flipped = False
        self.next_player = 'white'
        self.next_state = None
        self.queen_raid_pending = False
        # self.in_check_flag = False
        self.hovered_sqr = None
        self.hovered_crd = None
        self.hovered_btn = None
        self.hovered_dom = None
        self.hovered_grave = None
        self.white_cast_prompt = ''
        self.black_cast_prompt = ''
        self.lightning = Lightning_effect(self)
        self.hourglass = Hourglass_effect(self)
        self.board = Board(self.flipped)
        self.dragger = Dragger()
        self.clicker = Clicker()
        self.config = Config()
        
        # saving game
        self.save_naming_mode = False
        self.current_save_name = ""
        
        # loading game
        self.load_menu_mode = False
        self.save_files = []
        self.selected_save_idx = 0
        
        # history viewer
        self.view_index = 0 # will be sunced with len(self.move_log)
        
        # ai difficulty
        self.ai_difficulty = "Medium"
        
        # menu action
        self.active_menu = None
        self.show_rules_overlay = False
        self.show_controls_overlay = False
        self.help_scroll_y = 0
        
    def set_player_color(self, color):
        # set the player's color (white or black)
        self.player_color = color
        # to set initial turn based on color:
        self.next_player = color
        
# ╭━━━┳╮╱╭┳━━━┳╮╭╮╭╮╭━━╮╭━━━┳━━━┳╮╭━┳━━━┳━━━┳━━━┳╮╱╭┳━╮╱╭┳━━━╮
# ┃╭━╮┃┃╱┃┃╭━╮┃┃┃┃┃┃┃╭╮┃┃╭━╮┃╭━╮┃┃┃╭┫╭━╮┃╭━╮┃╭━╮┃┃╱┃┃┃╰╮┃┣╮╭╮┃
# ┃╰━━┫╰━╯┃┃╱┃┃┃┃┃┃┃┃╰╯╰┫┃╱┃┃┃╱╰┫╰╯╯┃┃╱╰┫╰━╯┃┃╱┃┃┃╱┃┃╭╮╰╯┃┃┃┃┃
# ╰━━╮┃╭━╮┃┃╱┃┃╰╯╰╯┃┃╭━╮┃╰━╯┃┃╱╭┫╭╮┃┃┃╭━┫╭╮╭┫┃╱┃┃┃╱┃┃┃╰╮┃┃┃┃┃┃
# ┃╰━╯┃┃╱┃┃╰━╯┣╮╭╮╭╯┃╰━╯┃╭━╮┃╰━╯┃┃┃╰┫╰┻━┃┃┃╰┫╰━╯┃╰━╯┃┃╱┃┃┣╯╰╯┃
# ╰━━━┻╯╱╰┻━━━╯╰╯╰╯╱╰━━━┻╯╱╰┻━━━┻╯╰━┻━━━┻╯╰━┻━━━┻━━━┻╯╱╰━┻━━━╯
    
    # show methods
    def show_bg(self, surface):
        theme = self.config.theme
        
        for sq in SQS:
            # get raw board coordinates
            col, row = sq[0], sq[1]
            
            # convert to display coordinates
            if self.flipped:
                display_col = COLS - 1 - col
                display_row = ROWS - 1 - row
            else:
                display_col = col
                display_row = row
            
            # draw squares
            color = theme.bg.dark if sq in CARDSQS else theme.bg.light
            rect = (display_col * RWIDTH + 100, (display_row * RHEIGHT if display_row < 3 else \
                        display_row * RHEIGHT + RAMPART_HEIGHT), RWIDTH-2, RHEIGHT-2)
            pygame.draw.rect(surface, color, rect)
            
        # rampart image between rows 2 and 3
        rampart_y = 3 * RHEIGHT  # position after row 2
        rampart_rect = pygame.Rect(
            100,  # x position (same as board)
            rampart_y,
            RWIDTH * COLS,  # width of entire board
            RAMPART_HEIGHT
        )
        surface.blit(self.config.rampart_img, rampart_rect)
    
        # card table text (fixed positions, doesn't flip)
        font = pygame.font.SysFont("timesnewroman", 24, bold=True)
        for crd in TABLE:
            col, row = crd[0], crd[1]
            if self.flipped:
                display_col = COLS - 1 - col
                display_row = ROWS - 1 - row
            else:
                display_col = col
                display_row = row
            
            text1 = font.render(f'{crd[2]}', True, (255,0,0))
            text2 = font.render(f'{crd[3]}', True, (255,0,0))
            surface.blit(text1, (display_col * RWIDTH + 7 + 100, (display_row * RHEIGHT \
                        if display_row < 3 else display_row * RHEIGHT + RAMPART_HEIGHT)))
            surface.blit(text2, (display_col * RWIDTH + 7 + 100, (display_row * RHEIGHT + 20 \
                        if display_row < 3 else display_row * RHEIGHT + 20 + RAMPART_HEIGHT)))
    
        # decks and graveyards (remain in fixed screen positions)
        for sq in DECK_SQS:
            suit, rank = sq[0], sq[1]
            color = theme.bg.dark if suit == 1 else theme.bg.light
            
            if self.flipped:
                # flip left/right but maintain top/bottom order
                if suit == 0:  # black deck (normally left)
                    x_pos = 908  # moves to right
                    y_pos = (12 - rank) * CHEIGHT + CEM_HEIGHT + RAMPART_HEIGHT
                else:  # white deck (normally right)
                    x_pos = 2    # moves to left
                    y_pos = rank * CHEIGHT + 2
            else:
                if suit == 0:  # black deck left
                    x_pos = 2
                    y_pos = rank * CHEIGHT + 2
                else:  # white deck right
                    x_pos = 908
                    y_pos = (12 - rank) * CHEIGHT + CEM_HEIGHT + RAMPART_HEIGHT
                    
            rect = (x_pos, y_pos, CWIDTH, CHEIGHT - 2)
            pygame.draw.rect(surface, color, rect)
        
        font = pygame.font.SysFont("timesnewroman", 24, bold=True)
    
        # card suit rendering
        for crd in TABLE:
            col, row = crd[0], crd[1]
            display_col = COLS - 1 - col if self.flipped else col
            display_row = ROWS - 1 - row if self.flipped else row
            
            # clear the exact card area
            clear_rect = pygame.Rect(
                display_col * RWIDTH + 100,
                display_row * RHEIGHT if display_row < 3 else display_row * RHEIGHT \
                    + RAMPART_HEIGHT,
                RWIDTH-2,
                RHEIGHT-2
            )
            bg_color = theme.bg.dark if (col, row) in CARDSQS else theme.bg.light
            pygame.draw.rect(surface, bg_color, clear_rect)
    
        # render cards with flip handling
        for crd in TABLE:
            col, row, rank, suit = crd[0], crd[1], crd[2], crd[3]
            
            if not rank and not suit:  # skip empty positions
                continue
                
            # get display position
            if self.flipped:
                display_col = COLS - 1 - col
                display_row = ROWS - 1 - row
                
                # transform suits based on original position
                original_pos = (col, row)
                if original_pos in TABLE_DICT:
                    original_rank, original_suit_idx = TABLE_DICT[original_pos]
                    
                    # only swap between:
                    # - hearts (SUITS[1] = '\u2665') 
                    # - diamonds (SUITS[2] = '\u2666')
                    if original_suit_idx == 3:  # if was heart
                        new_suit_idx = 1        # change to diamond
                    elif original_suit_idx == 2:  # if was diamond
                        new_suit_idx = 2        # change to heart
                    else:
                        new_suit_idx = original_suit_idx  # keep other suits same
                    
                    suit = SUITS[new_suit_idx]
            else:
                display_col = col
                display_row = row
                
            # render
            if rank:
                text_rank = font.render(rank, True, (255, 0, 0))
                surface.blit(text_rank, (display_col * RWIDTH + 7 + 100, (display_row * RHEIGHT if \
                                display_row < 3 else display_row * RHEIGHT + RAMPART_HEIGHT)))
            if suit:
                text_suit = font.render(suit, True, (255, 0, 0))
                surface.blit(text_suit, (display_col * RWIDTH + 7 + 100, (display_row * RHEIGHT + 20 if \
                                display_row < 3 else display_row * RHEIGHT + 20 + RAMPART_HEIGHT)))
    
        # deck text rendering (accounts for flipping)
        font = pygame.font.SysFont("timesnewroman", 24, bold=True)
        for crd in DECK_TABLE:
            suit, rank = crd[0], crd[1]
            
            if self.flipped:
                # flip deck positions
                if suit == 0:  # black deck (normally left)
                    x_pos = 908  # moves to right
                    y_pos = (12 - rank) * CHEIGHT + CEM_HEIGHT + 20
                else:  # white deck (normally right)
                    x_pos = 2    # moves to left
                    y_pos = rank * CHEIGHT + 2
            else:
                if suit == 0:  # black deck left
                    x_pos = 2
                    y_pos = rank * CHEIGHT + 2
                else:  # white deck right
                    x_pos = 908
                    y_pos = (12 - rank) * CHEIGHT + CEM_HEIGHT + 20
            
            text1 = font.render(f'{crd[2]}', True, (0, 0, 0))
            text2 = font.render(f'{crd[3]}', True, (0, 0, 0))
            
            if suit == 0:  # black deck
                surface.blit(text1, (x_pos + 5, y_pos))
                surface.blit(text2, (x_pos + 30, y_pos))
            else:  # white deck
                surface.blit(text1, (x_pos + 42, y_pos))
                surface.blit(text2, (x_pos + 67, y_pos))
                
        # row letters (vertical labels)
        if not self.flipped:
            # label first column (left edge) when not flipped
            for row in range(ROWS):
                # determine color based on original square
                color = theme.bg.dark if (row == 5 or row % 2 == 0) else theme.bg.light
                
                # get label text (A-F)
                label_text = Square.get_alpharow(ROWS - row - 1)
                
                # position on left edge
                lbl = self.config.font.render(label_text, 1, color)
                surface.blit(lbl, (5 + 100, (row * RHEIGHT + RHEIGHT - 25 if row < 3 else \
                                row * RHEIGHT + RHEIGHT - 25 + RAMPART_HEIGHT)))
        else:
            # label last column (right edge) when flipped
            for row in range(ROWS):
                # get flipped row position
                display_row = ROWS - 1 - row
                
                # determine color based on original square (column 0)
                color = theme.bg.dark if (row == 5 or row % 2 == 0) else theme.bg.light
                
                # get label text (A-F)
                label_text = Square.get_alpharow(ROWS - row - 1)
                
                # position on right edge
                lbl = self.config.font.render(label_text, 1, color)
                surface.blit(lbl, ((COLS-1)*RWIDTH + RWIDTH - 25 + 100, 
                                  (display_row * RHEIGHT + RHEIGHT - 25 if display_row < 3 else \
                                   display_row * RHEIGHT + RHEIGHT - 25 + RAMPART_HEIGHT)))
      
        # column numbers (horizontal labels)
        if not self.flipped:
            # label bottom row when not flipped
            for col in range(COLS):
                # determine color
                ref_sq = (col, ROWS-1)  # bottom row squares
                color = theme.bg.light if ref_sq in CARDSQS else theme.bg.dark
                
                # get label text (1-10)
                label_text = str(col + 1)
                
                # position on bottom
                lbl = self.config.font.render(label_text, 1, color)
                surface.blit(lbl, (col * RWIDTH + RWIDTH - 25 + 100, \
                                   (HEIGHT - 25 + RAMPART_HEIGHT)))
                
        else:
            # label top row when flipped
            for col in range(COLS):
                # get flipped column position
                display_col = COLS - 1 - col
                
                # determine color (using original bottom row squares)
                ref_sq = (col, ROWS-1)  # Original bottom row
                color = theme.bg.light if ref_sq in CARDSQS else theme.bg.dark
                
                # get label text (1-10)
                label_text = str(col + 1)
                
                # position on top
                lbl = self.config.font.render(label_text, 1, color)
                surface.blit(lbl, (display_col * RWIDTH + RWIDTH - 25 + 100, 5))

        # graveyards (flip sides when board is flipped)
        for grv in GRAVEYARD:
            grave_col, grave_row = grv[0], grv[1]
            color = (0, 0, 0)
            
            if self.flipped:
                if grave_col == 0:  # black graveyard (normally left)
                    x_pos = 908  # moves to right
                    y_pos = (8 - grave_row) * GHEIGHT + 90
                else:  # white graveyard (normally right)
                    x_pos = 2    # moves to left
                    y_pos = grave_row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) + RAMPART_HEIGHT
            else:
                if grave_col == 0:  # black graveyard left
                    x_pos = 2
                    y_pos = grave_row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) + RAMPART_HEIGHT
                else:  # white graveyard right
                    x_pos = 908
                    y_pos = (8 - grave_row) * GHEIGHT + 90
                    
            rect = (x_pos, y_pos, GWIDTH, GHEIGHT - 2)
            pygame.draw.rect(surface, color, rect)

# ╭━━━┳╮╱╭┳━━━┳╮╭╮╭╮╭━╮╭━┳━━━┳━━━━┳━━━┳━━━┳━━┳━━━┳╮╱╱╭━━━╮
# ┃╭━╮┃┃╱┃┃╭━╮┃┃┃┃┃┃┃┃╰╯┃┃╭━╮┃╭╮╭╮┃╭━━┫╭━╮┣┫┣┫╭━╮┃┃╱╱┃╭━╮┃
# ┃╰━━┫╰━╯┃┃╱┃┃┃┃┃┃┃┃╭╮╭╮┃┃╱┃┣╯┃┃╰┫╰━━┫╰━╯┃┃┃┃┃╱┃┃┃╱╱┃╰━━╮
# ╰━━╮┃╭━╮┃┃╱┃┃╰╯╰╯┃┃┃┃┃┃┃╰━╯┃╱┃┃╱┃╭━━┫╭╮╭╯┃┃┃╰━╯┃┃╱╭╋━━╮┃
# ┃╰━╯┃┃╱┃┃╰━╯┣╮╭╮╭╯┃┃┃┃┃┃╭━╮┃╱┃┃╱┃╰━━┫┃┃╰┳┫┣┫╭━╮┃╰━╯┃╰━╯┃
# ╰━━━┻╯╱╰┻━━━╯╰╯╰╯╱╰╯╰╯╰┻╯╱╰╯╱╰╯╱╰━━━┻╯╰━┻━━┻╯╱╰┻━━━┻━━━╯
    
    def _get_check_halo(self, size=104):
        # soft red radial-gradient glow, drawn behind an in-check king so it
        # peeks out around the piece's (transparent-background) silhouette -
        # built once per size and cached, since a per-pixel gradient isn't
        # something to redo every frame.
        halo = getattr(self, '_check_halo_cache', {}).get(size)
        if halo is not None:
            return halo
        halo = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size / 2
        max_r = size / 2
        max_alpha = 140
        for y in range(size):
            for x in range(size):
                dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if dist <= max_r:
                    alpha = max_alpha * (1 - dist / max_r) ** 1.4
                    halo.set_at((x, y), (220, 30, 30, int(alpha)))
        if not hasattr(self, '_check_halo_cache'):
            self._check_halo_cache = {}
        self._check_halo_cache[size] = halo
        return halo

    def show_pieces(self, surface):
        for col in range(COLS):
            for row in range(ROWS):
                if self.board.squares[col][row].has_piece():
                    piece = self.board.squares[col][row].piece
                    if piece is not self.dragger.piece:
                        # get display position
                        disp_col, disp_row = self.get_screen_position(col, row)
                        piece.set_texture(size=80)
                        img = pygame.image.load(piece.texture)
                        if img.get_size() != (80, 80):
                            img = pygame.transform.scale(img, (80, 80))
                        img_center = disp_col * RWIDTH + RWIDTH // 2 + 100, \
                                    (disp_row * RHEIGHT + RHEIGHT // 2 if disp_row < 3 \
                                     else disp_row * RHEIGHT + RHEIGHT // 2 + RAMPART_HEIGHT)
                        piece.texture_rect = img.get_rect(center=img_center)

                        if piece.name == 'king' and \
                            ((piece.color == 'white' and self.white_cast_prompt == 'in-check') or
                             (piece.color == 'black' and self.black_cast_prompt == 'in-check')):
                            halo = self._get_check_halo()
                            surface.blit(halo, halo.get_rect(center=img_center))

                        surface.blit(img, piece.texture_rect)
                    
    def show_dead(self, surface):
        for grv in GRAVEYARD:
            if self.board.graves[grv[0]][grv[1]].has_piece():
                piece = self.board.graves[grv[0]][grv[1]].piece
                piece.set_dead_texture()
                img = pygame.image.load(piece.dead_texture)
                img = pygame.transform.scale(img, (35, 35))
                
                # determine visual position based on flip state
                if self.flipped:
                    # swap grave positions visually but keep ownership
                    visual_grave_col = 1 - grv[0]  # flips 0→1 and 1→0
                    if visual_grave_col == 0:  # visually left (black's original graves)
                        x_pos = GWIDTH // 2 + 2
                        y_pos = grv[1] * GHEIGHT + GHEIGHT // 2 + (HEIGHT - CEM_HEIGHT + 65) \
                            + RAMPART_HEIGHT
                    else:  # visually right (white's original graves)
                        x_pos = GWIDTH // 2 + 908
                        y_pos = grv[1] * GHEIGHT + GHEIGHT // 2 + 90
                else:
                    # normal positions
                    if grv[0] == 0:  # black graves (left)
                        x_pos = GWIDTH // 2 + 2
                        y_pos = grv[1] * GHEIGHT + GHEIGHT // 2 + (HEIGHT - CEM_HEIGHT + 65) \
                            + RAMPART_HEIGHT
                    else:  # white graves (right)
                        x_pos = GWIDTH // 2 + 908
                        y_pos = grv[1] * GHEIGHT + GHEIGHT // 2 + 90
                
                # render the piece
                piece.texture_rect = img.get_rect(center=(x_pos, y_pos))
                surface.blit(img, piece.texture_rect)
                
    def show_dead_cards(self, surface):
        for sq in DECK_SQS:
            if self.board.cards[sq[0]][sq[1]].is_cast():
                img0 = pygame.image.load(self.config.dead_card)
                img0 = pygame.transform.scale(img0, (CWIDTH, CHEIGHT - 1))
                
                # determine visual position based on flip
                if self.flipped:
                    visual_suit = 1 - sq[0]  # flip suit for display only
                    if visual_suit == 0:  # visually left (originally right)
                        x_pos = 2
                        y_pos = sq[1] * CHEIGHT
                    else:  # visually right (originally left)
                        x_pos = 908
                        y_pos = (12 - sq[1]) * CHEIGHT + CEM_HEIGHT + RAMPART_HEIGHT
                else:
                    if sq[0] == 0:  # black deck (left)
                        x_pos = 2
                        y_pos = sq[1] * CHEIGHT
                    else:  # white deck (right)
                        x_pos = 908
                        y_pos = (12 - sq[1]) * CHEIGHT + CEM_HEIGHT + RAMPART_HEIGHT
                
                surface.blit(img0, (x_pos, y_pos))
                    
    
    def show_clicked_cards(self, surface):
        if self.clicker.clicked:
            for card in self.clicker.clicked_cards:
                color = (100, 216, 220)
                if not card.is_cast():
                    # handle deck cards
                    if card.suit in [0, 1]:  # black (0) or White (1) deck cards
                        if self.flipped:
                            # flip deck positions but keep card ownership
                            if card.suit == 1:  # white deck
                                x_pos = 2
                                y_pos = card.rank * CHEIGHT+2
                            else:  # black deck
                                x_pos = 908
                                y_pos = (12 - card.rank) * CHEIGHT + CEM_HEIGHT \
                                    + RAMPART_HEIGHT
                        else:
                            # normal deck positions
                            if card.suit == 1:  # white deck (right)
                                x_pos = 908
                                y_pos = (12 - card.rank) * CHEIGHT + CEM_HEIGHT \
                                    + RAMPART_HEIGHT
                            else:  # black deck (left)
                                x_pos = 2
                                y_pos = card.rank * CHEIGHT+2
                        
                        rect = (x_pos, y_pos, CWIDTH, CHEIGHT - 1)
                    
                    # handle board cards
                    else:
                        col = REV_TAB_DICT[(card.rank, card.suit)][0]
                        row = REV_TAB_DICT[(card.rank, card.suit)][1]
                        # convert board position to display coordinates
                        disp_col, disp_row = self.get_screen_position(col, row)
                        rect = (
                            disp_col * RWIDTH + 100, 
                            disp_row * RHEIGHT if disp_row < 3 else disp_row * RHEIGHT \
                                + RAMPART_HEIGHT,
                            RWIDTH-2, 
                            RHEIGHT-2
                        )
                    
                    pygame.draw.rect(surface, color, rect, width=2)
                    
    def show_cemetery(self, surface):
        try:
            img0 = pygame.image.load(self.config.emblem[0])
            img0 = pygame.transform.scale(img0, (80, 80))
            surface.blit(img0, (5, 715 + RAMPART_HEIGHT))
            img1 = pygame.image.load(self.config.emblem[1])
            img1 = pygame.transform.scale(img1, (80, 80))
            surface.blit(img1, (908, 2))
        except Exception as e:
            print(f"Error loading emblems: {e}")
            print(f"Attempted paths: {self.config.emblem}")
        
        
    def show_cast_buttons(self, surface):
        font = pygame.font.Font("assets/fonts/cinzel/Cinzel-SemiBold.ttf", 24)
        
        for btn in CASTBUTTONS:
            # color
            color =  (40, 40, 40)# self.config.theme.bg.dark
            #rect
            rect = (102, 802 + RAMPART_HEIGHT, 100, 35) if btn == 0 else \
                (205, 802 + RAMPART_HEIGHT, 83, 35)
            # blit
            pygame.draw.rect(surface, color, rect)
            
        for btn in CASTBUTTONS:
            
            text1 = font.render('STRIKE',True,
                            (255, 255, 255))
            text2 = font.render('RAISE',True, 
                            (255, 255, 255))
            if btn == 0:
                surface.blit(text1,(108, 805 + RAMPART_HEIGHT))
            else:
                surface.blit(text2,(210, 805 + RAMPART_HEIGHT))
                
    def show_clicked_btns(self, surface):
        # color
        color = (159, 43, 104)
        # rect
        if self.clicker.clicked_btn == 0:
            rect = (102, 802 + RAMPART_HEIGHT, 100, 35) 
            pygame.draw.rect(surface, color, rect, width=2)
        elif self.clicker.clicked_btn == 1:
            rect = (205, 802 + RAMPART_HEIGHT, 83, 35)
            pygame.draw.rect(surface, color, rect, width=2)
            
    
    def show_chosen_piece(self, surface):
        if self.clicker.clicked_grv:
            color = (100, 216, 220)
            grv = self.clicker.clicked_grv
            
            # calculate visual position accounting for flip
            if self.flipped:
                visual_col = 1 - grv.col  # flip the column
                if visual_col == 0:  # visually left (originally right)
                    x_pos = 2
                    y_pos = grv.row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) \
                        + RAMPART_HEIGHT
                else:  # visually right (originally left)
                    x_pos = 908
                    y_pos = grv.row * GHEIGHT + 90
            else:
                if grv.col == 0:  # left (black)
                    x_pos = 2
                    y_pos = grv.row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) \
                        + RAMPART_HEIGHT
                else:  # right (white)
                    x_pos = 908
                    y_pos = grv.row * GHEIGHT + 90
            
            rect = (x_pos, y_pos, GWIDTH - 1, GHEIGHT - 1)
            pygame.draw.rect(surface, color, rect, width=2)
        
                    
    def show_moves(self, surface):
        theme = self.config.theme
        
        if self.dragger.dragging:
            piece = self.dragger.piece
            for move in piece.moves:
                # get display coordinates (account for flipping)
                disp_col, disp_row = self.get_screen_position(move.final.col, move.final.row)
                
                # color
                color = theme.moves.light if (move.final.col, move.final.row) in CARDSQS else theme.moves.dark
                
                # rect (using display coordinates)
                rect = (
                    disp_col * RWIDTH + 100,  # +100 offset for board positioning
                    disp_row * RHEIGHT if disp_row < 3 else disp_row * RHEIGHT + RAMPART_HEIGHT,
                    RWIDTH-2, 
                    RHEIGHT-2
                )
                
                # blit
                pygame.draw.rect(surface, color, rect)
    
    def show_last_move(self, surface):
        theme = self.config.theme
        
        if self.board.last_move:
            if isinstance(self.board.last_move, Move):
                initial = self.board.last_move.initial
                final = self.board.last_move.final
                for pos in [initial, final]:
                    # convert to display coordinates
                    disp_col, disp_row = self.get_screen_position(pos.col, pos.row)
                    # color
                    color = theme.trace.light if (pos.col, pos.row) in CARDSQS else \
                        theme.trace.dark
                    # rect
                    rect = (
                        disp_col * RWIDTH + 100, 
                        disp_row * RHEIGHT if disp_row < 3 else \
                            disp_row * RHEIGHT + RAMPART_HEIGHT, 
                        RWIDTH - 2, 
                        RHEIGHT - 2
                    )
                    # blit
                    pygame.draw.rect(surface, color, rect, width=5)
                    
            elif isinstance(self.board.last_move, Cast_move):
                final = self.board.last_move.final
                # convert to display coordinates
                disp_col, disp_row = self.get_screen_position(final.col, final.row)
                # color
                color = theme.trace.light if (final.col, final.row) in CARDSQS else \
                    theme.trace.dark
                # rect
                rect = (
                    disp_col * RWIDTH + 100, 
                    disp_row * RHEIGHT if disp_row < 3 else disp_row * RHEIGHT \
                        + RAMPART_HEIGHT, 
                    RWIDTH - 2, 
                    RHEIGHT - 2
                )
                # blit
                pygame.draw.rect(surface, color, rect, width=5)
                
# ╭━━━┳╮╱╭┳━━━┳╮╭╮╭╮╭╮╱╭┳━━━┳╮╱╱╭┳━━━┳━━━┳━━━╮
# ┃╭━╮┃┃╱┃┃╭━╮┃┃┃┃┃┃┃┃╱┃┃╭━╮┃╰╮╭╯┃╭━━┫╭━╮┃╭━╮┃
# ┃╰━━┫╰━╯┃┃╱┃┃┃┃┃┃┃┃╰━╯┃┃╱┃┣╮┃┃╭┫╰━━┫╰━╯┃╰━━╮
# ╰━━╮┃╭━╮┃┃╱┃┃╰╯╰╯┃┃╭━╮┃┃╱┃┃┃╰╯┃┃╭━━┫╭╮╭┻━━╮┃
# ┃╰━╯┃┃╱┃┃╰━╯┣╮╭╮╭╯┃┃╱┃┃╰━╯┃╰╮╭╯┃╰━━┫┃┃╰┫╰━╯┃
# ╰━━━┻╯╱╰┻━━━╯╰╯╰╯╱╰╯╱╰┻━━━╯╱╰╯╱╰━━━┻╯╰━┻━━━╯
                
                
    def show_hover(self, surface):
        if self.hovered_sqr:
            # color
            color = (180, 180, 180)
            # rect
            rect = (self.hovered_sqr.col * RWIDTH + 100, self.hovered_sqr.row * RHEIGHT \
                    if self.hovered_sqr.row < 3 else self.hovered_sqr.row * RHEIGHT \
                    + RAMPART_HEIGHT, RWIDTH - 2, RHEIGHT - 2)
            # blit
            pygame.draw.rect(surface, color, rect, width=3)
            
        if self.hovered_crd:
            # color
            color = (173, 216, 230)
            # rect
            if self.hovered_crd.suit == 1:
                rect = (self.hovered_crd.suit * 908, (12 - self.hovered_crd.rank) * CHEIGHT \
                    + CEM_HEIGHT + RAMPART_HEIGHT, CWIDTH, CHEIGHT - 1)
            else:
                rect = (self.hovered_crd.suit, self.hovered_crd.rank * CHEIGHT, \
                    CWIDTH + 2, CHEIGHT + 1)
            pygame.draw.rect(surface, color, rect, width=2)
            
        if self.hovered_btn:
            # color
            color = (173, 216, 230)
            # rect
            rect = (102, 802 + RAMPART_HEIGHT, 100, 35) if self.hovered_btn.categ == 0 \
                else (205, 802 + RAMPART_HEIGHT, 83, 35)
                
            pygame.draw.rect(surface, color, rect, width=2)
            
        if self.hovered_dom:
            # convert to display coordinates
            disp_col, disp_row = self.get_screen_position(
                self.hovered_dom.col, 
                self.hovered_dom.row
            )
            
            color = (159, 43, 104)
            rect = (
                disp_col * RWIDTH + 100,
                disp_row * RHEIGHT if disp_row < 3 else disp_row * RHEIGHT + RAMPART_HEIGHT,
                RWIDTH - 2,
                RHEIGHT - 2
            )
            pygame.draw.rect(surface, color, rect, width=3)
            
        if self.hovered_grave:
            # color
            color = (159, 43, 104)
            
            # calculate visual position to account for flipping
            if self.flipped:
                # flip column but keep row and vertical offsets
                visual_col = 1 - self.hovered_grave.col
                if visual_col == 0:  # visually left (originally right)
                    x_pos = 2  # left edge
                    y_pos = self.hovered_grave.row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) \
                        + RAMPART_HEIGHT
                else:  # visually right (originally left)
                    x_pos = 908  # right edge
                    y_pos = self.hovered_grave.row * GHEIGHT + 90
            else:
                # original positions
                if self.hovered_grave.col == 0:  # left (black)
                    x_pos = 2
                    y_pos = self.hovered_grave.row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) \
                        + RAMPART_HEIGHT
                else:  # right (white)
                    x_pos = 908
                    y_pos = self.hovered_grave.row * GHEIGHT + 90
            
            # create rectangle (keeping original dimensions)
            rect = (x_pos, y_pos, GWIDTH - 1, GHEIGHT - 1)
            
            # draw highlight
            pygame.draw.rect(surface, color, rect, width=2)
                        

# ░█████╗░████████╗██╗░░██╗███████╗██████╗░
# ██╔══██╗╚══██╔══╝██║░░██║██╔════╝██╔══██╗
# ██║░░██║░░░██║░░░███████║█████╗░░██████╔╝
# ██║░░██║░░░██║░░░██╔══██║██╔══╝░░██╔══██╗
# ╚█████╔╝░░░██║░░░██║░░██║███████╗██║░░██║
# ░╚════╝░░░░╚═╝░░░╚═╝░░╚═╝╚══════╝╚═╝░░╚═╝

# ███╗░░░███╗███████╗████████╗██╗░░██╗░█████╗░██████╗░░██████╗
# ████╗░████║██╔════╝╚══██╔══╝██║░░██║██╔══██╗██╔══██╗██╔════╝
# ██╔████╔██║█████╗░░░░░██║░░░███████║██║░░██║██║░░██║╚█████╗░
# ██║╚██╔╝██║██╔══╝░░░░░██║░░░██╔══██║██║░░██║██║░░██║░╚═══██╗
# ██║░╚═╝░██║███████╗░░░██║░░░██║░░██║╚█████╔╝██████╔╝██████╔╝
# ╚═╝░░░░░╚═╝╚══════╝░░░╚═╝░░░╚═╝░░╚═╝░╚════╝░╚═════╝░╚═════╝░

    
    def cast_cards(self):
        for card in self.clicker.clicked_cards:
            if card.suit in [0, 1]:
                suit, rank = card.suit, card.rank
                self.board.cards[suit][rank] = Card(suit, rank, True)
                
        self.clicker.clicked_cards = []

# ╭━━━┳━━━┳━━━┳━╮╭━┳━━━┳━━━━┳━━━╮
# ┃╭━╮┃╭━╮┃╭━╮┃┃╰╯┃┃╭━╮┃╭╮╭╮┃╭━╮┃
# ┃╰━╯┃╰━╯┃┃╱┃┃╭╮╭╮┃╰━╯┣╯┃┃╰┫╰━━╮
# ┃╭━━┫╭╮╭┫┃╱┃┃┃┃┃┃┃╭━━╯╱┃┃╱╰━━╮┃
# ┃┃╱╱┃┃┃╰┫╰━╯┃┃┃┃┃┃┃╱╱╱╱┃┃╱┃╰━╯┃
# ╰╯╱╱╰╯╰━┻━━━┻╯╰╯╰┻╯╱╱╱╱╰╯╱╰━━━╯
            
    def show_cast_prompt(self, surface, color):
        font = pygame.font.SysFont("timesnewroman", 24, bold=True)
        if self.hourglass.active:
            # driven off the hourglass itself (not a cast-prompt state) so the
            # real prompt underneath is left untouched and simply reappears
            # once the AI's move is applied and the hourglass stops.
            dot_count = (self.hourglass.frame // 20) % 4
            text = font.render('Thinking' + '.' * dot_count, True, (255, 255, 255))
            surface.blit(text, (320, 805 + RAMPART_HEIGHT))
            full_width = font.render('Thinking...   ', True, (255, 255, 255)).get_width()
            icon_center = (320 + full_width + 18,
                           805 + RAMPART_HEIGHT + text.get_height() // 2)
            self.hourglass.draw(surface, center=icon_center, size=9)
            return
        if color == 'white' and self.white_cast_prompt:
            if self.white_cast_prompt == 'cast':
                text = font.render('To begin casting, click on a card in your deck.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'strike':
                text = font.render('Choose a raider to send to the grave.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'raise':
                text = font.render('Choose a tile where you want to place a raider.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'raiseq':
                text = font.render('Choose a tile where you want to place the queen.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'choosegrv':
                text = font.render('Choose a peice from the cemetery to raise.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'no-raise':
                text = font.render('No eligible square to raise on.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'no-strike':
                text = font.render('No eligible raider to strike.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'strike-needs-2-board':
                text = font.render('Striking requires two board cards.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'make21':
                text = font.render('Choose cards from your deck and from the board that sum to 21.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'choosecast':
                text = font.render('Click one of the "strike" or "raise" buttons.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'in-check':
                text = font.render("White's king is in check -- ",True,(255, 0, 0))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt[1] == 'mated':
                	font = pygame.font.SysFont("timesnewroman", 24, bold=True)
                	text1 = font.render('White mated Black',True,(255, 255, 255)) if self.white_cast_prompt[0] \
                        == 'black' else font.render('Black mated White',True,(255, 255, 255))
                	surface.blit(text1,(320, 805 + RAMPART_HEIGHT))
                	text2 = font.render('-- Press "r" key to start new game.',True,(255, 255, 255))
                	surface.blit(text2,(540, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt[1] == 'stale-mated':
                	font = pygame.font.SysFont("timesnewroman", 24, bold=True)
                	text1 = font.render('Black stalemated',True,(255, 255, 255)) if self.white_cast_prompt[0] \
                        == 'black' else font.render('White stalemated',True,(255, 255, 255))
                	surface.blit(text1,(320, 805 + RAMPART_HEIGHT))
                	text2 = font.render('-- Press "r" key to start new game.',True,(255, 255, 255))
                	surface.blit(text2,(540, 805 + RAMPART_HEIGHT))
            elif isinstance(self.white_cast_prompt, list) and self.white_cast_prompt[1] == 'repetition':
                text1 = font.render('Draw by repetition', True, (255, 255, 255))
                surface.blit(text1, (320, 805 + RAMPART_HEIGHT))
                text2 = font.render('-- Press "r" key to start new game.', True, (255, 255, 255))
                surface.blit(text2, (540, 805 + RAMPART_HEIGHT))
            elif isinstance(self.white_cast_prompt, list) and self.white_cast_prompt[1] == 'insufficient-material':
                text1 = font.render('Draw by insufficient material', True, (255, 255, 255))
                surface.blit(text1, (320, 805 + RAMPART_HEIGHT))
                text2 = font.render('-- Press "r" key to start new game.', True, (255, 255, 255))
                surface.blit(text2, (320 + text1.get_width() + 10, 805 + RAMPART_HEIGHT))

        if color == 'black' and self.black_cast_prompt:
            if self.black_cast_prompt == 'cast':
                text = font.render('To begin casting, click on a card in your deck.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'strike':
                text = font.render('Choose a raider to send to the grave.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'raise':
                text = font.render('Choose a tile where you want to place a raider.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'raiseq':
                text = font.render('Choose a tile where you want to place the queen.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'choosegrv':
                text = font.render('Choose a peice from the cemetery to raise.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'no-raise':
                text = font.render('No eligible square to raise on.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'no-strike':
                text = font.render('No eligible raider to strike.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'strike-needs-2-board':
                text = font.render('Striking requires two board cards.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'make21':
                text = font.render('Choose cards from your deck and from the board that sum to 21.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'choosecast':
                text = font.render('Click one of the "strike" or "raise" buttons.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'in-check':
                text = font.render("Black's king is in check -- ",True,(255, 0, 0))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt[1] == 'mated':
               	font = pygame.font.SysFont("timesnewroman", 24, bold=True)
               	text1 = font.render('White mated Black',True,(255, 255, 255)) if self.black_cast_prompt[0] \
                        == 'black' else font.render('Black mated White',True,(255, 255, 255))
               	surface.blit(text1,(320, 805 + RAMPART_HEIGHT))
               	text2 = font.render('-- Press "r" key to start new game.',True,(255, 255, 255))
               	surface.blit(text2,(540, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt[1] == 'stale-mated':
               	font = pygame.font.SysFont("timesnewroman", 24, bold=True)
               	text1 = font.render('Black stalemated',True,(255, 255, 255)) if self.black_cast_prompt[0] \
                        == 'black' else font.render('White stalemated',True,(255, 255, 255))
               	surface.blit(text1,(320, 805 + RAMPART_HEIGHT))
               	text2 = font.render('-- Press "r" key to start new game.',True,(255, 255, 255))
               	surface.blit(text2,(540, 805 + RAMPART_HEIGHT))
            elif isinstance(self.black_cast_prompt, list) and self.black_cast_prompt[1] == 'repetition':
                text1 = font.render('Draw by repetition', True, (255, 255, 255))
                surface.blit(text1, (320, 805 + RAMPART_HEIGHT))
                text2 = font.render('-- Press "r" key to start new game.', True, (255, 255, 255))
                surface.blit(text2, (540, 805 + RAMPART_HEIGHT))
            elif isinstance(self.black_cast_prompt, list) and self.black_cast_prompt[1] == 'insufficient-material':
                text1 = font.render('Draw by insufficient material', True, (255, 255, 255))
                surface.blit(text1, (320, 805 + RAMPART_HEIGHT))
                text2 = font.render('-- Press "r" key to start new game.', True, (255, 255, 255))
                surface.blit(text2, (320 + text1.get_width() + 10, 805 + RAMPART_HEIGHT))

    def next_turn(self):
        # with self.turn_lock:  # thread safety
        if not self.queen_raid_pending:
            if self.board.is_draw_by_insufficient_material() or \
                    self.board.is_draw_by_locked_material():
                self.board.king_stalemated = True
                self.set_insufficient_material_prompt()
                return

            if self.next_player == 'white':
                self.next_player = 'black'
            else:
                self.next_player = 'white'

            self.next_state = 'update1'
                
    def change_state(self):
        if self.next_state == 'update1':
            self.next_state = 'update2'
            self.lightning.active = False
            self.lightning.persist_frames = 0
            self.next_state = None
    
    def flip_board(self):
        self.flipped = not self.flipped
        
    def get_screen_position(self, col, row):
        if self.flipped:
            return (COLS - 1 - col, ROWS - 1 - row)
        return (col, row)
    
    def get_board_position(self, screen_x, screen_y):
        # convert screen coordinates to board coordinates accounting for flip
        if screen_x >= 100 and screen_x < 900:  # main board area
            col = (screen_x - 100) // RWIDTH
            if screen_y < 3 * RHEIGHT: # above rampart
                row = screen_y // RHEIGHT
            else: # below rampart
                row = (screen_y - RAMPART_HEIGHT) // RHEIGHT
                row = min(row, 5)
                
            if self.flipped:
                return (COLS - 1 - col, ROWS - 1 - row)
            return (col, row)
        return (None, None)
    
    def get_card_position(self, screen_x, screen_y):
        # returns (suit, rank) accounting for visual flip without changing card ownership
        # deck boundaries (adjust if needed)
        in_black_deck = (0 <= screen_x < 100)       # always left visually
        in_white_deck = (900 <= screen_x <= 1000)   # always right visually
        
        if not (in_black_deck or in_white_deck):
            return (None, None)
        
        # determine actual deck ownership (not affected by flip)
        if in_black_deck:
            suit = 1 if self.flipped else 0  # visually left deck
        else:
            suit = 0 if self.flipped else 1  # visually right deck
        
        # calculate rank (handles both decks' vertical positions)
        if (suit == 1 and not self.flipped) or (suit == 0 and self.flipped):
            # white deck position (top-aligned when unflipped)
            rank = max(0, min(12, 12 - (screen_y - CEM_HEIGHT - RAMPART_HEIGHT) // CHEIGHT)) if \
                (screen_y - CEM_HEIGHT - RAMPART_HEIGHT) >= 0 else 0
        else:
            # black deck position (bottom-aligned when unflipped)
            rank = max(0, min(12, screen_y // CHEIGHT))
        
        return (suit, rank)
        
    def get_grave_position(self, screen_x, screen_y):
        # preserves original calculations but accounts for flipping
        if self.flipped:
            # when flipped, swap which side to check based on player
            if (screen_x < 100 and self.next_player == 'white') or \
               (screen_x >= 900 and self.next_player == 'black'):
                
                # convert to unflipped coordinates for calculation
                calc_x = screen_x
                calc_y = screen_y
                
                # black graveyard (now on right when flipped)
                if self.next_player == 'black' and screen_x >= 900:
                    motion_col = 1
                    adjusted_y = calc_y - 80  # original white graveyard calculation
                    if adjusted_y <= 0:
                        motion_row = 0
                    elif adjusted_y // GHEIGHT > 8:
                        motion_row = 8
                    else:
                        motion_row = adjusted_y // GHEIGHT
                    return (motion_col, motion_row)
                
                # white graveyard (now on left when flipped)
                elif self.next_player == 'white' and screen_x < 100:
                    motion_col = 0
                    adjusted_y = calc_y - (HEIGHT - CEM_HEIGHT + 65 + RAMPART_HEIGHT)  # original black calculation
                    if adjusted_y < 0:
                        motion_row = 0
                    elif adjusted_y // GHEIGHT > 8:
                        motion_row = 8
                    else:
                        motion_row = (adjusted_y // GHEIGHT) + 1 if (adjusted_y // GHEIGHT) + 1 <= 8 else 8
                    return (motion_col, motion_row)
        
        else:
            # original unflipped logic
            if screen_x < 100 and self.next_player == 'black':
                motion_col = 0
                adjusted_y = screen_y - (HEIGHT - CEM_HEIGHT + 10 + RAMPART_HEIGHT) - 90
                if adjusted_y < 0:
                    motion_row = 0
                elif adjusted_y // GHEIGHT > 8:
                    motion_row = 8
                else:
                    motion_row = (adjusted_y // GHEIGHT) + 1 if (adjusted_y // GHEIGHT) + 1 <= 8 else 8
                return (motion_col, motion_row)
                
            elif screen_x >= 900 and self.next_player == 'white':
                motion_col = 1
                adjusted_y = screen_y - 80
                if adjusted_y <= 0:
                    motion_row = 0
                elif adjusted_y // GHEIGHT > 8:
                    motion_row = 8
                else:
                    motion_row = adjusted_y // GHEIGHT
                return (motion_col, motion_row)
        
        return (None, None)
        
    def set_mated_prompt(self, color):
        # guard against overwrite of a draw already detected
        if isinstance(self.white_cast_prompt, list) and \
            len(self.white_cast_prompt) > 1 and \
            self.white_cast_prompt[1] in ('repetition', 'insufficient-material'):
            return
        
        if self.board.king_mated:
            self.white_cast_prompt = [color, 'mated']
            self.black_cast_prompt = [color, 'mated']
        elif self.board.king_stalemated:
            self.white_cast_prompt = [color, 'stale-mated']
            self.black_cast_prompt = [color, 'stale-mated']
            
    def set_repetition_prompt(self):
        self.white_cast_prompt = ['both', 'repetition']
        self.black_cast_prompt = ['both', 'repetition']

    def set_insufficient_material_prompt(self):
        self.white_cast_prompt = ['both', 'insufficient-material']
        self.black_cast_prompt = ['both', 'insufficient-material']
        
    def set_in_check_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'in-check'
        else:
            self.black_cast_prompt = 'in-check'
        
    def set_cast_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'cast'
        else:
            self.black_cast_prompt = 'cast'
        
    def set_strike_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'strike'
        else:
            self.black_cast_prompt = 'strike'
        
    def set_raise_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'raise'
        else:
            self.black_cast_prompt = 'raise'
        
    def set_raise_queen_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'raiseq'
        else:
            self.black_cast_prompt = 'raiseq'
        
    def set_choose_grave_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'choosegrv'
        else:
            self.black_cast_prompt = 'choosegrv'

    def set_no_raise_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'no-raise'
        else:
            self.black_cast_prompt = 'no-raise'

    def set_no_strike_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'no-strike'
        else:
            self.black_cast_prompt = 'no-strike'

    def set_strike_needs_two_board_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'strike-needs-2-board'
        else:
            self.black_cast_prompt = 'strike-needs-2-board'


    def set_make_21_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'make21'
        else:
            self.black_cast_prompt = 'make21'
            
    def set_choose_cast_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'choosecast'
        else:
            self.black_cast_prompt = 'choosecast'

        
    def kill_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = ''
        else:
            self.black_cast_prompt = ''

    def restore_cast_prompt(self, color):
        # re-show 'cast' if COLOR's piece is still sitting on the enemy jack
        # house after an overriding prompt (e.g. 'in-check') is cleared -
        # that condition doesn't go away just because the prompt covering it did.
        if self.board._enemy_jack_house_occupied(color):
            self.set_cast_prompt(color)
            
    def set_sq_hover(self, col, row):
        if self.flipped:
            col, row = COLS-1-col, ROWS-1-row
            
        is_playable = True
        
        house_cols = [2, 3, 4] if row == 0 else [5, 6, 7]
        
        if row == 0 or row == ROWS - 1:
            if col not in house_cols:
                is_playable = False
                
        if (0 <= col < COLS) and (0 <= row < ROWS) and is_playable:
            self.hovered_sqr = self.board.squares[col][row]
        else:
            self.hovered_sqr = None
        
    def set_dom_hover(self, col, row):
        # sets hover using board coordinates - display conversion happens in rendering
        if 0 <= col < COLS and 0 <= row < ROWS:
            self.hovered_dom = self.board.squares[col][row]
        else:
            self.hovered_dom = None
        
    def kill_dom_hover(self):
        self.hovered_dom = None
        
    def set_crd_hover(self, suit, rank):
        self.hovered_crd = self.board.cards[suit][rank]
        
    def set_btn_hover(self, categ):
        self.hovered_btn = self.board.cast_buttons[categ]
    
    def set_grave_hover(self, col, row):
        if col is None or row is None:
            self.hovered_grave = None
            return
        if (isinstance(col, int) and isinstance(row, int) and \
            0 <= col < len(self.board.graves) and \
            0 <= row < len(self.board.graves[col])):
            self.hovered_grave = self.board.graves[col][row]
        else:
            self.hovered_grave = None
        
    def kill_grave_hover(self):
        self.hovered_grave = None
        
    def change_theme(self):
        self.config.change_theme()
        
    def change_emblem(self):
        self.config.change_emblem()
        
    def change_dead_card(self):
        self.config.change_dead_card()
        
    def play_sound(self, captured=False):
        if captured:
            self.config.capture_sound.play()
        else:
            self.config.move_sound.play()
            
    def play_card_sound(self):
        self.config.card_click_sound.play()
        
    def play_strike_sound(self):
        self.config.strike_sound.play()
        
    def play_raise_sound(self):
        self.config.raise_sound.play()
            
    def reset(self):
        self.__init__()
        

# ╭━━┳━━┳╮╭┳━━╮╭━━┳━━┳╮╭┳━━╮
# ┃━━┫╭╮┃╰╯┃┃━┫┃╭╮┃╭╮┃╰╯┃┃━┫
# ┣━━┃╭╮┣╮╭┫┃━┫┃╰╯┃╭╮┃┃┃┃┃━┫
# ╰━━┻╯╰╯╰╯╰━━╯╰━╮┣╯╰┻┻┻┻━━╯
# ╱╱╱╱╱╱╱╱╱╱╱╱╱╭━╯┃
# ╱╱╱╱╱╱╱╱╱╱╱╱╱╰━━╯

    def show_naming_prompt(self, screen):
        if self.save_naming_mode:
            # create darkened overlay in sidebar
            sidebar_rect = pygame.Rect(WIDTH, 0, 200, HEIGHT + 40 + RAMPART_HEIGHT)
            pygame.draw.rect(screen, (30, 30, 30), sidebar_rect)
    
            # render text
            font = pygame.font.SysFont('monospace', 18, bold=True)
            title = font.render("SAVE GAME", True, (255, 215, 0)) # gold
            name_label = font.render("NAME:", True, (255, 255, 255))
            
            # display string being typed
            typed_name = font.render(self.current_save_name + "_", True, (0, 255, 0))
            
            # blit to screen (WITDTH is start of extra 200px)
            screen.blit(title, (WIDTH + 20, 100))
            screen.blit(name_label, (WIDTH + 20, 140))
            screen.blit(typed_name, (WIDTH + 20, 170))
            
            # instruction
            inst = pygame.font.SysFont('monospace', 12).render("Press ENTER to save",\
                     True, (150, 150, 150))
            screen.blit(inst, (WIDTH + 20, 210))
                

    def save_game(self, filename="savegame.json"):
        data = {
            "next_player": self.next_player,
            "history": self.move_log, # your RN list
            "board": [],
            "white_deck": [c.is_cast() for c in self.board.cards[1]],
            "black_deck": [c.is_cast() for c in self.board.cards[0]],
            "white_grave": self.board.graves[1], # simplify to counts
            "black_grave": self.board.graves[0]
        }
        # serialize board
        for col in range(COLS):
            for row in range(ROWS):
                sq = self.board.squares[col][row]
                if sq.has_piece():
                    data["board"].append({
                        "pos": (col, row),
                        "piece": sq.piece.name,
                        "color": sq.piece.color
                    })
                    
        def serialize_grave(grave_list):
            return [g.piece.name if g.has_piece() else None for g in grave_list]
        
        data["white_grave"] = serialize_grave(self.board.graves[1])
        data["black_grave"] = serialize_grave(self.board.graves[0])
        
        with open(filename, "w") as f:
            json.dump(data, f)

        save_dir = os.path.dirname(filename) or '.'
        self.save_files = [f for f in os.listdir(save_dir) if f.endswith('.json')]
        print(f"Game saved as {filename}. Total saves: {len(self.save_files)}")
    
    def load_game(self, filename="savegame.json"):
        with open(filename, "r") as f:
            data = json.load(f)
            
        self.reset() # clear board and reset cards
        self.next_player = data["next_player"]
        self.history = data.get("history", [])
        
        # 1. reconstruct board pieces
        # first clear initial setup piecs created by reset()
        for col in range(COLS):
            for row in range(ROWS):
                self.board.squares[col][row].piece = None
                
        for p_data in data["board"]:
            col, row = p_data["pos"]
            color = p_data["color"]
            name = p_data["piece"]
            
            # instantiate correct piece class
            if name == 'raider': piece = Raider(color)
            elif name == 'knight': piece = Knight(color)
            elif name == 'rook': piece = Rook(color)
            elif name == 'bishop': piece = Bishop(color)
            elif name == 'queen': piece = Queen(color)
            elif name == 'king': piece = King(color)
            
            piece.set_texture() # loads image path
            piece.moved = True
            
            self.board.squares[col][row].piece = piece
            
            if isinstance(piece, King):
                self.board._king_positions[color] = (col, row)
            
        # 2. reconstruct decks (cast status)
        for i, is_cast in enumerate(data["white_deck"]):
            self.board.cards[1][i].cast = is_cast
        for i, is_cast in enumerate(data["black_deck"]):
            self.board.cards[0][i].cast = is_cast
            
        # 3. reconstruct graveyards
        def rebuild_grave(grave_col, names, color):
            for i, name in enumerate(names):
                if name:
                    p = Raider(color) if name == 'raider' else Queen(color)
                    self.board.graves[grave_col][i].piece = p
                else:
                    self.board.graves[grave_col][i].piece = None
                    
        rebuild_grave(1, data["white_grave"], 'white')
        rebuild_grave(0, data["black_grave"], 'black')
        
        # update last move highlight
        if self.history:
            last_notation = self.history[-1]
            self.sync_last_move_highlight(last_notation)
            
        # udpate prompt
        # 1. clear any ghost prompts
        self.kill_prompt('white')

        # 2.get the correct Player object for the board's methods
        current_player = self.board.players[1] if self.next_player == 'white' else self.board.players[0]

        # 3. explicitly check states and set the UI strings directly.
        # Mate/stalemate is checked against BOTH players rather than just
        # current_player: when a saved game actually ended in mate,
        # next_player was never advanced to the mated side (the turn-switch
        # that would do that is skipped once mate is detected - see
        # _post_move_check_validation), so next_player still names the
        # winner here, not the side with no moves.
        mated_or_stale_color = None
        for p in self.board.players:
            if self.board._king_mated(p):
                mated_or_stale_color = p.color
                break

        if mated_or_stale_color:
            self.set_mated_prompt(mated_or_stale_color)

        elif self.board.king_in_check(current_player):
            self.set_in_check_prompt(self.next_player)

        elif self.next_player == 'white':
            self.set_cast_prompt('white')
        
        # self.kill_prompt('white')
        # king_pos = self.board._get_king_position(self.next_player)
        # if king_pos:
        #     col, row = king_pos
        #     king_piece = self.board.squares[col][row].piece
        #     self.board.calc_moves(king_piece, col, row, bool=True)
        
        # if not self.white_cast_prompt and not self.next_player == 'white':
        #     self.set_cast_prompt(self.next_player)
        
    def sync_last_move_highlight(self, notation):
        """parses notation to highlight last move"""
        if ">" in notation:
            dst_token = notation.split('>')[1]
            t_col, t_row = self._parse_square_token(dst_token)

            self.board.last_move = Move(Square(0, 0), Square(t_col, t_row))
        
    def show_load_menu(self, screen):
        if self.load_menu_mode:
            # darken sidebar
            sidebar_rect = pygame.Rect(WIDTH, 0, 200, HEIGHT + 40 + RAMPART_HEIGHT)
            pygame.draw.rect(screen, (30, 30, 30), sidebar_rect)
            
            font = pygame.font.SysFont('monospace', 16, bold=True)
            title = font.render("LOAD GAME", True, (0, 255, 255)) # cyan
            screen.blit(title, (WIDTH + 20, 100))
            
            # list the files
            for i, filename in enumerate(self.save_files):
                # highlight selected file in green
                color = (0, 255, 0) if i == self.selected_save_idx else \
                    (200, 200, 200)
                # truncate long names
                file_text = font.render(filename[:15], True, color)
                screen.blit(file_text, (WIDTH + 20, 140 + (i * 25)))
                
    # view history
    def reconstruct_at_move(self, index, history):
        # reset board and replay history up to specified index
        self.board = Board(self.flipped) # fresh board

        self.dragger.board = self.board
        self.clicker.board = self.board

        self.next_player = 'white' # game begin

        # replay moves from history
        for i in range(index):
            notation = history[i]
            self.apply_notation_to_board(notation)

            if self.next_player == 'white':
                self.next_player = 'black'
            else:
                self.next_player = 'white'

        # Board(...) always starts with king_mated/king_stalemated False, so
        # a reconstruction landing on the real game's final position would
        # otherwise silently look "in progress" again - re-derive both the
        # flags (main.py's AI-turn/event routing reads them straight off
        # self.board) and the prompt from the reconstructed position itself,
        # the same way load_game() does, rather than trusting next_player
        # (which only reflects the mover, not the mated/stalemated side).
        self.kill_prompt('white')
        self.kill_prompt('black')

        current_player = self.board.players[1] if self.next_player == 'white' \
            else self.board.players[0]

        mated_or_stale_color = None
        for p in self.board.players:
            if self.board._king_mated(p):
                mated_or_stale_color = p.color
                break

        if mated_or_stale_color:
            self.set_mated_prompt(mated_or_stale_color)
        elif self.board.king_in_check(current_player):
            self.set_in_check_prompt(self.next_player)
        elif self.next_player == 'white':
            self.set_cast_prompt('white')

    # parses a "<col><row-letter>" square token, e.g. "3f" or "10a".
    # column is 1-10 (COLS=10) so it can be 1 or 2 digits - can't use
    # fixed-width slicing to split it from the row letter.
    SQUARE_TOKEN_RE = re.compile(r'^(\d+)([a-g])')

    def _parse_square_token(self, token):
        match = self.SQUARE_TOKEN_RE.match(token)
        col = int(match.group(1)) - 1
        row = 5 - (ord(match.group(2)) - ord('a'))
        return col, row

    # notation parser
    def apply_notation_to_board(self, notation):
        # handle standard moves
        if ">" in notation and "/" not in notation:
            p_char = notation[0]
            src_str, dst_str = notation[1:].split(">")

            f_col, f_row = self._parse_square_token(src_str)
            t_col, t_row = self._parse_square_token(dst_str)

            piece = self.board.squares[f_col][f_row].piece
            
            # in case of corrupted file
            if piece is None:
                print(f"DEBUG: History sync error! No piece found at {src_str} for move: {notation}")
                return # Skip this invalid move instead of crashing
            
            # Board.move() overwrites the destination unconditionally - it
            # never sends a captured piece to the grave itself, that's
            # always the caller's job. The live click-handler does this
            # (main.py, right before calling board.move()); this replay
            # path never did, so browsing history to a position just after
            # a normal-move capture showed one fewer piece in the grave
            # than the live game actually had at that point.
            captured = self.board.squares[t_col][t_row].piece
            if captured is not None and captured.name in ('raider', 'queen'):
                self.board._send_to_grave(captured)

            move = Move(Square(f_col, f_row), Square(t_col, t_row))

            self.board.move(piece, move)

        # handle cast moves and queen spawns
        elif "++" in notation or "--" in notation:
            is_raise = "++" in notation
            # extract target square: the chars after '@'
            target_part = notation.split('@')[1].split('(')[0]
            t_col, t_row = self._parse_square_token(target_part)
            target_sq = self.board.squares[t_col][t_row]
            
            # determine piece
            p_char = notation[2]
            piece = Raider(self.next_player) if p_char == 'R' else \
                Queen(self.next_player)
            
            if is_raise:
                self.board._raise_raider(t_col, t_row, self.next_player, \
                    target_sq.card) if p_char == 'R' else self.board._raise_queen\
                    (t_col, t_row, self.next_player, target_sq.card)
                    
            else:
                self.board._send_to_grave(target_sq.piece)
                target_sq.piece = None
                
            cards_part = notation.split('(')[1].split(')')[0]
            card_labels = cards_part.split(',')
            
            # determine deck
            deck_suit = 1 if self.next_player == 'white' else 0
            
            for label in card_labels:
                # only deck cards needed
                if not any(s in label for s in SUITS):
                    # convert rank label back to index
                    rank_idx = RANKS.index(label)
                    # mark card as cast in reconstructed board
                    self.board.cards[deck_suit][rank_idx].cast = True

            # Board.cast_move() normally sets this as a side effect of
            # actually casting - since replay drives the board directly via
            # _raise_raider/_raise_queen/_send_to_grave instead, it has to be
            # set here too, or show_last_move() keeps highlighting whatever
            # the previous (non-cast) history entry left behind.
            self.board.last_move = Cast_move([], target_sq, 0 if not is_raise else 1)
                
        # handle compound moves
        elif "/" in notation:
            # split and call this function twice for each part
            move_part, spawn_part = notation.split("/")
            self.apply_notation_to_board(move_part)
            
            # manually handle queen spawn
            q_target = spawn_part.split('@')[1]
            q_col, q_row = self._parse_square_token(q_target)
            self.board._raise_queen(q_col, q_row, self.next_player, self.board.\
                squares[q_col][q_row].card)

            # same reasoning as the plain cast-move branch above - the queen
            # spawn is the actual final action of this compound move, so it's
            # what should end up highlighted.
            self.board.last_move = Cast_move([], self.board.squares[q_col][q_row], 1)



# █▀▀ █▀█ █▀▄▀█ █▀▄▀█ ▄▀█ █▄░█ █▀▄   █▀▄▀█ █▀▀ █▄░█ █░█
# █▄▄ █▄█ █░▀░█  █░▀░█ █▀█ █░▀█ █▄▀    █░▀░█ ██▄ █░▀█ █▄█
            

    def show_side_menu(self, screen):
         # do not draw anything if no menu is active
         if not getattr(self, 'active_menu', None):
             return
             
         # draw dark sidebar background
         sidebar_rect = pygame.Rect(WIDTH, 0, 200, HEIGHT + 0 + RAMPART_HEIGHT)
         pygame.draw.rect(screen, (30, 30, 30), sidebar_rect)
         
         font_title = pygame.font.SysFont('monospace', 18, bold=True)
         font_opt = pygame.font.SysFont('monospace', 14, bold=True)
         
         # determine text to show based on which button clicked
         if self.active_menu == 'game':
             title = "GAME MENU"
             options = ["Save Game (S)", "Load Game (L)", "Restart (R)", "Flip Board (F)", "Main Menu (M)"] # Changed Rematch to Restart
         elif self.active_menu == 'pref':
             title = "PREFERENCES"
             options = ["Change Theme (T)", "Piece Styles (Y)", f"AI Level: {self.ai_difficulty} (A)"]
         elif self.active_menu == 'help':
             title = "HELP"
             options = ["Rules (WIP)", "Controls (WIP)"]
             
         # draw title
         title_surf = font_title.render(title, True, (0, 255, 255))
         screen.blit(title_surf, (WIDTH + 20, 200))
         
         # draw options with hover effect (scaled back to design-resolution
         # coordinates - see Main._get_mouse_pos() for why)
         _mx, _my = pygame.mouse.get_pos()
         ui_scale = getattr(self, 'ui_scale', 1.0)
         mouse_pos = (int(_mx / ui_scale), int(_my / ui_scale))
         for i, opt in enumerate(options):
             opt_rect = pygame.Rect(WIDTH + 20, 240 + (i * 40), 160, 30)
             color = (255, 255, 255) if opt_rect.collidepoint(mouse_pos) else (150, 150, 150)
             opt_surf = font_opt.render(f"> {opt}", True, color)
             screen.blit(opt_surf, (opt_rect.x, opt_rect.y + 5))
             
    def show_help_overlays(self, screen):
        active = (self.show_rules_overlay or self.show_controls_overlay or 
                  getattr(self, 'show_save_overlay', False) or \
                  getattr(self, 'show_load_overlay', False))
        
        if not active:
            return
            
        # draw dark, semi-transparent background overlay
        overlay = pygame.Surface((WIDTH + 50, HEIGHT - 150))
        overlay.set_alpha(230) # 0 is invisible, 255 is solid
        overlay.fill((20, 20, 25))
        screen.blit(overlay, (0, 0))
        
        font_title = pygame.font.SysFont('monospace', 36, bold=True)
        font_body = pygame.font.SysFont('monospace', 18)
        
        # define text based on which menu was clicked
        if self.show_rules_overlay:
            title = font_title.render("RAMPART RULES", True, (0, 255, 255))
            lines = [
                "Official Rulebook: https://apecrank.net/rampart_rulebook/",
                "--------------------------------------------------",
                "RAMPART: DESCRIPTION",
                "Rampart is a strategic hybrid of chess and cardplay, where two",
                "players compete to checkmate their opponent's king using a",
                "combination of tactical piece movement and deck-based casting.",
                "",
                "MATERIALS & SETUP",
                "- 1 standard deck of cards (White uses Spades, Black uses Clubs)",
                "- Chess pieces per player: 8 Raiders (pawns), 1 Rook, 1 Knight,",
                "  1 Bishop, 1 Queen, and 1 King.",
                "- Board: Bottom half is Diamonds, top half is Hearts.",
                "- Houses: Jack, Queen, and King cards on rows 'a' and 'f'.",
                "",
                "PIECE MOVEMENT",
                "- Raiders: Move 1 space any direction, capture diagonally.",
                "  Cannot cross back over the rampart (the mid-board barrier).",
                "- Knights/Rooks/Bishops/Queens/Kings: Move standard to chess.",
                "",
                "CASTING & HOUSES",
                "Casting requires using exactly 3 cards totaling 21.",
                "Raiders are the ONLY pieces allowed in enemy Houses.",
                "- Jack's House: Unlocks spawning and striking.",
                "- Queen's House: Unlocks spawning your Queen.",
                "- King's House: Restricts enemy King to only card squares.",
                "",
                "RAISING (SPAWNING)",
                "Use 1-2 raiders on card squares + 1-2 deck cards to make 21.",
                "Discard the deck cards, place a captured raider or queen on",
                "an empty square in your territory.",
                "",
                "STRIKING (CAPTURING)",
                "Requires a raider in enemy Jack's house. Use 2 raiders on",
                "card squares + 1 deck card to make 21 to capture an enemy",
                "raider."
            ]
        elif self.show_controls_overlay:
            title = font_title.render("CONTROLS", True, (0, 255, 255))
            lines = [
                "Mouse Left Click: Select pieces and cards.",
                "Mouse Drag: Move pieces across the board.",
                "Keyboard [T]: Cycle through board themes.",
                "Keyboard [F]: Flip board orientation.",
                "Keyboard [R]: Request Rematch.",
                "Keyboard [C]: Open multiplayer chat box.",
                "Keyboard [<] [>]: Navigate move history."
            ]
        elif getattr(self, 'show_save_overlay', False):
            title = font_title.render("SAVE GAME", True, (0, 255, 0)) # Green
            lines = ["Slot 1: Manual Save", "Slot 2: Auto-Save", "Slot 3: Empty"]
            # no scrolling for these -- so reset scroll
            self.help_scroll_y = 0 
            
        elif getattr(self, 'show_load_overlay', False):
            title = font_title.render("LOAD GAME", True, (255, 165, 0)) # Orange
            lines = ["Slot 1: Manual Save (10:15 AM)", "Slot 2: Auto-Save (9:00 AM)", "Slot 3: Empty"]
            self.help_scroll_y = 0

        # draw title centered near the top
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
        
        # 1. define the window area
        view_height = (HEIGHT - 250) - 225 
        view_rect = pygame.Rect(100, 225, WIDTH - 75, view_height)
        
        # 2. ONLY draw inside this rectangle
        screen.set_clip(view_rect)
        
        # 3. draw lines
        line_height = 35
        # safety check: if scroll_y doesn't exist, set it to 0
        scroll_y = getattr(self, 'help_scroll_y', 0)
        
        for i, line in enumerate(lines):
            # dynamic colors
            color = (0, 255, 255) if "https://" in line else (255, 215, 0) if \
                (line.isupper() and "---" not in line) else (220, 220, 220)
                
            text_surf = font_body.render(line, True, color)
            # apply the scroll
            y_pos = 225 + (i * line_height) + scroll_y
            screen.blit(text_surf, (125, y_pos))
            
        # 4. SET LIMITS
        total_height = len(lines) * line_height
        max_scroll = max(0, total_height - view_rect.height)
        self.help_scroll_y = max(-max_scroll, min(0, scroll_y))

        # 4. turn off clipping so that ESC prompt can draw
        screen.set_clip(None) 
            
        # draw "Press ESC to close" prompt
        esc_surf = font_body.render("Press [ESC] to close", True, (255, 100, 100))
        screen.blit(esc_surf, (WIDTH//2 - esc_surf.get_width()//2 - 7, HEIGHT - 200))
        
        
        