 document.getElementById('videoForm').addEventListener('submit', function (e) {
            e.preventDefault();

            const formData = new FormData(this);

            fetch('/video_generation', {
                method: 'POST',
                body: formData
            })
                .then(res => res.json())
                .then(data => {
                    console.log("后端返回:", data);
                    if (data.status === 'success') {
                        const videoEl = document.getElementById('outputVideo');
                        const newSrc = data.video_path + '?t=' + new Date().getTime();
                        videoEl.src = newSrc;
                        videoEl.load();
                        videoEl.play().catch(err => console.warn('自动播放被阻止:', err));
                    } else {
                        alert('视频生成失败！');
                    }
                })
                .catch(err => console.error('错误:', err));
        });