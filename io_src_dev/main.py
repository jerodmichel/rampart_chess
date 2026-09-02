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


from services.firebase_manager import FirebaseManager
# from firebase_admin import db



import os
import time
import random

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

import copy
import threading
import queue
import json

from const import *
from game import Game
from square import Square
from piece import *
from move import Move
from cast_move import Cast_move
from player import Player


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
        
        
# ╭━╮╱╭┳━━━┳━━━━┳╮╭╮╭┳━━━┳━━━┳╮╭━┳━━┳━╮╱╭┳━━━╮
# ┃┃╰╮┃┃╭━━┫╭╮╭╮┃┃┃┃┃┃╭━╮┃╭━╮┃┃┃╭┻┫┣┫┃╰╮┃┃╭━╮┃
# ┃╭╮╰╯┃╰━━╋╯┃┃╰┫┃┃┃┃┃┃╱┃┃╰━╯┃╰╯╯╱┃┃┃╭╮╰╯┃┃╱╰╯
# ┃┃╰╮┃┃╭━━╯╱┃┃╱┃╰╯╰╯┃┃╱┃┃╭╮╭┫╭╮┃╱┃┃┃┃╰╮┃┃┃╭━╮
# ┃┃╱┃┃┃╰━━╮╱┃┃╱╰╮╭╮╭┫╰━╯┃┃┃╰┫┃┃╰┳┫┣┫┃╱┃┃┃╰┻━┃
# ╰╯╱╰━┻━━━╯╱╰╯╱╱╰╯╰╯╰━━━┻╯╰━┻╯╰━┻━━┻╯╱╰━┻━━━╯
        
        self.game_id = None
        self.my_color = None
        self.is_host = False
        self.process_flag = True
        self.opponent_rematch_requested = False
        
        self.queen_raid_context = None  # networked
        
        self.move_queue = queue.Queue()  # for thread-safe move handling
        self.fb = FirebaseManager()
        
        self.move_lock = threading.Lock()
        
        self.rematch_requested = False  # track if current player requested rematch
        self.awaiting_rematch_response = False  # track if waiting for opponent
    
        # start listener thread if in networked game
        if self.game_id:  
            threading.Thread(
                target=self._start_firebase_listener, 
                daemon=True
            ).start()
            
        # heartbeat system:
        self.running = False
        self.last_heartbeat = {}  # track last heartbeat timestamps
        self.heartbeat_interval = 5  # seconds between heartbeats
        self.timeout_threshold = 15  # seconds before considering disconnected
            
        # UI elements
        self.ui_font = pygame.font.SysFont('Arial', 24)
        self.input_text = ""
        self.active_input = False
        self.status_message = "Press H to host or J to join"
        
        # chat system variables
        self.chat_listener = None
        self.chat_font = pygame.font.SysFont('Arial', 16)
        self.chat_active = False
        self.chat_text = ""
        self.chat_messages = []
        self.chat_rect = pygame.Rect(WIDTH - 265, 23, 300, 100)
        self.max_messages = 4  # visible messages at once
        self.max_chars = 25 # maximum characters per message
        
        # history
        self.move_log = []

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
        
    def start_networking(self, game_id):
        
        if hasattr(self, 'networking_thread') and self.networking_thread.is_alive():
            self.running = False
            self.networking_thread.join(timeout=1.0)
        
        self.running = True
        
        # simplified version with proper db access
        print(f"DEBUG: Attempting to connect to game {game_id}")
        print(f"\n SS FIREBASE PATH DEBUG SS")
        print(f"My Color: {self.my_color}")
        print(f"Game ID: {game_id}")
        print(f"Full Path: games/{game_id}/moves")
        
        # verify game exists using firebaseManager
        if not self.fb.game_exists(game_id):
            print("ERROR: Game ID does not exist or connection failed")
            return
    
        def handle_incoming_move(event):
            # case 1: firebase Event object
            if hasattr(event, 'data'):
                move_data = event.data
            # case 2: already extracted move dict
            elif isinstance(event, dict):
                move_data = event
            else:
                print(f"ERROR: Unknown event type {type(event)}: {event}")
                return
        
            if not move_data:
                print("DEBUG: Empty move data")
                return
            
            if isinstance(move_data, dict) and any(k.startswith('-') for k in move_data.keys()):
                print(f"DEBUG: Received full moves node, extracting latest")
                move_data = list(move_data.values())[-1]  # get most recent move
        
            print(f"DEBUG: Processing move data: {move_data}")
            
            if not isinstance(move_data, dict) or 'type' not in move_data:
                print(f"DEBUG: Invalid move structure: {move_data}")
                return
            
            if move_data['type'] == 'queen_raid_sequence':
                if move_data.get('sender') == self.my_color: return
                try:
                    sender = move_data.get('sender')
                    initial = self.game.board.squares[move_data['initial']['col']][\
                            move_data['initial']['row']]
                    final = self.game.board.squares[move_data['final']['col']][\
                            move_data['final']['row']]  
                    move = Move(initial, final)
                
                    queen_data = {
                        'col': move_data['queen_data']['col'],
                        'row': move_data['queen_data']['row']
                        }
                
                    self.move_queue.put({
                        'type': 'queen_raid_sequence',
                        'sender': sender,
                        'move': move,
                        'queen_data': queen_data
                        })
                    
                except Exception as e:
                    print(f"DEBUG [B]: Move processing failed: {e}")
                
            elif move_data['type'] == 'move':
                if move_data.get('sender') == self.my_color: return
                try:
                    print(f"DEBUG [B]: Creating Square objects...")
                    initial = self.game.board.squares[move_data['initial']['col']][move_data['initial']['row']]
                    final = self.game.board.squares[move_data['final']['col']][move_data['final']['row']]
                    move = Move(initial, final)
                    self.move_queue.put(move)
                    print("DEBUG [B]: Move queued successfully!")
                except Exception as e:
                    print(f"DEBUG [B]: Move processing failed: {e}")
                    
            elif move_data['type'] == 'cast':
                if move_data.get('sender') == self.my_color: return
                try:
                    cards = [self.game.board.get_card(c['suit'], c['rank']) for c in move_data['cards']]
                    final = self.game.board.squares[move_data['final']['col']][move_data['final']['row']]
                    cast_type = move_data['cast_type']
                    
                    cast_move = Cast_move(cards, final, cast_type)
                    
                    # player
                    player = self.game.board.players[0] if self.my_color == 'white' \
                        else self.game.board.players[1]
                    
                    # reconstruct piece
                    piece = None
                    if move_data['piece_type']:
                        piece_class = {
                            'raider': Raider,
                            'queen': Queen,
                            }[move_data['piece_type']]
                        piece = piece_class(move_data['piece_color'])
                    
                    # reconstruct card
                    card = None
                    if move_data.get('card_suit') is not None:
                        card = self.game.board.get_card(move_data['card_suit'], move_data['card_rank'])
                        
                    self.move_queue.put({
                        'type': 'cast_execution',
                        'player': player,
                        'piece': piece,
                        'card': card,
                        'move': cast_move,
                        })
                    
                    print("DEBUG [B]: Move queued successfully!")
                except Exception as e:
                    print(f"DEBUG [B]: Move processing failed: {e}")
            
            # save/load incoming
            elif move_data['type'] in ['sync', 'load_sync']:
                try:
                    # pass raw data to queue
                    self.move_queue.put(move_data)
                    print(f"DEBUG [B]: {move_data['type']} queued successfully!")
                except Exception as e:
                    print(f"DEBUG [B]: Sync processing failed: {e}")
                        
        print("DEBUG: Starting listener thread...")
        networking_thread = threading.Thread(
            target=self.fb.listen_for_moves,
            args=(game_id, handle_incoming_move),
            daemon=True
        )
        networking_thread.start()
        print(f"DEBUG [B]: Networking thread alive? {networking_thread.is_alive()}")
        
        def send_heartbeat():
            while self.running:
                self.fb.update_heartbeat(self.game_id, self.my_color) # Simplified!
                time.sleep(self.heartbeat_interval)
        
        threading.Thread(target=send_heartbeat, daemon=True).start()
        
        def handle_heartbeat(message):
            data = message.get('data')
            path = message.get('path', '/')
            
            if path == '/':
                beat_data = data
            else:
                color = path.split('/')[-1]
                beat_data = {color: data}
            
            for player, heartbeat in (beat_data or {}).items():
                if player != self.my_color:
                    self.last_heartbeat[player] = time.time()
                    print(f"Heartbeat received from {player}")
    
        # Use the manager to start the stream
        self.heartbeat_listener = self.fb.db.child('games').child(game_id).child('heartbeats').stream(
            lambda m: handle_heartbeat(m), 
            token=self.fb.user['idToken']
        )

        # █▀▀ █░█ ▄▀█ ▀█▀
        # █▄▄ █▀█ █▀█ ░█░
        
        # chat listener
        def handle_incoming_chat(message):
            data = message.get('data')
            path = message.get('path', '/')  # 1. Grab the path
            if data and isinstance(data, dict):
                # 2. Group into a list: values() if it's history, or [data] if it's a single live message
                messages_to_process = data.values() if path == '/' else [data]
                
                # 3. Loop through our new list instead of .items()
                for msg_data in messages_to_process:
                    if isinstance(msg_data, dict) and msg_data.get('player') != self.my_color:
                        msg = f"{msg_data.get('player', 'Opponent')}: {msg_data.get('text', '')}"
                        if msg not in self.chat_messages: # Prevent duplicates
                            self.chat_messages.append(msg)
                            if len(self.chat_messages) > self.max_messages:
                                self.chat_messages.pop(0)
        
        # firebase managed listener
        self.chat_listener = self.fb.db.child('games').child(game_id).child('chat').stream(
            lambda m: handle_incoming_chat(m),
            token=self.fb.user['idToken']
        )
        
        def handle_rematch_update(message):
            data = message.get('data')
            path = message.get('path', '/')
            opponent = 'black' if self.my_color == 'white' else 'white'
            
            # Parse Pyrebase stream data
            parsed_data = {}
            if path == '/':
                parsed_data = data or {}
            else:
                color = path.strip('/')
                parsed_data = {color: data}
            
            # only care about opponent's state changes
            if opponent in parsed_data:
                opponent_state = parsed_data[opponent]
                if opponent_state != self.opponent_rematch_requested:
                    self.opponent_rematch_requested = opponent_state
                    if opponent_state:
                        self.status_message = "Opponent wants rematch! Press R to accept"
                    
                    # don't execute rematch here, just set flag
                    if opponent_state and self.rematch_requested:
                        self.execute_rematch()  # this now avoids direct display ops
    
        self.rematch_listener = self.fb.db.child('games').child(game_id).child('rematch').stream(
            lambda m: handle_rematch_update(m),
            token=self.fb.user['idToken']
        )
            
    def request_rematch(self):
        if not self.game_id:
            return
            
        status = self.fb.db.child(f'games/{self.game_id}/rematch').get(\
            self.fb.user['idToken']).val() or {}
        opponent = 'black' if self.my_color == 'white' else 'white'
        
        # only request if haven't already and opponent hasn't requested
        if not status.get(self.my_color, False) and not status.get(opponent, False):
            self.fb.update_rematch_status(self.game_id, self.my_color, True)
            self.rematch_requested = True
            self.status_message = "Rematch requested - waiting"
    
    def check_rematch_status(self):
        status = self.fb.db.child(f'games/{self.game_id}/rematch').get(\
            self.fb.user['idToken']).val() or {}
        self.opponent_rematch_requested = status.get('white' if self.my_color == 'black' else 'black', False)

    def execute_rematch(self):
        # reset game objects
        self.game.reset()
        self.game = Game()
        self.game.ui_scale = self.ui_scale
        self.need_refresh = True
        
        # swap colors
        new_color = 'black' if self.my_color == 'white' else 'white'
        self.my_color = new_color
        
        # reset flags and states
        self.rematch_requested = False
        self.opponent_rematch_requested = False
        self.process_flag = True
        self.game.next_player = 'white'
        self.game.next_state = None
        self.game.board.last_player_color = None
        
        self.move_queue.queue.clear()
        
        self.move_log = []
        
        # queue display update for main thread
        self.rematch_complete = True
        self.status_message = f"Rematch! You're now {self.my_color}. {'Your turn!' if self.my_color == 'white' else 'Waiting for white...'}"
        
        # send sync as move
        if self.game_id:
            sync_move = {
                'type': 'sync',
                'next_player': 'white',
                'sender': self.my_color,
                'process_flag': (self.my_color == 'white'),
                'reset': True  # flag to indicate full reset
            }
            self.fb.send_move(self.game_id, sync_move)
            
        print(
            f"REMATCH STATE CHECK:\n"
            f"My Color: {self.my_color}\n"
            f"Next Player: {self.game.next_player}\n"
            f"Board Last Color: {self.game.board.last_player_color}\n"
            f"Process Flag: {self.process_flag}\n"
        )
            
    def check_and_execute_rematch(self):
        if not self.game_id:
            return
            
        status = self.fb.db.child(f'games/{self.game_id}/rematch').get(\
            self.fb.user['idToken']).val() or {}
        
        # only proceed if both players have agree to rematch
        if status.get('white', False) and status.get('black', False):
            self.execute_rematch()

    def send_move_to_opponent(self, move, piece=None, card=None):
        # minimal move sender without serialization
        if self.game.queen_raid_pending and isinstance(move, dict):
            move_data = {
                'type': 'queen_raid_sequence',
                'initial': {'col': self.queen_raid_context['move'].initial.col,
                                'row': self.queen_raid_context['move'].initial.row},
                'final': {'col': self.queen_raid_context['move'].final.col,
                              'row': self.queen_raid_context['move'].final.row},
                'queen_data': {
                    'col': self.queen_raid_context['queen_data']['col'],
                    'row': self.queen_raid_context['queen_data']['row']},
                'next_player': 'black' if self.game.next_player == 'white' else 'white',
                'process_flag': not self.process_flag,
                'sender': self.my_color
                }
            self.game.queen_raid_pending = False
        else:
              
            if isinstance(move, Move):
                move_data = {
                    'type': 'move',
                    'initial': {'col': move.initial.col, 'row': move.initial.row},
                    'final': {'col': move.final.col, 'row': move.final.row},
                    'next_player': 'black' if self.game.next_player == 'white' else 'white',
                    'process_flag': not self.process_flag,
                    'sender': self.my_color
                }
                
            elif isinstance(move, Cast_move):
                move_data = {
                    'type': 'cast',
                    'cards': [{'suit': c.suit, 'rank': c.rank} for c in move.cards],
                    'final': {'col': move.final.col, 'row': move.final.row},
                    'cast_type': move.cast_type,
                    # context
                    'piece_type': piece.name if piece else None,
                    'piece_color': piece.color if piece else None,
                    'card_suit': card.suit if card else None,
                    'card_rank': card.rank if card else None,
                    'next_player': 'black' if self.game.next_player == 'white' else 'white',
                    'process_flag': not self.process_flag,
                    'sender': self.my_color
                    }
        
        if isinstance(move_data, dict):
            move_data['next_player'] = 'black' if self.game.next_player == 'white' else 'white'
            
        self.fb.send_move(self.game_id, move_data)
        
    def broadcast_loaded_game(self):
        # send loaded history and turn state to joiner
        if self.game_id and self.is_host:
            sync_data = {
                'type': 'load_sync',
                'sender': self.my_color,
                'history': self.move_log,
                'next_player': self.game.next_player
            }
            self.fb.send_move(self.game_id, sync_data)
            print("DEBUG: Broadcasted oaded game state to opponent.")

    def process_networked_moves(self):
        while not self.move_queue.empty():
            item = self.move_queue.get()
            
            if isinstance(item, dict) and item.get('type') == 'sync':
                if item['sender'] != self.my_color:  # only process opponent's sync
                    # full state synchronization
                    self.game.next_player = item['next_player']
                    self.process_flag = item['process_flag']
                    if item.get('reset'):
                        self.game.next_state = None  # reset turn system
                        self.game.board.last_player_color = None
                continue
            
            if isinstance(item, dict) and item.get('type') == 'load_sync':
                if item['sender'] != self.my_color:
                    print("DEBUG: Receiving loaded game state from host")
                    
                    # 1. Overwrite local history and state
                    self.move_log = item['history']
                    self.game.next_player = item['next_player']
                    self.game.view_index = len(self.move_log)
                    
                    # 2. Reconstruct the board from the loaded history
                    self.game.reconstruct_at_move(self.game.view_index, self.move_log)
                    
                    # sync local turn state
                    self.game.board.last_player_color = 'white' if self.game.next_player \
                        == 'black' else 'black'
                    
                    # 3. Update the process flag so the correct player can move
                    self.process_flag = (self.my_color == self.game.next_player)
                    
                    # 4. Sync the visual highlight of the last move
                    if self.move_log:
                        self.game.sync_last_move_highlight(self.move_log[-1])
                        
                    # 5. Tell the main loop to grab the fresh Board object
                    self.need_refresh = True
                continue
            
            print(f"DEBUG [C]: Processing queued item: {item}")
            if self.game.next_player == self.my_color:
                continue
            
            if isinstance(item, dict) and item.get('type') == 'queen_raid_sequence':
                if (not self.process_flag and self.my_color == 'white') or \
                    (self.process_flag and self.my_color == 'black'):
                    if item.get('sender') != self.my_color:
                        try:
                            # snap view to live
                            self.game.view_index = len(self.move_log)
                            
                            move = item['move']
                            final_sq = move.final  # define final_sq here
                            captured = final_sq.has_piece()
                            
                            notation = self.game.board.apply_networked_move(move)
                            self.game.play_sound(captured)
                            
                            col = item['queen_data']['col']
                            row = item['queen_data']['row']
                            
                            color = 'white' if self.my_color == 'black' else 'black'
                            card = self.game.board.squares[col][row].card
                            
                            final = self.game.board.squares[col][row]
                            cards = []
                            cast_move = Cast_move(cards, final, 1)
                            
                            player = self.game.board.players[1] if self.my_color == 'black' \
                                else self.game.board.players[0]
                            piece = Queen(color)
                            
                            print(f"DEBUG: Attempting cast_move with:")
                            print(f"- Player: {player.color}")
                            print(f"- Piece: {piece.name} {piece.color}")
                            print(f"- Card: {card.suit if card else 'None'}")
                            print(f"- Move: {cast_move.final.col},{cast_move.final.row}")
                            
                            self.game.board.cast_move(player, piece, card, cast_move)
                            
                            # queen spawn notation
                            spawn_dst = f"{col + 1}{Square.get_alpharow(5 - row)}"
                            notation += f"/Q@{spawn_dst}"
                            
                            # move history
                            if not self.move_log or self.move_log[-1] != notation:
                                self.move_log.append(notation)
                            self.game.view_index = len(self.move_log)
                            
                            self.game.lightning.trigger(color, persist_frames=10)
                            self.game.play_raise_sound()
                            
                            my_player = self.game.board.players[0] if self.my_color == 'black' \
                                else self.game.board.players[1]
                                
                            is_check = self.game.board.king_in_check(my_player)
                            
                            if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                self.game.kill_prompt(self.my_color)
                                self.game.restore_cast_prompt(self.my_color)
                            elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                self.game.kill_prompt(self.my_color)
                                self.game.restore_cast_prompt(self.my_color)

                            # show if in check
                            if is_check:
                                self.game.set_in_check_prompt(self.my_color)
                                
                            if self.game.board._king_mated(my_player):
                                self.game.set_mated_prompt(my_player.color)
                            else:
                                # next turn/player
                                self.game.next_turn()
                        
                        except Exception as e:
                            print(f"DEBUG: Move failed - {e}")
            
            elif isinstance(item, Move):
                self.game.view_index = len(self.move_log)
                
                if hasattr(item, 'next_player'):  # for networked moves
                    self.game.next_player = item.next_player
                elif isinstance(item, dict) and 'next_player' in item:  # for queued moves
                    self.game.next_player = item['next_player']
                
                final_sq = item.final
                captured = final_sq.has_piece()
                captured_piece = final_sq.piece
                if (not self.process_flag and self.my_color == 'white') or \
                    (self.process_flag and self.my_color == 'black'):
                    try:
                        if captured and captured_piece.name in ['raider', 'queen']:
                            self.game.board._send_to_grave(captured_piece) 
                        notation = self.game.board.apply_networked_move(item)  # apply to board
                        print("DEBUG: Move applied successfully")
                        
                        # move history
                        if not self.move_log or self.move_log[-1] != notation:
                            self.move_log.append(notation)
                        self.game.view_index = len(self.move_log)
                        
                        self.game.play_sound(captured)
                        
                        my_player = self.game.board.players[0] if self.my_color == 'black' \
                            else self.game.board.players[1]
                            
                        opponent = self.game.board.players[0] if self.my_color == 'white' \
                            else self.game.board.players[1]
                            
                        is_check = self.game.board.king_in_check(my_player)
                        print(f"[CHECK STATE] is_check={is_check}, my_player={my_player.color}, self.my_color={self.my_color}")
                        
                        if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                            self.game.kill_prompt(self.my_color)
                            self.game.restore_cast_prompt(self.my_color)
                        elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                            self.game.kill_prompt(self.my_color)
                            self.game.restore_cast_prompt(self.my_color)
                        
                        if is_check:
                            print(">> Setting check prompt for", self.my_color)
                            self.game.set_in_check_prompt(self.my_color)
                        
                        if self.game.board.squares[item.final.col][item.final.row].is_own_king_house(my_player.color):
                            if self.game.board._opponent_king_on_noncard(opponent.color):
                                self.game.board.king_mated = True

                        if self.game.board.king_mated:
                            # "mate by capture": checked first and separately from the
                            # ordinary checkmate call below, since my_player can easily
                            # still have legal moves available - board._king_mated()
                            # alone would return False here and fall through to
                            # game.next_turn(), silently discarding this flag and
                            # letting the game continue past the mate.
                            self.game.set_mated_prompt(my_player.color)
                        elif self.game.board._king_mated(my_player):
                            self.game.set_mated_prompt(my_player.color)
                        else:
                            # next turn/player
                            self.game.next_turn()
                        
                    except Exception as e:
                        print(f"DEBUG: Move failed - {e}")
                        
            elif isinstance(item, dict) and item['type'] == 'cast_execution':
                if 'next_player' in item:
                    self.game.next_player = item['next_player']
                    
                if (not self.process_flag and self.my_color == 'white') or \
                    (self.process_flag and self.my_color == 'black'):
                    try:
                        player = item['player']
                        piece = item['piece']
                        card = item['card']
                        move = item['move']
                        
                        # 1. snap view index back to live
                        self.game.view_index = len(self.move_log)
                        
                        # 2. re-map the pointer to the actual board's square
                        mapped_sq = self.game.board.squares[move.final.col][move.final.row]
                        move.final = mapped_sq
                        
                        notation = self.game.board.apply_networked_cast_move(player, \
                                piece, card, move)  # delegate to board
                        print("DEBUG: Move applied successfully")
                        
                        # move history
                        if not self.move_log or self.move_log[-1] != notation:
                            self.move_log.append(notation)
                        self.game.view_index = len(self.move_log)
                        
                        self.game.set_cast_prompt(self.my_color)
                        self.game.lightning.trigger(self.game.next_player, persist_frames=10)
                        
                        print('cast_type:', move.cast_type)
                        if move.cast_type == 0:
                            self.game.play_strike_sound()
                        elif move.cast_type == 1:
                            self.game.play_raise_sound()
                        
                        print('cards:',move.cards)
                        self.game.cast_cards_networked(move.cards)
                        
                        my_player = self.game.board.players[0] if self.my_color == 'black' \
                            else self.game.board.players[1]
                            
                        is_check = self.game.board.king_in_check(my_player)
                        
                        if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                            self.game.kill_prompt(self.my_color)
                            self.game.restore_cast_prompt(self.my_color)
                        elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                            self.game.kill_prompt(self.my_color)
                            self.game.restore_cast_prompt(self.my_color)

                        # show if in check
                        if is_check:
                            self.game.set_in_check_prompt(self.my_color)
                            
                        if self.game.board._king_mated(my_player):
                            self.game.set_mated_prompt(my_player.color)
                        else:
                            # next turn/player
                            self.game.next_turn()
                        
                    except Exception as e:
                        print(f"DEBUG: Move failed - {e}")
             
            # ensure UI goes back to live view
            self.game.view_index = len(self.move_log) # Force index to the end
            self.game.board = self.game.board # Ensure we are on the live board object
            self.game.dragger.board = self.game.board
            self.game.clicker.board = self.game.board
            self.need_refresh = True
            print(f"DEBUG: References refreshed to live index {self.game.view_index}")
        
        # print(f"SYNC CHECK - {self.my_color} log: {self.move_log}")
        
        if self.game.board.last_player_color:
            # if not self.game.queen_raid_pending:
            last_color = self.game.board.last_player_color
            if last_color == 'white':
                self.process_flag = False
            else:
                self.process_flag = True
            
    def check_connection_health(self):
        if not self.game_id or not self.my_color:
            return True  # local game
        
        opponent = 'black' if self.my_color == 'white' else 'white'
        
        # start checking after at least one heartbeat
        if opponent not in self.last_heartbeat:
            return True  # opponent hasn't connected yet
            
        last_seen = self.last_heartbeat[opponent]
        time_since = time.time() - last_seen
        
        if time_since > self.timeout_threshold:
            self.status_message = "Opponent disconnected!"
            return False
            
        return True
            
    def _log_listeners(self):
        # debug statement to show active listeners
        print("ACTIVE LISTENERS:")
        print(f"- Rematch: {hasattr(self, '_rematch_listener')}")
        print(f"- Heartbeat: {hasattr(self, '_heartbeat_listener')}") 
        print(f"- Chat: {hasattr(self, '_chat_listener')}")
         
    def cleanup(self):
        print("🛑 DEBUG: Initiated shutdown sequence")
        
        print(f"🔍 Pre-cleanup listener state: {hasattr(self, 'rematch_listener')}")
        
        self.running = False  # this stops the heartbeat
        
        # 0. close rematch listener first
        if hasattr(self, 'rematch_listener') and self.rematch_listener:
            try:
                print("♻️ Closing rematch listener")
                self.rematch_listener.close()
            except Exception as e:
                print(f"⚠️ Rematch listener close error: {e}")
            finally:
                self.rematch_listener = None
                
        if hasattr(self, 'chat_listener') and self.chat_listener:
            try:
                print("♻️ Closing chat listener")
                self.chat_listener.close()
            except Exception: pass
            
        if hasattr(self, 'heartbeat_listener') and self.heartbeat_listener:
            try:
                print("♻️ Closing heartbeat listener")
                self.heartbeat_listener.close()
            except Exception: pass
    
        print("🛑 Stopping all threads...")
        
        threads = []
        if hasattr(self, 'networking_thread'):
            threads.append(('networking', self.networking_thread))
        if hasattr(self, 'heartbeat_thread'):  # if you has a separate heartbeat thread
            threads.append(('heartbeat', self.heartbeat_thread))
            
        for name, thread in threads:
            if thread and thread.is_alive():
                print(f"🛑 Stopping {name} thread...")
                thread.join(timeout=0.5)  # brief wait
                if thread.is_alive():
                    print(f"⚠️ {name} thread didn't stop gracefully")
        
        
        # cleanup heartbeats first
        if hasattr(self, 'game_id') and self.game_id and hasattr(self, 'my_color'):
            try:
                print("♻️ Removing heartbeat from Firebase")
                self.fb.db.child('games').child(self.game_id).child('heartbeats').child(self.my_color).remove(self.fb.user['idToken'])
            except Exception as e:
                print(f"⚠️ Heartbeat cleanup error: {e}")
        
        # 1. thread termination (with timeout tracking)
        thread = getattr(self, 'networking_thread', None)
        if thread and thread.is_alive():
            print("🛑 DEBUG: Stage 1 - Thread termination started")
            self.process_flag = False
            
            # triple termination
            start_time = time.time()
            try:
                # attempt graceful shutdown
                self.move_queue.put('TERMINATE', timeout=0.5)
                thread.join(timeout=1.0)
                
                if thread.is_alive():
                    print("⚠️ DEBUG: Graceful timeout - forcing daemon")
                    thread.daemon = True
            except Exception as e:
                print(f"⚠️ DEBUG: Thread termination error: {e}")
            finally:
                print(f"⏱️ DEBUG: Thread shutdown took {time.time()-start_time:.2f}s")
        
        # 2. firebase cleanup (with forced timeout)
        if hasattr(self, 'fb'):
            print("🛑 DEBUG: Stage 2 - Firebase cleanup")
            fb_cleanup_start = time.time()
            try:
                # create thread for firebase cleanup with timeout
                def fb_cleaner():
                    self.fb.cleanup()
                
                fb_thread = threading.Thread(target=fb_cleaner, daemon=True)
                fb_thread.start()
                fb_thread.join(timeout=2.0)
                
                if fb_thread.is_alive():
                    print("⚠️ DEBUG: Firebase cleanup timeout")
            except Exception as e:
                print(f"⚠️ DEBUG: Firebase error: {e}")
            finally:
                print(f"⏱️ DEBUG: Firebase cleanup took {time.time()-fb_cleanup_start:.2f}s")
        
        # 3. resource finalization
        print("🛑 DEBUG: Stage 3 - Final resource cleanup")
        try:
            while not self.move_queue.empty():
                self.move_queue.get_nowait()
        except:
            pass
        
        print(f"🔍 Post-cleanup listener state: {hasattr(self, 'rematch_listener')}")
        
        print("✅ DEBUG: Cleanup completed successfully")
        
    def _generate_pin(self):
        # generate a 4-digit pin and map it to the firebase ID
        self.game_pin = str(random.randint(1000, 9999))
        # store mapping in Firebase
        self.fb.db.child(f'pin_mappings/{self.game_pin}').set({
            'game_id': self.game_id,
            'created': int(time.time() * 1000)
        }, self.fb.user['idToken'])

    def _start_host_ui(self):
        self.status_message = "Creating game..."
        self._present()  # force UI update
        
        # existing host code:
        self.host_new_game()  
        self.status_message = f"Game ID: {self.game_pin}"
    
    def _handle_join_ui(self):
        print(f"Attempting to join with PIN: {self.input_text}")
        pin = self.input_text.strip()
        if len(pin) != 4 or not pin.isdigit():
            self.status_message = "PIN must be 4 digits!"
            print("Invalid PIN format")
            return
        
        self.join_game(pin)  # update status_message on success/failure
        self.active_input = False  # important: close input after submitting
        
    def host_new_game(self):
        # original + PIN generation
        self.my_color = 'white'
        self.is_host = True
        self.last_heartbeat = {}
        self.game_id = self.fb.create_game(  # keep existing firebase call
            self.game.board.get_serialized_state()
        )
        self._generate_pin()  # generate 4-digit PIN
        self.status_message = f"Game PIN: {self.game_pin}"  # show short PIN
        self.start_networking(self.game_id)  # start listening for moves
        
        self.fb.db.child(f'games/{self.game_id}/rematch').set({
            'white': False,
            'black': False,
            'initiator': None
        }, self.fb.user['idToken'])
        
        print(f"DEBUG: Host networking started for game {self.game_id}")
    
    def join_game(self, pin):
        try:
            # clean up any existing listener first
            if hasattr(self, 'networking_thread'):
                self.cleanup()
            print(f"Looking up PIN: {pin}")  # debug
            mapping = self.fb.db.child(f'pin_mappings/{pin}').get(\
                    self.fb.user['idToken']).val()
            
            if not mapping or 'game_id' not in mapping:
                self.status_message = "Invalid PIN - Game not found"
                print("No game found for this PIN")  # debug
                return
                
            self.my_color = 'black'
            self.game_id = mapping['game_id']
            print(f"Success! Joining game: {self.game_id}")  # debug
            
            # clear any previous networking
            if hasattr(self, 'networking_thread'):
                self.cleanup()
                
            self.status_message = f"Joined game! Waiting for host..."
            self.start_networking(self.game_id)
            
        except Exception as e:
            print(f"Join failed: {str(e)}")  # debug
            self.status_message = f"Connection failed: {str(e)}"
            self.active_input = True  # keep input open if failed
            
    # █▀▀ █░█ ▄▀█ ▀█▀   █▀█ █▀▀ █▄░█ █▀▄ █▀▀ █▀█
    # █▄▄ █▀█ █▀█ ░█░    █▀▄ ██▄ █░▀█ █▄▀ ██▄ █▀▄            
    
    def show_chat(self):
        # draw chat box
        pygame.draw.rect(self.screen, (255, 255, 255), self.chat_rect)
        pygame.draw.rect(self.screen, (0, 0, 139), self.chat_rect, 2)  # blue border
        
        # display messages
        for i, msg in enumerate(self.chat_messages[-self.max_messages:]):
            msg_surface = self.chat_font.render(msg, True, (0, 0, 0))
            self.screen.blit(msg_surface, (self.chat_rect.x + 5, self.chat_rect.y + 5 + i * 20))
        
        # show current input
        if self.chat_active:
            input_surface = self.chat_font.render("> " + self.chat_text, True, (0, 0, 0))
            self.screen.blit(input_surface, (self.chat_rect.x + 5, self.chat_rect.y + 80))
        else:
            prompt_surface = self.chat_font.render("Press 'C' to chat", True, (100, 100, 100))
            self.screen.blit(prompt_surface, (self.chat_rect.x + 5, self.chat_rect.y + 80))
            
    
    # █▀▀ █▀█ █▀▄▀█ █▀▄▀█ ▄▀█ █▄░█ █▀▄   █▀▄▀█ █▀▀ █▄░█ █░█
    # █▄▄ █▄█ █░▀░█ █░▀░█  █▀█ █░▀█ █▄▀    █░▀░█ ██▄  █░▀█ █▄█
    
    def execute_menu_action(self, menu_type, index):
        """Routes sidebar clicks to the actual game logic"""
        if menu_type == 'game':
            if index == 0:   # save Game
                if self.is_host:
                    self.game.save_naming_mode = True
                else:
                    self.status_message = "Only the host can save the game"
            elif index == 1: # load Game
                if self.is_host:
                    if not os.path.exists('saves'):
                        os.makedirs('saves', exist_ok=True)
                    self.game.save_files = [f for f in os.listdir('saves') if f.endswith('.json')]
                    self.game.load_menu_mode = True
                else:
                    self.status_message = "Only the host can load a game"
            elif index == 2: # Rematch
                if not self.rematch_requested and not self.opponent_rematch_requested:
                    self.request_rematch()
                elif self.opponent_rematch_requested and not self.rematch_requested:
                    self.rematch_requested = True
                    self.fb.update_rematch_status(self.game_id, self.my_color, True)
                    self.status_message = "Rematch accepted - waiting for game reset"
                    self.check_and_execute_rematch()
            elif index == 3: # flip board
                self.game.flip_board()
            elif index == 4: # Main Menu
                self.return_to_launcher = True
                
        elif menu_type == 'pref':
            if index == 0:   # change theme
                self.game.change_theme()
                self.game.change_emblem()
                self.game.change_dead_card()
            elif index == 1: # change pieces styles
                self.game.board.change_all_piece_textures()
                
        elif menu_type == 'help':
            if index == 0:   # rules
                self.game.show_rules_overlay = True
            elif index == 1: # controls
                self.game.show_controls_overlay = True
                
        # close the menu after selection made
        self.game.active_menu = None
                

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
        
        # network:
        fb = FirebaseManager()
        
        
        clicked_suit = None
        clicked_rank = None
        casting = False
        queen_house_raided = False
        cast_sound = None
        
        # connection health
        last_health_check = 0
        health_check_interval = 3  # seconds
        
        # launcher
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
            
            # show-methods
            screen.fill((0,0,0))
            game.show_bg(screen)
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
            
            # save/load show-methods
            game.show_naming_prompt(screen)
            game.show_load_menu(screen)
            
            # command menu
            game.show_side_menu(screen)
            game.show_help_overlays(screen)
            
            # chat
            self.show_chat()
            self.process_networked_moves()
            
            # network health:
            current_time = time.time()
        
            # connection health monitoring
            if current_time - last_health_check > health_check_interval:
                if not self.check_connection_health():
                    # handle disconnection (e.g. paused game)
                    pass
                last_health_check = current_time
            
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
                        self.show_chat()
                        
                        # draw lightning if active
                        if game.lightning.active:
                            
                            # force a small delay to ensure animation is visible
                            pygame.time.delay(30)
                            
                            screen.fill((255,255,255))
                            game.show_bg(screen)
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
                            
                            self.show_chat()
                            
                            if cast_sound == 'strike':
                                game.play_strike_sound()
                            elif cast_sound == 'raise':
                                game.play_raise_sound()
                            
                            cast_sound = None
                            
                        else:
                            # small delay to ensure animation is visible
                            pygame.time.delay(30)
                                
                            game.show_bg(screen)
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
                            
                            self.show_chat()
                        
                        game.change_state()
                        
                    elif game.next_state == "update2":
                        
                        pygame.time.delay(30)
                            
                        game.show_bg(screen)
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
                        
                        self.show_chat()
                        
                        game.change_state()
                    

# █▀▄▀█ █▀█ █░█ █▀ █▀▀ █▄▄ █░█ ▀█▀ ▀█▀ █▀█ █▄░█ █▀▄ █▀█ █░█░█ █▄░█
# █░▀░█ █▄█ █▄█ ▄█ ██▄  █▄█ █▄█ ░█░ ░█░ █▄█ █░▀█ █▄▀ █▄█ ▀▄▀▄▀ █░▀█
                    
                    # mouse click
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        
                        # intercept save/load menus
                        if self.game.save_naming_mode or self.game.load_menu_mode:
                            if event.pos[0] < WIDTH: 
                                self.game.save_naming_mode = False
                                self.game.load_menu_mode = False
                                continue
                        
                        # 1. check if save/load menu is open
                        if getattr(self.game, 'show_save_overlay', False) or getattr(self.game, 'show_load_overlay', False):
                            mx, my = event.pos
                            # check if player clicked in slot
                            # lines start at y=225 and go down 35px each
                            if 150 < mx < WIDTH - 150: # horizontal bounds
                                clicked_index = (my - 225) // 35
                                if 0 <= clicked_index < 3: # three slots
                                    if getattr(self.game, 'show_save_overlay', False):
                                        print(f"Saving to Slot {clicked_index + 1}...")
                                        # self.game.save_state(clicked_index)
                                    else:
                                        print(f"Loading from Slot {clicked_index + 1}...")
                                    
                                    # close menu after clicking
                                    self.game.show_save_overlay = False
                                    self.game.show_load_overlay = False
                            else:
                                self.game.show_save_overlay = False
                                self.game.show_load_overlay = False
                                    
                            continue # stop processing piece clicks if menu is open
                            
                        # +++ COMMAND CENTER CLICK INTERCEPT +++
                        if hasattr(self, 'btn_game') and event.button == 1: 
                            mouse_pos = event.pos
                            
                            # 1. check history arrows (< and >)
                            if hasattr(self, 'btn_prev') and self.btn_prev.collidepoint(mouse_pos):
                                if self.game.view_index > 0:
                                    self.game.view_index -= 1
                                    self.game.reconstruct_at_move(self.game.view_index, self.move_log)
                                    # force refresh local pointers exactly like your K_LEFT key does
                                    board = self.game.board
                                    dragger.board = board
                                    clicker.board = board
                                continue
                                
                            elif hasattr(self, 'btn_next') and self.btn_next.collidepoint(mouse_pos):
                                if self.game.view_index < len(self.move_log):
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
                                    # mathematically determine which option was clicked
                                    clicked_index = (mouse_pos[1] - 240) // 40
                                    if 0 <= clicked_index < 5:
                                        self.execute_menu_action(self.game.active_menu, clicked_index)
                                    continue
                                else:
                                    # clicked outside the menu, auto-close it!
                                    self.game.active_menu = None
                        
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
                            if clicker.clicked_btn == None:
                                if len(clicker.clicked_cards) > 0:
                                    if board.squares[clicked_col][clicked_row].is_card() and \
                                        board.squares[clicked_col][clicked_row].has_piece() and \
                                            clicked_row not in [0, 5]:
                                        card = board.squares[clicked_col][clicked_row].card
                                        piece = board.squares[clicked_col][clicked_row].piece
                                        if not clicker.is_clicked(card):
                                            if piece.name == 'raider' and \
                                                    piece.color == game.next_player:
                                                clicker.explic_save_card(card)
                                                clicker.click_card(card)
                                                # play sound
                                                game.play_card_sound()
                                                # show methods
                                                game.show_bg(screen)
                                                game.show_last_move(screen)
                                                game.show_moves(screen)
                                                game.show_pieces(screen)
                                                game.show_clicked_cards(screen)
                                                game.show_dead(screen)
                                                game.show_dead_cards(screen)
                                                self.show_chat()
                                                
                                                if clicker.has_sum_21(clicker.clicked_cards):
                                                    game.set_choose_cast_prompt(game.next_player)
                                        else:
                                            clicker.unclick_card(card)
                                            # play sound
                                            game.play_card_sound()
                                            if len(clicker.clicked_cards) == 0:
                                                casting = False
                                                game.set_cast_prompt(game.next_player)
                                else:
                                    # clicked square has a piece?
                                    if board.squares[clicked_col][clicked_row].has_piece():
                                        piece = board.squares[clicked_col][clicked_row].piece
                                        print("MOVE:", piece.color, game.next_player, self.my_color)
                                        # check if piece (color) is valid
                                        if piece.color == game.next_player and \
                                            self.my_color == game.next_player:
                                            board.calc_moves(piece, clicked_col, clicked_row, bool=True)
                                            dragger.save_initial(clicked_col, clicked_row)
                                            dragger.drag_piece(piece)
                                            # show methods
                                            game.show_bg(screen)
                                            game.show_last_move(screen)
                                            game.show_moves(screen)
                                            game.show_pieces(screen)
                                            game.show_clicked_cards(screen)
                                            game.show_dead(screen)
                                            game.show_dead_cards(screen)
                                            self.show_chat()
                        
    
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
                                            game.play_card_sound()
                                            if len(clicker.clicked_cards) == 0:
                                                casting = False
                                                game.set_cast_prompt(game.next_player)
                                                

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
                                game.show_last_move(screen)
                                game.show_moves(screen)
                                game.show_pieces(screen)
                                game.show_clicked_cards(screen)
                                game.show_dead(screen)
                                game.show_dead_cards(screen)
                                game.show_hover(screen)
                                dragger.update_blit(screen)
                                self.show_chat()
                    
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
                                    
                                    if self.game_id:  # only if in a networked game
                                        self.send_move_to_opponent(move)
                                        print(f"DEBUG: Sent move to opponent: {move.initial.col},{move.initial.row} \
                                              -> {move.final.col},{move.final.row}")
                                    # sounds
                                    game.play_sound(captured)
                                    # show methods
                                    game.show_bg(screen)
                                    # show last move
                                    game.show_last_move(screen)
                                    # show pieces
                                    game.show_pieces(screen)
                                    # show clicked cards
                                    game.show_clicked_cards(screen)
                                    # show dead pieces
                                    game.show_dead(screen)
                                    
                                    game.show_dead_cards(screen)
                                    
                                    self.show_chat()
                                    
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
                                        # rival_player, not game.next_player (the mover) -
                                        # set_mated_prompt's color argument is the side that
                                        # lost. Checked first and separately from the ordinary
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
                                        
                                        # infiltration notation
                                        inf_notation = board.move(dragger.piece, move)
                                        self.move_log.append(inf_notation)
                                        
                                        if self.game_id:  # only if in a networked game
                                            self.game.queen_raid_pending = True
                                            self.queen_raid_context = {
                                                'move': move,
                                                'queen_data': None
                                            }
                                            # self.send_move_to_opponent(move)
                                            print(f"DEBUG: Sent move to opponent: {move.initial.col},{move.initial.row} \
                                                  -> {move.final.col},{move.final.row}")
                                        # sounds
                                        game.play_sound(captured)
                                        # show methods
                                        game.show_bg(screen)
                                        # show last move
                                        game.show_last_move(screen)
                                        # show pieces
                                        game.show_pieces(screen)
                                        # show clicked cards
                                        game.show_clicked_cards(screen)
                                        # show dead pieces
                                        game.show_dead(screen)
                                        
                                        game.show_dead_cards(screen)
                                        
                                        self.show_chat()
                                        
                                    else:
                                        
                                        board.move(dragger.piece, move)
                                        if self.game_id:  # only if in networked game
                                            self.send_move_to_opponent(move)
                                            print(f"DEBUG: Sent move to opponent: {move.initial.col},{move.initial.row} \
                                                  -> {move.final.col},{move.final.row}")
                                        # sounds
                                        game.play_sound(captured)
                                        # show methods
                                        game.show_bg(screen)
                                        # show last move
                                        game.show_last_move(screen)
                                        # show pieces
                                        game.show_pieces(screen)
                                        # show clicked cards
                                        game.show_clicked_cards(screen)
                                        # show dead pieces
                                        game.show_dead(screen)
                                        
                                        game.show_dead_cards(screen)
                                        
                                        self.show_chat()
                                        
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

                                                board.calc_cast_moves(player, None, booL=True)

                                                if len(player.cast_moves) == 0:
                                                    clicker.unclick_btn()
                                                    game.set_no_strike_prompt(game.next_player)
                                                else:
                                                    game.set_strike_prompt(game.next_player)
                                                    casting = True
                                                    game.show_clicked_btns(screen)

                                                game.play_card_sound()

                                    elif 205 <= mouse_x <= 288:
                                        if len(clicker.clicked_cards) > 0:
                                            if clicker.has_board_card() and clicker.has_sum_21(clicker.clicked_cards):
                                                clicker.clicked_btn = 1

                                                player = board.players[1] if game.next_player == 'white' \
                                                        else board.players[0]

                                                board.calc_cast_moves(player, Raider(game.next_player), booL=True)

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
                                        clicker.unclick_grv()
                                        game.kill_dom_hover()
                                        game.kill_grave_hover()
                                                
                                    elif 205 <= mouse_x <= 288:
                                        game.play_card_sound()
                                        clicker.unclick_btn()
                                        clicker.unclick_grv()
                                        game.kill_dom_hover()
                                        game.kill_grave_hover()
                                    
                                    
                            else:
                                clicked_col = max(0, min(COLS-1, (mouse_x - 100) // RWIDTH))
                                clicked_row = max(0, min(ROWS-1, mouse_y // RHEIGHT))
                                # clicked_col = (mouse_x - 100) // RWIDTH if mouse_x < 900 else 9
                                # clicked_row = mouse_y // RHEIGHT if mouse_y < 800 else 5
                                if game.flipped:
                                    clicked_col = COLS - 1 - clicked_col
                                    clicked_row = ROWS - 1 - clicked_row
                                
                                print(clicked_col, clicked_row)
                                clicked_sq = board.squares[clicked_col][clicked_row]
                                if not queen_house_raided:
                                    if clicker.clicked_btn == 0:
                                        rAnge = range(1, 3) if self.my_color == 'white' else range(3, 5)
                                        if clicked_sq.has_piece() and clicked_sq.piece.name == \
                                            'raider' and clicked_row in rAnge and \
                                                game.next_player != clicked_sq.piece.color:
                                            
                                            cast_type = clicker.clicked_btn
                                            cards = clicker.clicked_cards.copy()
                                            print("CLICKER:", cards)
                                            
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
                                                
                                                if self.game_id:
                                                    self.send_move_to_opponent(move, piece, card)
                                                print(f"DEBUG: Sent move to opponent: {move.final.col},\
                                                      {move.final.row}")
                                                game.set_cast_prompt(game.next_player)
                                                game.kill_dom_hover()
                                                game.show_bg(screen)
                                                game.show_last_move(screen)
                                                game.show_pieces(screen)
                                                game.show_clicked_cards(screen)
                                                game.show_dead(screen)
                                                game.show_dead_cards(screen)
                                                
                                                self.show_chat()
                                                
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
                                            print("CLICKER:", cards)
                                            for cd in cards:
                                                print("SUIT, RANK:", cd.suit, cd.rank)
                                                    
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
                                                
                                                if self.game_id:
                                                    self.send_move_to_opponent(move, piece, card)
                                                print(f"DEBUG: Sent move to opponent: {move.final.col},\
                                                      {move.final.row}")
                                                clicker.unclick_btn()
                                                game.cast_cards()
                                                casting = False
                                                
                                                game.set_cast_prompt(game.next_player)
                                                game.kill_dom_hover()
                                                game.show_bg(screen)
                                                game.show_last_move(screen)
                                                game.show_pieces(screen)
                                                game.show_clicked_cards(screen)
                                                game.show_dead(screen)
                                                game.show_dead_cards(screen)
                                                
                                                self.show_chat()
                                                
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
                                                            
                                                        board.calc_cast_moves(player, piece, booL=True)
                                                        
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
                                                        
                                                        if self.game_id:
                                                            self.send_move_to_opponent(move, piece, card)
                                                        print(f"DEBUG: Sent move to opponent: {move.final.col},\
                                                              {move.final.row}")
                                                        clicker.unclick_btn()
                                                        clicker.unclick_grv()
                                                        game.cast_cards()
                                                        casting = False
                                                        
                                                        game.set_cast_prompt(game.next_player)
                                                        game.kill_dom_hover()
                                                        game.kill_grave_hover()
                                                        game.show_bg(screen)
                                                        game.show_last_move(screen)
                                                        game.show_pieces(screen)
                                                        game.show_clicked_cards(screen)
                                                        game.show_dead(screen)
                                                        game.show_dead_cards(screen)
                                                        self.show_chat()
                                                        
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
                                            spawn_dst = f"{clicked_col + 1}{Square.get_alpharow(5 - clicked_row)}"
                                            self.move_log[-1] += f"/Q@{spawn_dst}"
                                            
                                            self.game.view_index = len(self.move_log)
                                            
                                            if self.game_id:
                                                self.queen_raid_context['queen_data'] = \
                                                    {'col': clicked_sq.col, 'row': clicked_sq.row}
                                                self.send_move_to_opponent(self.queen_raid_context, piece, card)
                                            print(f"DEBUG: Sent move to opponent: {move.final.col},\
                                                  {move.final.row}")
                                            game.set_cast_prompt(game.next_player)
                                            game.kill_dom_hover()
                                            game.show_bg(screen)
                                            game.show_last_move(screen)
                                            game.show_pieces(screen)
                                            game.show_clicked_cards(screen)
                                            game.show_dead(screen)
                                            game.show_dead_cards(screen)
                                            self.show_chat()
                                            
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
                                            spawn_dst = f"{clicked_col + 1}{Square.get_alpharow(5 - clicked_row)}"
                                            self.move_log[-1] += f"/Q@{spawn_dst}" # Suffix the infiltration move
                                            self.game.view_index = len(self.move_log)
                                            
                                            if self.game_id:
                                                self.queen_raid_context['queen_data'] = \
                                                    {'col': clicked_sq.col, 'row': clicked_sq.row}
                                                self.send_move_to_opponent(self.queen_raid_context, piece, card)
                                            print(f"DEBUG: Sent move to opponent: {move.final.col},\
                                                  {move.final.row}")
                                            game.set_cast_prompt(game.next_player)
                                            game.kill_dom_hover()
                                            game.show_bg(screen)
                                            game.show_last_move(screen)
                                            game.show_pieces(screen)
                                            game.show_clicked_cards(screen)
                                            game.show_dead(screen)
                                            game.show_dead_cards(screen)
                                            self.show_chat()
                                            
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
                        
                        # active menu
                        if getattr(self.game, 'active_menu', None):
                            if event.key == pygame.K_ESCAPE:
                                self.game.active_menu = None
                            continue
                        
                        # close help overlays
                        if self.game.show_rules_overlay or self.game.show_controls_overlay:
                            if event.key == pygame.K_ESCAPE:
                                self.game.show_rules_overlay = False
                                self.game.show_controls_overlay = False
                            elif event.key == pygame.K_UP:
                                self.game.help_scroll_y += 35 # scroll up one line
                            elif event.key == pygame.K_DOWN:
                                self.game.help_scroll_y -= 35
                            continue
                        
                        # save game menu
                        if self.game.save_naming_mode:
                            if event.key == pygame.K_RETURN:
                                if self.game.current_save_name.strip():
                                    self.game.save_game(self.game.current_save_name, \
                                            self.move_log)
                                    self.game.save_naming_mode = False
                                    self.game.current_save_name = ""
                                    self.status_message = "Game saved successfully!"
                            elif event.key == pygame.K_ESCAPE:
                                self.game.save_naming_mode = False
                                self.game.current_save_name = ""
                            elif event.key == pygame.K_BACKSPACE:
                                self.game.current_save_name \
                                    = self.game.current_save_name[:-1]
                            else:
                                # limit to 15 chars
                                if len(self.game.current_save_name) < 15 and \
                                    event.unicode.isprintable():
                                    self.game.current_save_name += event.unicode
                                    
                        # load game menu
                        elif self.game.load_menu_mode:
                            if event.key == pygame.K_UP:
                                if self.game.selected_save_idx > 0:
                                    self.game.selected_save_idx -= 1
                            elif event.key == pygame.K_DOWN:
                                if self.game.save_files and \
                                    self.game.selected_save_idx \
                                    < len(self.game.save_files) -1:
                                    self.game.selected_save_idx += 1
                            elif event.key == pygame.K_RETURN:
                                if self.game.save_files:
                                    selected_file = self.game.save_files\
                                        [self.game.selected_save_idx]
                                    self.game.load_game(selected_file)
                                    # update main's local log to match loaded game's
                                    self.move_log = self.game.history.copy()
                                    self.game.load_menu_mode = False
                                    self.status_message = f"Loaded: {selected_file}"
                                    self.need_refresh = True
                                    self.game.board.last_player_color = 'white' if self.game.next_player == 'black' else 'black'
                                    self.process_flag = (self.game.next_player == 'white')
                                    
                                    # push to joiner
                                    self.broadcast_loaded_game()
                            elif event.key == pygame.K_ESCAPE:
                                self.game.load_menu_mode = False

                        # chat functions - chained as elif (not a separate if)
                        # so that typing into the save-name/load-menu boxes
                        # above doesn't ALSO fall through here and toggle
                        # chat (or, in the else branch below, fire any of
                        # the single-letter game shortcuts) on every
                        # matching keystroke.
                        elif self.chat_active:
                            if event.key == pygame.K_RETURN:
                                if self.chat_text.strip():
                                    self.fb.send_chat_message(self.game_id, self.my_color, self.chat_text)
                                    self.chat_messages.append(f"You: {self.chat_text}")
                                    self.chat_text = ""
                                self.chat_active = False
                            elif event.key == pygame.K_BACKSPACE:
                                self.chat_text = self.chat_text[:-1]
                            elif event.key == pygame.K_c:  # allow 'c' to be typed in chat
                                self.chat_text += 'c'
                            elif len(self.chat_text) < self.max_chars:
                                self.chat_text += event.unicode
                        else:
                            # change theme
                            if event.key == pygame.K_t:
                                game.change_theme()
                                game.change_emblem()
                                game.change_dead_card()
                                
                            # view history back
                            elif event.key == pygame.K_LEFT:
                                if self.game.view_index > 0:
                                    self.game.view_index -= 1
                                    self.game.reconstruct_at_move(self.game.view_index, self.move_log)
                                    
                                    # refresh local points for rendering loop
                                    board = self.game.board
                                    dragger = self.game.dragger
                                    dragger.board = board
                                    clicker = self.game.clicker
                                    clicker.board = board
                                    print(f"Viewing move: {self.game.view_index}")
                            
                            # view history forward
                            elif event.key == pygame.K_RIGHT:
                                if self.game.view_index < len(self.move_log):
                                    self.game.view_index += 1
                                    
                                    # reconstruct board state for this index
                                    self.game.reconstruct_at_move(self.game.view_index, self.move_log)
                                    
                                    # refresh local pointers
                                    board = self.game.board
                                    dragger = self.game.dragger
                                    dragger.board = board
                                    clicker = self.game.clicker
                                    clicker.board = board
                                    print(f"Viewing move: {self.game.view_index}")
                                    
                            # change piece styles
                            elif event.key == pygame.K_y:
                                game.board.change_all_piece_textures()
                                
                            # restart game
                            elif event.key == pygame.K_r:
                                if not self.rematch_requested and not self.opponent_rematch_requested:
                                    # first press - request rematch
                                    self.request_rematch()
                                elif self.opponent_rematch_requested and not self.rematch_requested:
                                    # accepting opponent's request
                                    self.rematch_requested = True
                                    self.fb.update_rematch_status(self.game_id, self.my_color, True)
                                    self.status_message = "Rematch accepted - waiting for game reset"
                                    # immediate check in case both players accepted simultaneously
                                    self.check_and_execute_rematch() 
                            
                            # flip board key
                            elif event.key == pygame.K_f:
                                game.flip_board()
                                
                            # save game (host only)
                            elif event.key == pygame.K_s:
                                if self.is_host:
                                    self.game.save_naming_mode = True
                                else:
                                    self.status_message = "Only the host can save the game"

                            # load game (host only)
                            elif event.key == pygame.K_l:
                                if self.is_host:
                                    if not os.path.exists('saves'):
                                        os.makedirs('saves', exist_ok=True)
                                    self.game.save_files = [f for f in os.listdir('saves') if f.endswith('.json')]
                                    self.game.load_menu_mode = not self.game.load_menu_mode
                                else:
                                    self.status_message = "Only the host can load a game"

                            # start network keys
                            elif event.key == pygame.K_h:
                                self._start_host_ui()
                            elif event.key == pygame.K_j:
                                print("J key pressed - activating input")
                                self.active_input = True
                                self.status_message = "Enter 4-digit PIN:"
                                self.input_text = ""  # clear previous input
                            elif self.active_input:
                                if event.key == pygame.K_RETURN:
                                    self._handle_join_ui()
                                elif event.key == pygame.K_BACKSPACE:
                                    self.input_text = self.input_text[:-1]
                                else:
                                    self.input_text += event.unicode
                                
                            # chat toggle
                            elif event.key == pygame.K_c:  # toggle chat
                                self.chat_active = True
                    
                    # quit application
                    elif event.type == pygame.QUIT:
                        print("🛑 QUIT EVENT RECEIVED - STARTING CLEANUP")
                        try:
                            self.cleanup()
                        except Exception as e:
                            print(f"💥 CLEANUP CRASHED: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            print("🏁 CLEANUP COMPLETE - QUITTING PYGAME")
                            pygame.quit()
                            sys.exit()
                       
                     
                else:
                    opponent = self.game.board.players[0] if self.my_color == 'white' \
                        else self.game.board.players[1]
                    self.game.set_mated_prompt(opponent.color)
                    game.show_cast_prompt(screen, self.my_color)
                    
                    # key press
                    if event.type == pygame.KEYDOWN:
                        
                        # active menu
                        if hasattr(self.game, 'active_menu'):
                            if event.key == pygame.K_ESCAPE:
                                self.game.active_menu = None
                            continue
                        
                        # close help overlays
                        if self.game.show_rules_overlay or self.game.show_controls_overlay:
                            if event.key == pygame.K_ESCAPE:
                                self.game.show_rules_overlay = False
                                self.game.show_controls_overlay = False
                            elif event.key == pygame.K_UP:
                                self.game.help_scroll_y += 35 # scroll up one line
                            elif event.key == pygame.K_DOWN:
                                self.game.help_scroll_y -= 35
                            continue
                        
                        # save game menu
                        if self.game.save_naming_mode:
                            if event.key == pygame.K_RETURN:
                                if self.game.current_save_name.strip():
                                    self.game.save_game(self.game.current_save_name, \
                                            self.move_log)
                                    self.game.save_naming_mode = False
                                    self.game.current_save_name = ""
                                    self.status_message = "Game saved successfully!"
                            elif event.key == pygame.K_ESCAPE:
                                self.game.save_naming_mode = False
                                self.game.current_save_name = ""
                            elif event.key == pygame.K_BACKSPACE:
                                self.game.current_save_name \
                                    = self.game.current_save_name[:-1]
                            else:
                                # limit to 15 chars
                                if len(self.game.current_save_name) < 15 and \
                                    event.unicode.isprintable():
                                    self.game.current_save_name += event.unicode
                                    
                        # load game menu
                        elif self.game.load_menu_mode:
                            if event.key == pygame.K_UP:
                                if self.game.selected_save_idx > 0:
                                    self.game.selected_save_idx -= 1
                            elif event.key == pygame.K_DOWN:
                                if self.game.save_files and \
                                    self.game.selected_save_idx \
                                    < len(self.game.save_files) -1:
                                    self.game.selected_save_idx += 1
                            elif event.key == pygame.K_RETURN:
                                if self.game.save_files:
                                    selected_file = self.game.save_files\
                                        [self.game.selected_save_idx]
                                    self.game.load_game(selected_file)
                                    # update main's local log to match loaded game's
                                    self.move_log = self.game.history.copy()
                                    self.game.load_menu_mode = False
                                    self.status_message = f"Loaded: {selected_file}"
                                    self.need_refresh = True
                                    self.game.board.last_player_color = 'white' if self.game.next_player == 'black' else 'black'
                                    self.process_flag = (self.game.next_player == 'white')
                                    
                                    # push to joiner
                                    self.broadcast_loaded_game()
                            elif event.key == pygame.K_ESCAPE:
                                self.game.load_menu_mode = False

                        # change theme - chained as elif (not a separate if)
                        # so that typing into the save-name/load-menu boxes
                        # above doesn't ALSO fall through here and fire any
                        # of these single-letter game shortcuts on every
                        # matching keystroke.
                        elif event.key == pygame.K_t:
                            game.change_theme()
                            game.change_emblem()
                            game.change_dead_card()
                            
                        # view history back
                        elif event.key == pygame.K_LEFT:
                            if self.game.view_index > 0:
                                self.game.view_index -= 1
                                self.game.reconstruct_at_move(self.game.view_index, self.move_log)
                                
                                # refresh local points for rendering loop
                                board = self.game.board
                                dragger = self.game.dragger
                                dragger.board = board
                                clicker = self.game.clicker
                                clicker.board = board
                                print(f"Viewing move: {self.game.view_index}")
                        
                        # view history forward
                        elif event.key == pygame.K_RIGHT:
                            if self.game.view_index < len(self.move_log):
                                self.game.view_index += 1
                                
                                # reconstruct board state for this index
                                self.game.reconstruct_at_move(self.game.view_index, self.move_log)
                                
                                # refresh local pointers
                                board = self.game.board
                                dragger = self.game.dragger
                                dragger.board = board
                                clicker = self.game.clicker
                                clicker.board = board
                                print(f"Viewing move: {self.game.view_index}")
                            
                        # change piece styles
                        elif event.key == pygame.K_y:
                            game.board.change_all_piece_textures()
                            
                        # restart game
                        elif event.key == pygame.K_r:
                            if not self.rematch_requested and not self.opponent_rematch_requested:
                                # first press - request rematch
                                self.request_rematch()
                            elif self.opponent_rematch_requested and not self.rematch_requested:
                                # accepting opponent's request
                                self.rematch_requested = True
                                db.reference(f'games/{self.game_id}/rematch/{self.my_color}').set(True)
                                self.status_message = "Rematch accepted - waiting for game reset"
                                # immediate check in case both players accepted simultaneously
                                self.check_and_execute_rematch()
                                
                        # save game (host only)
                        elif event.key == pygame.K_s:
                            if self.is_host:
                                self.game.save_naming_mode = True
                            else:
                                self.status_message = "Only the host can save the game"

                        # load game (host only)
                        elif event.key == pygame.K_l:
                            if self.is_host:
                                if not os.path.exists('saves'):
                                    os.makedirs('saves', exist_ok=True)
                                self.game.save_files = [f for f in os.listdir('saves') if f.endswith('.json')]
                                self.game.load_menu_mode = not self.game.load_menu_mode
                            else:
                                self.status_message = "Only the host can load a game"

                    # quit application
                    elif event.type == pygame.QUIT:
                        print("QUIT EVENT RECEIVED - STARTING CLEANUP")
                        try:
                            self.cleanup()
                        except Exception as e:
                            print(f"💥 CLEANUP CRASHED: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            print("🏁 CLEANUP COMPLETE - QUITTING PYGAME")
                            pygame.quit()
                            sys.exit()
            
            # STATUS MESSAGE RENDERING
            # 1. track message changes to create a self-managing timer
            if not hasattr(self, '_last_status'):
                self._last_status = self.status_message
                self._status_time = time.time()
                
            if self.status_message != self._last_status:
                self._last_status = self.status_message
                self._status_time = time.time()

            # 2. categorize the current message
            msg = self.status_message
            is_rematch = "Rematch" in msg or "rematch" in msg
            is_disconnect = "disconnect" in msg
            is_idle = "Press H" in msg or "PIN" in msg
            
            game_started = len(self.move_log) > 0
            time_alive = time.time() - self._status_time
            
            # 3. decide if we should block the game prompt to show this message
            show_override = False
            
            if self.active_input:
                show_override = True
            elif is_rematch or is_disconnect:
                show_override = True  # high Priority: always show
            elif is_idle and not game_started:
                show_override = True  # setup: show until the first move is made
            elif time_alive < 4.0 and msg: 
                show_override = True  # transient: show for 4 seconds
                
            # 4. draw the override if approved
            if show_override:
                # erase the standard game prompt
                erase_rect = pygame.Rect(320, 800 + RAMPART_HEIGHT, 600, 65)
                pygame.draw.rect(self.screen, (0, 0, 0), erase_rect)
                
                # draw the network message
                self.ui_font = pygame.font.SysFont("timesnewroman", 24, bold=True)
                text_color = (150, 150, 150) if is_idle else (255, 255, 255)
                
                if self.active_input:
                    # combine "Enter 4-digit PIN:" with the actual typed numbers
                    display_text = f"{msg} {self.input_text}_"
                    text_color = (240, 240, 245) # Silver
                else:
                    display_text = msg
                    text_color = (150, 150, 150) if is_idle else (255, 255, 255)
                
                status_surface = self.ui_font.render(display_text, True, text_color)
                self.screen.blit(status_surface, (320, 805 + RAMPART_HEIGHT))
            
            # COMMAND STRIP
            # 1. define hitboxes
            base_x = 115 
            # We move base_y down slightly if needed, but keeping it in your area
            base_y = HEIGHT + RAMPART_HEIGHT - 60
            
            # --- HORIZONTAL STRIP CONFIG ---
            h_gap = 10    # space between buttons
            btn_h = 25
            
            # size widths to be slightly wider than text
            # game (~45px text), preferences (~95px text), help (~35px text)
            w_game, w_pref, w_help = 80, 120, 80 
            
            self.btn_game = pygame.Rect(base_x, base_y, w_game, btn_h)
            self.btn_pref = pygame.Rect(self.btn_game.right + h_gap, base_y, w_pref, btn_h)
            self.btn_help = pygame.Rect(self.btn_pref.right + h_gap, base_y, w_help, btn_h)

            # history viewer arrows (Keeping your +535 offset logic)
            arrow_x = self.btn_game.right + 555
            # align arrows vertically with the new horizontal strip
            self.btn_prev = pygame.Rect(arrow_x, base_y - 5, 35, 33) 
            self.btn_next = pygame.Rect(arrow_x + 45, base_y - 5, 35, 33) 

            # 2. draw rectangles with HOVER POP
            mouse_pos = self._get_mouse_pos()
            
            bg_color = (240, 240, 245)     
            base_border = (90, 90, 90)
            hover_border = (0, 0, 0) 
            
            for rect in [self.btn_game, self.btn_pref, self.btn_help, self.btn_prev, self.btn_next]:
                pygame.draw.rect(self.screen, bg_color, rect)
                current_border = hover_border if rect.collidepoint(mouse_pos) else base_border
                pygame.draw.rect(self.screen, current_border, rect, 2)

            # 3. draw text & hover logic
            menu_font = pygame.font.SysFont('Arial', 16, bold=True)
            arrow_font = pygame.font.SysFont('Arial', 18, bold=True)
            
            def get_color(rect):
                return (0, 0, 0) if rect.collidepoint(mouse_pos) else (100, 100, 100)

            # Render and Center text within each button
            for label, rect in [("Game", self.btn_game), ("Preferences", self.btn_pref), ("Help", self.btn_help)]:
                txt_surf = menu_font.render(label, True, get_color(rect))
                # Calculate centering math: (Button Center - Text Half-Width)
                text_x = rect.x + (rect.width // 2 - txt_surf.get_width() // 2)
                text_y = rect.y + (rect.height // 2 - txt_surf.get_height() // 2)
                self.screen.blit(txt_surf, (text_x, text_y))

            # arrow texts
            self.screen.blit(arrow_font.render("<", True, get_color(self.btn_prev)), (self.btn_prev.x + 12, self.btn_prev.y + 6))
            self.screen.blit(arrow_font.render(">", True, get_color(self.btn_next)), (self.btn_next.x + 12, self.btn_next.y + 6))

            self._present()


if __name__ == "__main__":
    # initialize game
    main = Main()
    main.mainloop()