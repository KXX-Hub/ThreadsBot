"""
穩定版 Threads 貼文擷取程式
基於先前可運行的版本，並改進文本處理
"""
import requests
from datetime import datetime
import re
import json
import time
from urllib.parse import unquote

class ThreadsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }

    def _clean_text(self, text):
        """清理和處理文本"""
        try:
            # 處理URL和轉義字符
            text = text.replace('\\/', '/')  # 修正URL中的斜線
            text = text.replace('\\n', '\n')  # 換行符
            text = text.replace('\\r', '')    # 回車符
            text = text.replace('\\t', '\t')  # 製表符
            text = text.replace('\\"', '"')   # 引號

            # 嘗試解碼 Unicode
            try:
                text = text.encode().decode('unicode-escape')
            except:
                pass

            # 解碼URL編碼
            text = unquote(text)

            return text.strip()
        except Exception as e:
            print(f"清理文本時出錯: {e}")
            return text.strip()

    def _extract_posts_from_html(self, html_content):
        """從HTML中提取貼文"""
        posts = []
        seen = set()

        try:
            # 找出所有可能的JSON數據
            script_pattern = r'<script[^>]*type="application/json"[^>]*>(.*?)</script>'
            json_matches = re.finditer(script_pattern, html_content, re.DOTALL)

            for match in json_matches:
                try:
                    json_content = match.group(1)

                    # 提取時間和文本
                    text_matches = re.finditer(r'"text":"(.*?)(?<!\\)"', json_content)
                    time_matches = re.finditer(r'"taken_at":(\d+)', json_content)

                    texts = [m.group(1) for m in text_matches]
                    times = [int(m.group(1)) for m in time_matches]

                    # 配對並創建貼文
                    for text, timestamp in zip(texts, times):
                        post_time = datetime.fromtimestamp(timestamp)
                        cleaned_text = self._clean_text(text)

                        # 創建唯一標識
                        post_id = f"{post_time.strftime('%Y-%m-%d %H:%M:%S')}-{cleaned_text}"

                        if post_id not in seen and cleaned_text.strip():
                            seen.add(post_id)
                            posts.append({
                                '時間': post_time.strftime('%Y-%m-%d %H:%M:%S'),
                                '內容': cleaned_text
                            })

                except Exception as e:
                    print(f"處理JSON時出錯: {e}")
                    continue

        except Exception as e:
            print(f"提取貼文時出錯: {e}")

        return posts

    def get_user_posts(self, username, max_posts=None):
        """獲取用戶的 Threads 貼文"""
        try:
            username = username.lstrip('@')
            url = f'https://www.threads.net/@{username}'

            print(f"正在訪問: {url}")
            response = self.session.get(url, timeout=30)

            print(f"回應狀態碼: {response.status_code}")

            if response.status_code == 404:
                return "找不到此用戶"
            elif response.status_code != 200:
                return f"請求失敗 (狀態碼: {response.status_code})"

            # 提取貼文
            posts = self._extract_posts_from_html(response.text)

            if not posts:
                return "未找到任何貼文或帳號為私人"

            # 按時間排序
            posts.sort(key=lambda x: x['時間'], reverse=True)

            # 限制貼文數量
            if max_posts:
                posts = posts[:max_posts]

            return posts

        except requests.exceptions.RequestException as e:
            return f"網路請求錯誤: {str(e)}"
        except Exception as e:
            return f"發生未預期的錯誤: {str(e)}"

def display_post(post):
    """顯示貼文內容"""
    try:
        print(f"\n時間: {post['時間']}")
        print(f"內容: {post['內容']}")
        print("-" * 50)
    except Exception as e:
        print(f"顯示貼文時出錯: {e}")

def main():
    scraper = ThreadsScraper()

    while True:
        try:
            username = input("\n請輸入要查詢的用戶名（輸入 'exit' 結束）: ").strip()
            if not username:
                continue
            if username.lower() == 'exit':
                break

            max_posts = input("要獲取多少則貼文？（按Enter獲取全部）: ").strip()
            max_posts = int(max_posts) if max_posts.isdigit() else None

            print(f"\n正在獲取 @{username} 的貼文...")
            results = scraper.get_user_posts(username, max_posts)

            if isinstance(results, list):
                print(f"\n找到 {len(results)} 則貼文:")
                for post in results:
                    display_post(post)
            else:
                print(f"\n{results}")

        except KeyboardInterrupt:
            print("\n程序已中止")
            break
        except Exception as e:
            print(f"發生錯誤: {e}")
            continue

if __name__ == "__main__":
    main()
