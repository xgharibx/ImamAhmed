package com.ahmedelfashny.official;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.GeolocationPermissions;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

public class MainActivity extends Activity {
    private static final int FILE_CHOOSER_REQUEST = 42;
    private static final String LIVE_SITE_URL = BuildConfig.LIVE_SITE_URL;
    private static final String LIVE_SITE_HOST = BuildConfig.LIVE_SITE_HOST;

    private WebView webView;
    private SwipeRefreshLayout swipeRefreshLayout;
    private ProgressBar progressBar;
    private View offlineView;
    private ValueCallback<Uri[]> filePathCallback;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildLayout();
        configureWebView();

        String startUrl = resolveStartUrl(getIntent());
        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState);
        } else {
            webView.loadUrl(startUrl);
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        webView.loadUrl(resolveStartUrl(intent));
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        webView.saveState(outState);
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            settings.setSafeBrowsingEnabled(true);
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
            CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);
        }
        CookieManager.getInstance().setAcceptCookie(true);

        webView.setWebViewClient(new AppWebViewClient());
        webView.setWebChromeClient(new AppWebChromeClient());
        webView.setDownloadListener(createDownloadListener());
    }

    private void buildLayout() {
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.WHITE);

        swipeRefreshLayout = new SwipeRefreshLayout(this);
        swipeRefreshLayout.setColorSchemeResources(
                R.color.primary_green,
                R.color.primary_gold,
                R.color.primary_green_dark
        );
        swipeRefreshLayout.setOnRefreshListener(() -> webView.reload());

        webView = new WebView(this);
        webView.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));
        swipeRefreshLayout.addView(webView);
        root.addView(swipeRefreshLayout);

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setVisibility(View.GONE);
        FrameLayout.LayoutParams progressParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(3),
                Gravity.TOP
        );
        root.addView(progressBar, progressParams);

        offlineView = createOfflineView();
        offlineView.setVisibility(View.GONE);
        root.addView(offlineView);

        setContentView(root);
    }

    private View createOfflineView() {
        FrameLayout wrapper = new FrameLayout(this);
        wrapper.setBackgroundColor(getColorCompat(R.color.surface_light));

        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setGravity(Gravity.CENTER);
        panel.setBackgroundResource(R.drawable.offline_panel);
        panel.setElevation(dp(4));

        TextView title = new TextView(this);
        title.setText(R.string.offline_title);
        title.setTextColor(getColorCompat(R.color.primary_green_dark));
        title.setTextSize(22);
        title.setGravity(Gravity.CENTER);
        title.setTypeface(null, 1);

        TextView message = new TextView(this);
        message.setText(R.string.offline_message);
        message.setTextColor(Color.rgb(72, 78, 75));
        message.setTextSize(16);
        message.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams messageParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        messageParams.setMargins(0, dp(12), 0, dp(20));

        Button retry = new Button(this);
        retry.setText(R.string.retry);
        retry.setTextColor(Color.WHITE);
        retry.setAllCaps(false);
        retry.setBackgroundResource(R.drawable.retry_button);
        retry.setOnClickListener(v -> {
            offlineView.setVisibility(View.GONE);
            webView.loadUrl(currentOrHomeUrl());
        });

        panel.addView(title);
        panel.addView(message, messageParams);
        panel.addView(retry);

        FrameLayout.LayoutParams panelParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
                Gravity.CENTER
        );
        int margin = dp(24);
        panelParams.setMargins(margin, margin, margin, margin);
        wrapper.addView(panel, panelParams);
        return wrapper;
    }

    private String resolveStartUrl(Intent intent) {
        Uri uri = intent != null ? intent.getData() : null;
        if (uri != null && isInternalHttpUrl(uri)) {
            return uri.toString();
        }
        return LIVE_SITE_URL;
    }

    private boolean isInternalHttpUrl(Uri uri) {
        String scheme = uri.getScheme();
        String host = uri.getHost();
        if (scheme == null || host == null) return false;
        boolean isHttp = "https".equalsIgnoreCase(scheme) || "http".equalsIgnoreCase(scheme);
        return isHttp && (LIVE_SITE_HOST.equalsIgnoreCase(host) || ("www." + LIVE_SITE_HOST).equalsIgnoreCase(host));
    }

    private boolean shouldOpenExternally(Uri uri) {
        String scheme = uri.getScheme();
        if (scheme == null) return false;
        if (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme)) return true;
        return !isInternalHttpUrl(uri);
    }

    private void openExternal(Uri uri) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, uri);
            intent.addCategory(Intent.CATEGORY_BROWSABLE);
            startActivity(intent);
        } catch (ActivityNotFoundException error) {
            Toast.makeText(this, "لا يوجد تطبيق مناسب لفتح الرابط", Toast.LENGTH_SHORT).show();
        }
    }

    private DownloadListener createDownloadListener() {
        return (url, userAgent, contentDisposition, mimeType, contentLength) -> openExternal(Uri.parse(url));
    }

    private String currentOrHomeUrl() {
        String current = webView.getUrl();
        return current == null || current.trim().isEmpty() ? LIVE_SITE_URL : current;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private int getColorCompat(int colorRes) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            return getColor(colorRes);
        }
        return getResources().getColor(colorRes);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        super.onBackPressed();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != FILE_CHOOSER_REQUEST || filePathCallback == null) return;

        Uri[] results = null;
        if (resultCode == RESULT_OK && data != null) {
            if (data.getClipData() != null) {
                int count = data.getClipData().getItemCount();
                results = new Uri[count];
                for (int index = 0; index < count; index++) {
                    results[index] = data.getClipData().getItemAt(index).getUri();
                }
            } else if (data.getData() != null) {
                results = new Uri[]{data.getData()};
            }
        }

        filePathCallback.onReceiveValue(results);
        filePathCallback = null;
    }

    private final class AppWebViewClient extends WebViewClient {
        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            if (shouldOpenExternally(uri)) {
                openExternal(uri);
                return true;
            }
            return false;
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, String url) {
            Uri uri = Uri.parse(url);
            if (shouldOpenExternally(uri)) {
                openExternal(uri);
                return true;
            }
            return false;
        }

        @Override
        public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
            offlineView.setVisibility(View.GONE);
            progressBar.setVisibility(View.VISIBLE);
            super.onPageStarted(view, url, favicon);
        }

        @Override
        public void onPageFinished(WebView view, String url) {
            progressBar.setVisibility(View.GONE);
            swipeRefreshLayout.setRefreshing(false);
            super.onPageFinished(view, url);
        }

        @Override
        public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && request.isForMainFrame()) {
                showOfflineIfNeeded();
            }
            super.onReceivedError(view, request, error);
        }

        @Override
        public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
            showOfflineIfNeeded();
            super.onReceivedError(view, errorCode, description, failingUrl);
        }

        private void showOfflineIfNeeded() {
            progressBar.setVisibility(View.GONE);
            swipeRefreshLayout.setRefreshing(false);
            offlineView.setVisibility(View.VISIBLE);
        }
    }

    private final class AppWebChromeClient extends WebChromeClient {
        @Override
        public void onProgressChanged(WebView view, int newProgress) {
            progressBar.setProgress(newProgress);
            progressBar.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
        }

        @Override
        public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> callback, FileChooserParams params) {
            if (filePathCallback != null) {
                filePathCallback.onReceiveValue(null);
            }
            filePathCallback = callback;

            Intent intent;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                intent = params.createIntent();
            } else {
                intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
            }

            try {
                startActivityForResult(intent, FILE_CHOOSER_REQUEST);
                return true;
            } catch (ActivityNotFoundException error) {
                filePathCallback = null;
                Toast.makeText(MainActivity.this, "لا يوجد تطبيق لاختيار الملفات", Toast.LENGTH_SHORT).show();
                return false;
            }
        }

        @Override
        public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {
            boolean granted = Build.VERSION.SDK_INT < Build.VERSION_CODES.M
                    || checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
            callback.invoke(origin, granted, false);
        }
    }
}
