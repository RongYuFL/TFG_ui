(function(){
    const openBtn = document.getElementById('openHelpBtn');
    const closeBtn = document.getElementById('closeHelpBtn');
    const modal = document.getElementById('helpModal');
    const helpBody = document.getElementById('helpBody');

    // 新增控件
    const playBtn = document.getElementById('playTutorialBtn');
    const modalVideo = document.getElementById('modalVideo');
    const tutorialVideo = document.getElementById('tutorialVideo');
    const closeVideoBtn = document.getElementById('closeVideoBtn');

    // 缓存已加载文本，避免重复请求
    let cachedHelpText = null;

    // 在打开 modal 时加载文本（优先使用缓存）
    function loadHelpText() {
        if (!helpBody) return;
        if (cachedHelpText !== null) {
            helpBody.textContent = cachedHelpText;
            return;
        }
        fetch('/static/text/index.txt', {cache: "no-store"})
            .then(resp => {
                if (!resp.ok) throw new Error('Network response was not ok');
                return resp.text();
            })
            .then(text => {
                cachedHelpText = text;
                helpBody.textContent = text;
            })
            .catch(() => {
                // 失败时保留现有内容（不抛错）
            });
    }

    function openModal() {
        if (!modal) return;
        loadHelpText();
        modal.classList.add('show');
        const first = modal.querySelector('.modal-close') || modal;
        first && first.focus();
        document.body.style.overflow = 'hidden';
    }
    function closeModal() {
        if (!modal) return;
        if (tutorialVideo && !tutorialVideo.paused) {
            tutorialVideo.pause();
            tutorialVideo.currentTime = 0;
        }
        if (modalVideo) {
            modalVideo.hidden = true;
            modalVideo.setAttribute('aria-hidden', 'true');
        }
        if (helpBody) {
            helpBody.hidden = false;
            helpBody.setAttribute('aria-hidden', 'false');
        }
        modal.classList.remove('show');
        if (openBtn) openBtn.focus();
        document.body.style.overflow = '';
    }

    // 新：点击播放直接在新标签页打开视频文件
    function openVideoInNewTab() {
        if (!playBtn) return;
        const url = playBtn.getAttribute('data-video') || '/static/videos/tutorial.mp4';
        // 打开新标签页
        window.open(url, '_blank', 'noopener,noreferrer');
    }

    if (openBtn) openBtn.addEventListener('click', openModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    // 修改：play 按钮事件改为在新标签打开视频
    if (playBtn) playBtn.addEventListener('click', openVideoInNewTab);
    if (closeVideoBtn) closeVideoBtn.addEventListener('click', function(){
        // 保留原有关闭视频逻辑以防仍有内嵌视频展示的情况
        if (tutorialVideo) {
            tutorialVideo.pause();
            tutorialVideo.currentTime = 0;
        }
        if (modalVideo) { modalVideo.hidden = true; modalVideo.setAttribute('aria-hidden','true'); }
        if (helpBody) { helpBody.hidden = false; helpBody.setAttribute('aria-hidden','false'); }
        playBtn && playBtn.focus();
    });

    if (modal) {
        modal.addEventListener('click', function(e){
            if (e.target === modal) closeModal();
        });
    }
    document.addEventListener('keydown', function(e){
        if (e.key === 'Escape' && modal && modal.classList.contains('show')) {
            if (modalVideo && !modalVideo.hidden) { 
                if (tutorialVideo) { tutorialVideo.pause(); tutorialVideo.currentTime = 0; }
                modalVideo.hidden = true; modalVideo.setAttribute('aria-hidden','true');
                if (helpBody) { helpBody.hidden = false; helpBody.setAttribute('aria-hidden','false'); }
            } else closeModal();
        }
        if (e.key === 'Tab' && modal && modal.classList.contains('show')) {
            const focusables = modal.querySelectorAll('button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])');
            if (!focusables.length) return;
            const arr = Array.prototype.slice.call(focusables);
            const idx = arr.indexOf(document.activeElement);
            if (e.shiftKey && idx === 0) { arr[arr.length-1].focus(); e.preventDefault(); }
            if (!e.shiftKey && idx === arr.length-1) { arr[0].focus(); e.preventDefault(); }
        }
    });

    window.addEventListener('beforeunload', function(){ if (tutorialVideo) { tutorialVideo.pause(); } });
})();