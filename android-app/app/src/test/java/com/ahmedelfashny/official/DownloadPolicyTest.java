package com.ahmedelfashny.official;

import org.junit.Test;
import static org.junit.Assert.*;

public class DownloadPolicyTest {
    @Test public void onlyOwnedHttpsUrlsAreAllowed() {
        assertTrue(DownloadPolicy.isOwnedHttps("https://ahmedelfashny.com/a.pdf"));
        assertTrue(DownloadPolicy.isOwnedHttps("https://www.ahmedelfashny.com/a.pdf"));
        assertFalse(DownloadPolicy.isOwnedHttps("https://ahmedelfashny.com.evil.test/a.pdf"));
        assertFalse(DownloadPolicy.isOwnedHttps("http://ahmedelfashny.com/a.pdf"));
        assertFalse(DownloadPolicy.isOwnedHttps("https://user@ahmedelfashny.com/a.pdf"));
        assertFalse(DownloadPolicy.isOwnedHttps("https://ahmedelfashny.com:8443/a.pdf"));
        assertFalse(DownloadPolicy.isOwnedHttps("javascript:alert(1)"));
    }

    @Test public void filenamesAreSafeAndRetainArabic() {
        assertEquals("خطبة.pdf", DownloadPolicy.pdfFilename("خطبة.pdf"));
        assertEquals("خطبة.pdf", DownloadPolicy.pdfFilename("../خطبة"));
        assertEquals("khutba.pdf", DownloadPolicy.pdfFilename(null));
        assertFalse(DownloadPolicy.pdfFilename("bad\nname.pdf").contains("\n"));
    }

    @Test public void sharedFilesRequireKnownTypesAndMatchingHeaders() {
        byte[] png = {(byte) 137, 80, 78, 71, 13, 10, 26, 10};
        byte[] jpeg = {(byte) 255, (byte) 216, (byte) 255};
        byte[] pdf = {37, 80, 68, 70, 45};
        assertTrue(DownloadPolicy.validHeader(png, "image/png"));
        assertTrue(DownloadPolicy.validHeader(jpeg, "image/jpeg"));
        assertTrue(DownloadPolicy.validHeader(pdf, "application/pdf"));
        assertFalse(DownloadPolicy.validHeader(pdf, "image/png"));
        assertFalse(DownloadPolicy.validHeader(new byte[0], "application/pdf"));
        assertFalse(DownloadPolicy.supportedMime("text/html"));
        assertEquals("بطاقة.png", DownloadPolicy.filename("../بطاقة", "image/png"));
        assertEquals("photo.jpg", DownloadPolicy.filename("photo.jpg", "image/jpeg"));
    }
}
