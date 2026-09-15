const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');
const base = process.env.PREVIEW_URL || 'http://127.0.0.1:4174';

(async () => {
    const data = JSON.parse(fs.readFileSync(path.join(root, 'data/videos.json'), 'utf8'));
    const newest = (a, b) => (Date.parse(b.publishedAt || b.date) || 0) - (Date.parse(a.publishedAt || a.date) || 0);
    const browser = await chromium.launch({ channel: 'chrome', headless: true });
    fs.mkdirSync(path.join(__dirname, 'artifacts'), { recursive: true });
    try {
        for (const width of [390, 820, 1440]) {
            const page = await browser.newPage({ viewport: { width, height: 900 } });
            const errors = [];
            page.on('pageerror', error => errors.push(error.message));
            for (const [file, select] of [
                ['videos.html', v => v.sourceChannel !== 'tarteel' && v.category !== 'khutbah'],
                ['khutab-video.html', v => v.category === 'khutbah'],
                ['tilawa.html', v => v.sourceChannel === 'tarteel']
            ]) {
                await page.goto(base + '/' + file, { waitUntil: 'domcontentloaded' });
                await page.locator('.video-card').first().waitFor();
                const expected = data.filter(select).sort(newest).slice(0, 20).map(v => v.id);
                const actual = await page.locator('.video-card .video-thumbnail').evaluateAll(elements =>
                    elements.map(element => element.getAttribute('onclick').match(/\('([^']+)'/)[1]));
                assert.deepEqual(actual, expected);
                if (file === 'videos.html') {
                    await page.locator('.filter-btn[data-filter="quran"]').click();
                    const titles = await page.locator('.video-title').allTextContents();
                    assert.deepEqual(titles, data.filter(v => v.sourceChannel !== 'tarteel' && v.category === 'quran').sort(newest).slice(0, 20).map(v => v.title));
                }
                await page.screenshot({ path: path.join(__dirname, 'artifacts', `catalog-${width}-${file}.png`) });
                console.log(`PASS ${width} ${file}: newest 20 IDs and category filtering`);
            }
            assert.deepEqual(errors, []);
            await page.close();
        }
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exit(1); });
