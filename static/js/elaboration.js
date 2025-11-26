(function(){
    const openBtn = document.getElementById('vg_openHelpBtn');
    const closeBtn = document.getElementById('vg_closeHelpBtn');
    const modal = document.getElementById('vg_helpModal');
    const bodyPre = document.getElementById('vg_helpBody');
    const playBtn = document.getElementById('vg_playTutorialBtn');

    let cachedText = null;

    function loadText() {
        if (!bodyPre) return Promise.resolve();
        const src = bodyPre.getAttribute('data-src') || '/static/text/index.txt';
        if (cachedText !== null) {
            bodyPre.textContent = cachedText;
            return Promise.resolve();
        }
        return fetch(src, {cache: 'no-store'}).then(r => {
            if (!r.ok) throw new Error('load fail');
            return r.text();
        }).then(t => { cachedText = t; bodyPre.textContent = t; })
        .catch(()=>{ /* 保持为空或已有内容，不抛错 */ });
    }

    function openModal() {
        if (!modal) return;
        loadText().finally(() => {
            modal.classList.add('show');
            modal.removeAttribute('hidden');
            // focus first control
            const first = modal.querySelector('.vg-modal-close') || modal;
            first && first.focus();
            document.body.style.overflow = 'hidden';
        });
    }
    function closeModal() {
        if (!modal) return;
        modal.classList.remove('show');
        modal.setAttribute('hidden','');
        if (openBtn) openBtn.focus();
        document.body.style.overflow = '';
    }

    function openVideoInNewTab() {
        if (!playBtn) return;
        const url = playBtn.getAttribute('data-video') || '/static/videos/tutorial.mp4';
        window.open(url, '_blank', 'noopener,noreferrer');
    }

    if (openBtn) openBtn.addEventListener('click', openModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (playBtn) playBtn.addEventListener('click', openVideoInNewTab);

    // 点遮罩外关闭
    if (modal) {
        modal.addEventListener('click', function(e){
            if (e.target === modal) closeModal();
        });
    }
    // ESC 关闭
    document.addEventListener('keydown', function(e){
        if (e.key === 'Escape' && modal && modal.classList.contains('show')) closeModal();
        // 简易 focus-trap
        if (e.key === 'Tab' && modal && modal.classList.contains('show')) {
            const focusables = modal.querySelectorAll('button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])');
            if (!focusables.length) return;
            const arr = Array.prototype.slice.call(focusables);
            const idx = arr.indexOf(document.activeElement);
            if (e.shiftKey && idx === 0) { arr[arr.length-1].focus(); e.preventDefault(); }
            if (!e.shiftKey && idx === arr.length-1) { arr[0].focus(); e.preventDefault(); }
        }
    });
})();