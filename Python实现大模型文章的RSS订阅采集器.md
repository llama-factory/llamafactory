# Python实大模型文章的RSS订阅采集器

在这篇教程中，我们将详细讲解如何使用Python构建一个可靠的RSS订阅采集器。这个工具可以帮助你自动收集和过滤来自知乎、博客等支持RSS的平台的文章。

实际上也是我们[技术博客站点](https://www.llamafactory.cn/llm-technical-articles/)的源码
以下是细节拆解，完整的源码见：https://github.com/llama-factory/llamafactory/blob/main/Python实现大模型文章的RSS订阅采集器.md

## 目录
1. [项目概述](#项目概述)
2. [环境准备](#环境准备)
3. [项目结构](#项目结构)
4. [详细实现](#详细实现)
5. [运行说明](#运行说明)
6. [最佳实践和错误处理](#最佳实践和错误处理)

## 项目概述

我们的RSS订阅采集器主要完成以下任务：
1. 从YAML配置文件读取配置信息
2. 从多个源获取RSS订阅
3. 解析订阅并提取相关信息
4. 基于相关性过滤内容
5. 将收集到的数据存储到MySQL数据库中

## 环境准备

你需要安装以下Python包：
```bash
pip install requests PyYAML pymysql schedule tqdm
```

## 项目结构

项目主要包含两个文件：
1. `collect.py` - 主Python脚本
2. `config.yaml` - 配置文件

### 配置文件示例
```yaml
sources:
  知乎:
    - https://www.zhihu.com/people/username/posts
  科学空间:
    - https://spaces.ac.cn/feed
  博客:
    - https://example.com/feed.xml

rss_templates:
  zhihu: "https://rsshub.example.com/zhihu/posts/people/{uid}"

database:
  host: "localhost"
  user: "username"
  password: "password"
  database: "dbname"
  table: "rss_feed_data"

workflow:
  base_url: "https://api.example.com/v1/workflows/run"
  api_key: "your-api-key"
```

## 详细实现

### 1. 创建基础类结构

```python
class RSSFeedCollector:
    def __init__(self):
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        logger = logging.getLogger("RSSFeedCollector")
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # 使用 RotatingFileHandler 进行日志轮转
        file_handler = RotatingFileHandler(
            "rss_collector.log", maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 同时输出到控制台
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
```

### 2. 加载配置文件

```python
def load_config(self):
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    self.SOURCE = {
        url: source_type
        for source_type, urls in config["sources"].items()
        for url in urls
    }
    self.db_config = config["database"]
    self.table = self.db_config.pop("table")
    self.workflow_config = config["workflow"]
```

### 3. 获取和解析RSS数据

```python
def fetch_rss_data(self, url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return ET.fromstring(response.text)
    except requests.RequestException as e:
        self.logger.error(f"获取RSS数据失败: {url}, 错误: {str(e)}")
        raise RSSFetchError(f"无法获取RSS数据: {url}") from e
    except ET.ParseError as e:
        self.logger.error(f"解析RSS XML失败: {url}, 错误: {str(e)}")
        raise RSSParseError(f"无法解析RSS XML: {url}") from e

def parse_channel_info(self, channel):
    return {
        "channel_title": channel.findtext("title"),
        "channel_link": channel.findtext("link"),
        "channel_description": channel.findtext("description"),
        "language": channel.findtext("language"),
    }

def parse_rss_item(self, item):
    pubDate = item.findtext("pubDate")
    if pubDate:
        try:
            dt = parsedate_to_datetime(pubDate)
            pubDate = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.logger.warning(f"无法解析日期: {pubDate}")
            pubDate = None

    content = item.findtext("description") or ""
    description = self.smart_truncate(
        self.extract_text(content), length=200, max_length=250
    )

    return {
        "title": item.findtext("title"),
        "description": description,
        "link": item.findtext("link"),
        "pubDate": pubDate,
        "content": content,
    }
```

### 4. 内容过滤

```python
def filter_relevant_blogs(self, data_list):
    results = []
    for blog in tqdm(data_list, desc="过滤文章"):
        is_relevant = self.check_blog_relevance(blog)
        if is_relevant:
            results.append(blog)
    
    filtered_count = len(data_list) - len(results)
    self.logger.info(f"过滤了 {filtered_count} 篇不相关的文章")
    return results
```

### 5. 数据库操作

```python
def insert_into_database(self, connection, cursor, data_list):
    if not data_list:
        self.logger.info("没有相关文章需要插入数据库")
        return

    insert_query = f"""
    INSERT INTO {self.table} 
    (title, description, link, pubDate, content)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    title = VALUES(title),
    description = VALUES(description),
    content = VALUES(content)
    """

    batch_size = 100
    success_count = 0
    error_count = 0

    for i in range(0, len(data_list), batch_size):
        batch = data_list[i:i + batch_size]
        try:
            cursor.executemany(insert_query, [
                (item["title"], item["description"], item["link"],
                 item["pubDate"], item["content"])
                for item in batch
            ])
            connection.commit()
            success_count += len(batch)
        except Error as e:
            connection.rollback()
            error_count += len(batch)
            self.logger.error(f"批量插入错误: {str(e)}")

    self.logger.info(f"插入完成。成功: {success_count}, 失败: {error_count}")
```

## 运行说明

你可以通过以下两种方式运行采集器：

1. 立即执行一次采集：
```bash
python collect.py --now
```

2. 启动定时任务（每3天执行一次）：
```bash
python collect.py
```

## 最佳实践和错误处理

1. **使用日志轮转**：通过`RotatingFileHandler`确保日志文件不会无限增长。

2. **批量数据库操作**：使用批量插入提高效率，同时在出错时进行单条重试。

3. **优雅的错误处理**：使用自定义异常类和try/except块处理各种可能的错误：
```python
class RSSFetchError(Exception):
    """获取RSS数据时发生的错误"""
    pass

class RSSParseError(Exception):
    """解析RSS数据时发生的错误"""
    pass
```

4. **进度显示**：使用tqdm库显示处理进度，提供更好的用户体验。

## 进阶优化建议

1. **添加代理支持**：在`fetch_rss_data`中添加代理支持，避免IP被封禁：
```python
def fetch_rss_data(self, url, proxies=None):
    try:
        response = requests.get(url, proxies=proxies)
        response.raise_for_status()
        return ET.fromstring(response.text)
    except requests.RequestException as e:
        self.logger.error(f"获取RSS数据失败: {url}, 错误: {str(e)}")
        raise RSSFetchError(f"无法获取RSS数据: {url}") from e
```

2. **添加重试机制**：对于不稳定的网络环境，添加重试机制：
```python
from retrying import retry

@retry(stop_max_attempt_number=3, wait_fixed=2000)
def fetch_rss_data(self, url):
    # ... 原有的实现 ...
```

3. **异步支持**：使用`aiohttp`和`asyncio`实现异步爬取，提高效率：
```python
async def fetch_rss_data_async(self, url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            text = await response.text()
            return ET.fromstring(text)
```

## 总结

通过这个项目，我们实现了一个功能完整的RSS订阅采集器。它不仅可以自动收集多个来源的RSS内容，还能进行内容过滤和存储。通过使用日志记录、错误处理和批量操作等最佳实践，我们确保了程序的可靠性和效率。

你可以基于这个基础实现，根据自己的需求进行定制和扩展，比如添加更多的数据源、实现更复杂的过滤逻辑，或者集成到其他系统中。

记住，在处理网络请求时要注意添加适当的延迟，遵守网站的robots.txt规则，做一个有道德的爬虫程序。同时，定期备份你的数据库，以防意外情况发生。