from flask import Flask, render_template, request, jsonify
from pydub import AudioSegment
import os
from backend.video_generator import generate_video
from backend.model_trainer import train_model
from backend.chat_engine import chat_response
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# 首页
@app.route('/')
def index():
    return render_template('index.html')

# 视频生成界面
@app.route('/video_generation', methods=['GET', 'POST'])
def video_generation():
    if request.method == 'POST':
        data = {
            "model_name": request.form.get('model_name'),
            "model_param": request.form.get('model_param'),
            "ref_audio": request.form.get('ref_audio'),
            "gpu_choice": request.form.get('gpu_choice'),
            "target_text": request.form.get('target_text'),
        }

        video_path = generate_video(data)
        return jsonify({'status': 'success', 'video_path': video_path})

    return render_template('video_generation.html')


# 模型训练界面
@app.route('/model_training', methods=['GET', 'POST'])
def model_training():
    if request.method == 'POST':
        data = {
            "model_choice": request.form.get('model_choice'),
            "ref_video": request.form.get('ref_video'),
            "gpu_choice": request.form.get('gpu_choice'),
            "epoch": request.form.get('epoch'),
            "custom_params": request.form.get('custom_params')
        }

        video_path = train_model(data)
        video_path = "/" + video_path.replace("\\", "/")

        return jsonify({'status': 'success', 'video_path': video_path})

    return render_template('model_training.html')


# 实时对话系统界面
@app.route('/chat_system', methods=['GET', 'POST'])
def chat_system():
    if request.method == 'POST':
        data = {
            "model_name": request.form.get('model_name'),
            "model_param": request.form.get('model_param'),
            "voice_clone": request.form.get('voice_clone'),
            "api_choice": request.form.get('api_choice'),
        }

        video_path = chat_response(data)
        video_path = "/" + video_path.replace("\\", "/")

        return jsonify({'status': 'success', 'video_path': video_path})

    return render_template('chat_system.html')

@app.route('/save_audio', methods=['POST'])
def save_audio():
    if 'audio' not in request.files:
        return jsonify({'status': 'error', 'message': '没有音频文件'})

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择文件'})

    # --- 修复流程开始 ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(base_dir, 'SyncTalk', 'audio')
    os.makedirs(save_dir, exist_ok=True)

    # 1. 先将浏览器发送的(可能损坏的)Blob保存到一个临时文件
    # (我们不关心它的扩展名，因为 pydub 会自动检测)
    raw_file_path = os.path.join(save_dir, 'aud_raw_from_browser')
    audio_file.save(raw_file_path)

    # 2. 定义我们最终想要的、修复后的、固定的 WAV 路径
    final_wav_path = os.path.join(save_dir, 'aud.wav')

    # 3. 使用 pydub 加载这个(可能损坏的)文件，并重新导出
    #    pydub (和 ffmpeg) 擅长猜测原始格式
    try:
        print(f"[app.py] 收到原始音频。正在从 {raw_file_path} 加载...")
        # 加载文件 (pydub 会自动检测格式, 无论是 ogg, webm, 还是无头的 wav)
        audio = AudioSegment.from_file(raw_file_path)
        
        print(f"[app.py] 正在重新导出为标准 WAV: {final_wav_path}")
        
        # 重新导出为标准的、带头的 WAV 文件
        # 这时你可以强制设置参数，以确保 ASR 兼容：
        # audio.set_channels(1) 设为单声道
        # audio.set_frame_rate(16000) 设为 16kHz
        
        audio.export(final_wav_path, format="wav")
        
        print(f"[app.py] 音频保存并修复成功。")

    except Exception as e:
        print(f"!!!!!!!!!!!!!! [app.py] 严重错误: 修复音频文件失败 !!!!!!!!!!!!!!")
        print(f"Error: {e}")
        print("请确保 'ffmpeg' 已正确安装并_INCLUDED_在您 'RVC_cuda' 环境的 PATH 中。")
        # 返回一个错误，停止流程
        return jsonify({'status': 'error', 'message': f'后台处理音频文件失败: {e}'}), 500
    finally:
        # 4. (可选) 清理临时的原始文件
        try:
            if os.path.exists(raw_file_path):
                os.remove(raw_file_path)
        except Exception as e:
            print(f"[app.py] 清理临时文件 {raw_file_path} 失败: {e}")
            pass # 即使清理失败也不是大问题

    # --- 修复流程结束 ---

    # 5. 返回成功信息
    web_path = '/SyncTalk/audio/aud.wav'
    return jsonify({'status': 'success', 'message': '音频保存并修复成功', 'file_path': web_path})


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
