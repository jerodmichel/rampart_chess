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
import re
import sys
import time
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
from const import RANKS, SUITS


class IllegalMoveError(Exception):
    pass


class GameSession:
    # "pool": a shared budget per color that depletes over the whole game
    # (standard chess clock). "per_move": resets to the full period every
    # time it becomes that color's turn instead of accumulating - a move
    # that took 10 minutes doesn't cost you anything toward your next one.
    TIME_CONTROLS = {
        "30min": {"kind": "pool", "ms": 30 * 60 * 1000},
        "1hour": {"kind": "pool", "ms": 60 * 60 * 1000},
        "1day_per_move": {"kind": "per_move", "ms": 24 * 60 * 60 * 1000},
    }

    # Ported from io_src_dev_ai/main.py's AI_DIFFICULTY_SETTINGS - Hard
    # needs a much larger time_limit alongside the deeper max_depth, or the
    # search hits NegamaxEngine's default 5s cap before finishing even the
    # depth Medium already targets, let alone going deeper (confirmed live:
    # a real Medium search hit "Time limit reached at Depth 5" instead of
    # its intended 6 - this mapping is what actually fixes that, not just
    # raising max_depth on its own would).
    AI_DIFFICULTY_SETTINGS = {
        "Easy": {"max_depth": 4, "time_limit": 5.0},
        "Medium": {"max_depth": 6, "time_limit": 5.0},
        "Hard": {"max_depth": 7, "time_limit": 15.0},
    }

    def __init__(self, ai_color="black", ai_difficulty="Medium", white_uid=None, black_uid=None,
                 time_control=None):
        """ai_color=None means a real two-human game (see challenges.py) -
        white_uid/black_uid then identify who's allowed to move each side
        (enforced in app.py, not here); both stay None for the existing
        anonymous human-vs-AI mode, which still needs no account at all.

        time_control (None | one of TIME_CONTROLS' keys) is likewise only
        meaningful for a real two-human game - an AI opponent has its own
        search-time budget to worry about, which is a separate concern this
        doesn't try to unify with player clocks."""
        self.id = uuid.uuid4().hex[:12]
        self.board = Board(False)
        self.next_player = "white"
        self.move_log = []
        self.state_history = []
        self.ai_color = ai_color
        self.white_uid = white_uid
        self.black_uid = black_uid
        self.resigned_by = None  # 'white' | 'black' | None
        self.draw_agreed = False
        self.draw_offered_by = None  # 'white' | 'black' | None - most recent offer
        self.ai_engine = NegamaxEngine()
        settings = self.AI_DIFFICULTY_SETTINGS.get(ai_difficulty, self.AI_DIFFICULTY_SETTINGS["Medium"])
        self.ai_engine.max_depth = settings["max_depth"]
        self.ai_engine.time_limit = settings["time_limit"]

        if time_control is not None and time_control not in self.TIME_CONTROLS:
            raise ValueError(f"unknown time control {time_control!r}")
        self.time_control = time_control
        self.timed_out_color = None  # 'white' | 'black' | None
        if time_control is not None:
            initial_ms = self.TIME_CONTROLS[time_control]["ms"]
            self.white_remaining_ms = initial_ms
            self.black_remaining_ms = initial_ms
            self.clock_running_since_ms = int(time.time() * 1000)
        else:
            self.white_remaining_ms = None
            self.black_remaining_ms = None
            self.clock_running_since_ms = None

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
        immediate abort - i.e. every AI search would return None.

        A human-vs-human game (ai_color is None) has no AI search to ever
        abort, so that concern doesn't apply - record after every move there
        instead, or threefold repetition would never be detected at all."""
        self._tick_clock(mover_color)

        rival_color = "black" if mover_color == "white" else "white"
        rival_player = self._player(rival_color)

        self.board._king_mated(rival_player)
        if self.board.king_mated or self.board.king_stalemated:
            return

        record_now = self.ai_color is None or mover_color == self.ai_color
        if record_now and self._record_repetition():
            return

        if self.board.is_draw_by_insufficient_material():
            self.board.king_stalemated = True
            return

        self.next_player = rival_color

    def _tick_clock(self, mover_color):
        """Stops mover_color's clock (deducting elapsed time - or, for a
        per-move time control, simply resetting since that kind never
        accumulates) and starts the run for whoever moves next. Called from
        _post_move so every move-executing path (human or AI, normal or
        cast) goes through this same single choke point. No-op for untimed
        games (time_control is None), which includes every AI game."""
        if self.time_control is None:
            return
        now_ms = int(time.time() * 1000)
        elapsed_ms = now_ms - self.clock_running_since_ms
        is_pool = self.TIME_CONTROLS[self.time_control]["kind"] == "pool"
        period_ms = self.TIME_CONTROLS[self.time_control]["ms"]

        if mover_color == "white":
            self.white_remaining_ms = max(0, self.white_remaining_ms - elapsed_ms) if is_pool else period_ms
        else:
            self.black_remaining_ms = max(0, self.black_remaining_ms - elapsed_ms) if is_pool else period_ms
        self.clock_running_since_ms = now_ms

    def _check_timeout(self):
        """Lazily evaluates whether whoever's on the clock right now has
        run out - called before any read or move-attempt so a timeout is
        detected without needing a background scheduler polling every game
        in memory. No-op for untimed games or a game that's already over."""
        if self.time_control is None or self.is_game_over():
            return
        now_ms = int(time.time() * 1000)
        elapsed_ms = now_ms - self.clock_running_since_ms
        remaining = self.white_remaining_ms if self.next_player == "white" else self.black_remaining_ms
        if elapsed_ms >= remaining:
            self.timed_out_color = self.next_player

    def _live_remaining_ms(self):
        """(white_ms, black_ms) as of right now, for display - the side not
        on the clock is exactly its stored value; the side currently on the
        clock has the still-elapsing time subtracted live, so a client
        polling this sees an accurate countdown rather than a number that
        only updates once per move."""
        if self.time_control is None:
            return None, None
        now_ms = int(time.time() * 1000)
        elapsed_ms = now_ms - self.clock_running_since_ms
        white_ms, black_ms = self.white_remaining_ms, self.black_remaining_ms
        if self.next_player == "white":
            white_ms = max(0, white_ms - elapsed_ms)
        else:
            black_ms = max(0, black_ms - elapsed_ms)
        return white_ms, black_ms

    def is_game_over(self):
        return bool(self.board.king_mated or self.board.king_stalemated
                    or self.resigned_by or self.draw_agreed or self.timed_out_color)

    def result(self):
        """Unified "how did the game end" summary - None while still in
        progress. Board-driven endings (checkmate/stalemate) are read
        straight off self.board, which is already the source of truth for
        those; resignation/draw/timeout are tracked here since the board
        itself has no concept of any of them."""
        if self.board.king_mated:
            # _post_move only advances next_player when the game ISN'T
            # over, so next_player here is still the side that delivered
            # mate - i.e. the winner.
            return {"winner": self.next_player, "reason": "checkmate"}
        if self.resigned_by:
            winner = "black" if self.resigned_by == "white" else "white"
            return {"winner": winner, "reason": "resignation"}
        if self.draw_agreed:
            return {"winner": None, "reason": "draw_agreement"}
        if self.timed_out_color:
            winner = "black" if self.timed_out_color == "white" else "white"
            return {"winner": winner, "reason": "timeout"}
        if self.board.king_stalemated:
            return {"winner": None, "reason": "stalemate"}
        return None

    def resign(self, color):
        self._check_timeout()
        if self.is_game_over():
            raise IllegalMoveError("the game is already over")
        self.resigned_by = color

    def offer_draw(self, color):
        self._check_timeout()
        if self.is_game_over():
            raise IllegalMoveError("the game is already over")
        self.draw_offered_by = color

    def respond_draw(self, color, accept):
        self._check_timeout()
        if self.is_game_over():
            raise IllegalMoveError("the game is already over")
        if self.draw_offered_by is None:
            raise IllegalMoveError("no draw has been offered")
        if self.draw_offered_by == color:
            raise IllegalMoveError("you can't respond to your own draw offer")
        if accept:
            self.draw_agreed = True
        self.draw_offered_by = None  # offer is consumed either way

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
        self._check_timeout()
        if self.is_game_over():
            raise IllegalMoveError("the game is already over")
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

    def _resolve_card(self, spec, color):
        """spec: {'rank': int, 'suit': int}, as returned by this same
        wrapper's own card serialization. Returns the real Card object the
        rest of board.py operates on (not a reconstructed lookalike), or
        None if the request doesn't describe an actual usable card."""
        rank, suit = spec["rank"], spec["suit"]
        if suit in (0, 1):
            own_deck_suit = 1 if color == "white" else 0
            if suit != own_deck_suit:
                return None  # not this player's own deck
            card = self.board.cards[suit][rank]
            return None if card.is_cast() else card
        # board card (suit 2 or 3): find the square carrying it that also
        # has one of COLOR's own raiders sitting on it - mirrors how
        # board.py's possible_hand is built.
        for col in range(10):
            for row in range(1, 5):
                sq = self.board.squares[col][row]
                if sq.has_piece() and sq.piece.name == "raider" and sq.piece.color == color \
                        and sq.is_card() and sq.card.rank == rank and sq.card.suit == suit:
                    return sq.card
        return None

    def _resolve_cards(self, card_specs, color):
        cards = []
        for spec in card_specs:
            card = self._resolve_card(spec, color)
            if card is None:
                return None
            cards.append(card)
        return cards

    def legal_cast_destinations_for_combo(self, card_specs, kind):
        """Like legal_cast_moves(), but for one SPECIFIC combo of cards -
        e.g. what a browser player manually selected - rather than
        whichever single combo board.py's _find_valid_combo happens to
        find first for the whole board. kind: 'strike' | 'raise'.

        This exists because _find_valid_combo only ever returns one combo
        per category and reuses it for every destination square, so a
        player's own (equally legal) combo choice can differ from the one
        the engine's own search landed on - see known_combo in
        board.py's calc_cast_moves, which is exactly how the desktop
        client avoids this same problem."""
        color = self.next_player
        player = self._player(color)

        cards = self._resolve_cards(card_specs, color)
        if cards is None:
            raise IllegalMoveError("one or more selected cards are not available")
        if not self.board.clicker.has_sum_21(cards):
            raise IllegalMoveError("selected cards do not sum to 21")

        board_card_count = sum(1 for c in cards if c.suit in (2, 3))

        player.clear_cast_moves()
        self.board.cast_cache.cache = {}

        if kind == "strike":
            if board_card_count < 2:
                raise IllegalMoveError("striking needs two board cards")
            self.board.calc_cast_moves(player, None, booL=True, known_combo=cards)
            strikes = [m for m in player.cast_moves if m.cast_type == 0]
            player.clear_cast_moves()
            self.board.cast_cache.cache = {}
            return {"strike": strikes, "raise_raider": [], "raise_queen": []}

        if board_card_count < 1:
            raise IllegalMoveError("raising needs at least one board card")

        self.board.calc_cast_moves(player, Raider(color), booL=True, known_combo=cards)
        raw_moves = list(player.cast_moves)
        player.clear_cast_moves()
        self.board.cast_cache.cache = {}

        # calc_cast_moves can append the same raise move more than once -
        # once per piece type it happened to be independently safe for -
        # same quirk legal_cast_moves() works around, for the same reason.
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

        return {"strike": [], "raise_raider": raise_raider, "raise_queen": raise_queen}

    def apply_cast_combo_move(self, card_specs, kind, to_col, to_row):
        """Execute a cast using a manually-selected combo rather than a
        (category, index) pair into legal_cast_moves(). Re-derives the
        legal destinations for this exact combo fresh - never trusts the
        client's claim that `to` is a valid destination for it - before
        executing, same principle as apply_cast_move()."""
        self._check_timeout()
        if self.is_game_over():
            raise IllegalMoveError("the game is already over")
        destinations = self.legal_cast_destinations_for_combo(card_specs, kind)

        if kind == "strike":
            match = next((m for m in destinations["strike"]
                          if m.final.col == to_col and m.final.row == to_row), None)
            if match is None:
                raise IllegalMoveError("no such strike destination for this combo")
            return self._execute_cast_move(match, None)

        # raise: prefer raider, fall back to queen where only queen is
        # safe there - matches the browser client's own simplification of
        # not yet offering an explicit "choose a piece" UI when both are
        # legal at the same square.
        raider_match = next((m for m in destinations["raise_raider"]
                             if m.final.col == to_col and m.final.row == to_row), None)
        if raider_match is not None:
            return self._execute_cast_move(raider_match, "raider")

        queen_match = next((m for m in destinations["raise_queen"]
                            if m.final.col == to_col and m.final.row == to_row), None)
        if queen_match is not None:
            return self._execute_cast_move(queen_match, "queen")

        raise IllegalMoveError("no such raise destination for this combo")

    def apply_cast_move(self, category, index):
        """category: 'strike' | 'raise_raider' | 'raise_queen'. Re-derives
        the legal cast moves fresh (rather than trusting a client-submitted
        move) so a stale/fabricated request can't be executed, and so the
        move carries real Card object references instead of a JSON
        round-trip reconstruction of them."""
        self._check_timeout()
        if self.is_game_over():
            raise IllegalMoveError("the game is already over")
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

        # Board.cast_move() doesn't mark the deck cards it consumed as
        # cast - the desktop client does that itself via Game.cast_cards()
        # right after committing a cast move, which this wrapper never
        # called. Without this, a deck card could be reused indefinitely.
        for c in cast_move.cards:
            if c.suit in (0, 1):
                c.cast = True

        self.move_log.append(notation)
        self._post_move(self.next_player)
        return notation

    # -- AI -----------------------------------------------------------------

    def request_ai_move(self):
        self._check_timeout()  # no-op here (AI games are untimed) - kept for symmetry
        if self.is_game_over():
            raise IllegalMoveError("the game is already over")
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

    @staticmethod
    def _serialize_board(board):
        """The board-shaped part of to_dict()/state_at()'s response -
        factored out so a historical replay board can be serialized
        exactly the same way as the live one. Doesn't touch self at all,
        so ReplayOnlyGame (below) can reuse it directly for a persisted
        record whose live GameSession no longer exists."""
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
            "pieces": pieces,
            "white_deck": [c.is_cast() for c in board.cards[1]],
            "black_deck": [c.is_cast() for c in board.cards[0]],
            "white_grave": serialize_grave(board.graves[1]),
            "black_grave": serialize_grave(board.graves[0]),
        }

    def to_dict(self):
        self._check_timeout()
        out = self._serialize_board(self.board)
        white_ms, black_ms = self._live_remaining_ms()
        out.update({
            "id": self.id,
            "next_player": self.next_player,
            "ai_color": self.ai_color,
            "white_uid": self.white_uid,
            "black_uid": self.black_uid,
            "history": self.move_log,
            "king_mated": bool(self.board.king_mated),
            "king_stalemated": bool(self.board.king_stalemated),
            "draw_offered_by": self.draw_offered_by,
            "time_control": self.time_control,
            "white_time_ms": white_ms,
            "black_time_ms": black_ms,
            "result": self.result(),
            "view_index": len(self.move_log),
            "is_live": True,
        })
        return out

    # -- history replay -------------------------------------------------

    # parses a "<col><row-letter>" square token, e.g. "3f" or "10a" -
    # column is 1-10 so it can be 1 or 2 digits, can't fixed-width-slice
    # it from the row letter. Ported from game.py's identical regex.
    SQUARE_TOKEN_RE = re.compile(r'^(\d+)([a-f])')

    @classmethod
    def _parse_square_token(cls, token):
        match = cls.SQUARE_TOKEN_RE.match(token)
        col = int(match.group(1)) - 1
        row = 5 - (ord(match.group(2)) - ord('a'))
        return col, row

    @staticmethod
    def _apply_notation(board, notation, next_player):
        """Applies one move_log entry to `board` (mutated in place) and
        returns the color who moves next. Ported from game.py's
        apply_notation_to_board, adapted to take an explicit board/
        next_player instead of self.board/self.next_player so it can
        replay onto a throwaway board without touching the live game -
        and, since it doesn't touch self at all, ReplayOnlyGame (below)
        can reuse it too for a persisted record with no live GameSession.
        (Doesn't bother tracking board.last_move - nothing here reads it;
        the web client derives its own highlight from the notation
        string directly.)"""
        if ">" in notation and "/" not in notation:
            src_str, dst_str = notation[1:].split(">")
            f_col, f_row = GameSession._parse_square_token(src_str)
            t_col, t_row = GameSession._parse_square_token(dst_str)
            piece = board.squares[f_col][f_row].piece
            if piece is not None:
                # Board.move() overwrites the destination unconditionally -
                # it never sends a captured piece to the grave itself, that
                # is always the caller's job (apply_normal_move does this
                # for a live move; game.py's own apply_notation_to_board
                # does NOT for a replayed one, a real gap there too - see
                # the chat note flagging it for the desktop client).
                captured = board.squares[t_col][t_row].piece
                if captured is not None and captured.name in ("raider", "queen"):
                    board._send_to_grave(captured)
                move = Move(Square(f_col, f_row), Square(t_col, t_row))
                board.move(piece, move)

        elif "++" in notation or "--" in notation:
            is_raise = "++" in notation
            target_part = notation.split('@')[1].split('(')[0]
            t_col, t_row = GameSession._parse_square_token(target_part)
            target_sq = board.squares[t_col][t_row]
            p_char = notation[2]

            if is_raise:
                if p_char == 'R':
                    board._raise_raider(t_col, t_row, next_player, target_sq.card)
                else:
                    board._raise_queen(t_col, t_row, next_player, target_sq.card)
            else:
                board._send_to_grave(target_sq.piece)
                target_sq.piece = None

            cards_part = notation.split('(')[1].split(')')[0]
            deck_suit = 1 if next_player == "white" else 0
            for label in cards_part.split(','):
                if not any(s in label for s in SUITS):
                    rank_idx = RANKS.index(label)
                    board.cards[deck_suit][rank_idx].cast = True

        elif "/" in notation:
            move_part, spawn_part = notation.split("/")
            GameSession._apply_notation(board, move_part, next_player)
            q_target = spawn_part.split('@')[1]
            q_col, q_row = GameSession._parse_square_token(q_target)
            board._raise_queen(q_col, q_row, next_player, board.squares[q_col][q_row].card)

        return "black" if next_player == "white" else "white"

    def state_at(self, index):
        """Read-only snapshot of the position after `index` half-moves of
        this game's move_log (0 = the start, len(move_log) = the live
        position). Replays onto a throwaway Board rather than mutating
        self.board - unlike the desktop client's reconstruct_at_move,
        nothing needs a reconstructed board to sit around between calls,
        since each request already carries its own index."""
        if index < 0 or index > len(self.move_log):
            raise IllegalMoveError(f"no such history index {index}")
        self._check_timeout()

        replay = Board(False)
        next_player = "white"
        for notation in self.move_log[:index]:
            next_player = self._apply_notation(replay, notation, next_player)

        # An earlier index was, by definition, not a game-over position -
        # the real game continued past it. Only the live index can be
        # actually mated/stalemated, and self.board already has the
        # authoritative, fully-tracked flags for it (including repetition/
        # insufficient-material, which aren't derivable from a replay
        # board alone) - reuse those rather than re-deriving from scratch.
        is_live = index == len(self.move_log)
        white_ms, black_ms = self._live_remaining_ms() if is_live else (None, None)

        out = self._serialize_board(replay)
        out.update({
            "id": self.id,
            "next_player": next_player,
            "ai_color": self.ai_color,
            "white_uid": self.white_uid,
            "black_uid": self.black_uid,
            "history": self.move_log,
            "king_mated": bool(self.board.king_mated) if is_live else False,
            "king_stalemated": bool(self.board.king_stalemated) if is_live else False,
            "draw_offered_by": self.draw_offered_by if is_live else None,
            "time_control": self.time_control,
            "white_time_ms": white_ms,
            "black_time_ms": black_ms,
            "result": self.result() if is_live else None,
            "view_index": index,
            "is_live": is_live,
        })
        return out


class ReplayOnlyGame:
    """A read-only stand-in for a GameSession that's been evicted from
    memory (the in-memory GAMES dict doesn't survive a server restart) but
    still has a persisted record (see game_records.py) - supports exactly
    the two read-only methods app.py's GET endpoints need (to_dict/
    state_at), reconstructed by replaying the persisted move history
    through the exact same GameSession._apply_notation/_serialize_board
    used for a live game's own history viewer.

    Deliberately supports nothing else: once a game's real GameSession is
    gone, so is its AI engine, negamax repetition-tracking state, and
    exact live clock - it can only ever be viewed from here on, not
    continued. A real "resume a live game across a restart" would need
    replay through the actual move-execution path (apply_normal_move/
    _execute_cast_move), not this display-only one - out of scope for now,
    and a rare enough case (a game interrupted mid-play by a restart) that
    "it's still fully viewable, just not resumable" is a reasonable trade
    for what a solo-dev in-memory server can support today."""

    def __init__(self, record):
        self.id = record["id"]
        self.ai_color = None  # only human-vs-human games are persisted at all
        self.white_uid = record.get("white_uid")
        self.black_uid = record.get("black_uid")
        self.time_control = record.get("time_control")
        self.move_log = record.get("history", [])
        self._result = record.get("result")

    def to_dict(self):
        return self.state_at(len(self.move_log))

    def state_at(self, index):
        if index < 0 or index > len(self.move_log):
            raise IllegalMoveError(f"no such history index {index}")

        replay = Board(False)
        next_player = "white"
        for notation in self.move_log[:index]:
            next_player = GameSession._apply_notation(replay, notation, next_player)

        is_live = index == len(self.move_log)
        out = GameSession._serialize_board(replay)
        out.update({
            "id": self.id,
            "next_player": next_player,
            "ai_color": self.ai_color,
            "white_uid": self.white_uid,
            "black_uid": self.black_uid,
            "history": self.move_log,
            # king_mated/king_stalemated were only ever a live GameSession's
            # own board flags, not persisted - the unified `result` field
            # (computed once, correctly, at the moment the real game ended)
            # is the only game-over signal this can offer.
            "king_mated": False,
            "king_stalemated": False,
            "draw_offered_by": None,
            "white_time_ms": None,
            "black_time_ms": None,
            "result": self._result if is_live else None,
            "view_index": index,
            "is_live": is_live,
        })
        return out
