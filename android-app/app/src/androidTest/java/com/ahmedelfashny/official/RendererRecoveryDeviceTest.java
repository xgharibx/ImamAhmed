package com.ahmedelfashny.official;

import android.app.Instrumentation;
import android.content.Intent;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.filters.SdkSuppress;
import androidx.test.platform.app.InstrumentationRegistry;

import org.junit.Test;
import org.junit.runner.RunWith;

import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
@SdkSuppress(minSdkVersion = 29)
public class RendererRecoveryDeviceTest {
    private static WebView findWebView(View view) {
        if (view instanceof WebView) return (WebView) view;
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) {
                WebView found = findWebView(group.getChildAt(i));
                if (found != null) return found;
            }
        }
        return null;
    }

    private static WebView awaitPage(Instrumentation instrumentation, MainActivity activity, String url, WebView excluded) throws Exception {
        for (int attempt = 0; attempt < 100; attempt++) {
            AtomicReference<WebView> ready = new AtomicReference<>();
            instrumentation.runOnMainSync(() -> {
                WebView view = findWebView(activity.getWindow().getDecorView());
                if (view != null && view != excluded && url.equals(view.getUrl()) && view.getProgress() == 100) ready.set(view);
            });
            if (ready.get() != null) return ready.get();
            Thread.sleep(100);
        }
        throw new AssertionError("Reading page was not restored: " + url);
    }

    @Test public void rendererTerminationRestoresTrustedOfflineReadingPage() throws Exception {
        Instrumentation instrumentation = InstrumentationRegistry.getInstrumentation();
        Intent intent = new Intent(instrumentation.getTargetContext(), MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        MainActivity activity = (MainActivity) instrumentation.startActivitySync(intent);
        String url = "https://ahmedelfashny.com/articles.html";
        try {
            instrumentation.runOnMainSync(() -> findWebView(activity.getWindow().getDecorView()).loadUrl(url));
            WebView original = awaitPage(instrumentation, activity, url, null);
            instrumentation.runOnMainSync(() -> {
                assertNotNull(original.getWebViewRenderProcess());
                assertTrue(original.getWebViewRenderProcess().terminate());
            });
            WebView replacement = awaitPage(instrumentation, activity, url, original);
            assertNotSame(original, replacement);
        } finally {
            instrumentation.runOnMainSync(activity::finish);
        }
    }
}
