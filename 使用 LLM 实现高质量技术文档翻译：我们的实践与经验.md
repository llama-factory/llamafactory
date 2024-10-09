## 引言

在开源技术社区中，大量优秀的文档仍然只有英文版本，这对中文用户造成了一定的使用障碍。为了让更多中文开发者能够方便地使用这些技术，我们开发了一套基于大语言模型的文档翻译流程，并已经成功翻译了vllm、sglang等中文文档。本文将详细介绍我们的翻译方法、技术实现以及已完成的翻译项目。

## 技术实现

### 1. 环境准备

首先，确保你的系统中已经安装了必要的工具：

```bash
# 安装 Sphinx 和翻译工具
pip install sphinx sphinx-intl polib tqdm requests

# 安装项目依赖（如果有的话）
pip install -r requirements.txt
```

### 2. 配置 Sphinx 项目

修改 `conf.py` 文件，添加国际化支持：

```python
# conf.py

# 支持的语言列表
language = 'zh_CN'

# 翻译文件路径配置
locale_dirs = ['locale/']   
gettext_compact = False     

# 确保使用 alabaster 主题，它对中文支持较好
html_theme = 'alabaster'
```

### 3. 生成待翻译文件

使用以下命令生成 .pot 文件和对应的 .po 文件：

```bash
# 生成 .pot 文件
make gettext

# 为中文创建 .po 文件
sphinx-intl update -p _build/gettext -l zh_CN
```

这将在 `locale/zh_CN/LC_MESSAGES/` 目录下生成 .po 文件。

### 4. 核心翻译流程

依次对 .po 文件进行翻译，我们的翻译系统主要基于以下几个关键组件：

1. **文档解析**：使用 Sphinx 和 polib 处理 .po 文件
2. **翻译引擎**：采用 Gemini-1.5-flash 模型通过 Dify API 进行翻译
3. **批处理机制**：实现了智能的文本分批处理，确保翻译质量的同时提高效率

关键代码实现：

```python
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
    
    # 实现了重试机制，确保翻译的可靠性
    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = requests.post(
                os.getenv("BASE_URL"), 
                headers=headers, 
                data=json.dumps(data)
            )
            response.raise_for_status()
            return response.json()["data"]["outputs"]["target"]
        except Exception as e:
            logger.error(f"尝试 {attempt + 1} 失败：{e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return ""
    
    return ""
```

### 5. 翻译提示词优化

为了确保翻译质量，我们精心设计了翻译提示词，主要特点包括：

1. 明确角色定位：将模型定位为技术文档翻译专家
2. 详细的翻译要求：包括术语准确性、格式保持等
3. 特殊处理说明：如统一将"you"翻译为"你"，保持表格格式等
4. 使用指定分隔符实现高效批处理

```
Role：技术文档翻译专家

Background：你是一位资深的技术文档翻译专家，专注于网页文本和 AI 领域的英译汉翻译。

Skills & Goals：
- 准确理解并翻译技术术语和专业名词
- 提供准确、流畅的翻译，保持原文的专业性和清晰度
- 确保翻译符合技术文档的专业标准和行业规范
- 保持翻译的忠实性、准确性和连贯性

Workflow：
1. 接收多条由===SEPARATOR===分隔的英文内容
2. 逐条翻译，确保准确性
3. 审核校对每条翻译，确保流畅性和连贯性
4. 使用===SEPARATOR===分隔每条翻译结果
5. 输出最终翻译，符合要求

注意事项：
- 将"you"统一翻译为"你"
- 保持表格或行列格式与原文一致
- 只输出译文，不输出额外说明
- 不破坏原文的格式，保证网页链接不丢失
- 保持原文的分隔符===SEPARATOR===，用于区分不同条目

任务：将以下多条英文内容翻译成中文，每条内容之间用===SEPARATOR===分隔。确保翻译符合大部分中文读者的阅读习惯和理解能力。翻译完成后，使用相同的分隔符===SEPARATOR===分隔每条翻译结果。

请按照以上指示翻译以下英文文本：
{source_content}
```

### 6. 批处理机制

为了提高翻译效率，我们实现了批处理机制：

1. 将文本按照 2000 字符的长度分批
2. 使用特殊分隔符 `===SEPARATOR===` 连接多条文本
3. 批量发送翻译请求，提高处理效率

```python
def translate_po_file(file_path):
    po = polib.pofile(file_path)
    
    # 收集未翻译条目
    untranslated_entries = []
    for entry in po:
        if entry.msgstr == "":
            untranslated_entries.append(entry)
    
    # 智能分批处理
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
    po.save()
```

### 7. 构建中文文档

翻译完成后，构建中文文档：

```bash
sphinx-build -b html -D language=zh_CN . _build/html/zh_CN
```

## 已完成的翻译项目

我们的 [LlamaFactory](https://www.llamafactory.cn/#features) 站点已经成功完成了多个重要项目的文档翻译：

 1. [vLLM 中文文档](https://vllm-zh.llamafactory.cn)
 2. [SGLang 中文文档](https://sglang-zh.llamafactory.cn)


## 未来展望

我们计划在未来进一步改进翻译系统：

1. 扩展更多项目的文档翻译
2. 优化翻译模型，提高专业术语的翻译准确度
3. 支持更多类型的文档翻译，不仅仅是sphinx
4. 建立更完善的翻译质量评估体系，尽可能进行人工审核

## 结论

通过结合 Sphinx、Gemini-1.5-flash 模型和精心设计的翻译流程，我们实现了高质量的技术文档翻译。这不仅使得优秀的技术文档能够服务于更广泛的中文开发者社区，也为未来的文档本地化工作提供了有价值的经验和参考。

我们期待看到更多的开发者能够因为这些中文文档而受益，同时也欢迎社区成员参与到文档翻译的改进工作中来。