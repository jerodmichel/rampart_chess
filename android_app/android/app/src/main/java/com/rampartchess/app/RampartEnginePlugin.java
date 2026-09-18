package com.rampartchess.app;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONException;

// Bridges web/js's own function shapes to the on-device Python engine
// (android_app/mobile_bridge.py, a thin wrapper around the real
// server/game_session.py/io_src_dev_ai) for offline vs-AI play - see
// web/js/api.js's ANDROID LOCAL ENGINE section for the JS side that
// decides when to call this instead of a real fetch() to the server.
//
// Every method here just forwards to one mobile_bridge.py function and
// resolves with its JSON result VERBATIM - a success body, or a
// {error, status} body on a rule violation (e.g. an illegal move). Turning
// the latter into a thrown Error (matching api.js's own
// "PATH failed (status): detail" format) is api.js's job, not this
// plugin's, so callers never need to know which transport handled a
// request.
@CapacitorPlugin(name = "RampartEngine")
public class RampartEnginePlugin extends Plugin {

    private PyObject bridge() {
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(getContext()));
        }
        return Python.getInstance().getModule("mobile_bridge");
    }

    private void resolveJson(PluginCall call, PyObject result) {
        try {
            call.resolve(new JSObject(result.toString()));
        } catch (JSONException e) {
            call.reject("malformed JSON from local engine: " + e.getMessage());
        }
    }

    @PluginMethod
    public void newGame(PluginCall call) {
        resolveJson(call, bridge().callAttr("new_game",
                call.getString("aiColor"), call.getString("aiDifficulty")));
    }

    @PluginMethod
    public void getGame(PluginCall call) {
        resolveJson(call, bridge().callAttr("get_game", call.getString("gameId")));
    }

    @PluginMethod
    public void legalMoves(PluginCall call) {
        resolveJson(call, bridge().callAttr("legal_moves",
                call.getString("gameId"), call.getInt("col"), call.getInt("row")));
    }

    @PluginMethod
    public void castMoves(PluginCall call) {
        resolveJson(call, bridge().callAttr("cast_moves", call.getString("gameId")));
    }

    // queenCol/queenRow may be null (Chaquopy passes that through as
    // Python None) - only needed for the queen-house-entry two-step move.
    @PluginMethod
    public void move(PluginCall call) {
        resolveJson(call, bridge().callAttr("make_move",
                call.getString("gameId"), call.getInt("fromCol"), call.getInt("fromRow"),
                call.getInt("toCol"), call.getInt("toRow"),
                call.getInt("queenCol"), call.getInt("queenRow")));
    }

    // cardsJson: a JSON-encoded [{rank,suit}, ...] string (simpler to pass
    // one opaque string across the bridge than reconstruct a JS array on
    // the Python side via Chaquopy's Java/Python list conversion).
    @PluginMethod
    public void castComboDestinations(PluginCall call) {
        resolveJson(call, bridge().callAttr("cast_combo_destinations",
                call.getString("gameId"), call.getString("cardsJson"), call.getString("kind")));
    }

    @PluginMethod
    public void castComboMove(PluginCall call) {
        resolveJson(call, bridge().callAttr("cast_combo_move",
                call.getString("gameId"), call.getString("cardsJson"), call.getString("kind"),
                call.getInt("toCol"), call.getInt("toRow")));
    }

    @PluginMethod
    public void aiMove(PluginCall call) {
        resolveJson(call, bridge().callAttr("ai_move", call.getString("gameId")));
    }

    @PluginMethod
    public void historyAt(PluginCall call) {
        resolveJson(call, bridge().callAttr("history_at",
                call.getString("gameId"), call.getInt("index")));
    }

    @PluginMethod
    public void moves(PluginCall call) {
        resolveJson(call, bridge().callAttr("moves", call.getString("gameId")));
    }

    @PluginMethod
    public void resign(PluginCall call) {
        resolveJson(call, bridge().callAttr("resign",
                call.getString("gameId"), call.getString("color")));
    }

    @PluginMethod
    public void abort(PluginCall call) {
        resolveJson(call, bridge().callAttr("abort", call.getString("gameId")));
    }
}
