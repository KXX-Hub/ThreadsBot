"""
簡單的 Threads 貼文擷取程式
只獲取公開貼文的內容和時間
"""
import requests
from datetime import datetime
import re
import json
import time

class ThreadsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }

    def _clean_text(self, text):
        """清理和處理文本，確保正確處理 Unicode 字符"""
        try:
            # 將Unicode轉義序列解碼
            decoded = text.encode('utf-8').decode('unicode_escape')
            # 移除代理對字符
            cleaned = decoded.encode('utf-16', 'surrogatepass').decode('utf-16')
            return cleaned
        except UnicodeError:
            # 如果出現錯誤，返回原始文本
            return text

    def _extract_json_from_script(self, html_content):
        """提取頁面中的JSON數據"""
        matches = re.findall(r'<script type="application\/json"\s+[^>]*?data-sjs>(.*?)<\/script>', html_content)
        json_data = []

        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and 'require' in data:
                    json_data.append(data)
            except json.JSONDecodeError:
                continue

        return json_data

    def _extract_posts_from_json(self, json_data):
        """從JSON數據中提取貼文"""
        posts = []

        for data in json_data:
            try:
                if 'require' in data:
                    for item in data['require']:
                        if isinstance(item, list) and len(item) > 2:
                            content = str(item[2])
                            # 尋找時間戳和文本內容
                            time_matches = re.findall(r'"taken_at":(\d+)', content)
                            text_matches = re.findall(r'"text":"([^"]*?)"(?=[,}])', content)

                            if time_matches and text_matches:
                                for timestamp, text in zip(time_matches, text_matches):
                                    try:
                                        date = datetime.fromtimestamp(int(timestamp))
                                        cleaned_text = self._clean_text(text)
                                        if cleaned_text:  # 只添加非空的貼文
                                            posts.append({
                                                '時間': date.strftime('%Y-%m-%d %H:%M:%S'),
                                                '內容': cleaned_text
                                            })
                                    except ValueError:
                                        continue
            except Exception as e:
                print(f"解析JSON時發生錯誤: {e}")
                continue

        return posts

    def get_user_posts(self, username):
        """
        獲取用戶的 Threads 貼文
        :param username: 用戶名（不需要 @ 符號）
        :return: 貼文列表或錯誤訊息
        """
        try:
            username = username.lstrip('@')
            url = f'https://www.threads.net/@{username}'

            print(f"正在訪問: {url}")
            response = self.session.get(url, timeout=30)

            print(f"回應狀態碼: {response.status_code}")
            print(f"回應內容長度: {len(response.text)} 字符")

            if response.status_code == 404:
                return "找不到此用戶"
            elif response.status_code != 200:
                return f"請求失敗 (狀態碼: {response.status_code})"

            # 提取並解析JSON數據
            json_data = self._extract_json_from_script(response.text)
            posts = self._extract_posts_from_json(json_data)

            if not posts:
                # 如果沒有找到貼文，嘗試在HTML中直接搜索
                text_matches = re.findall(r'"text":"([^"]*?)"(?=[,}])', response.text)
                time_matches = re.findall(r'"taken_at":(\d+)', response.text)

                if text_matches and time_matches:
                    for timestamp, text in zip(time_matches, text_matches):
                        try:
                            date = datetime.fromtimestamp(int(timestamp))
                            cleaned_text = self._clean_text(text)
                            if cleaned_text:  # 只添加非空的貼文
                                posts.append({
                                    '時間': date.strftime('%Y-%m-%d %H:%M:%S'),
                                    '內容': cleaned_text
                                })
                        except ValueError:
                            continue

            if not posts:
                return "未找到任何貼文或帳號為私人"

            # 按時間排序
            return sorted(posts, key=lambda x: x['時間'], reverse=True)

        except requests.exceptions.RequestException as e:
            return f"網路請求錯誤: {str(e)}"
        except Exception as e:
            return f"發生未預期的錯誤: {str(e)}"

def display_post(post):
    """安全地顯示貼文"""
    try:
        print(f"\n時間: {post['時間']}")
        print(f"內容: {post['內容']}")
        print("-" * 50)
    except UnicodeEncodeError:
        # 如果出現編碼錯誤，嘗試使用替代字符
        print(f"\n時間: {post['時間']}")
        content = post['內容'].encode('ascii', 'replace').decode('ascii')
        print(f"內容: {content}")
        print("-" * 50)

def main():
    scraper = ThreadsScraper()

    while True:
        username = input("\n請輸入要查詢的用戶名（輸入 'exit' 結束）: ")
        if username.lower() == 'exit':
            break

        print(f"\n正在獲取 @{username} 的貼文...")
        results = scraper.get_user_posts(username)

        if isinstance(results, list):
            print(f"\n找到 {len(results)} 則貼文:")
            for post in results:
                display_post(post)
        else:
            print(f"\n{results}")

if __name__ == "__main__":
    main()
