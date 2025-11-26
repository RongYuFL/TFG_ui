document.getElementById('trainForm').addEventListener('submit', function (e) {
e.preventDefault();
const formData = new FormData(this);

// 立即从表单获取视频路径并播放
const refVideoPath = formData.get('ref_video');
const videoEl = document.getElementById('trainVideo');

if (refVideoPath) {
    // 立即设置视频源并播放
    const newSrc = "/" + refVideoPath.replace("\\", "/") + '?t=' + new Date().getTime();
    videoEl.src = newSrc;
    videoEl.load();
    videoEl.play().catch(e => console.log('自动播放可能被阻止:', e));
}

fetch('/model_training', {
    method: 'POST',
    body: formData
})
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            alert('训练完成！');
        }
    })
    .catch(err => console.error('错误:', err));
});