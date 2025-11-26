import os
import sys
import subprocess
from datetime import datetime
import re
from pydub import AudioSegment
import shutil  # 用于清理文件夹

# --- 关键路径配置 ---

# 1. Python 解释器 (使用您当前激活的 conda 环境)
PYTHON_EXECUTABLE = sys.executable 

# 2. 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 3. RVC 脚本路径
RVC_SCRIPT = os.path.join(BASE_DIR, "RVC.py")

# --- 可配置的测试参数 ---

# 4. (输入) 参考音色
REFERENCE_AUDIO = os.path.join(BASE_DIR, "input", "audio", "nahida.wav")
# (您也可以改成 "zhb.wav")
# REFERENCE_AUDIO = os.path.join(BASE_DIR, "input", "audio", "zhb.wav")

# 5. (输入) 包含长文本的 TXT 文件
INPUT_LONG_TEXT_FILE = os.path.join(BASE_DIR, "input", "text", "test.txt")
# (确保这个文件里有您想测试的长文本)

# 6. (输出) 最终拼接好的音频
FINAL_OUTPUT_AUDIO = os.path.join(BASE_DIR, "output", f"offline_test_output_{datetime.now().strftime('%H%M%S')}.wav")

# 7. (临时) RVC 循环时使用的临时文件
TEMP_TEXT_FILE = os.path.join(BASE_DIR, "temp_offline_test.txt") 
TEMP_CHUNK_DIR = os.path.join(BASE_DIR, "output", "temp_chunks_offline") 


# --- 从 chat_engine.py 复制的核心功能 ---

def simple_splitter(text, max_len=45):
    """
    一个简单的文本切分器
    (从 backend/chat_engine.py 复制而来)
    """
    print(f"[Splitter] 正在切分总长 {len(text)} 的文本...")
    segments = re.findall(r"([^。！？，、,!?]+[。！？，、,!?]?)", text, re.UNICODE)
    
    if not segments:
        print("[Splitter] 未找到标点，将按最大长度硬切分。")
        return [text[i:i+max_len] for i in range(0, len(text), max_len)]

    chunks = []
    current_chunk = ""
    for seg in segments:
        if len(current_chunk) + len(seg) > max_len:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = seg
            while len(current_chunk) > max_len:
                chunks.append(current_chunk[:max_len])
                current_chunk = current_chunk[max_len:]
        else:
            current_chunk += seg
            
    if current_chunk:
        chunks.append(current_chunk)

    print(f"[Splitter] 文本被切分为 {len(chunks)} 块。")
    return [c for c in chunks if c.strip()]


# --- 主执行函数 ---
def run_offline_test():
    """
    执行 RVC 长文本的“切分-克隆-拼接”测试
    """
    print("="*60)
    print("--- 启动 RVC 离线长文本测试 ---")
    print(f"  参考音色: {REFERENCE_AUDIO}")
    print(f"  输入文本: {INPUT_LONG_TEXT_FILE}")
    print(f"  Python: {PYTHON_EXECUTABLE}")
    print("="*60)

    # 确保临时文件夹存在
    os.makedirs(TEMP_CHUNK_DIR, exist_ok=True)
    
    # 存储所有生成的音频块
    chunk_audio_files = [] 
    
    try:
        # -----------------------------------------------
        # 步骤 1: 读取并切分长文本
        # -----------------------------------------------
        if not os.path.exists(INPUT_LONG_TEXT_FILE):
            print(f"错误: 输入文本文件未找到: {INPUT_LONG_TEXT_FILE}")
            return
            
        with open(INPUT_LONG_TEXT_FILE, 'r', encoding='utf-8') as f:
            ai_long_text = f.read().strip()

        text_chunks = simple_splitter(ai_long_text)

        # -----------------------------------------------
        # 步骤 2: 循环运行 RVC.py
        # -----------------------------------------------
        print(f"[RVC Test] 准备循环运行 RVC {len(text_chunks)} 次...")

        for i, chunk in enumerate(text_chunks):
            if not chunk.strip():
                continue
                
            print(f"[RVC Test] 正在克隆第 {i+1}/{len(text_chunks)} 块: {chunk[:20]}...")
            
            with open(TEMP_TEXT_FILE, 'w', encoding='utf-8') as f:
                f.write(chunk)
            
            temp_audio_path = os.path.join(TEMP_CHUNK_DIR, f"chunk_{i}.wav")
            
            cmd_rvc_chunk = [
                PYTHON_EXECUTABLE,
                RVC_SCRIPT,
                "--ref", REFERENCE_AUDIO,
                "--text-file", TEMP_TEXT_FILE,
                "--out", temp_audio_path
            ]
            
            # (使用 'gbk' 编码来捕获 Windows 上的中文日志)
            result = subprocess.run(cmd_rvc_chunk, check=True, cwd=BASE_DIR, capture_output=True, text=True, encoding='gbk')
            # print(result.stdout) # (如果需要，取消注释以查看 RVC 的详细日志)
            
            if os.path.exists(temp_audio_path):
                chunk_audio_files.append(temp_audio_path)
            else:
                print(f"警告: RVC 未能生成 {temp_audio_path}")
        
        print(f"[RVC Test] 所有 RVC 块已生成。")

        # -----------------------------------------------
        # 步骤 3: 拼接所有音频块
        # -----------------------------------------------
        
        if not chunk_audio_files:
            raise Exception("RVC 未能生成任何音频块。")

        print(f"[RVC Test] 正在拼接 {len(chunk_audio_files)} 个音频块...")
        
        final_audio = AudioSegment.empty()
        for audio_file in chunk_audio_files:
            try:
                chunk_segment = AudioSegment.from_wav(audio_file)
                final_audio += chunk_segment
            except Exception as e:
                print(f"警告: 无法加载或拼接 {audio_file}: {e}")

        # 导出最终的完整音频
        final_audio.export(FINAL_OUTPUT_AUDIO, format="wav")
        print("="*60)
        print(f"🎉 测试成功! 完整音频已保存到:")
        print(f"   {FINAL_OUTPUT_AUDIO}")
        print("="*60)


    except subprocess.CalledProcessError as e:
        print(f"!!!!!!!!!!!!!! [RVC Test] 脚本执行失败 !!!!!!!!!!!!!!")
        print(f"--- 失败的命令 --- \n{' '.join(e.cmd)}\n")
        print(f"--- STDOUT (标准输出) --- \n{e.stdout}\n")
        print(f"--- STDERR (错误输出) --- \n{e.stderr}\n")
    except Exception as e:
        print(f"!!! [RVC Test] 发生未知错误: {e}")
    finally:
        # -----------------------------------------------
        # 步骤 4: 清理所有临时文件
        # -----------------------------------------------
        print("[RVC Test] 正在清理临时文件...")
        try:
            if os.path.exists(TEMP_TEXT_FILE):
                os.remove(TEMP_TEXT_FILE)
            if os.path.exists(TEMP_CHUNK_DIR):
                # 删除整个临时文件夹及其内容
                shutil.rmtree(TEMP_CHUNK_DIR)
            print("[RVC Test] 清理完成。")
        except Exception as e:
            print(f"警告: 清理临时文件失败: {e}")


# --- 运行测试 ---
if __name__ == "__main__":
    run_offline_test()