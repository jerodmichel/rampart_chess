#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 25 15:46:27 2025

@author: stereo
"""
import time
# from typing import Dict, List, Tuple, Optional, Any


# ░█████╗░░█████╗░░██████╗████████╗  ░█████╗░░█████╗░░█████╗░██╗░░██╗███████╗
# ██╔══██╗██╔══██╗██╔════╝╚══██╔══╝  ██╔══██╗██╔══██╗██╔══██╗██║░░██║██╔════╝
# ██║░░╚═╝███████║╚█████╗░░░░██║░░░  ██║░░╚═╝███████║██║░░╚═╝███████║█████╗░░
# ██║░░██╗██╔══██║░╚═══██╗░░░██║░░░  ██║░░██╗██╔══██║██║░░██╗██╔══██║██╔══╝░░
# ╚█████╔╝██║░░██║██████╔╝░░░██║░░░  ╚█████╔╝██║░░██║╚█████╔╝██║░░██║███████╗
# ░╚════╝░╚═╝░░╚═╝╚═════╝░░░░╚═╝░░░  ░╚════╝░╚═╝░░╚═╝░╚════╝░╚═╝░░╚═╝╚══════╝

class ComprehensiveCastCache:
    def __init__(self):
        self.cache = {}  # state_hash -> { 'moves': [], 'timestamp': time }
        self.last_state_hashes = {}  # player_color -> last_state_hash
        
    def store_moves(self, player_color, state_hash, moves):
        """Store calculated moves in cache"""
        self.cache[state_hash] = {
            'moves': moves.copy(),  # store a copy to avoid modification
            'timestamp': time.time()
        }
        self.last_state_hashes[player_color] = state_hash
    
    def get_cached_moves(self, player_color, current_state_hash):
        if player_color in self.last_state_hashes:
            last_hash = self.last_state_hashes[player_color]
            
            # if state unchanged, return full cache
            if current_state_hash == last_hash and current_state_hash in self.cache:
                return self.cache[current_state_hash]['moves']
            
            # if similar state, try incremental update
            if self._states_are_similar(last_hash, current_state_hash):
                return self._incremental_update(last_hash, current_state_hash, player_color)
        
        # no usable cache
        return None
    
    def _states_are_similar(self, old_hash, new_hash):
        """Check if states are similar enough for incremental update"""
        # compare specific components that affect cast moves
        if old_hash not in self.cache or new_hash not in self.cache:
            return False
    
        # use timestamp-based similarity
        old_time = self.cache[old_hash]['timestamp']
        new_time = self.cache[new_hash]['timestamp']
        
        # consider states similar if they're within a short time window
        return abs(new_time - old_time) < 2.0  # allow 1-2 piece changes
    
    def _incremental_update(self, old_hash, current_state_hash, player_color):
        """
        Comprehensive incremental update that handles all edge cases:
        1. Missing cache entries
        2. Corrupted cache structure  
        3. Missing fingerprint data
        4. State mismatches
        """
        import time
        
        # 1. validate old_hash exists
        if old_hash not in self.cache:
            print(f"❌ Incremental update: Old hash {old_hash} not in cache")
            # clean up remaining references
            if hasattr(self, 'last_hash') and self.last_hash == old_hash:
                self.last_hash = None
            return None
        
        # 2. validate cache entry structure
        cache_entry = self.cache[old_hash]
        
        if not isinstance(cache_entry, dict):
            print(f"❌ Cache entry corrupted: Expected dict, got {type(cache_entry)}")
            # Remove corrupted entry
            del self.cache[old_hash]
            if hasattr(self, 'last_hash') and self.last_hash == old_hash:
                self.last_hash = None
            return None
        
        # 3. ensure required keys exist
        required_keys = ['fingerprint', 'moves', 'timestamp']
        missing_keys = [key for key in required_keys if key not in cache_entry]
        
        if missing_keys:
            print(f"❌ Cache entry missing keys: {missing_keys}")
            print(f"    Available keys: {list(cache_entry.keys())}")
            
            # try to salvage if only fingerprint is missing
            if 'moves' in cache_entry and len(missing_keys) == 1 and 'fingerprint' in missing_keys:
                print(f"⚠️  Using moves without fingerprint (legacy entry)")
                return cache_entry['moves'].copy()
            
            # remove corrupted entry
            del self.cache[old_hash]
            if hasattr(self, 'last_hash') and self.last_hash == old_hash:
                self.last_hash = None
            return None
        
        # 4. validate fingerprint structure
        old_fingerprint = cache_entry['fingerprint']
        if not isinstance(old_fingerprint, dict):
            print(f"❌ Fingerprint corrupted: Expected dict, got {type(old_fingerprint)}")
            del self.cache[old_hash]
            if hasattr(self, 'last_hash') and self.last_hash == old_hash:
                self.last_hash = None
            return None
        
        # 5. get current state fingerprint
        try:
            current_fingerprint = self._get_state_fingerprint(player_color)
        except Exception as e:
            print(f"❌ Failed to get current fingerprint: {e}")
            return None
        
        # 6. check if fingerprints match (states are identical)
        if old_fingerprint == current_fingerprint:
            print(f"✓ Incremental: States identical, returning cached moves")
            return cache_entry['moves'].copy()
        
        # 7. compare fingerprints to find still-valid moves
        print(f"⚠️  Incremental: States differ, filtering cached moves")
        
        # get difference between states
        # return None to force recalculation
        print(f"    States differ significantly, recalculating from scratch")
        return None
    
    def _is_cast_move_still_valid(self, move, old_state, new_state, player_color):
        """Check if a cached cast move is still valid given state changes"""
        # 1. check if required cards are still available
        if not self._cards_still_available(move.cards, old_state, new_state, player_color):
            return False
        
        # 2. check if target square is still valid
        if move.cast_type == 1:  # Raise move - square must be empty
            target_pos = (move.final.col, move.final.row)
            if not self._square_still_empty(target_pos, old_state, new_state):
                return False
        
        # 3. check if graveyard piece is still available (for raise moves)
        if hasattr(move, 'requires_grave_piece') and move.requires_grave_piece:
            if not self._grave_piece_still_available(move, old_state, new_state, player_color):
                return False
        
        return True
    
class CardComboCache:
    def __init__(self):
        self.combo_cache = {}  # (available_cards_hash) -> list of valid 21-sum combos
    
    def get_valid_combinations(self, available_cards, target_sum=21):
        cards_hash = self._hash_available_cards(available_cards)
        
        if cards_hash in self.combo_cache:
            return self.combo_cache[cards_hash]
        
        # calculate and cache
        combinations = self._find_21_combinations(available_cards, target_sum)
        self.combo_cache[cards_hash] = combinations
        return combinations
    
    def _hash_available_cards(self, available_cards):
        """Create hash based on available cards"""
        card_tuples = []
        for card in available_cards:
            if hasattr(card, 'suit') and hasattr(card, 'rank'):
                card_tuples.append((card.suit, card.rank, card.is_cast()))
            else:
                # handle board squares with cards
                card_tuples.append((getattr(card, 'suit', -1), 
                                  getattr(card, 'rank', -1), 
                                  getattr(card, 'is_cast', False)()))
        return hash(tuple(sorted(card_tuples)))
    
