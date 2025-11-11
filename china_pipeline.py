import argparse
import os
import time
from zhipuai import ZhipuAI
from pydub import AudioSegment 

# --- 文件名常量 ---
LATEST_RESPONSE_FILE = "latest_ai_response.txt"
LOG_FILE = "conversation_log.txt"

# 1. 设置API Key
api_key = "c4f0ad328f1248b2a0840c78c7b54ab4.6VT7eLDZ9T7ZagY7"

# 2. 初始化 ZhipuAI 客户端
try:
    client = ZhipuAI(api_key=api_key)
except Exception as e:
    print(f"API Key 初始化失败: {e}")
    exit()


# 3. 维护一个对话历史列表
conversation_history = [
    {"role": "system", "content": "你是一个乐于助人的对话助手，请用简洁明了的中文回答。"}
]

def convert_audio_if_needed(audio_file_path):
    """
    检查音频文件格式，如果不是 .mp3 或 .wav, 则转换为 .mp3
    同时，强制将所有音频文件转换为“单声道”
    """
    file_name, file_extension = os.path.splitext(audio_file_path)
    file_extension = file_extension.lower()

    # 定义输出文件名 (统一转为 .mp3)
    output_path = file_name + "_mono.mp3" # 改个名字避免覆盖
    
    # 检查输入文件是否存在
    if not os.path.exists(audio_file_path):
        print(f"[Converter] 错误：输入文件 {audio_file_path} 未找到。")
        return None

    print(f"[Converter] 正在处理: {audio_file_path}")
    
    try:
        # 1. 加载音频文件 (自动检测格式)
        audio = AudioSegment.from_file(audio_file_path)
        
        # 2. 【关键修复】 强制设置为单声道
        print("[Converter] 强制转换为单声道 (Mono)...")
        audio = audio.set_channels(1)
            
        # 3. 导出为 .mp3
        audio.export(output_path, format="mp3")
            
        print(f"[Converter] 单声道 .mp3 转换完成: {output_path}")
        return output_path
        
    except FileNotFoundError:
        print("\n" + "="*50)
        print("错误： 'ffmpeg' 未找到。")
        print("pydub 需要 ffmpeg 来转换 .m4a 文件。")
        print("请先安装 ffmpeg (例如: 'brew install ffmpeg' 或 'sudo apt install ffmpeg')")
        print("="*50 + "\n")
        return None
    except Exception as e:
        print(f"[Converter] 转换失败: {e}")
        return None


def transcribe_audio_zhipu(audio_file_path):
    """
    步骤 A: 语音转文字 (ASR) - 使用 智谱AI GLM ASR
    """
    if not audio_file_path: # 检查转换是否成功
        return None

    print(f"[ASR] 正在识别 (Zhipu): {audio_file_path}...")
    try:
        with open(audio_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="glm-asr",
                file=audio_file,
            )
        print(f"[ASR] 识别结果: {response.text}")
        return response.text
    except Exception as e:
        print(f"[ASR] 识别失败: {e}")
        return None

# --- 【【【 新增功能 】】】 ---
def save_response_to_file(user_text, assistant_reply):
    """
    将AI的回答保存到本地文件
    """
    print("[Save] 正在保存AI回答...")
    
    # 1. 保存最新的回答 (用于TTS) - 覆盖模式 (w)
    try:
        with open(LATEST_RESPONSE_FILE, 'w', encoding='utf-8') as f:
            f.write(assistant_reply)
        print(f"[Save] 最新回答已保存到: {LATEST_RESPONSE_FILE}")
    except Exception as e:
        print(f"[Save] 保存最新回答失败: {e}")

    # 2. 保存完整对话日志 - 追加模式 (a)
    try:
        # 确保 user_text 不是 None
        user_text_to_save = user_text if user_text else "N/A (ASR失败)"
        
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"【{time.ctime()}】\n")
            f.write(f"你: {user_text_to_save}\n")
            f.write(f"AI: {assistant_reply}\n\n")
        print(f"[Save] 对话日志已追加到: {LOG_FILE}")
    except Exception as e:
        print(f"[Save] 追加日志失败: {e}")
# --- 【【【 新增功能结束 】】】 ---


def get_llm_response_zhipu(user_text):
    """
    步骤 B: 获取大语言模型应答 (LLM) - 使用 智谱AI 同步接口
    """
    # 即使ASR失败(user_text is None)，我们仍然要让AI生成“我没听清”
    if not user_text:
        assistant_reply = "我没有听清，你能再说一遍吗？"
        print(f"[LLM] AI 回答: {assistant_reply}")
        # 即使是错误情况，也保存一下
        save_response_to_file(user_text, assistant_reply)
        return assistant_reply
        
    print(f"[LLM] 正在思考 (Zhipu)...")
    try:
        conversation_history.append({"role": "user", "content": user_text})
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=conversation_history,
        )
        assistant_reply = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": assistant_reply})
        print(f"[LLM] AI 回答: {assistant_reply}")

        # --- 【【【 新增调用 】】】 ---
        # 在获取到回答后，立即保存
        save_response_to_file(user_text, assistant_reply)
        
        return assistant_reply
        
    except Exception as e:
        print(f"[LLM] 思考失败: {e}")
        return "抱歉，我好像出错了。"

# --- 主流程 ---
if __name__ == "__main__":
    
    # 【【【!!! 关键修改 !!!】】】
    # 1. 添加命令行参数解析
    parser = argparse.ArgumentParser(description="ASR + LLM 管道")
    parser.add_argument("--input", "-i", required=True, help="输入的音频文件路径 (e.g., test2.m4a)")
    args = parser.parse_args()

    print("--- 启动对话机器人 (智谱AI + 自动格式转换 + 单声道 + 保存) ---")

    # 2. 从参数获取文件名
    my_audio_file = args.input 

    if not os.path.exists(my_audio_file):
        print(f"错误：文件 '{my_audio_file}' 未找到。")
    else:
        # 3. 转换文件为单声道 .mp3
        path_to_upload = convert_audio_if_needed(my_audio_file)
        
        # 4. 执行管线
        start_time = time.time()
        user_input_text = transcribe_audio_zhipu(path_to_upload)
        asr_time = time.time()
        ai_response_text = get_llm_response_zhipu(user_input_text)
        llm_time = time.time()
        
        # （你上一个脚本中的 generate_audio_zhipu (TTS) 已被RVC.py替代，所以这里不需要调用）

        # 5. 打印结果
        print("\n--- 任务完成 ---")
        print(f"你 (语音): {user_input_text}")
        print(f"AI (文字): {ai_response_text}")
        print("-----------------")
        print(f"ASR 耗时: {asr_time - start_time:.2f} 秒")
        print(f"LLM 耗时: {llm_time - asr_time:.2f} 秒")
        print(f"总计耗时: {llm_time - start_time:.2f} 秒")