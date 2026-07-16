"""
启动补丁：在应用启动最早阶段执行

解决 akshare 访问东方财富等网站的 TLS 连接问题：
1. 禁用 SSL 证书验证
2. 设置浏览器 UA，避免被识别为爬虫
3. 禁用系统代理（避免代理拦截东方财富子域名）
4. 添加重试机制

必须在任何其他 import 之前执行。
"""
import os
import time
import random
import urllib3
import requests

# 1. 清除系统代理（部分代理会拦截东方财富的 push2 子域名）
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)

# 2. 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 保存原始函数
_original_get = requests.get
_original_session_request = requests.Session.request
_original_session_init = requests.Session.__init__

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


def _patched_session_init(self, *args, **kwargs):
    """Session.__init__ 补丁：强制禁用代理和信任环境"""
    _original_session_init(self, *args, **kwargs)
    self.proxies = {}  # 禁用代理
    self.trust_env = False  # 不从环境变量读取代理


def _patched_get(url, **kwargs):
    """requests.get 补丁：禁用 SSL 验证 + 设置浏览器 UA + 重试"""
    kwargs["verify"] = False
    kwargs.setdefault("headers", {})
    for k, v in _HEADERS.items():
        kwargs["headers"].setdefault(k, v)

    # 添加重试机制
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return _original_get(url, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < max_retries - 1:
                delay = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
            else:
                raise


def _patched_session_request(self, method, url, **kwargs):
    """Session.request 补丁：禁用 SSL 验证 + 设置浏览器 UA + 重试"""
    kwargs["verify"] = False
    kwargs.setdefault("headers", {})
    for k, v in _HEADERS.items():
        kwargs["headers"].setdefault(k, v)

    # 添加重试机制
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return _original_session_request(self, method, url, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < max_retries - 1:
                delay = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
            else:
                raise


# 应用补丁
requests.get = _patched_get
requests.Session.__init__ = _patched_session_init
requests.Session.request = _patched_session_request