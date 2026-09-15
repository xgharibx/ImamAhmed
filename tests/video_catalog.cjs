const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

for (const file of ['videos-dynamic.js', 'khutab-video.js', 'tilawa-dynamic.js']) {
    const element = { addEventListener() {}, querySelector() { return null; } };
    const context = {
        document: {
            addEventListener(event, callback) { if (event === 'DOMContentLoaded') callback(); },
            querySelector() { return element; }, querySelectorAll() { return []; },
            getElementById() { return element; }
        },
        window: { addEventListener() {} },
        fetch: () => new Promise(() => {}), console, URLSearchParams
    };
    const names = ['extractDateFromText', 'extractVideoTimestamp', 'sortByNewest'];
    if (file !== 'tilawa-dynamic.js') names.push('classifyVideo');
    const source = fs.readFileSync(path.join(__dirname, '..', file), 'utf8').replace(
        "document.addEventListener('DOMContentLoaded', () => {",
        "document.addEventListener('DOMContentLoaded', () => { globalThis.api = {" + names.join(',') + '};'
    );
    vm.runInNewContext(source, context, { filename: file });
    const { extractDateFromText: date, extractVideoTimestamp: timestamp, sortByNewest: newest } = context.api;
    assert.equal(date('2026-07-05'), Date.UTC(2026, 6, 5));
    assert.equal(date('٢٠٢٦-٠٧-٠٥'), Date.UTC(2026, 6, 5));
    assert.equal(date('2026-02-31'), 0);
    assert.equal(date('05/07/2026'), Date.UTC(2026, 6, 5));
    assert.equal(timestamp({ date: '2026-07-05', publishedAt: '2026-07-05T10:15:19-07:00' }), Date.parse('2026-07-05T17:15:19Z'));
    const ordered = [
        { date: '2026-08-28', _sourceIndex: 0 },
        { date: '2026-09-11', _sourceIndex: 1 },
        { date: '2026-09-04', _sourceIndex: 2 }
    ].map(video => ({ ...video, _sortTimestamp: timestamp(video) })).sort(newest);
    assert.deepEqual(ordered.map(video => video.date), ['2026-09-11', '2026-09-04', '2026-08-28']);
    if (context.api.classifyVideo) {
        assert.equal(context.api.classifyVideo({ title: 'مقطع من خطبة الجمعة', category: 'shorts', categoryVerified: true }), 'shorts');
        assert.equal(context.api.classifyVideo({ title: 'تلاوة سورة الجمعة', category: 'quran', categoryVerified: true }), 'quran');
    }
    console.log('PASS ' + file + ': exact dates, newest-first order, verified categories');
}
