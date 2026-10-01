(() => {
    'use strict';
    if (window !== window.top || window.__sheikhAppRuntime) return;
    window.__sheikhAppRuntime = true;

    function hidePagePreloader() {
        if (!document.documentElement || document.getElementById('app-offline-preloader')) return;
        const style = document.createElement('style');
        style.id = 'app-offline-preloader';
        style.textContent = '#preloader{display:none!important}';
        (document.head || document.documentElement).appendChild(style);
    }
    hidePagePreloader();
    if (!document.documentElement) document.addEventListener('DOMContentLoaded', hidePagePreloader, { once: true });

    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, options) => {
        const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url, location.href);
        const method = (options?.method || input?.method || 'GET').toUpperCase();
        if (url.origin === location.origin && url.pathname.startsWith('/data/') && method === 'GET') {
            options = { ...options, cache: 'no-cache' };
        }
        return originalFetch(input, options);
    };

    if (!window.SheikhNative) return;
    const waiting = new Map();
    let nextId = 0;
    SheikhNative.onmessage = event => {
        const reply = JSON.parse(event.data);
        const request = waiting.get(reply.id);
        if (!request) return;
        waiting.delete(reply.id);
        clearTimeout(request.timer);
        if (reply.ok) request.resolve();
        else request.reject(new Error(reply.error || 'Native operation failed'));
    };
    function send(message) {
        return new Promise((resolve, reject) => {
            const id = ++nextId;
            const timer = setTimeout(() => { waiting.delete(id); reject(new Error('Native operation timed out')); }, 30000);
            waiting.set(id, { resolve, reject, timer });
            SheikhNative.postMessage(JSON.stringify({ ...message, id }));
        });
    }

    // Retain the actual Blob until transfer finishes, even if FileSaver revokes its URL.
    const blobs = new Map();
    const originalCreate = URL.createObjectURL.bind(URL);
    const originalRevoke = URL.revokeObjectURL.bind(URL);
    URL.createObjectURL = blob => {
        const url = originalCreate(blob);
        blobs.set(url, blob);
        return url;
    };
    URL.revokeObjectURL = url => { blobs.delete(url); originalRevoke(url); };

    const supportedTypes = new Set(['application/pdf', 'image/png', 'image/jpeg']);
    async function transfer(blob, name, operation = 'save') {
        if (blob.size > 64 * 1024 * 1024) throw new Error('File exceeds 64 MB');
        await send({ type: 'start', name, size: blob.size, mime: blob.type || 'application/pdf', operation });
        try {
            for (let offset = 0; offset < blob.size; offset += 49152) {
                const bytes = new Uint8Array(await blob.slice(offset, offset + 49152).arrayBuffer());
                let binary = '';
                for (const byte of bytes) binary += String.fromCharCode(byte);
                await send({ type: 'chunk', data: btoa(binary) });
            }
            await send({ type: 'finish' });
        } catch (error) {
            await send({ type: 'cancel' }).catch(() => {});
            throw error;
        }
    }
    function handleDownload(anchor) {
        if (!anchor.download || !anchor.href.startsWith('blob:')) return false;
        const blob = blobs.get(anchor.href);
        if (!blob || !(supportedTypes.has(blob.type) || /\.pdf$/i.test(anchor.download))) return false;
        transfer(blob, anchor.download).catch(error => {
            console.error(error);
            alert('تعذر حفظ الملف. يرجى المحاولة مرة أخرى.');
        });
        return true;
    }
    const originalClick = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () {
        if (!handleDownload(this)) originalClick.call(this);
    };
    const originalDispatch = HTMLAnchorElement.prototype.dispatchEvent;
    HTMLAnchorElement.prototype.dispatchEvent = function (event) {
        if (event.type === 'click' && handleDownload(this)) return false;
        return originalDispatch.call(this, event);
    };
    document.addEventListener('click', event => {
        const anchor = event.target.closest?.('a[download]');
        if (anchor && handleDownload(anchor)) event.preventDefault();
    }, true);

    Object.defineProperty(navigator, 'share', { configurable: true, value: async data => {
        if (data.files?.length) {
            if (data.files.length !== 1 || !supportedTypes.has(data.files[0].type)) throw new Error('Unsupported shared file');
            await transfer(data.files[0], data.files[0].name, 'share');
            return;
        }
        await send({ type: 'share', title: data.title || '', text: data.text || '', url: data.url || '' });
    }});
    Object.defineProperty(navigator, 'canShare', { configurable: true, value: data => !data?.files?.length || (data.files.length === 1 && supportedTypes.has(data.files[0].type)) });
})();
