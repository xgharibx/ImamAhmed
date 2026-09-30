package com.ahmedelfashny.official;

import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

final class DownloadPolicy {
    static final long MAX_BYTES = 64L * 1024 * 1024;

    static boolean isOwnedHttps(String value) {
        try {
            URI uri = new URI(value);
            String host = uri.getHost();
            return "https".equalsIgnoreCase(uri.getScheme()) && uri.getUserInfo() == null
                    && (uri.getPort() == -1 || uri.getPort() == 443)
                    && ("ahmedelfashny.com".equalsIgnoreCase(host)
                    || "www.ahmedelfashny.com".equalsIgnoreCase(host));
        } catch (Exception error) {
            return false;
        }
    }

    static String pdfFilename(String value) {
        return filename(value, "application/pdf");
    }

    static boolean supportedMime(String mime) {
        return "application/pdf".equals(mime) || "image/png".equals(mime) || "image/jpeg".equals(mime);
    }

    static boolean validHeader(byte[] bytes, String mime) {
        if ("application/pdf".equals(mime)) return bytes.length >= 5 && new String(bytes, 0, 5, StandardCharsets.US_ASCII).equals("%PDF-");
        if ("image/png".equals(mime)) return bytes.length >= 8 && bytes[0] == (byte) 137 && bytes[1] == 80 && bytes[2] == 78 && bytes[3] == 71 && bytes[4] == 13 && bytes[5] == 10 && bytes[6] == 26 && bytes[7] == 10;
        if ("image/jpeg".equals(mime)) return bytes.length >= 3 && bytes[0] == (byte) 255 && bytes[1] == (byte) 216 && bytes[2] == (byte) 255;
        return false;
    }

    static String filename(String value, String mime) {
        String extension = "image/png".equals(mime) ? ".png" : "image/jpeg".equals(mime) ? ".jpg" : ".pdf";
        if (value == null || value.trim().isEmpty()) return "khutba" + extension;
        String name = value.replace('\\', '/');
        name = name.substring(name.lastIndexOf('/') + 1).replaceAll("[\\p{Cntrl}:*?\"<>|]", "").trim();
        if (name.toLowerCase(Locale.ROOT).endsWith(extension)) name = name.substring(0, name.length() - extension.length());
        if (name.length() > 100) name = name.substring(0, 100);
        return (name.isEmpty() ? "khutba" : name) + extension;
    }
}
