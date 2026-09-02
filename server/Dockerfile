# Build from the REPO ROOT (not this directory), since this needs both
# server/ and the sibling io_src_dev_ai/ game-logic package:
#   docker build -f server/Dockerfile -t rampart-api .
FROM python:3.13-slim

WORKDIR /app

COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY server/ server/

# only the game-logic/AI modules the server actually imports - not
# main.py/game.py/config.py/effects.py/dragger.py (pygame-display/audio/
# rendering code with no place in a headless server), not assets/ (images,
# only used by the desktop client's rendering), not services/ (Firebase -
# a separate future step), not saves/ or the stray debug/trace *.txt files.
COPY io_src_dev_ai/const.py io_src_dev_ai/board.py io_src_dev_ai/square.py \
     io_src_dev_ai/piece.py io_src_dev_ai/card.py io_src_dev_ai/grave.py \
     io_src_dev_ai/clicker.py io_src_dev_ai/player.py io_src_dev_ai/move.py \
     io_src_dev_ai/cast_move.py io_src_dev_ai/cast_button.py \
     io_src_dev_ai/comprehensiveCastCache.py io_src_dev_ai/ai_engine.py \
     io_src_dev_ai/ai_casting.py io_src_dev_ai/rampartbitboard.py \
     io_src_dev_ai/rampartmovegenerator.py \
     io_src_dev_ai/

EXPOSE 8080
WORKDIR /app/server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
