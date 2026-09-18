package com.rampartchess.app;

import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;

import com.getcapacitor.BridgeActivity;

// True immersive fullscreen (status bar AND nav bar hidden, swipe to reveal
// temporarily) - the CSS "fullscreen mode" the desktop/web client already
// has only ever hides the browser chrome, never the phone's own system
// bars, which is the actual point of a native wrapper over a home-screen
// PWA shortcut. Re-applied on every focus regain (not just onCreate) since
// Android re-shows the system bars whenever focus is lost/regained (e.g.
// after a permission dialog, or switching apps and back).
public class MainActivity extends BridgeActivity {
    // Instance initializer, not onCreate - Capacitor's own docs call for
    // registering a bundled (non-npm) plugin here, before the Bridge
    // itself is constructed by BridgeActivity's onCreate.
    {
        registerPlugin(RampartEnginePlugin.class);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        enableImmersiveMode();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            enableImmersiveMode();
        }
    }

    private void enableImmersiveMode() {
        View decorView = getWindow().getDecorView();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            getWindow().setDecorFitsSystemWindows(false);
            WindowInsetsController controller = decorView.getWindowInsetsController();
            if (controller != null) {
                controller.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                controller.setSystemBarsBehavior(
                        WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            decorView.setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        }
    }
}
