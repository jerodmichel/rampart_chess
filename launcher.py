#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 01:36:26 2026

@author: stereo
"""

import pygame
import sys
import subprocess
import os
import time


class Launcher:
    def __init__(self):
        os.environ['SDL_VIDEO_CENTERED'] = '1'

        # No SetProcessDPIAware() here (unlike an earlier version of this
        # file) - it opts the process out of Windows' own DPI scaling
        # without pygame.SCALED then compensating for it, which is exactly
        # what made the window render oversized on Windows displays with a
        # scale factor above 100%. main.py's window never sets DPI
        # awareness and only relies on pygame.SCALED below, which is the
        # combination that actually renders correctly.
        pygame.init()

        # Query the actual screen this happens to be running on, instead of
        # assuming a fixed resolution (the previous "cap width at 1024px"
        # approach) - that number is meaningless on a device with a smaller
        # screen, and doesn't shrink further on a scaled-down Windows
        # display either. Not calling SetProcessDPIAware() above means
        # Windows presents this (DPI-unaware) process with its own
        # already-scaled/virtualized resolution here, so sizing relative to
        # whatever comes back adapts automatically to the user's actual
        # display and DPI setting without this code needing to know either.
        try:
            display_info = pygame.display.Info()
            screen_w, screen_h = display_info.current_w, display_info.current_h
        except Exception:
            screen_w, screen_h = 1280, 800  # sane fallback if the query fails

        # splash art
        self.bg_path = "rampart_bg.png"
        try:
            raw_bg = pygame.image.load(self.bg_path)
            orig_w, orig_h = raw_bg.get_size()

            # fit within a comfortable fraction of the actual screen, never
            # upscaling past the art's native resolution
            max_w = screen_w * 0.5
            max_h = screen_h * 0.75
            scale_factor = min(max_w / orig_w, max_h / orig_h, 1.0)
            self.width = max(1, int(orig_w * scale_factor))
            self.height = max(1, int(orig_h * scale_factor))
            self.bg_image = raw_bg if scale_factor == 1.0 else \
                pygame.transform.smoothscale(raw_bg, (self.width, self.height))
            # every other UI element below (button font/padding/offsets, the
            # about-overlay box and its text) was sized in absolute pixels
            # tuned for the art's native 749px width - scale them by the
            # same ratio the background itself just got scaled by, so
            # buttons/text shrink along with it instead of staying fixed
            # size and overflowing a smaller window.
            self.ui_scale = self.width / orig_w
        except Exception as e:
            print(f"Could not load background image: {e}")
            self.width, self.height = 800, 600 # fallback sizes
            self.bg_image = None
            self.ui_scale = self.width / 749

        self.screen = pygame.display.set_mode((self.width, self.height), pygame.SCALED)

        # adjust size here
        pygame.display.set_caption("Rampart -- Main Menu")
        self.font = pygame.font.Font("fonts/cinzel/Cinzel-Black.ttf", max(10, int(26 * self.ui_scale)))
        self.about_font = pygame.font.SysFont("timesnewroman", max(8, int(22 * self.ui_scale)))
        
        # about
        self.show_about = False
        
        self.music_path = "alexgrohl-metal.mp3"
        try:
            pygame.mixer.music.load(self.music_path)
            pygame.mixer.music.play(-1) # -1 loops it infinitely
        except Exception as e:
            print(f"Could not load music: {e}")
            
    def draw_about_overlay(self):
        # 1. dim the background
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210)) 
        self.screen.blit(overlay, (0, 0))
    
        # 2. draw box
        box_w = box_h = int(550 * self.ui_scale)
        box_rect = pygame.Rect((self.width//2 - box_w//2), (self.height//2 - box_h//2), box_w, box_h)
        pygame.draw.rect(self.screen, (30, 30, 35), box_rect, border_radius=15)
        pygame.draw.rect(self.screen, (180, 180, 180), box_rect, 2, border_radius=15)
    
        # 3. text content
        lines = [
            ("RAMPART", True),              
            ("", False),
            ("A strategic hybrid of chess and", False),
            ("cardplay where players battle across", False),
            ("a rampart barrier using tactical", False),
            ("movement and card-based casting.", False),
            ("", False),
            ("Credits:", True),
            ("", False),
            ("Lead Dev: Jerod Michel", False),
            ('Support Dev: Corey Russell', False),
            ("Support Design: Jordan Michel, Mac McMorran", False),
            ("Splash Art/Other Art: Leland Stuebig/Billy Hill", False),
            ("Music: Alex Grohl", False),
            ("", False),
            ("( Click anywhere to close )", False)
        ]
        
        # margin
        line_margin = int(30 * self.ui_scale)
        line_height = int(28 * self.ui_scale)
        left_margin = box_rect.left + line_margin
        
        for i, (text, is_title) in enumerate(lines):
            # fonts
            current_font = self.font if is_title else self.about_font
            
            # colors
            if i == 14: 
                color = (255, 0, 0) # Red
            else:
                color = (125, 249, 255) if is_title else (220, 220, 220)
            
            txt_surf = current_font.render(text, True, color)
            
            # alignment logic
            if i < 9 or i == 14:
                txt_rect = txt_surf.get_rect(centerx=self.width//2, top=box_rect.top + line_margin + (i * line_height))
            else:
                txt_rect = txt_surf.get_rect(left=left_margin, top=box_rect.top + line_margin + (i * line_height))
                
            self.screen.blit(txt_surf, txt_rect)

    def mainloop(self):
        
        while True:
            mouse_pos = pygame.mouse.get_pos()
            
            # 1. Draw Background
            if self.bg_image:
                self.screen.blit(self.bg_image, (0, 0))
            else:
                self.screen.fill((20, 20, 25))
            
            # 2. Setup Buttons (Automatic Width)
            button_data = [
                ("Play vs AI", "ai"),
                ("Play Multiplayer", "multi"),
                ("About", "about")
            ]
            
            button_rects = {}
            padding_x, padding_y = int(25 * self.ui_scale), int(10 * self.ui_scale)
            gap = int(20 * self.ui_scale)
            current_x = 40 # Start from left (or calculate for right)

            # Calculate total width to align group to the bottom right
            total_width = 0
            rendered_buttons = []
            for text, tag in button_data:
                surf = self.font.render(text, True, (20, 20, 10))
                w, h = surf.get_width() + (padding_x * 2), surf.get_height() + (padding_y * 2)
                rendered_buttons.append((surf, w, h, tag))
                total_width += w + gap

            # Draw buttons aligned to bottom right
            start_x = self.width - total_width - gap
            btn_y = self.height - int(70 * self.ui_scale)

            for surf, w, h, tag in rendered_buttons:
                rect = pygame.Rect(start_x, btn_y, w, h)
                button_rects[tag] = rect
                
                # Hover color logic
                color = (150, 150, 150) if rect.collidepoint(mouse_pos) else (240, 240, 245)
                pygame.draw.rect(self.screen, color, rect, border_radius=10)
                
                # Center text in the dynamic rect
                txt_rect = surf.get_rect(center=rect.center)
                self.screen.blit(surf, txt_rect)
                start_x += w + gap # Move x for next button

            # 3. Draw Overlay if active
            if self.show_about:
                self.draw_about_overlay()
            
            # 4. Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                    
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.show_about:
                        self.show_about = False # Close overlay on click
                    else:
                        if button_rects["ai"].collidepoint(mouse_pos):
                            self.launch_game("main.py", "io_src_dev_ai")
                        elif button_rects["multi"].collidepoint(mouse_pos):
                            self.launch_game("main.py", "io_src_dev")
                        elif button_rects["about"].collidepoint(mouse_pos):
                            self.show_about = True
                            
            pygame.display.update()
            
    def launch_game(self, script_name, folder_name):

        pygame.quit()

        # Log every launch attempt to a file (appended, not overwritten) -
        # this is the only way to see what actually happened on a
        # --noconsole/--windowed exe build, where a startup crash's
        # traceback would otherwise just vanish and look identical to the
        # launcher silently doing nothing.
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launch_error.log")

        def log(message):
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(message + "\n")
            except Exception:
                pass

        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller names the frozen binary "main.exe" on Windows
                # but just "main" (no extension) on Linux/macOS.
                target_exe = script_name.replace('.py', '.exe') if os.name == 'nt' \
                    else script_name.replace('.py', '')
                full_exe_path = os.path.abspath(os.path.join(folder_name, target_exe))
                log(f"=== Launch attempt: {full_exe_path} (exists: {os.path.exists(full_exe_path)}) ===")
                result = subprocess.run([full_exe_path], cwd=folder_name,
                                        capture_output=True, text=True)
            else:
                log(f"=== Launch attempt: {sys.executable} {script_name} in {folder_name} ===")
                result = subprocess.run([sys.executable, script_name], cwd=folder_name,
                                        capture_output=True, text=True)

            log(f"Return code: {result.returncode}")
            if result.stdout:
                log(f"--- stdout ---\n{result.stdout}")
            if result.stderr:
                log(f"--- stderr ---\n{result.stderr}")
        except Exception as e:
            log(f"=== Failed to launch {script_name}: {e} ===")
            print(f"Failed to launch {script_name}: {e}")
            time.sleep(1.0)

        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.SCALED)
        pygame.display.set_caption("Rampart -- Main Menu")
        self.font = pygame.font.Font("fonts/cinzel/Cinzel-Black.ttf", max(10, int(26 * self.ui_scale)))
        self.about_font = pygame.font.SysFont("timesnewroman", max(8, int(22 * self.ui_scale)))

        # reload image - re-scaled to the same (self.width, self.height)
        # computed in __init__, otherwise this reverts to the raw,
        # unscaled art (and the oversized-window bug with it) every time
        # the player returns here from a game.
        if self.bg_path:
            try:
                raw_bg = pygame.image.load(self.bg_path)
                self.bg_image = raw_bg if raw_bg.get_size() == (self.width, self.height) else \
                    pygame.transform.smoothscale(raw_bg, (self.width, self.height))
            except:
                pass
            
        if hasattr(self, 'music_path'):
            try:
                pygame.mixer.music.load(self.music_path)
                pygame.mixer.music.play(-1)
            except:
                pass
        
        
if __name__ == "__main__":
    launcher = Launcher()
    launcher.mainloop()
        
        
        
        
        