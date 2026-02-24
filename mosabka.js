document.addEventListener('DOMContentLoaded', async () => {
    if (window.AOS) {
        AOS.init({ duration: 700, once: true });
    }

    const form = document.getElementById('competition-form');
    const wrap = document.getElementById('questions-wrap');
    const notes = document.getElementById('footer-notes');
    const sendBtn = document.getElementById('send-whatsapp');
    const pdfBtn = document.getElementById('download-pdf');

    let config = null;

    try {
        const response = await fetch('data/mosabka_ramadan_1447.json');
        config = await response.json();
    } catch (error) {
        wrap.innerHTML = '<p>تعذر تحميل بيانات المسابقة حالياً.</p>';
        return;
    }

    document.getElementById('competition-title').textContent = config.title || 'مسابقة شهر رمضان الكبرى';
    document.getElementById('competition-intro').textContent = config.intro || '';
    document.getElementById('competition-whatsapp').textContent = config.whatsappDisplay || config.whatsapp || '';
    updateDeadlineCountdown(config);

    (config.questions || []).forEach((item) => {
        const block = document.createElement('article');
        block.className = 'question-item';
        block.innerHTML = `
            <div class="question-head">
                <span class="question-num">${item.number}</span>
                <span class="question-axis">${escapeHtml(item.axis || '')}</span>
            </div>
            <p class="question-text">${escapeHtml(item.question || '')}</p>
            <textarea id="answer-${item.number}" placeholder="اكتب إجابتك هنا..."></textarea>
        `;
        wrap.appendChild(block);
    });

    const submissionNotice = config.submissionNotice || 'يمكنك تعبئة الإجابات ثم الضغط على زر إرسال عبر واتساب مباشرة، أو تحميل الإجابات PDF ثم إرسالها عبر واتساب.';
    notes.innerHTML = `<p>${escapeHtml(submissionNotice)}</p>`;

    sendBtn.addEventListener('click', () => {
        const payload = collectAnswers(config.questions || []);
        const message = buildWhatsappMessage(config, payload);
        const wa = `https://wa.me/${config.whatsapp}?text=${encodeURIComponent(message)}`;
        window.open(wa, '_blank', 'noopener');
    });

    pdfBtn.addEventListener('click', async () => {
        if (form && !form.reportValidity()) {
            form.reportValidity();
            return;
        }

        const payload = collectAnswers(config.questions || []);
        if (!window.SheikhPdfExporter || typeof window.SheikhPdfExporter.exportCompetitionItem !== 'function') {
            alert('تعذر إنشاء PDF حالياً.');
            return;
        }

        try {
            const participantName = payload.participant.fullName || 'مشارك-بدون-اسم';
            const titleForFile = `مسابقة شهر رمضان الكبرى - ${participantName}`;

            const answersHtml = payload.answers.map((item) => `
                <h3>${escapeHtml(String(item.number))}) ${escapeHtml(item.axis || '')}</h3>
                <p>السؤال: ${escapeHtml(item.question || '')}</p>
                <blockquote>الإجابة: ${escapeHtml(item.answer || 'بدون إجابة')}</blockquote>
            `).join('');

            const participantHeader = `
                <h2>بيانات المشارك</h2>
                <p><strong>الاسم:</strong> ${escapeHtml(payload.participant.fullName || '')}</p>
                <p><strong>السن:</strong> ${escapeHtml(payload.participant.age || '')}</p>
                <p><strong>الهاتف:</strong> ${escapeHtml(payload.participant.phone || '')}</p>
                <p><strong>العنوان:</strong> ${escapeHtml(payload.participant.address || '')}</p>
                <h2>الإجابات</h2>
            `;

            await window.SheikhPdfExporter.exportCompetitionItem({
                title: titleForFile,
                subtitle: '',
                author: `المشارك: ${participantName}`,
                date_display: config.deadlineText || '',
                content_html: participantHeader + answersHtml
            });
        } catch (error) {
            alert('حدثت مشكلة أثناء إنشاء ملف PDF، يرجى المحاولة مرة أخرى.');
        }
    });

    function collectAnswers(questions) {
        const participant = {
            fullName: document.getElementById('fullName').value.trim(),
            age: document.getElementById('age').value.trim(),
            address: document.getElementById('address').value.trim(),
            phone: document.getElementById('phone').value.trim()
        };

        const answers = questions.map((q) => ({
            number: q.number,
            axis: q.axis,
            question: q.question,
            answer: (document.getElementById(`answer-${q.number}`)?.value || '').trim() || 'بدون إجابة'
        }));

        return { participant, answers };
    }

    function updateDeadlineCountdown(cfg) {
        const deadlineNode = document.getElementById('competition-deadline');
        if (!deadlineNode) return;

        const baseText = cfg.deadlineText || '';
        const targetRaw = cfg.deadlineGregorian;
        if (!targetRaw) {
            deadlineNode.innerHTML = `<i class="fas fa-hourglass-half"></i> ${baseText}`;
            return;
        }

        const target = new Date(targetRaw);
        if (Number.isNaN(target.getTime())) {
            deadlineNode.innerHTML = `<i class="fas fa-hourglass-half"></i> ${baseText}`;
            return;
        }

        const now = new Date();
        const diffMs = target.getTime() - now.getTime();
        const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays <= 0) {
            deadlineNode.innerHTML = `<i class="fas fa-hourglass-half"></i> ${baseText} — انتهى الموعد`;
            return;
        }

        const dayWord = diffDays === 1 ? 'يوم' : 'أيام';
        deadlineNode.innerHTML = `<i class="fas fa-hourglass-half"></i> ${baseText} — متبقٍ ${diffDays} ${dayWord}`;
    }

    function buildWhatsappMessage(cfg, payload) {
        const lines = [];
        lines.push(cfg.title || 'مسابقة رمضان');
        lines.push('');
        lines.push('بيانات المشارك:');
        lines.push(`الاسم: ${payload.participant.fullName}`);
        lines.push(`السن: ${payload.participant.age}`);
        lines.push(`العنوان: ${payload.participant.address}`);
        lines.push(`الهاتف: ${payload.participant.phone}`);
        lines.push('');
        lines.push('الإجابات:');

        payload.answers.forEach((item) => {
            lines.push(`${item.number}) [${item.axis}] ${item.question}`);
            lines.push(`الإجابة: ${item.answer}`);
            lines.push('');
        });

        return lines.join('\n');
    }

    function escapeHtml(text) {
        return (text || '')
            .toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});
