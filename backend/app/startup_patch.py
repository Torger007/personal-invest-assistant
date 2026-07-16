"""
启动补丁：在应用启动最早阶段执行

解决 akshare 访问东方财富等网站的 TLS 连接问题：
1. 禁用 SSL 证书验证
2. 设置浏览器 UA，避免被识别为爬虫
3. 添加重试机制

必须在任何其他 import 之前执行。
"""
import urllib3
import requests

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 保存原始函数
_original_get = requests.get
_original_session_request = requests.Session.request

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def _patched_get(url, **kwargs):
    """requests.get 补丁：禁用 SSL 验证 + 设置浏览器 UA"""
    kwargs["verify"] = False
    kwargs.setdefault("headers", {})
    kwargs["headers"].setdefault("User-Agent", _UA)
    kwargs["headers"].setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
    kwargs["headers"].setdefault("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
    return _original_get(url, **kwargs)


def _patched_session_request(self, method, url, **kwargs):
    """Session.request 补丁：禁用 SSL 验证 + 设置浏览器 UA"""
    kwargs["verify"] = False
    kwargs.setdefault("headers", {})
    kwargs["headers"].setdefault("User-Agent", _UA)
    kwargs["headers"].setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
    kwargs["headers"].setdefault("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
    return _original_session_request(self, method, url, **kwargs)


# 应用补丁
requests.get = _patched_get
requests.Session.request = _patched_session_request