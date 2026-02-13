(function (global) {
    function normalizeDigits(text) {
        return String(text || '')
            .replace(/[٠-٩]/g, function (digit) {
                return String(digit.charCodeAt(0) - 1632);
            });
    }

    function normalizeArabic(text) {
        return normalizeDigits(String(text || ''))
            .normalize('NFKD')
            .replace(/[\u0640]/g, '')
            .replace(/[\u064B-\u065F\u0670\u06D6-\u06ED]/g, '')
            .replace(/[أإآٱ]/g, 'ا')
            .replace(/[ؤئ]/g, 'ء')
            .replace(/ى/g, 'ي')
            .replace(/ة/g, 'ه')
            .replace(/[^0-9a-zA-Z\u0621-\u064A\s]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim()
            .toLowerCase();
    }

    function tokenize(query) {
        return normalizeArabic(query)
            .split(' ')
            .map(function (token) { return token.trim(); })
            .filter(function (token) { return token.length > 0; });
    }

    function createMatcher(query) {
        var normalizedQuery = normalizeArabic(query || '');
        var tokens = tokenize(query || '');

        return {
            normalizedQuery: normalizedQuery,
            tokens: tokens,
            score: function (haystack) {
                var target = normalizeArabic(haystack || '');
                if (!target) return 0;
                if (!normalizedQuery) return 1;

                var score = 0;
                var matchedTokens = 0;

                if (target.indexOf(normalizedQuery) !== -1) {
                    score += 60;
                }

                for (var i = 0; i < tokens.length; i++) {
                    var token = tokens[i];
                    if (!token) continue;
                    var idx = target.indexOf(token);
                    if (idx !== -1) {
                        matchedTokens += 1;
                        score += 20;
                        if (idx < 30) score += 4;
                    } else {
                        score -= 6;
                    }
                }

                if (matchedTokens === 0 && target.indexOf(normalizedQuery) === -1) {
                    return 0;
                }

                return Math.max(0, score);
            },
            matches: function (haystack) {
                return this.score(haystack) > 0;
            }
        };
    }

    global.SiteSearchUtils = {
        normalize: normalizeArabic,
        normalizeDigits: normalizeDigits,
        tokenize: tokenize,
        createMatcher: createMatcher
    };
})(window);
