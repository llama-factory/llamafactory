import requests
import polib
import json
import time
import os
import logging
from logging.handlers import RotatingFileHandler
import sys

from dotenv import load_dotenv
from tqdm import tqdm

# 设置日志
log_file = 'translation.log'
logger = logging.getLogger('translation_logger')
logger.setLevel(logging.INFO)

# 文件处理器
file_handler = RotatingFileHandler(log_file, maxBytes=3*1024*1024, backupCount=5)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# 终端处理器
stream_handler = logging.StreamHandler(sys.stdout)
stream_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(stream_formatter)
logger.addHandler(stream_handler)


load_dotenv(override=True)


def translate_text(text):
    if len(text.strip().split()) < 3:
        return text
    headers = {
        "Authorization": f"Bearer {os.getenv('DIFY_API_KEY')}",
        "Content-Type": "application/json",
    }

    data = {
        "inputs": {"source": text},
        "user": "vllm-doc",
    }

    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = requests.post(
                os.getenv("BASE_URL"), headers=headers, data=json.dumps(data)
            )
            response.raise_for_status()
            return response.json()["data"]["outputs"]["target"]
        except Exception as e:
            logger.error(f"尝试 {attempt + 1} 失败：{e}")
            if attempt < max_retries - 1:
                logger.info("等待 2 秒后重试...")
                time.sleep(2)
            else:
                logger.error("已达到最大重试次数。返回空。")
                return ""

    return ""

def translate_po_file(file_path):
    po = polib.pofile(file_path)

    untranslated_entries = []
    for entry in po:
        if entry.msgstr == "":
            untranslated_entries.append(entry)

    if not untranslated_entries:
        logger.info("没有需要翻译的条目，跳过翻译。")
        return

    batches = []
    current_batch = []
    current_length = 0

    for entry in untranslated_entries:
        if current_length + len(entry.msgid) > 2000:
            batches.append(current_batch)
            current_batch = []
            current_length = 0
        current_batch.append(entry)
        current_length += len(entry.msgid)

    if current_batch:
        batches.append(current_batch)

    for batch in tqdm(batches, desc="翻译批次"):
        batch_text = "===SEPARATOR===".join([entry.msgid for entry in batch])
        translated_batch = translate_text(batch_text)
        if not translated_batch:
            # translated_batch = batch_text
            logger.info(f"翻译失败原文：{batch_text}")
            logger.warning("警告：批次翻译失败，保持原有的空翻译")
            continue

        translated_entries = translated_batch.split("===SEPARATOR===")
        for entry, translated_text in zip(batch, translated_entries):
            entry.msgstr = translated_text.strip()

    current_dir = os.getcwd()
    translated_dir = os.path.join(current_dir, "translated_po")
    os.makedirs(translated_dir, exist_ok=True)

    # file_name = os.path.basename(file_path)
    # new_file_path = os.path.join(translated_dir, file_name)
    # po.save(new_file_path)
    po.save()
    logger.info(f"已保存翻译后的文件到: {file_path}")

def translate_all_po_files(directory):
    for root, dirs, files in tqdm(os.walk(directory), desc="遍历所有po文件"):
        for file in files:
            if file.endswith(".po"):
                file_path = os.path.join(root, file)
                logger.info(f"正在翻译 {file_path}")
                translate_po_file(file_path)

if __name__ == "__main__":
    locale_dir = "sglang/docs/cn/locale/zh_CN/LC_MESSAGES"
    translate_all_po_files(locale_dir)