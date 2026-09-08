#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 11 11:49:17 2024

@author: stereo
"""


#███╗░░░███╗░█████╗░██╗███╗░░██╗
#████╗░████║██╔══██╗██║████╗░██║
#██╔████╔██║███████║██║██╔██╗██║
#██║╚██╔╝██║██╔══██║██║██║╚████║
#██║░╚═╝░██║██║░░██║██║██║░╚███║
#╚═╝░░░░░╚═╝╚═╝░░╚═╝╚═╝╚═╝░░╚══╝


# from services.firebase_manager import FirebaseManager
# from firebase_admin import db

import sys

# On Windows, when stdout/stderr aren't attached to a real console (e.g.
# launched as a subprocess with piped output, as launcher.py does), Python
# falls back to the OS's legacy codepage (cp1252) instead of UTF-8 to
# encode printed text. Several debug prints in this codebase use emoji,
# which crashes with UnicodeEncodeError under that codepage. Force UTF-8
# so those prints (and any future ones) never depend on the console's
# encoding.
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, 'reconfigure'):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

print(f"DEBUG: Python executable path is: {sys.executable}")

import os
import time
import threading
import datetime

import pygame

# Windows-only: declare this process DPI-aware so Windows doesn't
# scale/blur the pygame window to match the display's DPI scaling setting
# (125%/150%/etc). Must run before pygame.init() / any window creation.
if os.name == 'nt':
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor v2 (Win 8.1+)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # fallback (Vista+)
        except (AttributeError, OSError):
            pass

def log_to_file(message):
    """Simple, reliable logging to a file in the current directory."""
    try:
        with open('mcts_trace.txt', 'a', encoding='utf-8') as f:
            timestamp = time.strftime('%H:%M:%S')
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"LOGGING FAILED: {e}")

log_to_file("=== MAIN.PY LOADED ===")

# ╭━━━┳╮╱╭┳━━━┳━━┳━━━╮
# ┃╭━╮┃┃╱┃┣╮╭╮┣┫┣┫╭━╮┃
# ┃┃╱┃┃┃╱┃┃┃┃┃┃┃┃┃┃╱┃┃
# ┃╰━╯┃┃╱┃┃┃┃┃┃┃┃┃┃╱┃┃
# ┃╭━╮┃╰━╯┣╯╰╯┣┫┣┫╰━╯┃
# ╰╯╱╰┻━━━┻━━━┻━━┻━━━╯

def init_audio():
    # try pipeWire first
    os.environ.update({
        'SDL_AUDIODRIVER': 'pipewire',
        'PIPEWIRE_LATENCY': '512/48000',
        'PW_STREAM_RATE': '1'
    })
    
    try:
        pygame.mixer.init(frequency=48000)
        if pygame.mixer.get_init():
            print("Audio: Using PipeWire backend")
            return True
    except:
        pass
    
    # fallback to default
    os.environ.pop('SDL_AUDIODRIVER', None)
    os.environ.pop('PIPEWIRE_LATENCY', None)
    
    try:
        pygame.mixer.quit()
        pygame.mixer.init()  # default initialization
        print("Audio: Using system default backend")
        return True
    except:
        print("Audio: Failed to initialize - running without sound")
        return False

# usage:
if init_audio():
    sound = pygame.mixer.Sound('assets/sounds/thunder_strike.wav')
    sound.play()

pygame.init()
pygame.font.init()  # explicit font initialization

test_sound = pygame.mixer.Sound('assets/sounds/thunder_strike.wav')
test_sound.play()

import copy

from const import *
from game import Game
from square import Square
from piece import *
from move import Move
from cast_move import Cast_move
from player import Player
from ai_engine import NegamaxEngine
from rampartbitboard import RampartBitboard

class Main:
    def __init__(self):
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()

        # pygame.SCALED alone doesn't shrink a window below its requested
        # size - by itself it only ever scales UP to an integer multiple on
        # a larger display, never down, so on a screen smaller than the
        # design resolution (WIDTH+200 x HEIGHT+40+RAMPART_HEIGHT, i.e.
        # 1000x860) the window used to render at full size regardless,
        # overflowing the screen. Instead, every existing draw call keeps
        # targeting self.screen - an off-screen Surface at the fixed design
        # resolution, completely unchanged - and self.display is the real,
        # on-screen window, sized to actually fit whatever screen this runs
        # on. _present() scales the former into the latter once per frame.
        design_w, design_h = WIDTH + 200, HEIGHT + 40 + RAMPART_HEIGHT
        try:
            display_info = pygame.display.Info()
            screen_w, screen_h = display_info.current_w, display_info.current_h
        except Exception:
            screen_w, screen_h = design_w, design_h

        scale = min(1.0, (screen_w * 0.95) / design_w, (screen_h * 0.85) / design_h)
        display_w = max(1, int(design_w * scale))
        display_h = max(1, int(design_h * scale))

        self.screen = pygame.Surface((design_w, design_h))
        self.display = pygame.display.set_mode((display_w, display_h), pygame.SCALED)
        self.ui_scale = scale
        pygame.display.set_caption('Rampart')
        self.game = Game()
        self.game.play_strike_sound()
        # game.py's own show_side_menu() reads the real mouse position
        # directly for a hover effect - give it the same scale factor so
        # that stays aligned with the design-resolution rects it hit-tests.
        self.game.ui_scale = self.ui_scale
        

# ░█████╗░██╗  ██╗░░░░░░█████╗░░██████╗░██╗░█████╗░
# ██╔══██╗██║  ██║░░░░░██╔══██╗██╔════╝░██║██╔══██╗
# ███████║██║  ██║░░░░░██║░░██║██║░░██╗░██║██║░░╚═╝
# ██╔══██║██║  ██║░░░░░██║░░██║██║░░╚██╗██║██║░░██╗
# ██║░░██║██║  ███████╗╚█████╔╝╚██████╔╝██║╚█████╔╝
# ╚═╝░░╚═╝╚═╝  ╚══════╝░╚════╝░░╚═════╝░╚═╝░╚════╝░
        
        self.ai_color = 'black'
        self.ai_thinking = False
        self.ai_thread = None
        self.ai_move_result = None
        self.ai_move_error = None

        # AI setup
        self.ai_engine = NegamaxEngine()
        self.ai_thinking_time = 3.0
        
        # Ensure player is white
        self.my_color = 'white'
        self.game.next_player = 'white'
        
        
# █░█ █ █▀ ▀█▀ █▀█ █▀█ █▄█
# █▀█ █ ▄█ ░█░ █▄█ █▀▄ ░█░
        
        self.state_history = []
        self.move_log = []
        self._autosaved = False

    def _get_mouse_pos(self):
        """pygame.mouse.get_pos() reports real on-screen pixels, but every
        click/hover rect in this file and game.py is defined in the fixed
        design resolution self.screen draws to - convert back to that
        space here rather than at every one of the many call sites."""
        x, y = pygame.mouse.get_pos()
        return (int(x / self.ui_scale), int(y / self.ui_scale))

    def _present(self):
        """Scale the fixed-resolution off-screen surface (self.screen, what
        every draw call in this file and game.py actually targets) into the
        real, screen-sized window and show it. Call this wherever the code
        used to call pygame.display.update()/flip() directly."""
        if self.display.get_size() == self.screen.get_size():
            self.display.blit(self.screen, (0, 0))
        else:
            pygame.transform.smoothscale(self.screen, self.display.get_size(), self.display)
        pygame.display.update()

    def _autosave_finished_game(self):
        """Called once per frame; the moment a game ends (checkmate,
        stalemate, repetition, or insufficient material), silently writes
        the full move history to saves/ so a finished game is never lost
        just because the window gets closed without an explicit Save."""
        if self._autosaved:
            return
        if not (self.game.board.king_mated or self.game.board.king_stalemated):
            return

        self._autosaved = True

        if not self.move_log:
            return  # nothing played, nothing worth saving

        if not os.path.exists('saves'):
            os.makedirs('saves', exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"saves/autosave_{timestamp}.json"

        self.game.move_log = self.move_log
        self.game.save_game(filename)
        print(f"[AUTOSAVE] Game over - saved to {filename}")

    # depth cap and per-move time budget for each difficulty - Hard gets a
    # much larger time budget because Medium's search was regularly hitting
    # TIME_LIMIT before finishing a depth-6 pass (see the
    # "[AI] Time limit reached at Depth 5/6" log lines during real games),
    # so simply raising max_depth without also raising the time budget
    # wouldn't let it search any deeper in practice.
    AI_DIFFICULTY_SETTINGS = {
        'Easy':   {'max_depth': 4, 'time_limit': 5.0},
        'Medium': {'max_depth': 6, 'time_limit': 5.0},
        'Hard':   {'max_depth': 7, 'time_limit': 15.0},
    }
    AI_DIFFICULTY_NEXT = {'Easy': 'Medium', 'Medium': 'Hard', 'Hard': 'Easy'}

    def _cycle_ai_difficulty(self):
        """Advance ai_difficulty Easy -> Medium -> Hard -> Easy, applying
        the matching search depth and time budget to the engine."""
        self.game.ai_difficulty = self.AI_DIFFICULTY_NEXT.get(
            self.game.ai_difficulty, 'Easy')
        settings = self.AI_DIFFICULTY_SETTINGS[self.game.ai_difficulty]
        self.ai_engine.max_depth = settings['max_depth']
        self.ai_engine.time_limit = settings['time_limit']

    def _check_repetition_draw(self):
        # temp bitboard
        temp_bb = RampartBitboard()
        temp_bb.sync_from_board(self.game.board)
        current_hash = temp_bb.get_state_hash()
        
        self.state_history.append(current_hash)
        
        # if this is 3rd instance of this state then draw
        if self.state_history.count(current_hash) >= 3:
            print("!!! GAME DRAWN (Threefold Repetition) !!!")
            
            # 1. end game
            self.game.board.king_stalemated = True
            
            # 2. set repetition prompt
            self.game.set_repetition_prompt()
            
            return True
        return False
        
    def _post_move_check_validation(self):
        """Handle check/checkmate validation after AI move"""
        
        # 1.determine who the AI just played against
        rival_color = 'white' if self.ai_color == 'black' else 'black'
        
        # we need the actual Player object for the standard checks
        if self.game.board.players[0].color == rival_color:
            rival_player = self.game.board.players[0]
        else:
            rival_player = self.game.board.players[1]
        
        # 2. clear AI's old prompts
        if self.ai_color == 'white' and self.game.white_cast_prompt == 'in-check':
            self.game.kill_prompt(self.ai_color)
            self.game.restore_cast_prompt(self.ai_color)
        elif self.ai_color == 'black' and self.game.black_cast_prompt == 'in-check':
            self.game.kill_prompt(self.ai_color)
            self.game.restore_cast_prompt(self.ai_color)
            
        # 3. DETECT CHECK BEFORE TURN SWITCH
        if self.game.board.king_in_check(rival_player):
            print(f"[GAME] Human player ({rival_color}) is in check!")
            self.game.set_in_check_prompt(rival_color)
            
        # 4. DETECT GAME OVER
        has_no_moves = self.game.board._king_mated(rival_player)
        if self.game.board.king_mated:
            print(f"!!! CHECKMATE: Human player ({rival_color}) is mated!")
            self.game.set_mated_prompt(rival_color)
            return False  # game over, do not switch turns
             
        if self.game.board.king_stalemated:
            print(f"!!! STALEMATE !!!")
            return False # game Over
        
        if self._check_repetition_draw():
            return False
            
        # 3. SWITCH TURN
        print(f"Switching to {rival_color}'s turn (human)")
        self.game.next_turn()
        
        return True
        
        
    def ai_make_move(self):
        """AI using Negamax (Bitboards) to make moves.

        Kicks the search off on a background thread rather than blocking
        the main loop, so the render loop keeps running (and the thinking
        hourglass keeps animating) for however long the search takes.
        The actual move is applied back on the main thread by
        _poll_ai_thread() once the thread finishes.
        """
        # only run if it's AI's turn, game isn't over, and AI isn't already thinking
        if (self.game.next_player == self.ai_color and
            not self.game.board.king_mated and
            not self.game.board.king_stalemated and
            not self.ai_thinking):

            # quick sanity check
            from rampartbitboard import RampartBitboard
            from ai_engine import BitboardGameState

            bb = RampartBitboard()
            bb.sync_from_board(self.game.board)
            state = BitboardGameState(bb, self.ai_color)

            moves = state.get_legal_moves()

            if len(moves) == 0:
                print("WARNING: Bitboard says AI has no moves!")
                # check if AI king is in check
                in_check = state.attack_gen.is_king_in_check(bb, self.ai_color)
                print(f"AI king in check: {in_check}")

            self.ai_thinking = True
            self.game.hourglass.start()
            self.ai_move_result = None
            self.ai_move_error = None

            def _search():
                try:
                    self.ai_move_result = self.ai_engine.get_best_move(
                        self.game.board, self.ai_color, self.state_history, debug=False)
                except Exception as e:
                    self.ai_move_error = e

            self.ai_thread = threading.Thread(target=_search, daemon=True)
            self.ai_thread.start()

    def _poll_ai_thread(self):
        """Called once per frame; applies the AI's move on the main thread
        as soon as the background search thread finishes."""
        if not self.ai_thinking or self.ai_thread is None or self.ai_thread.is_alive():
            return

        self.ai_thread = None
        self.game.hourglass.stop()

        try:
            if self.ai_move_error is not None:
                raise self.ai_move_error

            if self.ai_move_result:
                self._apply_engine_move(self.ai_move_result)
            else:
                print("[AI] No move returned by engine.")
                self._fallback_random_move()

        except Exception as e:
            log_to_file(f"[MAIN] !!! AI MOVE EXCEPTION: {e}")
            # important: print to console so can see it immediately
            print(f"AI ERROR: {e}")
            self._fallback_random_move()
        finally:
            self.ai_move_result = None
            self.ai_move_error = None
            self.ai_thinking = False


    def _apply_engine_move(self, engine_move):
        """Executes a single EngineMove (normal / enter_queen_house / cast)
        against the live pygame board. Shared by the main AI move path and
        the random-move fallback so both go through identical execution
        logic."""
        if engine_move.move_type == 'normal':
            # convert 0-59 bitboard indices to Col/Row
            # integer // 10 = Row, integer % 10 = Column
            from_col = engine_move.from_sq % 10
            from_row = engine_move.from_sq // 10
            to_col = engine_move.to_sq % 10
            to_row = engine_move.to_sq // 10

            move_data = {
                'from_col': from_col,
                'from_row': from_row,
                'to_col': to_col,
                'to_row': to_row,
                'piece_type': engine_move.piece_type
            }

            self._execute_normal_move(move_data)

        elif engine_move.move_type == 'enter_queen_house':
            # execute occupation
            # reuse normal move logic but do not switch turns yet
            from_col = engine_move.from_sq % 10
            from_row = engine_move.from_sq // 10
            to_col = engine_move.to_sq % 10
            to_row = engine_move.to_sq // 10

            move_data = {
                'from_col': from_col, 'from_row': from_row,
                'to_col': to_col, 'to_row': to_row,
                'piece_type': 'raider'
            }

            # execute move
            if self._execute_normal_move(move_data, auto_end_turn=False):

                # execute spawn of queen
                if engine_move.spawn_sq is not None:
                    sp_col = engine_move.spawn_sq % 10
                    sp_row = engine_move.spawn_sq // 10

                    # pass 'None' for cards as not needed for initial
                    # queen spawn
                    self.game.board._raise_queen(sp_col, sp_row, \
                        engine_move.color, None)
                    self.game.play_raise_sound()
                    self.game.lightning.trigger(engine_move.color, \
                        persist_frames=10)

                    # record the spawn in the move log - without this suffix
                    # (mirroring the human click-handler's compound notation,
                    # e.g. "R5e>4f/Q@7c") the queen exists on the live board
                    # but history replay has no record of how it got there,
                    # and desyncs on its first subsequent move.
                    spawn_dst = f"{sp_col + 1}{Square.get_alpharow(5 - sp_row)}"
                    self.move_log[-1] += f"/Q@{spawn_dst}"

                self._post_move_check_validation()

        else:
            # cast move
            self._execute_cast_move(engine_move)


    def _fallback_random_move(self):
        """Last-resort recovery when the search engine returns no move, or
        raises partway through a turn: pick a uniformly random legal move
        for the AI so the game can continue instead of stalling/crashing.
        (Previously called but never defined - AI errors used to crash out
        to an unhandled AttributeError instead of recovering.)"""
        from rampartbitboard import RampartBitboard
        from ai_engine import BitboardGameState
        import random

        try:
            bb = RampartBitboard()
            bb.sync_from_board(self.game.board)
            state = BitboardGameState(bb, self.ai_color)
            moves = state.get_legal_moves()

            if not moves:
                print("[AI] Fallback: no legal moves available for AI.")
                log_to_file("[MAIN] Fallback: AI has no legal moves")
                return

            move = random.choice(moves)
            log_to_file(f"[MAIN] Fallback: playing random move {move}")
            self._apply_engine_move(move)
        except Exception as e:
            log_to_file(f"[MAIN] !!! FALLBACK MOVE EXCEPTION: {e}")
            print(f"AI FALLBACK ERROR: {e}")


    def _execute_normal_move(self, move_data, auto_end_turn=True):
        """Executes a standard board move determined by AI."""
        f_col, f_row = move_data['from_col'], move_data['from_row']
        t_col, t_row = move_data['to_col'], move_data['to_row']
        
        log_to_file(f"[AI EXEC] Moving from ({f_col},{f_row}) to ({t_col},{t_row})")
        
        # 1. Get the piece from the actual game board
        piece = self.game.board.squares[f_col][f_row].piece
        
        if not piece:
            print(f"[ERROR] AI tried to move from empty square: {f_col},{f_row}")
            self.game.next_turn() 
            return False

        # 2. recalculate valid moves for this piece (Pygame side validation)
        # ensures visual board agrees with AI's logic
        piece.clear_moves()
        self.game.board.calc_moves(piece, f_col, f_row, bool=True)
        
        # 3. create the Move object expected by your board logic
        initial = Square(f_col, f_row)
        final_piece = self.game.board.squares[t_col][t_row].piece # may be None
        final = Square(t_col, t_row, final_piece)
        
        game_move = Move(initial, final)
        
        # 4. final Validation & Execution
        if self.game.board.valid_move(piece, game_move):
            captured = self.game.board.squares[t_col][t_row].has_piece()
            if captured:
                captured_piece = self.game.board.squares[t_col][t_row].piece
                
                if captured_piece.name in ['raider', 'queen']:
                    self.game.board._send_to_grave(captured_piece)
                    
            notation = self.game.board.move(piece, game_move)
            self.move_log.append(notation)
            self.game.view_index = len(self.move_log)
            print(f"DEBUG: Move Log Update -> {self.move_log}")
             
            self.game.play_sound(captured)

            # "mate by capture": landing on the enemy's king house while their
            # king is off a card square is an immediate win, independent of
            # ordinary check/checkmate. Ported from the human-move handler
            # (this AI-move path had no equivalent check at all before this).
            # Setting the flag here is enough - _post_move_check_validation
            # already checks board.king_mated first, before it would call
            # _king_mated()/next_turn(), so it reports the win with the
            # correct color and doesn't switch turns.
            if self.game.board.squares[t_col][t_row].is_enemy_king_house(piece.color):
                if self.game.board._opponent_king_on_noncard(piece.color):
                    self.game.board.king_mated = True

            if auto_end_turn:
                self._post_move_check_validation()

            return True
            
        else:
            print(f"[CRITICAL] AI generated an illegal move: {f_col},{f_row} -> {t_col},{t_row}")
            log_to_file(f"[CRITICAL] Illegal AI move rejected by Pygame board.")
            self.game.next_turn()
            return False
            
    def _execute_cast_move(self, engine_move):
        
        # 1. coordinates
        t_col = engine_move.to_sq % 10
        t_row = engine_move.to_sq // 10
        
        # 2. identify player and suit
        ai_color = engine_move.color
        deck_suit = 1 if ai_color == 'white' else 0
        
        print(f"[AI EXEC] Executing CAST: {engine_move.move_type.upper()} at ({t_col},{t_row})")
        
        # 3. visuals: cast cards
        self.game.clicker.clicked_cards = []
        
        used_cards = []
        
        for rank_idx in engine_move.deck_cards:
            card = self.game.board.cards[deck_suit][rank_idx]
            self.game.clicker.clicked_cards.append(card)
            used_cards.append(card)
            
        self.game.cast_cards()
        self.game.clicker.clicked_cards = []
        
        # 4. execute board action
        target_sq = self.game.board.squares[t_col][t_row]
        
        piece = None
        
        cast_type_int = 0 # default to strike
        
        if engine_move.move_type == 'raise':
            piece = Raider(ai_color)
            cast_type_int = 1 # set to raise
            # self.game.board._raise_raider(t_col, t_row, ai_color, target_sq.card)
            self.game.play_raise_sound()
            self.game.lightning.trigger(ai_color, persist_frames=10)
            
        elif engine_move.move_type == 'raise_queen':
            piece = Queen(ai_color)
            cast_type_int = 1 # treated as a raise for history/UI
            # use existing board method to bring queen back
            # self.game.board._raise_queen(t_col, t_row, ai_color, target_sq.card)
            self.game.play_raise_sound()
            self.game.lightning.trigger(ai_color, persist_frames=10)
            
        elif engine_move.move_type == 'strike':
            piece = target_sq.piece
            cast_type_int = 0 # set to strike
            # if target_piece:
            #     self.game.board._send_to_grave(target_piece)
            #    target_sq.piece = None
            self.game.play_strike_sound()
            self.game.lightning.trigger(ai_color, persist_frames=10)
            
        # manually set the last move so that UI draws it --
        ai_cast_move_obj = Cast_move(used_cards, target_sq, cast_type_int)
        self.game.board.last_move = ai_cast_move_obj
        
        # pass the 'piece' object
        notation = self.game.board.cast_move(Player(ai_color), piece, target_sq.card, \
                    ai_cast_move_obj)
        self.move_log.append(notation)
        self.game.view_index = len(self.move_log)
        
        # 5. post move check detect
        self._post_move_check_validation()
        


# █▀▄ █▀█ ▄▀█ █░█░█
# █▄▀ █▀▄ █▀█ ▀▄▀▄▀

        
    def draw_command_strip(self):
        screen = self.screen
        
        base_x = 115 
        base_y = HEIGHT + RAMPART_HEIGHT - 60
        h_gap = 10
        btn_h = 25
        w_game, w_pref, w_help = 80, 120, 80 
        
        # define hitboxes
        self.btn_game = pygame.Rect(base_x, base_y, w_game, btn_h)
        self.btn_pref = pygame.Rect(self.btn_game.right + h_gap, base_y, w_pref, btn_h)
        self.btn_help = pygame.Rect(self.btn_pref.right + h_gap, base_y, w_help, btn_h)
        arrow_x = self.btn_game.right + 555
        self.btn_prev = pygame.Rect(arrow_x, base_y - 5, 35, 33) 
        self.btn_next = pygame.Rect(arrow_x + 45, base_y - 5, 35, 33) 

        mouse_pos = self._get_mouse_pos()
        bg_color = (240, 240, 245)
        base_border = (90, 90, 90)
        hover_border = (0, 0, 0) 
        
        # draw buttons
        for rect in [self.btn_game, self.btn_pref, self.btn_help, self.btn_prev, self.btn_next]:
            pygame.draw.rect(screen, bg_color, rect)
            current_border = hover_border if rect.collidepoint(mouse_pos) else base_border
            pygame.draw.rect(screen, current_border, rect, 2)

        menu_font = pygame.font.SysFont('Arial', 16, bold=True)
        arrow_font = pygame.font.SysFont('Arial', 18, bold=True)
        
        def get_color(rect):
            return (0, 0, 0) if rect.collidepoint(mouse_pos) else (100, 100, 100)

        # draw text
        for label, rect in [("Game", self.btn_game), ("Preferences", self.btn_pref), ("Help", self.btn_help)]:
            txt_surf = menu_font.render(label, True, get_color(rect))
            text_x = rect.x + (rect.width // 2 - txt_surf.get_width() // 2)
            text_y = rect.y + (rect.height // 2 - txt_surf.get_height() // 2)
            screen.blit(txt_surf, (text_x, text_y))

        screen.blit(arrow_font.render("<", True, get_color(self.btn_prev)), (self.btn_prev.x + 12, self.btn_prev.y + 6))
        screen.blit(arrow_font.render(">", True, get_color(self.btn_next)), (self.btn_next.x + 12, self.btn_next.y + 6))
        
        # --- AI LEVEL INDICATOR HERE ---
        diff_str = f"{self.game.ai_difficulty.upper()}"
        # green for easy, orange for medium, red for hard
        diff_colors = {'Easy': (0, 255, 0), 'Medium': (255, 165, 0), 'Hard': (255, 60, 60)}
        diff_color = diff_colors.get(self.game.ai_difficulty, (255, 165, 0))
        diff_surf = arrow_font.render(diff_str, True, diff_color)

        # center under the alpha-omega emblem, which show_cemetery() blits
        # at x=5 scaled to 80px wide (game.py) - so its horizontal center is
        # x=45.
        diff_x = 45 - diff_surf.get_width() // 2
        self.screen.blit(diff_surf, (diff_x, base_y + 70))
        
        
# █▀▀ █▀█ █▀▄▀█ █▀▄▀█ ▄▀█ █▄░█ █▀▄   █▀▄▀█ █▀▀ █▄░█ █░█
# █▄▄ █▄█ █░▀░█  █░▀░█ █▀█ █░▀█ █▄▀    █░▀░█ ██▄ █░▀█ █▄█
          

    def execute_menu_action(self, menu_type, index):
        """Routes sidebar clicks to the actual game logic (AI Version)"""
        if menu_type == 'game':
            if index == 0:   # Save Game
                self.game.save_naming_mode = True
            elif index == 1: # Load Game
                if not os.path.exists('saves'): 
                    os.makedirs('saves', exist_ok=True)
                self.game.save_files = [f for f in os.listdir('saves') if f.endswith('.json')]
                self.game.load_menu_mode = True
            elif index == 2: # Restart Game
                self.game.reset()
                self.ai_thinking = False
                self.move_log = []
                self.state_history = []
                self._autosaved = False
                temp_bb = RampartBitboard()
                temp_bb.sync_from_board(self.game.board)
                self.state_history.append(temp_bb.get_state_hash())
                print("Game restarted from menu!")
            elif index == 3: # Flip Board
                self.game.flip_board()
            elif index == 4: # Main Menu
                self.return_to_launcher = True
                
        elif menu_type == 'pref':
            if index == 0:   # Change Theme
                self.game.change_theme()
                self.game.change_emblem()
                self.game.change_dead_card()
            elif index == 1: # Change Pieces
                self.game.board.change_all_piece_textures()
            elif index == 2: # Toggle AI Difficulty
                self._cycle_ai_difficulty()
                
        elif menu_type == 'help':
            if index == 0:   # Rules
                self.game.show_rules_overlay = True
            elif index == 1: # Controls
                self.game.show_controls_overlay = True
                
        self.game.active_menu = None # Close menu after selection


# ╭━╮╭━┳━━━┳━━┳━╮╱╭┳╮╱╱╭━━━┳━━━┳━━━╮
# ┃┃╰╯┃┃╭━╮┣┫┣┫┃╰╮┃┃┃╱╱┃╭━╮┃╭━╮┃╭━╮┃
# ┃╭╮╭╮┃┃╱┃┃┃┃┃╭╮╰╯┃┃╱╱┃┃╱┃┃┃╱┃┃╰━╯┃
# ┃┃┃┃┃┃╰━╯┃┃┃┃┃╰╮┃┃┃╱╭┫┃╱┃┃┃╱┃┃╭━━╯
# ┃┃┃┃┃┃╭━╮┣┫┣┫┃╱┃┃┃╰━╯┃╰━╯┃╰━╯┃┃
# ╰╯╰╯╰┻╯╱╰┻━━┻╯╱╰━┻━━━┻━━━┻━━━┻╯

    
    def mainloop(self):
        
        screen = self.screen
        game = self.game
        board = game.board
        dragger = game.dragger
        clicker = game.clicker
        
        clicked_suit = None
        clicked_rank = None
        casting = False
        queen_house_raided = False
        cast_sound = None
        self.return_to_launcher = False
        
        while True:
            
            if getattr(self, 'return_to_launcher', False):
                # clean up any threads or connections
                if hasattr(self, 'cleanup'): 
                    self.cleanup()
                return
            
            if hasattr(self, 'need_refresh') and self.need_refresh:
                game = self.game  # update local reference
                board = game.board
                dragger = game.dragger
                clicker = game.clicker
                del self.need_refresh  # clear flag
                print("References refreshed!")

            # pick up the AI's move as soon as the background search
            # thread finishes, and keep the thinking hourglass animating
            # every iteration of this loop (which has no frame cap)
            self._poll_ai_thread()
            self._autosave_finished_game()
            game.hourglass.update()

            # show-methods
            screen.fill((0,0,0))
            game.show_bg(screen)
            self.draw_command_strip()
            game.show_last_move(screen)
            game.show_moves(screen)
            game.show_pieces(screen)    
            game.show_dead(screen)
            game.show_cemetery(screen)
            game.show_cast_buttons(screen)
            game.show_hover(screen)
            game.show_clicked_cards(screen)
            game.show_clicked_btns(screen)
            game.show_dead_cards(screen)
            game.show_chosen_piece(screen)
            game.show_cast_prompt(screen, self.my_color)
            
            # same game prompt
            game.show_naming_prompt(screen)
            
            # load game prompt
            game.show_load_menu(screen)
            
            # command menu and help overlays
            game.show_side_menu(screen)
            game.show_help_overlays(screen)
            
            # call AI if it's AI's turn
            if not self.game.board.king_mated and not self.game.board.king_stalemated:
                is_live = (self.game.view_index == len(self.move_log))
                
                if is_live and not self.game.lightning.active:
                    self.ai_make_move()
                
                if self.game.board.king_mated:
                    # force one final draw so the user sees the board state
                    screen.fill((0,0,0))
                    game.show_bg(screen)
                    self.draw_command_strip()
                    game.show_pieces(screen)
                    game.show_cast_buttons(screen)
                    game.show_dead(screen)
                    # ensure the prompt is drawn
                    game.show_cast_prompt(screen, self.my_color)
                    self._present()

                elif self.game.board.king_stalemated:
                    screen.fill((0,0,0))
                    game.show_bg(screen)
                    self.draw_command_strip()
                    game.show_pieces(screen)
                    game.show_cast_buttons(screen)
                    game.show_dead(screen)
                    # ensure the prompt is drawn
                    game.show_cast_prompt(screen, self.my_color)
                    self._present()

            if dragger.dragging:
                dragger.update_blit(screen)

            if hasattr(self, 'rematch_complete') and self.rematch_complete:
                self._present()
                del self.rematch_complete
            
            
            for event in pygame.event.get():
                # mouse events report real on-screen pixels; every rect this
                # file hit-tests against (board squares, buttons, cards) is
                # defined in the fixed design resolution self.screen draws
                # to - rewrite event.pos once here rather than at each of
                # the many places below that read it.
                if hasattr(event, 'pos'):
                    event.pos = (int(event.pos[0] / self.ui_scale), int(event.pos[1] / self.ui_scale))

                if self.ai_thinking:
                    # only allow quitting
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    # skip ALL other events
                    continue
                
                if not board.king_mated and not board.king_stalemated:
                    
                    if game.next_state == 'update1':
                        
                        if game.lightning.active:
                            game.lightning.update()
                            if game.lightning.persist_frames > 0:
                                game.lightning.persist_frames -= 1
                            else:
                                game.lightning.active = False
                        
                        
                        # draw all game elements
                        screen.fill((0,0,0))
                        game.show_bg(screen)
                        self.draw_command_strip()
                        game.show_last_move(screen)
                        game.show_moves(screen)
                        game.show_pieces(screen)
                        game.show_dead(screen)
                        game.show_cemetery(screen)
                        game.show_cast_buttons(screen)
                        game.show_hover(screen)
                        game.show_clicked_cards(screen)
                        game.show_clicked_btns(screen)
                        game.show_dead_cards(screen)
                        game.show_chosen_piece(screen)
                        game.show_cast_prompt(screen, self.my_color)
                        
                        # draw lightning if active
                        if game.lightning.active:
                            
                            # force a small delay to ensure animation is visible
                            pygame.time.delay(30)
                            
                            screen.fill((255,255,255))
                            game.show_bg(screen)
                            self.draw_command_strip()
                            game.show_last_move(screen)
                            game.show_moves(screen)
                            game.show_pieces(screen)
                            game.show_cemetery(screen)
                            game.show_cast_buttons(screen)
                            game.show_hover(screen)
                            game.show_clicked_cards(screen)
                            game.show_clicked_btns(screen)
                            game.show_dead_cards(screen)
                            game.show_chosen_piece(screen)
                            game.show_cast_prompt(screen, self.my_color)
                            game.lightning.draw(screen)
                            
                            if cast_sound == 'strike':
                                game.play_strike_sound()
                            elif cast_sound == 'raise':
                                game.play_raise_sound()
                            
                            cast_sound = None
                            
                        else:
                            # small delay to ensure animation is visible
                            pygame.time.delay(30)
                                
                            game.show_bg(screen)
                            self.draw_command_strip()
                            game.show_last_move(screen)
                            game.show_moves(screen)
                            game.show_pieces(screen)
                            game.show_dead(screen)
                            game.show_cemetery(screen)
                            game.show_cast_buttons(screen)
                            game.show_hover(screen)
                            game.show_clicked_cards(screen)
                            game.show_clicked_btns(screen)
                            game.show_dead_cards(screen)
                            game.show_chosen_piece(screen)
                            game.show_cast_prompt(screen, self.my_color)
                        
                        game.change_state()
                        
                    elif game.next_state == "update2":
                        
                        pygame.time.delay(30)
                            
                        game.show_bg(screen)
                        self.draw_command_strip()
                        game.show_last_move(screen)
                        game.show_moves(screen)
                        game.show_pieces(screen)
                        game.show_dead(screen)
                        game.show_cemetery(screen)
                        game.show_cast_buttons(screen)
                        game.show_hover(screen)
                        game.show_clicked_cards(screen)
                        game.show_clicked_btns(screen)
                        game.show_dead_cards(screen)
                        game.show_chosen_piece(screen)
                        game.show_cast_prompt(screen, self.my_color)
                        
                        game.change_state()
                    

# █▀▄▀█ █▀█ █░█ █▀ █▀▀ █▄▄ █░█ ▀█▀ ▀█▀ █▀█ █▄░█ █▀▄ █▀█ █░█░█ █▄░█
# █░▀░█ █▄█ █▄█ ▄█ ██▄  █▄█ █▄█ ░█░ ░█░ █▄█ █░▀█ █▄▀ █▄█ ▀▄▀▄▀ █░▀█
                    
                    # mouse click
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        
                        # close overlays when clicking board
                        if self.game.save_naming_mode or self.game.load_menu_mode:
                            if event.pos[0] < WIDTH: 
                                self.game.save_naming_mode = False
                                self.game.load_menu_mode = False
                                continue
                                
                        # --- COMMAND CENTER CLICK INTERCEPT ---
                        if hasattr(self, 'btn_game') and event.button == 1: 
                            mouse_pos = event.pos
                            
                            # 1. check history arrows (< and >)
                            if hasattr(self, 'btn_prev') and self.btn_prev.collidepoint(mouse_pos):
                                if self.game.view_index > 0:
                                    # Viewing history only makes sense at the live
                                    # position - drop any in-progress card/button
                                    # selection rather than carry it along.
                                    clicker.unclick_all_cards()
                                    clicker.unclick_btn()
                                    casting = False
                                    self.game.view_index -= 1
                                    self.game.reconstruct_at_move(self.game.view_index, self.move_log)
                                    board = self.game.board
                                    dragger.board = board
                                    clicker.board = board
                                continue

                            elif hasattr(self, 'btn_next') and self.btn_next.collidepoint(mouse_pos):
                                if self.game.view_index < len(self.move_log):
                                    clicker.unclick_all_cards()
                                    clicker.unclick_btn()
                                    casting = False
                                    self.game.view_index += 1
                                    self.game.reconstruct_at_move(self.game.view_index, self.move_log)
                                    board = self.game.board
                                    dragger.board = board
                                    clicker.board = board
                                continue

                            # 2. check sidebar toggle buttons
                            if self.btn_game.collidepoint(mouse_pos):
                                self.game.active_menu = 'game' if getattr(self.game, 'active_menu', None) != 'game' else None
                                continue
                            elif self.btn_pref.collidepoint(mouse_pos):
                                self.game.active_menu = 'pref' if getattr(self.game, 'active_menu', None) != 'pref' else None
                                continue
                            elif self.btn_help.collidepoint(mouse_pos):
                                self.game.active_menu = 'help' if getattr(self.game, 'active_menu', None) != 'help' else None
                                continue
                            
                            # 3. check if active menu is open and clicked
                            if getattr(self.game, 'active_menu', None):
                                if mouse_pos[0] >= WIDTH:  # clicked inside the sidebar area
                                    clicked_index = (mouse_pos[1] - 240) // 40
                                    if 0 <= clicked_index < 4:
                                        self.execute_menu_action(self.game.active_menu, clicked_index)
                                    continue
                                else:
                                    # clicked outside the menu, auto-close it!
                                    self.game.active_menu = None
                        # --- END COMMAND CENTER ---
                        
                        if self.game.view_index == len(self.move_log):
                            dragger.update_mouse(event.pos)
                            clicker.update_mouse(event.pos)
                            
                            # first get all possible positions using the new methods
                            clicked_col, clicked_row = game.get_board_position(event.pos[0], event.pos[1])
                            clicked_suit, clicked_rank = game.get_card_position(event.pos[0], event.pos[1])
                            
                            if dragger.mouseX < 100:  # left side (black deck/graveyard)
                                clicked_col = 0
                                clicked_row = 5
                                if 2 <= dragger.mouseX <= 2 + CWIDTH:  # card deck area
                                    clicked_suit, clicked_rank = game.get_card_position(event.pos[0], event.pos[1])
                                    
                            elif dragger.mouseX >= 900:  # right side (white deck/graveyard)
                                clicked_col = 9
                                clicked_row = 5
                                if 902 <= dragger.mouseX <= 902 + CWIDTH:  # card deck area
                                    clicked_suit, clicked_rank = game.get_card_position(event.pos[0], event.pos[1])
                                
                            if clicked_col is not None:  # clicked on main board
                                clicked_bsq = board.squares[clicked_col][clicked_row]

                                if len(clicker.clicked_cards) > 0 and clicked_bsq.is_card() and \
                                    clicked_bsq.has_piece() and clicked_row not in [0, 5] and \
                                        clicker.is_clicked(clicked_bsq.card):
                                    # Clicking one of our own already-highlighted board
                                    # cards always unselects it, regardless of whether a
                                    # STRIKE/RAISE button is currently committed - card
                                    # (de)selection order shouldn't matter to the player.
                                    # Since a committed button only ever means "the
                                    # currently-highlighted cards are a legal combo",
                                    # changing the cards un-commits it too.
                                    clicker.unclick_card(clicked_bsq.card)
                                    clicker.unclick_btn()
                                    casting = False
                                    # play sound
                                    game.play_card_sound()
                                    # show methods
                                    game.show_bg(screen)
                                    self.draw_command_strip()
                                    game.show_last_move(screen)
                                    game.show_moves(screen)
                                    game.show_pieces(screen)
                                    game.show_clicked_cards(screen)
                                    game.show_dead(screen)
                                    game.show_dead_cards(screen)
                                    if len(clicker.clicked_cards) == 0:
                                        game.set_cast_prompt(game.next_player)
                                    else:
                                        game.set_make_21_prompt(game.next_player)

                                elif clicker.clicked_btn == None:
                                    if len(clicker.clicked_cards) > 0:
                                        if clicked_bsq.is_card() and clicked_bsq.has_piece() and \
                                                clicked_row not in [0, 5]:
                                            card = clicked_bsq.card
                                            piece = clicked_bsq.piece
                                            if piece.name == 'raider' and \
                                                    piece.color == game.next_player:
                                                clicker.explic_save_card(card)
                                                clicker.click_card(card)
                                                # play sound
                                                game.play_card_sound()
                                                # show methods
                                                game.show_bg(screen)
                                                self.draw_command_strip()
                                                game.show_last_move(screen)
                                                game.show_moves(screen)
                                                game.show_pieces(screen)
                                                game.show_clicked_cards(screen)
                                                game.show_dead(screen)
                                                game.show_dead_cards(screen)

                                                if clicker.has_sum_21(clicker.clicked_cards):
                                                    game.set_choose_cast_prompt(game.next_player)
                                    else:
                                        # clicked square has a piece?
                                        if clicked_bsq.has_piece():
                                            piece = clicked_bsq.piece
                                            # check if piece (color) is valid
                                            if piece.color == game.next_player and \
                                                self.my_color == game.next_player:

                                                board.calc_moves(piece, clicked_col, clicked_row, bool=True)

                                                dragger.save_initial(clicked_col, clicked_row)
                                                dragger.drag_piece(piece)
                                                # show methods
                                                game.show_bg(screen)
                                                self.draw_command_strip()
                                                game.show_last_move(screen)
                                                game.show_moves(screen)
                                                game.show_pieces(screen)
                                                game.show_clicked_cards(screen)
                                                game.show_dead(screen)
                                                game.show_dead_cards(screen)

        
                            if ((2 <= clicker.mouseX <= 2+CWIDTH and clicker.mouseY <= 800-CEM_HEIGHT) or 
                                (902 <= clicker.mouseX <= 902+CWIDTH and CEM_HEIGHT <= clicker.mouseY <= 800)):
                                clicked_suit, clicked_rank = game.get_card_position(event.pos[0], event.pos[1])
                                if clicked_suit is not None and clicked_rank is not None:  # click was on a card in deck
                                    if not board.cards[clicked_suit][clicked_rank].is_cast():
                                        if not clicker.is_clicked(board.cards[clicked_suit][clicked_rank]):
                                            card = board.cards[clicked_suit][clicked_rank]
                                            if (card.suit == 0 and game.next_player == 'black') or \
                                               (card.suit == 1 and game.next_player == 'white'):
                                                # check if jack house is occupied for casting
                                                jack_col = 5 if game.next_player == 'black' else 4
                                                jack_row = 5 if game.next_player == 'black' else 0
                                                if board.squares[jack_col][jack_row].has_piece():
                                                    clicker.save_card(event.pos)
                                                    clicker.click_card(card)
                                                    game.play_card_sound()
                                                    game.set_make_21_prompt(game.next_player)
                                                    if clicker.has_sum_21(clicker.clicked_cards):
                                                        game.set_choose_cast_prompt(game.next_player)
                                        else:
                                            mouse_x, mouse_y = event.pos
                                            in_deck_area = (
                                                (0 <= mouse_x < 100 and 0 <= mouse_y < HEIGHT - CEM_HEIGHT - 10) or
                                                (900 <= mouse_x <= 1000 and 800 - 13 * CHEIGHT <= mouse_y < HEIGHT)
                                            )
                                            
                                            if in_deck_area:
                                                clicker.unclick_card(board.cards[clicked_suit][clicked_rank])
                                                # A committed STRIKE/RAISE only ever means
                                                # "the highlighted cards are a legal combo" -
                                                # changing the cards un-commits it too.
                                                clicker.unclick_btn()
                                                casting = False
                                                game.play_card_sound()
                                                if len(clicker.clicked_cards) == 0:
                                                    game.set_cast_prompt(game.next_player)
                                                else:
                                                    game.set_make_21_prompt(game.next_player)
                                                

# █▀▄▀█ █▀█ █░█ █▀ █▀▀ █▀▄▀█ █▀█ ▀█▀ █ █▀█ █▄░█
# █░▀░█ █▄█ █▄█ ▄█ ██▄  █░▀░█ █▄█ ░█░ █ █▄█ █░▀█

                    
                    elif event.type == pygame.MOUSEMOTION:
                        # initialize variables at the start
                        hover_col, hover_row = None, None
                        hover_suit, hover_rank = None, None
                        
                        # clear all hovers first
                        game.hovered_sqr = None
                        game.hovered_crd = None
                        game.hovered_btn = None
                        game.hovered_dom = None
                        game.hovered_grave = None
                    
                        # get mouse position
                        mouse_x, mouse_y = event.pos
                    
                        # 1. handle graveyard hover in specific context
                        if (not clicker.clicked_grv and clicker.clicked_btn == 1 and 
                            board._enemy_queen_house_occupied(game.next_player) and 
                            board._queen_isdead(game.next_player)):
                            
                            # determine logical grave column (0=black, 1=white)
                            grave_col = 0 if game.next_player == 'black' else 1
                            
                            # calculate visual positions based on flip
                            if game.flipped:
                                # visual positions swap but logical ownership stays the same
                                visual_left = grave_col == 1  # white graves appear left when flipped
                            else:
                                visual_left = grave_col == 0  # black graves are left normally
                            
                            # set area coordinates based on visual position
                            if visual_left:
                                grave_area_x = 0
                                grave_area_y = HEIGHT - CEM_HEIGHT + 65
                            else:
                                grave_area_x = 900
                                grave_area_y = 90
                            
                            # check mouse in visual area
                            if (grave_area_x <= mouse_x < grave_area_x + 100 and
                                grave_area_y <= mouse_y < grave_area_y + GHEIGHT * 9):
                                
                                # calculate row (same for both orientations)
                                grave_row = min(8, (mouse_y - grave_area_y) // GHEIGHT)
                                
                                # set hover using LOGICAL grave column
                                try:
                                    grave = board.graves[grave_col][grave_row]
                                    if grave.has_piece() and grave.piece.name in ['raider', 'queen']:
                                        game.set_grave_hover(grave_col, grave_row)
                                except IndexError:
                                    game.set_grave_hover(None, None)
                            else:
                                game.set_grave_hover(None, None)
                        
                    
                        # 2. handle destination hover after grave selection
                        if (clicker.clicked_grv and clicker.clicked_btn == 1 and
                            board._enemy_queen_house_occupied(game.next_player) and 
                            board._queen_isdead(game.next_player)):
                            
                            hover_col, hover_row = game.get_board_position(mouse_x, mouse_y)
                            if hover_col is not None and hover_row is not None:
                                # check valid placement area (white: rows 3-5, black: rows 1-3)
                                valid_rows = (3, 4) if game.next_player == 'white' else (1, 2)
                                if hover_row in valid_rows:
                                    dest_sq = board.squares[hover_col][hover_row]
                                    if dest_sq.is_empty():
                                        game.set_dom_hover(hover_col, hover_row)
                    
                        # 3. handle card deck hovers
                        if mouse_y <= 800:
                            if mouse_x < 100:  # left edge (black deck)
                                hover_col = 0
                                hover_suit = 0
                                hover_rank = mouse_y // CHEIGHT if (mouse_y // CHEIGHT) <= 12 else 12
                                game.set_crd_hover(hover_suit, hover_rank)
                                
                            elif mouse_x >= 900:  # right edge (white deck)
                                hover_col = 9
                                hover_suit = 1
                                if (mouse_y - CEM_HEIGHT - RAMPART_HEIGHT) >= 0:
                                    hover_rank = 12 - ((mouse_y - CEM_HEIGHT - RAMPART_HEIGHT) // CHEIGHT) if \
                                        12 - ((mouse_y - CEM_HEIGHT - RAMPART_HEIGHT) // CHEIGHT) >= 0 else 0
                                else:
                                    hover_rank = 12
                                game.set_crd_hover(hover_suit, hover_rank)
                    
                        # 4. handle button hover
                        if mouse_y > 800:  # button area
                            if 102 <= mouse_x <= 202:
                                game.set_btn_hover(0)
                            elif 205 <= mouse_x <= 288:
                                game.set_btn_hover(1)
                    
                        # 5. handle board square hover
                        hover_col, hover_row = game.get_board_position(mouse_x, mouse_y)
                        if hover_col is not None and hover_row is not None:
                            game.set_sq_hover(hover_col, hover_row)
                    
                            # handle dragging
                            if dragger.dragging:
                                dragger.update_mouse(event.pos)
                                # update display
                                game.show_bg(screen)
                                self.draw_command_strip()
                                game.show_last_move(screen)
                                game.show_moves(screen)
                                game.show_pieces(screen)
                                game.show_clicked_cards(screen)
                                game.show_dead(screen)
                                game.show_dead_cards(screen)
                                game.show_hover(screen)
                                dragger.update_blit(screen)
                    
                       # 6. handle casting hover
                        if casting and not queen_house_raided:
                            # get display coordinates first
                            display_col = (mouse_x - 100) // RWIDTH
                            display_row = mouse_y // RHEIGHT
                            
                            # convert to board coordinates
                            if game.flipped:
                                board_col = COLS - 1 - display_col
                                board_row = ROWS - 1 - display_row
                            else:
                                board_col = display_col
                                board_row = display_row
                            
                            # validate board coordinates
                            if 0 <= board_col < COLS and 0 <= board_row < ROWS:
                                hover_sq = board.squares[board_col][board_row]
                                player = board.players[0] if game.next_player == 'black' else board.players[1]
                                
                                if clicker.clicked_btn == 0:  # strike
                                    move = Cast_move(clicker.clicked_cards, hover_sq, 0)
                                    if board.valid_cast_move(player, move):
                                        game.set_dom_hover(board_col, board_row)
                                        
                                elif clicker.clicked_btn == 1:  # raise
                                    valid_rows = range(3, 5) if game.next_player == 'white' else range(1, 3)
                                    if board_row in valid_rows and hover_sq.is_empty():
                                        move = Cast_move(clicker.clicked_cards, hover_sq, 1)
                                        print("CAST LIST SIZE:", len(player.cast_moves))
                                        if board.valid_cast_move(player, move):
                                            game.set_dom_hover(board_col, board_row)
                    
                        # 7. handle queen placement hover
                        if not casting and queen_house_raided and hover_col is not None and hover_row is not None:
                            # get fresh display coordinates (0-9 cols, 0-5 rows)
                            display_col = (mouse_x - 100) // RWIDTH
                            display_row = mouse_y // RHEIGHT
                            
                            # convert to board coordinates for validation
                            if game.flipped:
                                board_col = COLS - 1 - display_col
                                board_row = ROWS - 1 - display_row
                            else:
                                board_col = display_col
                                board_row = display_row
                            
                            # validate placement rows in BOARD coordinates
                            valid_rows = range(3, 5) if game.next_player == 'white' else range(1, 3)
                            if board_row in valid_rows:
                                hover_sq = board.squares[board_col][board_row]
                                if hover_sq.piece is None:
                                    # pass display coordinates to maintain existing behavior
                                    game.set_dom_hover(board_col, board_row)
                                    game.set_raise_queen_prompt(game.next_player)
                                    

# █▀▄▀█ █▀█ █░█ █▀ █▀▀ █▄▄ █░█ ▀█▀ ▀█▀ █▀█ █▄░█ █░█ █▀█
# █░▀░█ █▄█ █▄█ ▄█ ██▄  █▄█ █▄█ ░█░ ░█░ █▄█ █░▀█ █▄█ █▀▀
                    
                    # click release
                    elif event.type == pygame.MOUSEBUTTONUP:
                        if dragger.dragging:
                            dragger.update_mouse(event.pos)
                            
                            released_row = dragger.mouseY // RHEIGHT
                            released_col = (dragger.mouseX - 100) // RWIDTH
                            
                            # convert to board coordinates if flipped
                            if game.flipped:
                                released_col = COLS - 1 - released_col
                                released_row = ROWS - 1 - released_row
                            
                            # create possible move
                            initial = Square(dragger.initial_col, dragger.initial_row)
                            final = Square(released_col, released_row)
                            move = Move(initial, final)
    
                            # valid move?
                            if board.valid_move(dragger.piece, move):
                                captured = board.squares[released_col][released_row].\
                                    has_piece()
                                captured_piece = board.squares[released_col][released_row].piece
                                if captured and captured_piece.name in ['raider', 'queen']:
                                    board._send_to_grave(captured_piece)
                                    
                                if not (released_col == 3 and released_row == 0) and \
                                    not (released_col == 6 and released_row == 5):
                                    
                                    notation = board.move(dragger.piece, move)
                                    self.move_log.append(notation)
                                    self.game.view_index = len(self.move_log)
                                    print(f"DEBUG: Move Log Update -> {self.move_log}")
                                    
                                    # sounds
                                    game.play_sound(captured)
                                    # show methods
                                    game.show_bg(screen)
                                    self.draw_command_strip()
                                    # show last move
                                    game.show_last_move(screen)
                                    # show pieces
                                    game.show_pieces(screen)
                                    # show clicked cards
                                    game.show_clicked_cards(screen)
                                    # show dead pieces
                                    game.show_dead(screen)
                                    
                                    game.show_dead_cards(screen)
                                    
                                    rival_player = board.players[1] if game.next_player == 'black' else \
                                        board.players[0]
                                        
                                    if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                        self.game.kill_prompt(self.my_color)
                                        self.game.restore_cast_prompt(self.my_color)
                                    elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                        self.game.kill_prompt(self.my_color)
                                        self.game.restore_cast_prompt(self.my_color)
                                        
                                    if board.squares[released_col][released_row].is_enemy_jack_house(game.next_player):
                                        game.set_cast_prompt(game.next_player)
                                        
                                    if board.squares[released_col][released_row].is_enemy_king_house(game.next_player):
                                        if board._opponent_king_on_noncard(game.next_player):
                                            board.king_mated = True

                                    if board.king_mated:
                                        # "mate by capture": the rival's own king house was just
                                        # infiltrated while their king was off a card square.
                                        # Checked first and separately from the ordinary
                                        # checkmate call below, since the rival can easily still
                                        # have legal moves available - board._king_mated() alone
                                        # would return False here and fall through to
                                        # game.next_turn(), silently discarding this flag and
                                        # letting the game continue past the mate.
                                        game.set_mated_prompt(rival_player.color)
                                    elif board._king_mated(rival_player):
                                        game.set_mated_prompt(rival_player.color)
                                    else:
                                        # next turn/player
                                        game.next_turn()
                                    
                                else:
                                    if board._queen_isdead(game.next_player):
    
                                        queen_house_raided = True
                                        
                                        # 1. capture infiltration move
                                        inf_notation = board.move(dragger.piece, move)
                                        self.move_log.append(inf_notation)
                                        
                                        # sounds
                                        game.play_sound(captured)
                                        # show methods
                                        game.show_bg(screen)
                                        self.draw_command_strip()
                                        # show last move
                                        game.show_last_move(screen)
                                        # show pieces
                                        game.show_pieces(screen)
                                        # show clicked cards
                                        game.show_clicked_cards(screen)
                                        # show dead pieces
                                        game.show_dead(screen)
                                        
                                        game.show_dead_cards(screen)
                                        
                                    else:
                                        
                                        board.move(dragger.piece, move)
                                        
                                        # sounds
                                        game.play_sound(captured)
                                        # show methods
                                        game.show_bg(screen)
                                        self.draw_command_strip()
                                        # show last move
                                        game.show_last_move(screen)
                                        # show pieces
                                        game.show_pieces(screen)
                                        # show clicked cards
                                        game.show_clicked_cards(screen)
                                        # show dead pieces
                                        game.show_dead(screen)
                                        
                                        game.show_dead_cards(screen)
                                        
                                        game.next_turn()
                                        
                        else:
                            mouse_x, mouse_y = event.pos
                            if mouse_y > 800:
                                if clicker.clicked_btn == None:
                                    if 102 <= mouse_x <= 202:
                                        if len(clicker.clicked_cards) > 0:
                                            if clicker.has_2_raider_cards(clicker.clicked_cards) and clicker.has_sum_21(clicker.clicked_cards):
                                                clicker.clicked_btn = 0

                                                player = board.players[1] if game.next_player == 'white' \
                                                    else board.players[0]

                                                board.calc_cast_moves(player, None, booL=True, known_combo=clicker.clicked_cards)

                                                if len(player.cast_moves) == 0:
                                                    clicker.unclick_btn()
                                                    game.set_no_strike_prompt(game.next_player)
                                                else:
                                                    game.set_strike_prompt(game.next_player)
                                                    casting = True
                                                    game.show_clicked_btns(screen)

                                                game.play_card_sound()

                                            elif clicker.has_sum_21(clicker.clicked_cards):
                                                # A legal 21 combo, but it doesn't have the
                                                # two board cards striking needs - tell the
                                                # player why, instead of the click doing
                                                # nothing at all.
                                                game.set_strike_needs_two_board_prompt(game.next_player)
                                                game.play_card_sound()

                                    elif 205 <= mouse_x <= 288:
                                        if len(clicker.clicked_cards) > 0:
                                            if clicker.has_board_card() and clicker.has_sum_21(clicker.clicked_cards):
                                                clicker.clicked_btn = 1

                                                player = board.players[1] if game.next_player == 'white' \
                                                        else board.players[0]

                                                board.calc_cast_moves(player, Raider(game.next_player), booL=True, known_combo=clicker.clicked_cards)

                                                if len(player.cast_moves) == 0:
                                                    clicker.unclick_btn()
                                                    game.set_no_raise_prompt(game.next_player)
                                                else:
                                                    if not board._enemy_queen_house_occupied(game.next_player) or \
                                                        not board._queen_isdead(game.next_player) or \
                                                            not clicker.has_2_raider_cards(clicker.clicked_cards):

                                                        game.set_raise_prompt(game.next_player)
                                                        print(f"Valid moves: {[(m.cast_type, [c.rank for c in m.cards]) for m in player.cast_moves]}")

                                                    else:
                                                        game.set_choose_grave_prompt(game.next_player)

                                                    casting = True
                                                    game.show_clicked_btns(screen)

                                                game.play_card_sound()
                                                    
                                else:
                                    if 102 <= mouse_x <= 202:
                                        game.play_card_sound()
                                        clicker.unclick_btn()
                                        # Cancelling an already-committed cast button
                                        # unselects every highlighted card too, so the
                                        # player always returns to a clean slate here
                                        # rather than needing to unclick cards one by
                                        # one afterwards.
                                        clicker.unclick_all_cards()
                                        clicker.unclick_grv()
                                        game.kill_dom_hover()
                                        game.kill_grave_hover()
                                        casting = False
                                        game.set_cast_prompt(game.next_player)

                                    elif 205 <= mouse_x <= 288:
                                        game.play_card_sound()
                                        clicker.unclick_btn()
                                        clicker.unclick_all_cards()
                                        clicker.unclick_grv()
                                        game.kill_dom_hover()
                                        game.kill_grave_hover()
                                        casting = False
                                        game.set_cast_prompt(game.next_player)


                            else:
                                clicked_col = max(0, min(COLS-1, (mouse_x - 100) // RWIDTH))
                                clicked_row = max(0, min(ROWS-1, mouse_y // RHEIGHT))
                                # clicked_col = (mouse_x - 100) // RWIDTH if mouse_x < 900 else 9
                                # clicked_row = mouse_y // RHEIGHT if mouse_y < 800 else 5
                                if game.flipped:
                                    clicked_col = COLS - 1 - clicked_col
                                    clicked_row = ROWS - 1 - clicked_row
                                
                                clicked_sq = board.squares[clicked_col][clicked_row]
                                if not queen_house_raided:
                                    if clicker.clicked_btn == 0:
                                        rAnge = range(1, 3) if self.my_color == 'white' else range(3, 5)
                                        if clicked_sq.has_piece() and clicked_sq.piece.name == \
                                            'raider' and clicked_row in rAnge and \
                                                game.next_player != clicked_sq.piece.color:
                                            
                                            cast_type = clicker.clicked_btn
                                            cards = clicker.clicked_cards.copy()
                                            
                                            clicker.unclick_btn()
                                            game.cast_cards()
                                            casting = False
                                            
                                            player = board.players[1] if game.next_player == 'white' \
                                                else board.players[0]
                                            final = clicked_sq
                                            move = Cast_move(cards, final, cast_type)
                                            
                                            if board.valid_cast_move(player, move):
                                            
                                                card = clicked_sq.card
                                                piece = Raider(game.next_player)
                                                
                                                notation = board.cast_move(player, piece, card, move)
                                                self.move_log.append(notation)
                                                self.game.view_index = len(self.move_log)
                                                
                                                game.set_cast_prompt(game.next_player)
                                                game.kill_dom_hover()
                                                game.show_bg(screen)
                                                self.draw_command_strip()
                                                game.show_last_move(screen)
                                                game.show_pieces(screen)
                                                game.show_clicked_cards(screen)
                                                game.show_dead(screen)
                                                game.show_dead_cards(screen)
                                                
                                                game.lightning.trigger(game.next_player, persist_frames=10)
                                                cast_sound = 'strike'
                                                
                                                rival_player = board.players[1] if game.next_player == 'black' else \
                                                    board.players[0]
                                                    
                                                if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                                    self.game.kill_prompt(self.my_color)
                                                    self.game.restore_cast_prompt(self.my_color)
                                                elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                                    self.game.kill_prompt(self.my_color)
                                                    self.game.restore_cast_prompt(self.my_color)
                                        
                                                if board._king_mated(rival_player):
                                                    game.set_mated_prompt(rival_player.color)
                                                else:
                                                    # next turn/player
                                                    game.next_turn()
                                            
                                            
                                    elif clicker.clicked_btn == 1:
                                        
                                        if not board._enemy_queen_house_occupied(game.next_player) or \
                                            not clicker.has_2_raider_cards(clicker.clicked_cards) or not \
                                            board._queen_isdead(game.next_player):
                                                    
                                            cast_type = clicker.clicked_btn
                                            cards = clicker.clicked_cards
                                                    
                                            player = board.players[1] if game.next_player == 'white' \
                                                else board.players[0]
                                            final = clicked_sq
                                            move = Cast_move(cards, final, cast_type)
                                            
                                            if board.valid_cast_move(player, move):
                                            
                                                piece = Raider(game.next_player)
                                                card = clicked_sq.card
                                                
                                                notation = board.cast_move(player, piece, card, move)
                                                self.move_log.append(notation)
                                                self.game.view_index = len(self.move_log)
                                                
                                                clicker.unclick_btn()
                                                game.cast_cards()
                                                casting = False
                                                
                                                game.set_cast_prompt(game.next_player)
                                                game.kill_dom_hover()
                                                game.show_bg(screen)
                                                self.draw_command_strip()
                                                game.show_last_move(screen)
                                                game.show_pieces(screen)
                                                game.show_clicked_cards(screen)
                                                game.show_dead(screen)
                                                game.show_dead_cards(screen)
                                                
                                                game.lightning.trigger(game.next_player, persist_frames=10)
                                                cast_sound = 'raise'
                                                
                                                rival_player = board.players[1] if game.next_player == 'black' else \
                                                    board.players[0]
                                                    
                                                if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                                    self.game.kill_prompt(self.my_color)
                                                    self.game.restore_cast_prompt(self.my_color)
                                                elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                                    self.game.kill_prompt(self.my_color)
                                                    self.game.restore_cast_prompt(self.my_color)
                                                    
                                                if board._king_mated(rival_player):
                                                    
                                                    game.set_mated_prompt(rival_player.color)
                                                else:
                                                    # next turn/player
                                                    game.next_turn()
                                                    
                                        else:
                                            logical_grave_col = 0 if game.next_player == 'black' else 1

                                            # calculate visual positions based on flip
                                            if game.flipped:
                                                visual_left = (logical_grave_col == 1)  # white graves appear left when flipped
                                            else:
                                                visual_left = (logical_grave_col == 0)  # black graves appear left normally
                                            
                                            # check clicks in the correct VISUAL area
                                            if (visual_left and mouse_x < 100) or (not visual_left and mouse_x >= 900):
                                                # calculate clicked row
                                                grave_area_y = (HEIGHT - CEM_HEIGHT + 65) if visual_left else 90
                                                grave_row = (mouse_y - grave_area_y) // GHEIGHT
                                                grave_row = max(0, min(8, grave_row))  # nail to valid range
                                                
                                                # get grave (using LOGICAL column)
                                                clicked_grv = board.graves[logical_grave_col][grave_row]
                                                if clicked_grv.has_piece():
                                                    if not clicker.clicked_grv:
                                                        
                                                        game.play_card_sound()
                                                        clicker.explic_save_grv(clicked_grv)
                                                        clicker.click_grv(clicked_grv)
                                                        
                                                        piece = clicked_grv.piece
                                                        player = board.players[1] if game.next_player == 'white' else \
                                                            board.players[0]
                                                            
                                                        board.calc_cast_moves(player, piece, booL=True, known_combo=clicker.clicked_cards)
                                                        
                                                        game.show_chosen_piece(screen)
                                                        
                                                        if piece.name == 'raider':
                                                            game.set_raise_prompt(game.next_player)
                                                        elif piece.name == 'queen':
                                                            game.set_raise_queen_prompt(game.next_player)
                                                        
                                                    elif clicker.clicked_grv == clicked_grv:
                                                        game.play_card_sound()
                                                        clicker.unclick_grv()
                                                        game.show_chosen_piece(screen)
                                                        
                                                        
                                            elif dragger.mouseX >= 100 and dragger.mouseX < 900:
                                                if clicker.clicked_grv:
                                                    cast_type = clicker.clicked_btn
                                                    cards = clicker.clicked_cards
                                                    print("CLICKER:", cards)
                                                    
                                                    player = board.players[1] if game.next_player == 'white' \
                                                        else board.players[0]
                                                    final = clicked_sq
                                                    move = Cast_move(cards, final, cast_type)
                                                    
                                                    if board.valid_cast_move(player, move):
                                                        piece = clicker.clicked_grv.piece
                                                        card = clicked_sq.card
                                                        
                                                        notation = board.cast_move(player, piece, card, move)
                                                        self.move_log.append(notation)
                                                        self.game.view_index = len(self.move_log)
                                                        
                                                        clicker.unclick_btn()
                                                        clicker.unclick_grv()
                                                        game.cast_cards()
                                                        casting = False
                                                        
                                                        game.set_cast_prompt(game.next_player)
                                                        game.kill_dom_hover()
                                                        game.kill_grave_hover()
                                                        game.show_bg(screen)
                                                        self.draw_command_strip()
                                                        game.show_last_move(screen)
                                                        game.show_pieces(screen)
                                                        game.show_clicked_cards(screen)
                                                        game.show_dead(screen)
                                                        game.show_dead_cards(screen)
                                                        
                                                        game.lightning.trigger(game.next_player, persist_frames=10)
                                                        cast_sound = 'raise'
                                                        
                                                        rival_player = board.players[1] if game.next_player == 'black' else \
                                                            board.players[0]
                                                            
                                                        if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                                            self.game.kill_prompt(self.my_color)
                                                            self.game.restore_cast_prompt(self.my_color)
                                                        elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                                            self.game.kill_prompt(self.my_color)
                                                            self.game.restore_cast_prompt(self.my_color)
                                                            
                                                        if board._king_mated(rival_player):
                                                            
                                                            game.set_mated_prompt(rival_player.color)
                                                        else:
                                                            # next turn/player
                                                            game.next_turn()
                                                            
                                                            
                                else:
                                    if game.next_player == 'white' and (clicked_row >= 3 and \
                                            clicked_row <= 5):
                                        if clicked_sq.piece == None:
                                            
                                            board._raise_queen(clicked_col, clicked_row, \
                                                game.next_player, clicked_sq.card)
                                            
                                            queen_house_raided = False
                                            
                                            
                                            final = clicked_sq
                                            cards = clicker.clicked_cards
                                            move = Cast_move(cards, final, 1)
                                            
                                            player = board.players[1]
                                            piece = board.squares[clicked_col][clicked_row].piece
                                            card = clicked_sq.card
                                            
                                            board.cast_move(player, piece, card, move)
                                            
                                            # 2. add spawn suffix
                                            spawn_dst = f"{clicked_col + 1}{Square.get_alpharow(5 - clicked_row)}"
                                            self.move_log[-1] += f"/Q@{spawn_dst}"
                                            self.game.view_index = len(self.move_log)
                                            print(f"DEBUG: Compound Move Log -> {self.move_log[-1]}")
                                            
                                            game.set_cast_prompt(game.next_player)
                                            game.kill_dom_hover()
                                            game.show_bg(screen)
                                            self.draw_command_strip()
                                            game.show_last_move(screen)
                                            game.show_pieces(screen)
                                            game.show_clicked_cards(screen)
                                            game.show_dead(screen)
                                            game.show_dead_cards(screen)
                                            
                                            game.lightning.trigger(game.next_player, persist_frames=10)
                                            cast_sound = 'raise'
                                            
                                            rival_player = board.players[1] if game.next_player == 'black' else \
                                                board.players[0]
                                                
                                            if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                                self.game.kill_prompt(self.my_color)
                                                self.game.restore_cast_prompt(self.my_color)
                                            elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                                self.game.kill_prompt(self.my_color)
                                                self.game.restore_cast_prompt(self.my_color)
                                                
                                            if board._king_mated(rival_player):
                                                
                                                game.set_mated_prompt(rival_player.color)
                                            else:
                                                # next turn/player
                                                game.next_turn()
                                            
                                    elif game.next_player == 'black' and (clicked_row <= 3 and \
                                        clicked_row >= 1):
                                        if clicked_sq.piece == None:
                                            
                                            board._raise_queen(clicked_col, clicked_row, \
                                                game.next_player, clicked_sq.card)
                                            
                                            queen_house_raided = False
                                            
                                            final = clicked_sq
                                            cards = clicker.clicked_cards
                                            move = Cast_move(cards, final, 1)
                                            
                                            player = board.players[0]
                                            piece = board.squares[clicked_col][clicked_row].piece
                                            card = clicked_sq.card
                                            
                                            board.cast_move(player, piece, card, move)
                                            
                                            game.set_cast_prompt(game.next_player)
                                            game.kill_dom_hover()
                                            game.show_bg(screen)
                                            self.draw_command_strip()
                                            game.show_last_move(screen)
                                            game.show_pieces(screen)
                                            game.show_clicked_cards(screen)
                                            game.show_dead(screen)
                                            game.show_dead_cards(screen)   
                                            
                                            game.lightning.trigger(game.next_player, persist_frames=10)
                                            cast_sound = 'raise'
                                            
                                            rival_player = board.players[1] if game.next_player == 'black' else \
                                                board.players[0]
                                                
                                            if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                                self.game.kill_prompt(self.my_color)
                                                self.game.restore_cast_prompt(self.my_color)
                                            elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                                self.game.kill_prompt(self.my_color)
                                                self.game.restore_cast_prompt(self.my_color)
                                                
                                            if board._king_mated(rival_player):
                                                
                                                game.set_mated_prompt(rival_player.color)
                                            else:
                                                # next turn/player
                                                game.next_turn()
                        
                        dragger.undrag_piece()
                        
                    # mouse wheel
                    elif event.type == pygame.MOUSEWHEEL:
                        if getattr(self.game, 'show_rules_overlay', False) or getattr(self.game, 'show_controls_overlay', False):
                            # Multiply by 30 to make the scroll speed feel natural
                            self.game.help_scroll_y += event.y * 30
                        
                    # key press
                    elif event.type == pygame.KEYDOWN:
                        
                        # save game
                        if self.game.save_naming_mode:
                            if event.key == pygame.K_RETURN:
                                # finalize the save
                                self.game.move_log = self.move_log
                                if not os.path.exists('saves'):
                                    os.makedirs('saves', exist_ok=True)
                                filename = f"saves/{self.game.current_save_name}.json"
                                self.game.save_game(filename)
                                
                                # reset mode
                                self.game.save_naming_mode = False
                                self.game.current_save_name = ""
                                
                            elif event.key == pygame.K_BACKSPACE:
                                self.game.current_save_name = \
                                    self.game.current_save_name[:-1]
                                    
                            elif event.key == pygame.K_ESCAPE:
                                self.game.save_naming_mode = False
                                self.game.current_save_name = ""
                                
                            else:
                                # capture alphanumeric keys for name
                                if len(self.game.current_save_name) < 20 and                                     event.unicode.isprintable():
                                    self.game.current_save_name += event.unicode
                        
                        elif self.game.load_menu_mode:
                            if event.key == pygame.K_UP:
                                if self.game.save_files:
                                    self.game.selected_save_idx = \
                                        (self.game.selected_save_idx - 1) % \
                                        len(self.game.save_files)
                            elif event.key == pygame.K_DOWN:
                                if self.game.save_files:
                                    self.game.selected_save_idx = \
                                        (self.game.selected_save_idx + 1) % \
                                        len(self.game.save_files)
                            elif event.key == pygame.K_RETURN:
                                if self.game.save_files:
                                    # load selected file
                                    selected_file = self.game.save_files\
                                        [self.game.selected_save_idx]
                                    self.game.load_game(f"saves/{selected_file}")
                                    
                                    self.move_log = self.game.history
                                    self.game.view_index = len(self.move_log)
                                    self._autosaved = False

                                    self.game.load_menu_mode = False
                                    board = self.game.board
                                    dragger = self.game.dragger
                                    clicker = self.game.clicker
                                    self.game.view_index = len(self.move_log)
                                    print(f"Loaded {selected_file} successfully!")
                            elif event.key == pygame.K_ESCAPE:
                                self.game.load_menu_mode = False
                                
                        elif getattr(self.game, 'show_rules_overlay', False) or getattr(self.game, 'show_controls_overlay', False):
                            if event.key == pygame.K_ESCAPE:
                                self.game.show_rules_overlay = False
                                self.game.show_controls_overlay = False
                                self.game.help_scroll_y = 0  # reset scroll to top
                            elif event.key == pygame.K_UP:
                                # Scroll up (min(0) prevents scrolling past the very top)
                                self.game.help_scroll_y = min(0, self.game.help_scroll_y + 40)
                            elif event.key == pygame.K_DOWN:
                                # Scroll down
                                self.game.help_scroll_y -= 40
                                
                        # other keydown
                        else:
                            if event.key == pygame.K_s:
                                self.game.save_naming_mode = True
                                print("Enter file name...")
                                
                            elif event.key == pygame.K_l:
                                # scan for sved games in current directory
                                if not os.path.exists('saves'):
                                    os.makedirs('saves', exist_ok=True)
                                self.game.save_files = [f for f in os.listdir('saves') if \
                                    f.endswith('.json')]
                                self.game.load_menu_mode = not self.game.load_menu_mode
                                # ensure naming mode off
                                self.game.save_naming_mode = False
                            
                            # change theme
                            elif event.key == pygame.K_t:
                                game.change_theme()
                                game.change_emblem()
                                game.change_dead_card()
                                
                            elif event.key == pygame.K_d: # 'D' for Draw Test
                                print("DEBUG: Forcing Threefold Repetition...")
                                # 1. Get current state hash
                                temp_bb = RampartBitboard()
                                temp_bb.sync_from_board(game.board)
                                current_hash = temp_bb.get_state_hash()
                                
                                # 2. Inject it into history TWICE
                                # (So the current state becomes the 3rd occurrence)
                                self.state_history.append(current_hash)
                                self.state_history.append(current_hash)
                                
                                # 3. Trigger the check manually
                                self._check_repetition_draw()
                            
                            # change piece styles
                            elif event.key == pygame.K_y:
                                game.board.change_all_piece_textures()
                            
                            # change ai difficulty level
                            elif event.key == pygame.K_a:
                                self._cycle_ai_difficulty()

                            # flip board key
                            elif event.key == pygame.K_f:
                                game.flip_board()
                                
                            # view history
                            elif event.key == pygame.K_LEFT:
                                if self.game.view_index > 0:
                                    # Viewing history only makes sense at the live
                                    # position - drop any in-progress card/button
                                    # selection rather than carry it along.
                                    self.game.clicker.unclick_all_cards()
                                    self.game.clicker.unclick_btn()
                                    casting = False
                                    self.game.view_index -= 1
                                    # trigger reconstruction of baord at this index
                                    self.game.reconstruct_at_move(self.game.view_index, \
                                        self.move_log)

                                    board = self.game.board
                                    dragger = self.game.dragger
                                    dragger.board.dragger = board
                                    clicker = self.game.clicker
                                    clicker.board = board
                                    print(f"Viewing move: {self.game.view_index}")

                            elif event.key == pygame.K_RIGHT:
                                if self.game.view_index < len(self.move_log):
                                    self.game.clicker.unclick_all_cards()
                                    self.game.clicker.unclick_btn()
                                    casting = False
                                    self.game.view_index += 1
                                    self.game.reconstruct_at_move(self.game.view_index, \
                                        self.move_log)

                                    board = self.game.board
                                    dragger = self.game.dragger
                                    dragger.board.dragger = board
                                    clicker = self.game.clicker
                                    clicker.board = board
                                    print(f"Viewing move: {self.game.view_index}")
                            
                            # Add simple restart for AI mode
                            elif event.key == pygame.K_r:
                                game.reset()
                                
                                # game = self.game
                                board = self.game.board
                                dragger = self.game.dragger
                                clicker = self.game.clicker
                                
                                self.ai_thinking = False
                                
                                # clear logs
                                self.move_log = []
                                self.state_history = []
                                
                                temp_bb = RampartBitboard()
                                temp_bb.sync_from_board(board)
                                self.state_history.append(temp_bb.get_state_hash())
                                
                                print("Game reset successfully!")
                                
                    # quit application
                    elif event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    
                else:  # Game over state
                    opponent = self.game.board.players[0] if self.my_color == 'white' else self.game.board.players[1]
                    self.game.set_mated_prompt(opponent.color)
                    game.show_cast_prompt(screen, self.my_color)
                    
                    # key press in game over state
                    if event.type == pygame.KEYDOWN:
                        # save game
                        if self.game.save_naming_mode:
                            if event.key == pygame.K_RETURN:
                                # finalize the save
                                self.game.move_log = self.move_log
                                if not os.path.exists('saves'):
                                    os.makedirs('saves', exist_ok=True)
                                filename = f"saves/{self.game.current_save_name}.json"
                                self.game.save_game(filename)
                                
                                # reset mode
                                self.game.save_naming_mode = False
                                self.game.current_save_name = ""
                                
                            elif event.key == pygame.K_BACKSPACE:
                                self.game.current_save_name = \
                                    self.game.current_save_name[:-1]
                                    
                            elif event.key == pygame.K_ESCAPE:
                                self.game.save_naming_mode = False
                                self.game.current_save_name = ""
                                
                            else:
                                # capture alphanumeric keys for name
                                if len(self.game.current_save_name) < 20 and                                     event.unicode.isprintable():
                                    self.game.current_save_name += event.unicode
                        
                        elif self.game.load_menu_mode:
                            if event.key == pygame.K_UP:
                                if self.game.save_files:
                                    self.game.selected_save_idx = \
                                        (self.game.selected_save_idx - 1) % \
                                        len(self.game.save_files)
                            elif event.key == pygame.K_DOWN:
                                if self.game.save_files:
                                    self.game.selected_save_idx = \
                                        (self.game.selected_save_idx + 1) % \
                                        len(self.game.save_files)
                            elif event.key == pygame.K_RETURN:
                                if self.game.save_files:
                                    # load selected file
                                    selected_file = self.game.save_files\
                                        [self.game.selected_save_idx]
                                    self.game.load_game(f"saves/{selected_file}")
                                    
                                    self.game.view_index = len(self.move_log)
                                    
                                    self.move_log = self.game.history
                                    self.game.load_menu_mode = False
                                    board = self.game.board
                                    dragger = self.game.dragger
                                    clicker = self.game.clicker
                                    self.game.view_index = len(self.move_log)
                                    print(f"Loaded {selected_file} successfully!")
                            elif event.key == pygame.K_ESCAPE:
                                self.game.load_menu_mode = False
                                
                        elif getattr(self.game, 'show_rules_overlay', False) or getattr(self.game, 'show_controls_overlay', False):
                            if event.key == pygame.K_ESCAPE:
                                self.game.show_rules_overlay = False
                                self.game.show_controls_overlay = False
                                self.game.help_scroll_y = 0  # reset scroll to top
                            elif event.key == pygame.K_UP:
                                # Scroll up (min(0) prevents scrolling past the very top)
                                self.game.help_scroll_y = min(0, self.game.help_scroll_y + 40)
                            elif event.key == pygame.K_DOWN:
                                # Scroll down
                                self.game.help_scroll_y -= 40
                        
                        else:
                            # other keydown
                            if event.key == pygame.K_s:
                                self.game.save_naming_mode = True
                                print("Enter file name...")
                                
                            elif event.key == pygame.K_l:
                                # scan for sved games in current directory
                                if not os.path.exists('saves'):
                                    os.makedirs('saves', exist_ok=True)
                                self.game.save_files = [f for f in os.listdir('saves') if \
                                    f.endswith('.json')]
                                self.game.load_menu_mode = not self.game.load_menu_mode
                                # ensure naming mode off
                                self.game.save_naming_mode = False
                            
                            elif event.key == pygame.K_t:
                                game.change_theme()
                                game.change_emblem()
                                game.change_dead_card()
                            elif event.key == pygame.K_y:
                                game.board.change_all_piece_textures()
                            # change ai difficulty level
                            elif event.key == pygame.K_a:
                                self._cycle_ai_difficulty()
                            elif event.key == pygame.K_r:  # Restart from game over
                                game.reset()
                                
                                # game = self.game
                                board = self.game.board
                                dragger = self.game.dragger
                                clicker = self.game.clicker
                                
                                self.ai_thinking = False
                                
                                # clear logs
                                self.move_log = []
                                self.state_history = []
                                
                                temp_bb = RampartBitboard()
                                temp_bb.sync_from_board(board)
                                self.state_history.append(temp_bb.get_state_hash())
                                
                                print("Game reset successfully!")
                                
                            # view history
                            elif event.key == pygame.K_LEFT:
                                if self.game.view_index > 0:
                                    self.game.clicker.unclick_all_cards()
                                    self.game.clicker.unclick_btn()
                                    casting = False
                                    self.game.view_index -= 1
                                    # trigger reconstruction of baord at this index
                                    self.game.reconstruct_at_move(self.game.view_index, \
                                        self.move_log)

                                    board = self.game.board
                                    dragger = self.game.dragger
                                    dragger.board.dragger = board
                                    clicker = self.game.clicker
                                    clicker.board = board
                                    print(f"Viewing move: {self.game.view_index}")

                            elif event.key == pygame.K_RIGHT:
                                if self.game.view_index < len(self.move_log):
                                    self.game.clicker.unclick_all_cards()
                                    self.game.clicker.unclick_btn()
                                    casting = False
                                    self.game.view_index += 1
                                    self.game.reconstruct_at_move(self.game.view_index, \
                                        self.move_log)

                                    board = self.game.board
                                    dragger = self.game.dragger
                                    dragger.board.dragger = board
                                    clicker = self.game.clicker
                                    clicker.board = board
                                    print(f"Viewing move: {self.game.view_index}")

                    # mouse-driven history arrows (< and >) - the only mouse
                    # interaction kept alive in the game-over state; unlike
                    # the "in progress" branch this doesn't handle general
                    # board/menu clicks, since nothing else is actionable
                    # once the game has ended.
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1 and hasattr(self, 'btn_prev') and \
                            hasattr(self, 'btn_next'):
                            mouse_pos = event.pos
                            if self.btn_prev.collidepoint(mouse_pos):
                                if self.game.view_index > 0:
                                    self.game.clicker.unclick_all_cards()
                                    self.game.clicker.unclick_btn()
                                    casting = False
                                    self.game.view_index -= 1
                                    self.game.reconstruct_at_move(self.game.view_index, self.move_log)
                                    board = self.game.board
                                    dragger = self.game.dragger
                                    clicker = self.game.clicker
                                    clicker.board = board
                            elif self.btn_next.collidepoint(mouse_pos):
                                if self.game.view_index < len(self.move_log):
                                    self.game.clicker.unclick_all_cards()
                                    self.game.clicker.unclick_btn()
                                    casting = False
                                    self.game.view_index += 1
                                    self.game.reconstruct_at_move(self.game.view_index, self.move_log)
                                    board = self.game.board
                                    dragger = self.game.dragger
                                    clicker = self.game.clicker
                                    clicker.board = board

                    elif event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()

            self._present()


if __name__ == "__main__":
    # initialize game
    main = Main()
    main.mainloop()