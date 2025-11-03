let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let startTime;
let timerInterval;

const recordButton = document.getElementById('recordButton');
const timerDisplay = document.getElementById('timer');
const recordingIndicator = document.getElementById('recordingIndicator');
const statusMessage = document.getElementById('statusMessage');

// 格式化时间显示
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// 更新计时器
function updateTimer() {
    const elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
    timerDisplay.textContent = formatTime(elapsedSeconds);
}

// 开始录音
async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });

            // 创建FormData并发送到服务器
            const formData = new FormData();
            formData.append('audio', audioBlob, 'input.wav');

            fetch('/save_audio', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    statusMessage.textContent = '录音已结束';
                } else {
                    statusMessage.textContent = '保存录音失败';
                }
            })
            .catch(error => {
                console.error('保存录音错误:', error);
                statusMessage.textContent = '保存录音时出错';
            });

            // 停止所有音频轨道
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        isRecording = true;
        recordButton.innerHTML = '<span>■</span> 停止录音';
        recordButton.classList.add('recording');
        recordingIndicator.style.display = 'flex';
        statusMessage.textContent = '正在录音...';

        // 启动计时器
        startTime = Date.now();
        timerInterval = setInterval(updateTimer, 1000);

    } catch (error) {
        console.error('获取麦克风权限失败:', error);
        statusMessage.textContent = '无法访问麦克风，请检查权限设置';
    }
}

// 停止录音
function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        recordButton.innerHTML = '<span>●</span> 开始录音';
        recordButton.classList.remove('recording');
        recordingIndicator.style.display = 'none';
        statusMessage.textContent = '录音完成，正在保存...';

        // 停止计时器
        clearInterval(timerInterval);
    }
}

// 录音按钮点击事件
recordButton.addEventListener('click', () => {
    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }
});

document.getElementById('chatForm').addEventListener('submit', function (e) {
    e.preventDefault();
    const formData = new FormData(this);

    fetch('/chat_system', {
        method: 'POST',
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                const videoEl = document.getElementById('chatVideo');
                const newSrc = data.video_path + '?t=' + new Date().getTime();
                videoEl.src = newSrc;
                videoEl.load();
                videoEl.play();
                alert('对话完成！');
            }
        })
        .catch(err => console.error('错误:', err));
});