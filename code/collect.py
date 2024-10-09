import re
import sys
import time
import json
import yaml
import logging
import requests
import schedule
import traceback
from tqdm import tqdm
import concurrent.futures
from html import unescape
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from email.utils import parsedate_to_datetime

import pymysql
from pymysql import Error
import xml.etree.ElementTree as ET


# 自定义异常类
class RSSFetchError(Exception):
    """获取RSS数据时发生的错误"""

    pass


class RSSParseError(Exception):
    """解析RSS数据时发生的错误"""

    pass


class RSSFeedCollector:

    # 在类的开头定义 fields
    FIELDS = [
        "source",
        "title",
        "description",
        "link",
        "guid",
        "pubDate",
        "author",
        "category",
        "content",
        "image_url",
        "language",
        "channel_title",
        "channel_link",
        "channel_atom_link",
        "channel_description",
    ]

    def __init__(self):
        self.logger = logging.getLogger("RSSFeedCollector")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # 使用 RotatingFileHandler 替代 FileHandler
        file_handler = RotatingFileHandler(
            "rss_collector.log", maxBytes=5 * 1024 * 1024, backupCount=3  # 5 MB
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def load_config(self):
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)
        self.SOURCE = {
            url: source_type
            for source_type, urls in config["sources"].items()
            for url in urls
        }
        self.WECHAT_RSS_TEMPLATE = config["rss_templates"]["wechat"]
        self.ZHIHU_RSS_TEMPLATE = config["rss_templates"]["zhihu"]
        self.db_config = config["database"]
        self.table = self.db_config.pop("table")
        self.workflow_config = config["workflow"]

    def get_rss_url(self, url, source_type):
        if source_type == "知乎":
            uid = url.split("/")[-2]
            return self.ZHIHU_RSS_TEMPLATE.format(uid=uid)
        elif source_type == "微信公众号":
            biz = url.split("__biz=")[1].split("&")[0]
            aid = url.split("album_id=")[1]
            return self.WECHAT_RSS_TEMPLATE.format(biz=biz, aid=aid)
        else:
            return url

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
            "channel_atom_link": (
                channel.find("{http://www.w3.org/2005/Atom}link").get("href")
                if channel.find("{http://www.w3.org/2005/Atom}link") is not None
                else None
            ),
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

        # 获取完整的描述作为内容
        content = item.findtext("description") or ""

        # 提取纯文本并限制为前200个字符
        description = self.smart_truncate(
            self.extract_text(content), length=200, max_length=250
        )

        # 检查author和dc:creator
        author = item.findtext("author") or item.findtext(
            "{http://purl.org/dc/elements/1.1/}creator"
        )

        return {
            "title": item.findtext("title"),
            "description": description,
            "link": item.findtext("link"),
            "guid": item.findtext("guid"),
            "pubDate": pubDate,
            "author": author,
            "category": item.findtext("category"),
            "content": content,
            "image_url": (
                item.find("enclosure").get("url")
                if item.find("enclosure") is not None
                else None
            ),
        }

    def smart_truncate(self, text, length=200, max_length=250):
        """
        智能截断文本，尽量保持句子完整性。
        :param text: 要截断的文本
        :param length: 目标长度
        :param max_length: 允许的最大长度
        :return: 截断后的文本
        """
        if len(text) <= length:
            return text

        # 在最大长度处分割文本
        truncated = text[:max_length]

        # 查找最后一个句号、问号或感叹号
        last_sentence = max(
            truncated.rfind("。"),
            truncated.rfind("？"),
            truncated.rfind("！"),
            truncated.rfind("，"),
        )

        if last_sentence > length - 50:
            # 如果在目标长度之后找到了句子结束标记，就在句子结束处截断
            return text[:last_sentence].strip() + "..."

        # 如果没有找到合适的句子结束点，就查找最后一个完整的单词或中文字符
        for i in range(min(len(text), max_length), length - 1, -1):
            if "\u4e00" <= text[i] <= "\u9fff":
                # 如果是汉字，直接在此处截断
                return text[: i + 1].strip() + "..."
            elif text[i].isalpha():
                # 如果是字母，向前滑动直到找到非字母字符
                while i > 0 and text[i - 1].isalpha():
                    i -= 1
                return text[:i].strip() + "..."

        # 如果没有找到合适的截断点，就直接在目标长度处截断
        return text[:length].strip() + "..."

    def extract_text(self, html_content):
        # 移除HTML标签
        text = re.sub(r"<[^>]+>", "", html_content)
        # 解码HTML实体
        text = unescape(text)
        # 移除多余的空白字符
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def parse_analysis_result(self, output):
        # # 新增方法来解析输出
        # parts = output.split("分类结果:")
        # reason = parts[0].strip().lstrip("分类理由:").strip()
        # classification = parts[1].strip()
        # return {"分类理由": reason, "分类结果": classification}
        return json.loads(output)

    def check_blog_relevance(self, blog):
        title = blog.get("title", "")
        description = blog.get("description", "")
        url = self.workflow_config["base_url"]
        headers = {
            "Authorization": f"Bearer {self.workflow_config['api_key']}",
            "Content-Type": "application/json",
        }
        combined_text = f"{title}\n{description}"[:512]
        # combined_text = description[:512]
        data = {
            "inputs": {"blog": combined_text},
            "user": "rss_collector",
        }

        max_retries = 3
        self.logger.info("-" * 30)
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, data=json.dumps(data))
                result = response.json()["data"]

                if result["status"] == "succeeded":
                    analysis_result = result["outputs"]["analysisResult"].strip()
                    is_relevant = int(analysis_result) == 1
                    if not is_relevant:
                        self.logger.info(
                            f"过滤文章 *{blog['title']}*，链接：{blog['link']}。分类结果：{analysis_result}"
                        )
                    return is_relevant, blog
                else:
                    self.logger.warning(
                        f"Workflow 执行未成功: 文章链接 {blog['link']} {result['error']}"
                    )
            except KeyError:
                self.logger.error(
                    f"调用 Dify API 时出错: 文章链接 {blog['link']} {response.text}"
                )
            except Exception:
                self.logger.error(
                    f"调用 Dify API 时未知错误: 文章链接 {blog['link']}, 错误: {traceback.format_exc()}"
                )

            if attempt < max_retries - 1:
                self.logger.info(f"正在进行第 {attempt + 2} 次尝试...")
                time.sleep(2)  # 在重试之前等待2秒
            else:
                self.logger.error(f"在 {max_retries} 次尝试后仍然失败")

        return False, blog

    def filter_relevant_blogs(self, data_list, check_parallel=False):
        results = (
            self.parallel_check(data_list)
            if check_parallel
            else self.naive_check(data_list)
        )

        relevant_blogs = [blog for is_relevant, blog in results if is_relevant]
        filtered_count = len(data_list) - len(relevant_blogs)
        self.logger.info(f"过滤了 {filtered_count} 篇不相关的文章")
        return relevant_blogs

    def naive_check(self, data_list):
        results = [
            self.check_blog_relevance(blog)
            for blog in tqdm(data_list, total=len(data_list), desc="过滤文章")
        ]

        return results

    def parallel_check(self, data_list):
        with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
            results = list(
                tqdm(
                    executor.map(self.check_blog_relevance, data_list),
                    total=len(data_list),
                    desc="过滤文章",
                )
            )
        return results

    def insert_into_database(self, connection, cursor, data_list):
        relevant_blogs = self.filter_relevant_blogs(data_list)

        if not relevant_blogs:
            self.logger.info("没有相关文章需要插入数据库")
            return

        def get_item_values(item):
            return tuple(item.get(field) for field in self.FIELDS)

        update_fields = ", ".join(f"{field} = VALUES({field})" for field in self.FIELDS)
        insert_query = f"""
        INSERT INTO {self.table} ({', '.join(self.FIELDS)})
        VALUES ({', '.join(['%s'] * len(self.FIELDS))})
        ON DUPLICATE KEY UPDATE
        {update_fields}
        """

        batch_size = 100
        success_count = 0
        error_count = 0

        for i in range(0, len(relevant_blogs), batch_size):
            batch = relevant_blogs[i : i + batch_size]
            try:
                cursor.executemany(
                    insert_query, [get_item_values(item) for item in batch]
                )
                connection.commit()
                success_count += len(batch)
            except Error as e:
                connection.rollback()
                error_count += len(batch)
                self.logger.error(f"批量插入错误: {str(e)}")
                # 如果批量插入失败，尝试逐个插入
                for item in batch:
                    try:
                        cursor.execute(insert_query, get_item_values(item))
                        connection.commit()
                        success_count += 1
                        error_count -= 1
                    except Error as e:
                        connection.rollback()
                        self.logger.error(
                            f"单条插入错误: {str(e)}, 数据: {item['title']}"
                        )

        self.logger.info(f"插入完成。成功: {success_count}, 失败: {error_count}")

    def is_blog_exists(self, cursor, link):
        query = f"SELECT COUNT(*) FROM {self.table} WHERE link = %s"
        cursor.execute(query, (link,))
        result = cursor.fetchone()
        return result[0] > 0

    def collect_rss_feeds(self):
        self.load_config()
        self.logger.info("开始收集RSS订阅")
        all_data = []

        connection = None
        try:
            connection = pymysql.connect(**self.db_config)
            with connection.cursor() as cursor:
                # 使用tqdm创建进度条
                with tqdm(total=len(self.SOURCE), desc="收集RSS订阅") as pbar:
                    for url, source_type in self.SOURCE.items():
                        self.process_item(all_data, cursor, url, source_type)
                        # 更新进度条
                        pbar.update(1)

                if all_data:
                    self.insert_into_database(connection, cursor, all_data)

        except Error as e:
            self.logger.error(f"数据库连接错误: {str(e)}")
        finally:
            if connection:
                connection.close()

        self.logger.info("RSS订阅收集完成")

    def process_item(self, all_data, cursor, url, source_type):
        rss_url = self.get_rss_url(url, source_type)
        try:
            root = self.fetch_rss_data(rss_url)
            channel = root.find("channel")
            channel_info = self.parse_channel_info(channel)

            for item in channel.findall("item"):
                rss_item = self.parse_rss_item(item)
                rss_item.update(
                    {
                        "source": source_type,
                        "language": channel_info["language"],
                        "channel_title": channel_info["channel_title"],
                        "channel_link": channel_info["channel_link"],
                        "channel_atom_link": channel_info["channel_atom_link"],
                        "channel_description": channel_info["channel_description"],
                    }
                )
                # 检查文章是否已经存在于数据库中
                if self.is_blog_exists(cursor, rss_item["link"]):
                    self.logger.info(f"文章已存在，跳过: {rss_item['title']}")
                    continue
                all_data.append(rss_item)

        except (RSSFetchError, RSSParseError) as e:
            self.logger.error(f"处理RSS源失败: {rss_url}, 错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"处理RSS源时发生未知错误: {rss_url}, 错误: {str(e)}")

    def run_weekly(self):
        self.logger.info("启动每周定时任务")

        def wake_up_server():
            try:
                response = requests.get("your-rsshub-url")
                if response.status_code == 200:
                    self.logger.info(
                        f"成功唤醒RSS服务器: 状态码 {response.status_code}"
                    )
                    return True
                else:
                    self.logger.warning(
                        f"唤醒RSS服务器未返回200: 状态码 {response.status_code}"
                    )
                    return False
            except Exception as e:
                self.logger.error(f"唤醒RSS服务器失败: {str(e)}")
                return False

        def prepare_and_collect():
            # 尝试唤醒服务器，最多尝试6次（30分钟）
            for _ in range(12):
                if wake_up_server():
                    break
                time.sleep(300)  # 如果失败，等待5分钟后重试

            # 无论是否成功唤醒，都开始收集博客
            self.collect_rss_feeds()

        # 立即执行一次收集操作
        prepare_and_collect()

        schedule.every(3).days.do(prepare_and_collect)

        while True:
            schedule.run_pending()
            time.sleep(1)

    def run_immediately(self):
        self.logger.info("立即执行RSS订阅收集")
        self.collect_rss_feeds()


if __name__ == "__main__":
    collector = RSSFeedCollector()
    # collector.run_immediately()
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        collector.run_immediately()
    else:
        collector.run_weekly()
