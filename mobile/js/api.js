// Thin wrapper around the server/ FastAPI backend. No game logic lives
// here - every function is a direct call to one endpoint in server/app.py.

const BASE_URL = window.RAMPART_API_BASE || 'http://localhost:8080';

async function request(path, options) {
    const res = await fetch(`${BASE_URL}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!res.ok) {
        let detail = res.statusText;
        try {
            const body = await res.json();
            detail = body.detail || detail;
        } catch (_) { /* no JSON body */ }
        throw new Error(`${path} failed (${res.status}): ${detail}`);
    }
    return res.json();
}

export const api = {
    newGame(aiColor, aiDifficulty) {
        return request('/games', {
            method: 'POST',
            body: JSON.stringify({ ai_color: aiColor, ai_difficulty: aiDifficulty }),
        });
    },

    getGame(gameId) {
        return request(`/games/${gameId}`);
    },

    legalMoves(gameId, col, row) {
        return request(`/games/${gameId}/legal_moves?col=${col}&row=${row}`);
    },

    castMoves(gameId) {
        return request(`/games/${gameId}/cast_moves`);
    },

    move(gameId, fromCol, fromRow, toCol, toRow) {
        return request(`/games/${gameId}/move`, {
            method: 'POST',
            body: JSON.stringify({ from_col: fromCol, from_row: fromRow, to_col: toCol, to_row: toRow }),
        });
    },

    castMove(gameId, category, index) {
        return request(`/games/${gameId}/cast_move`, {
            method: 'POST',
            body: JSON.stringify({ category, index }),
        });
    },

    aiMove(gameId) {
        return request(`/games/${gameId}/ai_move`, { method: 'POST' });
    },
};
