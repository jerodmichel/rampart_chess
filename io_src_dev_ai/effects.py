#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 25 16:08:13 2025

@author: stereo
"""

# ███████╗███████╗███████╗███████╗░█████╗░████████╗░██████╗
# ██╔════╝██╔════╝██╔════╝██╔════╝██╔══██╗╚══██╔══╝██╔════╝
# █████╗░░█████╗░░█████╗░░█████╗░░██║░░╚═╝░░░██║░░░╚█████╗░
# ██╔══╝░░██╔══╝░░██╔══╝░░██╔══╝░░██║░░██╗░░░██║░░░░╚═══██╗
# ███████╗██║░░░░░██║░░░░░███████╗╚█████╔╝░░░██║░░░██████╔╝
# ╚══════╝╚═╝░░░░░╚═╝░░░░░╚══════╝░╚════╝░░░░╚═╝░░░╚═════╝░

import pygame
import random as rd
import time

from const import *

def generate_lightning(start_x, start_y, end_x, end_y, depth=50):
    # generate lightning bolt coordinates between two points
    points = [(start_x, start_y)]
    
    # calculate direction vector
    dx = (end_x - start_x) / depth
    dy = (end_y - start_y) / depth
    
    for i in range(1, depth):
        # base position along the line
        base_x = start_x + dx * i
        base_y = start_y + dy * i
        
        # add some randomness
        if i < depth-1:  # Don't randomize the last point
            offset_x = rd.randint(-15, 15)
            offset_y = rd.randint(-5, 5)
            
            # reduce randomness as we approach the end
            scale = 1 - (i / depth)
            offset_x *= scale
            offset_y *= scale
            
            points.append((base_x + offset_x, base_y + offset_y))
        else:
            points.append((end_x, end_y))
    
    return points

class Lightning_effect:
    def __init__(self, game):
        self.game = game
        self.active = False
        self.frame = 0
        self.max_frames = 30  # animation duration
        # new color properties:
        self.base_color = (150, 220, 255)  # bright cyan-blue
        self.core_color = (220, 240, 255)   # white-hot core
        self.bloom_color = (100, 150, 255)  # outer glow
        self.points = []  # stores lightning path coordinates
    
    def trigger(self, player_color, persist_frames=30):
        # start the lightning animation for the given player"""
        self.active = True
        self.frame = 0
        self.persist_frames = persist_frames
        
        # Base Y adjustments for rampart
        rampart_adj = RAMPART_HEIGHT if not self.game.flipped else 0
        
        # calculate positions based on layout
        if player_color == 'white':
            # white's graveyard and deck are on the right
            if not self.game.flipped:
                # normal orientation
                start_x = 908 + GWIDTH//2  # graveyard center (right side)
                start_y = 90 + GHEIGHT//2
                end_x = 908 + CWIDTH//2   # deck center (right side)
                end_y = CEM_HEIGHT + CHEIGHT//2
            else:
                # flipped orientation - swap to left side
                start_x = 2 + GWIDTH//2   # graveyard center (left side)
                start_y = (HEIGHT - CEM_HEIGHT + 65 + RAMPART_HEIGHT) + GHEIGHT//2 + 300
                end_x = 2 + CWIDTH//2     # deck center (left side)
                end_y = CHEIGHT//2 + 300
        else:  # black
            # black's graveyard and deck are on the left
            if not self.game.flipped:
                # normal orientation
                start_x = 2 + GWIDTH//2   # graveyard center (left side)
                start_y = (HEIGHT - CEM_HEIGHT + 65 + RAMPART_HEIGHT) + GHEIGHT//2 + 300
                end_x = 2 + CWIDTH//2     # deck center (left side)
                end_y = CHEIGHT//2 + 300
            else:
                # flipped orientation - swap to right side
                start_x = 908 + GWIDTH//2  # graveyard center (right side)
                start_y = 90 + GHEIGHT//2
                end_x = 908 + CWIDTH//2   # deck center (right side)
                end_y = CEM_HEIGHT + CHEIGHT//2 + rampart_adj
        
        # generate the lightning path
        self.points = generate_lightning(start_x, start_y, end_x, end_y)
    
    def update(self):
        # update animation frame
        if self.active:
            self.frame += 1
            if self.frame >= self.max_frames:
                self.active = False
    
    def draw(self, surface):
        if not self.active or len(self.points) < 2:
            return

        # create temporary surface for additive blending
        lightning_surface = pygame.Surface((surface.get_size()), pygame.SRCALPHA)
        
        # calculate fade (1.0 at start, 0.0 at end)
        fade = 1.0 - (self.frame / self.max_frames)
        
        # draw three layered components:
        for i in range(len(self.points)-1):
            # 1. outer glow (widest)
            pygame.draw.line(
                lightning_surface, 
                (*self.bloom_color, int(80*fade)),  # With alpha
                self.points[i], 
                self.points[i+1], 
                int(18 * fade)  # thickness decreases
            )
            
            # 2. main bolt
            pygame.draw.line(
                lightning_surface,
                (*self.base_color, int(200*fade)),
                self.points[i],
                self.points[i+1],
                int(10 * fade)
            )
            
            # 3. core (brightest)
            pygame.draw.line(
                lightning_surface,
                (*self.core_color, int(255*fade)),
                self.points[i],
                self.points[i+1],
                int(4 * fade)
            )
        
        # apply additive blending
        surface.blit(lightning_surface, (0, 0), special_flags=pygame.BLEND_ADD)
        
        # first-frame flash effect
        if self.frame == 0:
            flash = pygame.Surface((surface.get_size()), pygame.SRCALPHA)
            flash.fill((*self.core_color, 150))  # bright flash
            surface.blit(flash, (0, 0), special_flags=pygame.BLEND_ADD)


class Hourglass_effect:
    """An alchemist's hourglass shown while the AI is 'thinking'. Runs off
    its own frame counter (advanced once per rendered frame) rather than
    wall-clock time, since it needs to keep animating for however long the
    background search thread takes."""

    SAND_FRAMES = 90   # how long a full drain takes
    FLIP_FRAMES = 20   # how long the flip-over takes

    def __init__(self, game, size=17):
        self.game = game
        self.active = False
        self.frame = 0
        self.size = size

        # aged brass caps / dark wood frame
        self.brass_color = (156, 116, 48)
        self.brass_dark = (94, 66, 24)
        # parchment-tinted glass
        self.glass_color = (196, 186, 150)
        # glowing amber/gold sand
        self.sand_color = (224, 168, 47)
        self.sand_glow = (255, 208, 90)

    # animation timing is expressed as "frames" at this virtual rate rather
    # than actual render-loop iterations - the real loop's frame rate varies
    # a lot (piece/emblem images are reloaded from disk every frame), so
    # counting real iterations made the animation crawl or stall.
    VIRTUAL_FPS = 60

    def start(self):
        self.active = True
        self.start_time = time.time()
        self.frame = 0

    def stop(self):
        self.active = False

    def update(self):
        if self.active:
            self.frame = int((time.time() - self.start_time) * self.VIRTUAL_FPS)

    # black's deck sits at the top-left (x=2, width CWIDTH), black's
    # graveyard directly below it (x=2, width GWIDTH, starting at
    # y = (HEIGHT - CEM_HEIGHT + 65) + RAMPART_HEIGHT = 435) - this centers
    # the hourglass in that column, just inside the graveyard's top edge.
    def draw(self, surface, center=(GWIDTH // 2 + 2, (HEIGHT - CEM_HEIGHT + 65) + RAMPART_HEIGHT - 50), size=None):
        if not self.active:
            return

        size = self.size if size is None else size
        cycle = self.SAND_FRAMES + self.FLIP_FRAMES
        full_cycles = self.frame // cycle
        phase = self.frame % cycle
        orientation = 180 * (full_cycles % 2)

        if phase < self.SAND_FRAMES:
            angle = orientation
            sand_fraction = phase / self.SAND_FRAMES
        else:
            t = (phase - self.SAND_FRAMES) / self.FLIP_FRAMES
            angle = orientation + 180 * t
            sand_fraction = 1.0

        pad = 10
        cap_h = 6
        dim = size * 2 + pad * 2
        glass = pygame.Surface((dim, dim), pygame.SRCALPHA)
        cx = cy = dim // 2

        # soft alchemical glow behind the glass, pulsing with the sandfall
        pulse = 130 + int(70 * abs(0.5 - sand_fraction) * 2)
        pygame.draw.circle(glass, (*self.sand_glow, 40), (cx, cy), size + 10)
        pygame.draw.circle(glass, (*self.sand_glow, pulse // 4), (cx, cy), size + 4)

        # brass caps top/bottom
        pygame.draw.rect(glass, self.brass_color,
            (cx - size - 4, cy - size - cap_h, size * 2 + 8, cap_h), border_radius=2)
        pygame.draw.rect(glass, self.brass_color,
            (cx - size - 4, cy + size, size * 2 + 8, cap_h), border_radius=2)
        pygame.draw.rect(glass, self.brass_dark,
            (cx - size - 4, cy - size - cap_h, size * 2 + 8, cap_h), 1, border_radius=2)
        pygame.draw.rect(glass, self.brass_dark,
            (cx - size - 4, cy + size, size * 2 + 8, cap_h), 1, border_radius=2)

        # remaining sand in the top chamber (drains toward the neck)
        remaining_h = size * (1 - sand_fraction)
        if remaining_h > 0.5:
            pygame.draw.polygon(glass, self.sand_color, [
                (cx - remaining_h, cy - remaining_h),
                (cx + remaining_h, cy - remaining_h),
                (cx, cy),
            ])

        # sand piling up in the bottom chamber
        filled_h = size * sand_fraction
        if filled_h > 0.5:
            level_half_w = size - filled_h
            pygame.draw.polygon(glass, self.sand_color, [
                (cx - level_half_w, cy + size - filled_h),
                (cx + level_half_w, cy + size - filled_h),
                (cx + size, cy + size),
                (cx - size, cy + size),
            ])

        # trickle of falling grains through the neck
        if 0 < sand_fraction < 1.0:
            for i in range(3):
                fall_t = ((self.frame * 5 + i * 7) % 15) / 15
                gy = cy - size * 0.3 + fall_t * size * 0.6
                pygame.draw.circle(glass, self.sand_glow, (cx, int(gy)), 1)

        # glass outline (top and bottom triangles), parchment-tinted
        pygame.draw.polygon(glass, self.glass_color,
            [(cx - size, cy - size), (cx + size, cy - size), (cx, cy)], 2)
        pygame.draw.polygon(glass, self.glass_color,
            [(cx - size, cy + size), (cx + size, cy + size), (cx, cy)], 2)

        rotated = pygame.transform.rotate(glass, angle)
        rect = rotated.get_rect(center=center)
        surface.blit(rotated, rect)