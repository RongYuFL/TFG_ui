import os
import sys
import subprocess
from datetime import datetime
import re
from pydub import AudioSegment

# --- 关键路径配置 ---
PYTHON_EXECUTABLE = sys.executable 
print(f"[chat_engine.py] Using Python interpreter: {PYTHON_EXECUTABLE}")
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CHINA_PIPELINE_SCRIPT = os.path.join(BASE_DIR, "china_pipeline.py")
RVC_SCRIPT = os.path.join(BASE_DIR, "RVC.py")
INPUT_AUDIO_PATH = os.path.join(BASE_DIR, "SyncTalk", "audio", "aud.wav")
INTERMEDIATE_TEXT_FILE = os.path.join(BASE_DIR, "latest_ai_response.txt")
RVC_REF_AUDIO = os.path.join(BASE_DIR, "input", "audio", "nahida.wav")
FINAL_AUDIO_NAME = "cloned_output.wav"
FINAL_AUDIO_PATH_SERVER = os.path.join(BASE_DIR, "static", "audios", FINAL_AUDIO_NAME)
FINAL_AUDIO_PATH_WEB = f"/static/audios/{FINAL_AUDIO_NAME}"

# 【新】临时文件
TEMP_TEXT_FILE = os.path.join(BASE_DIR, "temp_rvc_text.txt") # 用于RVC的临时文本


def simple_splitter(text, max_len=50):
    """
    【新】一个简单的文本切分器
    尝试按标点符号切分，并确保每块不超过 max_len
    """
    print(f"[Splitter] 正在切分总长 {len(text)} 的文本...")
    
    # 1. 尝试按标点分割 (包括中英文)
    # 匹配非标点+一个标点 (例如 "你好," "world!")
    segments = re.findall(r"([^。！？，、,!?]+[。！？，、,!?]?)", text, re.UNICODE)
    
    # 2. 如果没有找到标点 (例如一长串无标点文字)
    if not segments:
        print("[Splitter] 未找到标点，将按最大长度硬切分。")
        #  fallback: 按 max_len 硬切分
        return [text[i:i+max_len] for i in range(0, len(text), max_len)]

    # 3. 组合短句，直到接近 max_len
    chunks = []
    current_chunk = ""
    for seg in segments:
        if len(current_chunk) + len(seg) > max_len:
            # 如果当前块非空，则保存
            if current_chunk:
                chunks.append(current_chunk)
            # 开始新块
            current_chunk = seg
            # (如果单个句子就超长，硬切分它)
            while len(current_chunk) > max_len:
                chunks.append(current_chunk[:max_len])
                current_chunk = current_chunk[max_len:]
        else:
            # 累加到当前块
            current_chunk += seg
            
    # 4. 添加最后一块
    if current_chunk:
        chunks.append(current_chunk)

    print(f"[Splitter] 文本被切分为 {len(chunks)} 块。")
    return [c for c in chunks if c.strip()]


def chat_response(data):
    """
    [重构] 运行 china_pipeline.py 和 RVC.py 的完整流程
    (支持长文本切分和拼接)
    """
    print("[backend.chat_engine] 收到对话请求...")
    print(f"[backend.chat_engine] 根目录: {BASE_DIR}")
    print(f"[backend.chat_engine] Python 路径: {PYTHON_EXECUTABLE}")

    if not os.path.exists(INPUT_AUDIO_PATH):
        print(f"[backend.chat_engine] 错误: 未找到输入音频 {INPUT_AUDIO_PATH}")
        raise FileNotFoundError(f"Input audio not found at {INPUT_AUDIO_PATH}")

    # 用于最后拼接的音频块列表
    chunk_audio_files = [] 
    
    try:
        # -----------------------------------------------
        # 步骤 1: 运行 china_pipeline.py (ASR + LLM)
        # -----------------------------------------------
        print(f"[backend.chat_engine] 正在运行 ASR+LLM 脚本 (china_pipeline.py)...")
        
        cmd_pipeline = [
            PYTHON_EXECUTABLE,
            CHINA_PIPELINE_SCRIPT,
            "--input", INPUT_AUDIO_PATH
        ]
        
        result_pipeline = subprocess.run(cmd_pipeline, check=True, cwd=BASE_DIR, capture_output=True, text=True, encoding='gbk')
        
        # --- 【【满足您的 Goal 2: 打印您的语音文字】】 ---
        print("\n" + "="*50)
        print("[backend.chat_engine] china_pipeline.py 完整日志 (您的语音识别结果在下方):")
        print(result_pipeline.stdout)
        print("="*50 + "\n")

        # 检查 AI 回复文本是否已生成
        if not os.path.exists(INTERMEDIATE_TEXT_FILE):
            print(f"[backend.chat_engine] 错误: 脚本未生成 {INTERMEDIATE_TEXT_FILE}")
            raise FileNotFoundError("china_pipeline.py failed to create output text")

        # --- 【【满足您的 Goal 2: 打印AI的应答文字】】 ---
        with open(INTERMEDIATE_TEXT_FILE, 'r', encoding='utf-8') as f:
            ai_long_text = f.read().strip()
        
        print("\n" + "="*50)
        print(f"[backend.chat_engine] AI 的完整回答 (共 {len(ai_long_text)} 字):")
        print(ai_long_text)
        print("="*50 + "\n")

        # -----------------------------------------------
        # 步骤 2: 切分文本, 循环运行 RVC.py
        # -----------------------------------------------
        
        # 【新】切分文本
        text_chunks = simple_splitter(ai_long_text)

        print(f"[backend.chat_engine] 准备循环运行 RVC {len(text_chunks)} 次...")

        for i, chunk in enumerate(text_chunks):
            if not chunk.strip(): # 跳过空块
                continue
                
            print(f"[backend.chat_engine] 正在克隆第 {i+1}/{len(text_chunks)} 块: {chunk[:20]}...")
            
            # a. 将当前块写入临时文本文件
            with open(TEMP_TEXT_FILE, 'w', encoding='utf-8') as f:
                f.write(chunk)
            
            # b. 定义此块的临时音频输出路径
            temp_audio_path = os.path.join(BASE_DIR, "static", "audios", f"chunk_{i}.wav")
            
            # c. 构造 RVC 命令
            cmd_rvc_chunk = [
                PYTHON_EXECUTABLE,
                RVC_SCRIPT,
                "--ref", RVC_REF_AUDIO,
                "--text-file", TEMP_TEXT_FILE,  # 使用临时文本文件
                "--out", temp_audio_path
            ]
            
            # d. 运行 RVC 脚本
            result_rvc_chunk = subprocess.run(cmd_rvc_chunk, check=True, cwd=BASE_DIR, capture_output=True, text=True, encoding='gbk')
            
            # e. 记录这个成功的音频块
            if os.path.exists(temp_audio_path):
                chunk_audio_files.append(temp_audio_path)
            else:
                print(f"[backend.chat_engine] 警告: RVC 未能生成 {temp_audio_path}")
        
        print(f"[backend.chat_engine] 所有 RVC 块已生成 ({len(chunk_audio_files)} 块)。")

        # -----------------------------------------------
        # 步骤 3: 【新】拼接所有音频块
        # -----------------------------------------------
        
        if not chunk_audio_files:
            raise Exception("RVC 未能生成任何音频块。")

        print(f"[backend.chat_engine] 正在拼接 {len(chunk_audio_files)} 个音频块...")
        
        final_audio = AudioSegment.empty()
        for audio_file in chunk_audio_files:
            try:
                chunk_segment = AudioSegment.from_wav(audio_file)
                final_audio += chunk_segment
            except Exception as e:
                print(f"[backend.chat_engine] 警告: 无法加载或拼接 {audio_file}: {e}")

        # 导出最终的完整音频
        final_audio.export(FINAL_AUDIO_PATH_SERVER, format="wav")
        print(f"[backend.chat_engine] 完整音频已保存到: {FINAL_AUDIO_PATH_SERVER}")


        # -----------------------------------------------
        # 步骤 4: 返回最终音频的 Web 路径
        # -----------------------------------------------
        
        return FINAL_AUDIO_PATH_WEB.lstrip('/') # 移除开头的 '/'

    except subprocess.CalledProcessError as e:
        # ... (错误处理 保持不变) ...
        print(f"!!!!!!!!!!!!!! [backend.chat_engine] 脚本执行失败 !!!!!!!!!!!!!!")
        print(f"--- 失败的命令 --- \n{' '.join(e.cmd)}\n")
        print(f"--- 返回码 --- \n{e.returncode}\n")
        print(f"--- STDOUT (标准输出) --- \n{e.stdout}\n")
        print(f"--- STDERR (错误输出) --- \n{e.stderr}\n")
        raise e # 将错误抛出，让 Flask 捕获
    except Exception as e:
        print(f"!!! [backend.chat_engine] 发生未知错误: {e}")
        raise e
    finally:
        # -----------------------------------------------
        # 步骤 5: 【新】清理所有临时文件
        # -----------------------------------------------
        print("[backend.chat_engine] 正在清理临时文件...")
        try:
            if os.path.exists(TEMP_TEXT_FILE):
                os.remove(TEMP_TEXT_FILE)
            for audio_file in chunk_audio_files:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            print("[backend.chat_engine] 清理完成。")
        except Exception as e:
            print(f"[backend.chat_engine] 警告: 清理临时文件失败: {e}")