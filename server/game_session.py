"""Headless wrapper around the io_src_dev_ai game/AI logic for the web
backend. Deliberately does NOT use game.py's Game/Main classes - those are
bound up in pygame rendering, sound (Config() calls pygame.mixer.init()),
and UI-only state (hourglass, hover, prompts) that a server has no use for
and that would drag in pygame as a runtime dependency. Board (and
ai_engine.py) have no pygame dependency at all, so this wrapper talks to
Board directly and re-derives only the turn-management/game-over logic
that main.py's Main class already has, minus anything UI-only.
"""

import os
import sys
import uuid

IO_SRC_DEV_AI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "io_src_dev_ai")
if IO_SRC_DEV_AI not in sys.path:
    sys.path.insert(0, IO_SRC_DEV_AI)

from board import Board
from square import Square
from move import Move
from cast_move import Cast_move
from piece import Raider, Queen
from rampartbitboard import RampartBitboard
from ai_engine import NegamaxEngine


class IllegalMoveError(Exception):
    pass


class GameSession:
    def __init__(self, ai_color="black", ai_difficulty="Medium"):
        self.id = uuid.uuid4().hex[:12]
        self.board = Board(False)
        self.next_player = "white"
        self.move_log = []
        self.state_history = []
        self.ai_color = ai_color
        self.ai_engine = NegamaxEngine()
        self.ai_engine.max_depth = 4 if ai_difficulty == "Easy" else 6

        temp_bb = RampartBitboard()
        temp_bb.sync_from_board(self.board)
        self.state_history.append(temp_bb.get_state_hash())

    # -- helpers --------------------------------------------------------

    def _player(self, color):
        return self.board.players[0] if self.board.players[0].color == color \
            else self.board.players[1]

    def _record_repetition(self):
        temp_bb = RampartBitboard()
        temp_bb.sync_from_board(self.board)
        current_hash = temp_bb.get_state_hash()
        self.state_history.append(current_hash)
        if self.state_history.count(current_hash) >= 3:
            self.board.king_stalemated = True
            return True
        return False

    def _post_move(self, mover_color):
        """Mirrors main.py's _post_move_check_validation + next_turn, minus
        the UI-only prompt/sound calls.

        Repetition tracking is recorded only after the AI's own move, not
        after every move - this matches main.py exactly: state_history is
        only ever appended to from _post_move_check_validation, which is
        only reached via the AI-move path (_apply_engine_move), never from
        the human-move handler. Recording after every move would put the
        position that's about to be searched into its own history, and
        negamax's root call treats "current hash already in history" as an
        immediate abort - i.e. every AI search would return None."""
        rival_color = "black" if mover_color == "white" else "white"
        rival_player = self._player(rival_color)

        self.board._king_mated(rival_player)
        if self.board.king_mated or self.board.king_stalemated:
            return

        if mover_color == self.ai_color and self._record_repetition():
            return

        if self.board.is_draw_by_insufficient_material():
            self.board.king_stalemated = True
            return

        self.next_player = rival_color

    def is_game_over(self):
        return bool(self.board.king_mated or self.board.king_stalemated)

    # -- normal moves -----------------------------------------------------

    def legal_moves(self, col, row):
        sq = self.board.squares[col][row]
        if not sq.has_piece():
            return []
        piece = sq.piece
        if piece.color != self.next_player:
            return []
        self.board.calc_moves(piece, col, row, bool=True)
        return [(mv.final.col, mv.final.row) for mv in piece.moves]

    def apply_normal_move(self, from_col, from_row, to_col, to_row):
        piece = self.board.squares[from_col][from_row].piece
        if not piece or piece.color != self.next_player:
            raise IllegalMoveError("no movable piece of the side to move there")

        self.board.calc_moves(piece, from_col, from_row, bool=True)

        final_piece = self.board.squares[to_col][to_row].piece
        game_move = Move(Square(from_col, from_row), Square(to_col, to_row, final_piece))

        if not self.board.valid_move(piece, game_move):
            raise IllegalMoveError(f"{from_col},{from_row} -> {to_col},{to_row} is not legal")

        if final_piece and final_piece.name in ("raider", "queen"):
            self.board._send_to_grave(final_piece)

        notation = self.board.move(piece, game_move)
        self.move_log.append(notation)
        self._post_move(piece.color)
        return notation

    # -- cast moves -------------------------------------------------------

    def legal_cast_moves(self):
        """Returns cast moves grouped by category: 'strike', 'raise_raider',
        'raise_queen'.

        Two real quirks in board.py's calc_cast_moves drive how this is
        built (both confirmed via git diff to predate this session, not
        touched here):

        1. The `piece` argument doesn't actually filter what gets computed -
        when called without a known_combo (the only way this wrapper calls
        it), it unconditionally computes and returns BOTH strike and raise
        candidates together in player.cast_moves regardless of what `piece`
        was passed. So categorizing by calling it three times with three
        different `piece` values (raider/queen/None) - the seemingly
        obvious approach - actually returns the same mixed list three
        times over. Instead this calls it once and categorizes the raw
        results by each move's own cast_type, then (for raise moves)
        independently re-checks safety per piece type via cast_in_check,
        the same call calc_cast_moves itself uses internally.

        2. ComprehensiveCastCache keys cached move lists by board state
        hash only, not by piece type, so a stale cache entry from a
        differently-typed call can otherwise get validated against the
        wrong piece type inside cast_move() and crash on piece.name. Only
        matters here because of quirk 1's workaround still calling
        calc_cast_moves fresh each time; cleared defensively regardless."""
        player = self._player(self.next_player)
        color = self.next_player

        player.clear_cast_moves()
        self.board.cast_cache.cache = {}
        self.board.calc_cast_moves(player, None, booL=True)
        raw_moves = list(player.cast_moves)
        player.clear_cast_moves()
        self.board.cast_cache.cache = {}

        strikes = [m for m in raw_moves if m.cast_type == 0]

        # calc_cast_moves can append the same raise move more than once -
        # once per piece type it happened to be independently safe for -
        # so dedupe by move identity before re-checking safety ourselves.
        raise_candidates = []
        for m in raw_moves:
            if m.cast_type == 1 and not any(m == existing for existing in raise_candidates):
                raise_candidates.append(m)

        queen_eligible = self.board._queen_isdead(color) and \
            self.board._enemy_queen_house_occupied(color)

        raise_raider = [m for m in raise_candidates
                         if not self.board.cast_in_check(player, Raider(color), m)]
        raise_queen = [m for m in raise_candidates
                        if queen_eligible and
                        not self.board.cast_in_check(player, Queen(color), m)] \
            if queen_eligible else []

        return {"strike": strikes, "raise_raider": raise_raider, "raise_queen": raise_queen}

    def apply_cast_move(self, category, index):
        """category: 'strike' | 'raise_raider' | 'raise_queen'. Re-derives
        the legal cast moves fresh (rather than trusting a client-submitted
        move) so a stale/fabricated request can't be executed, and so the
        move carries real Card object references instead of a JSON
        round-trip reconstruction of them."""
        moves_by_category = self.legal_cast_moves()
        candidates = moves_by_category.get(category, [])
        if index < 0 or index >= len(candidates):
            raise IllegalMoveError(f"no such {category} cast move at index {index}")
        cast_move = candidates[index]
        piece_type = {"strike": None, "raise_raider": "raider", "raise_queen": "queen"}[category]
        return self._execute_cast_move(cast_move, piece_type)

    def _execute_cast_move(self, cast_move, piece_type):
        """piece_type: 'raider' | 'queen' | None (strike). Shared by
        apply_cast_move (client-facing, index-validated) and
        request_ai_move (internal, already-trusted engine output)."""
        player = self._player(self.next_player)
        if piece_type == "queen":
            piece = Queen(self.next_player)
        elif piece_type == "raider":
            piece = Raider(self.next_player)
        else:
            piece = None

        card = self.board.squares[cast_move.final.col][cast_move.final.row].card
        notation = self.board.cast_move(player, piece, card, cast_move)
        self.move_log.append(notation)
        self._post_move(self.next_player)
        return notation

    # -- AI -----------------------------------------------------------------

    def request_ai_move(self):
        if self.next_player != self.ai_color:
            raise IllegalMoveError("it is not the AI's turn")

        engine_move = self.ai_engine.get_best_move(
            self.board, self.ai_color, self.state_history, debug=False)

        if engine_move is None:
            return None

        if engine_move.move_type == "normal":
            from_col, from_row = engine_move.from_sq % 10, engine_move.from_sq // 10
            to_col, to_row = engine_move.to_sq % 10, engine_move.to_sq // 10
            return self.apply_normal_move(from_col, from_row, to_col, to_row)

        # cast move: translate the engine's move back into a real Cast_move
        t_col, t_row = engine_move.to_sq % 10, engine_move.to_sq // 10
        target_sq = self.board.squares[t_col][t_row]
        deck_suit = 1 if self.ai_color == "white" else 0

        used_cards = [self.board.cards[deck_suit][rank_idx] for rank_idx in engine_move.deck_cards]
        cast_type_int = 0 if engine_move.move_type == "strike" else 1
        cast_move = Cast_move(used_cards, target_sq, cast_type_int)

        if engine_move.move_type == "strike":
            piece_type = None
        elif engine_move.move_type == "raise_queen":
            piece_type = "queen"
        else:
            piece_type = "raider"
        return self._execute_cast_move(cast_move, piece_type)

    # -- serialization ------------------------------------------------------

    def to_dict(self):
        board = self.board
        pieces = []
        for col in range(10):
            for row in range(6):
                sq = board.squares[col][row]
                if sq.has_piece():
                    pieces.append({
                        "col": col, "row": row,
                        "piece": sq.piece.name, "color": sq.piece.color,
                    })

        def serialize_grave(grave_list):
            return [g.piece.name if g.has_piece() else None for g in grave_list]

        return {
            "id": self.id,
            "next_player": self.next_player,
            "ai_color": self.ai_color,
            "pieces": pieces,
            "history": self.move_log,
            "white_deck": [c.is_cast() for c in board.cards[1]],
            "black_deck": [c.is_cast() for c in board.cards[0]],
            "white_grave": serialize_grave(board.graves[1]),
            "black_grave": serialize_grave(board.graves[0]),
            "king_mated": bool(board.king_mated),
            "king_stalemated": bool(board.king_stalemated),
        }
