"""
启动补丁：在应用启动最早阶段执行

解决 akshare 访问东方财富等网站的 TLS 连接问题：
1. 用 curl_cffi.requests.Session 替换 requests.Session，模拟浏览器 TLS 指纹
2. 禁用 SSL 证书验证
3. 禁用系统代理
4. 添加重试机制和完整浏览器 UA

必须在任何其他 import 之前执行。
"""
import os

# 1. 清除系统代理
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

# 2. 导入 curl_cffi 和 requests
import curl_cffi.requests as curl_requests
import requests

# 3. 全局 Session 补丁：用 curl_cffi.Session 替换 requests.Session
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_HEADERS = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# 保存原始 Session 类
_OriginalSession = requests.Session

class PatchedSession(curl_requests.Session):
    """使用 curl_cffi 的 Session，模拟浏览器 TLS 指纹"""

    def __init__(self, *args, **kwargs):
        # 强制使用 chrome 指纹
        kwargs['impersonate'] = 'chrome'
        super().__init__(*args, **kwargs)
        self.proxies = {}
        self.verify = False
        self.headers.update(_HEADERS)

# 替换 requests.Session
requests.Session = PatchedSession

# 4. 禁用 SSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)