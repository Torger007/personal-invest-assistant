"""
启动补丁：在应用启动最早阶段执行

解决 akshare 访问东方财富等网站的 TLS 连接问题：
1. 用 curl_cffi.requests.Session 替换 requests.Session，模拟浏览器 TLS 指纹
2. 禁用 SSL 证书验证
3. 禁用系统代理（通过环境变量和 Session 配置）
4. 添加重试机制和完整浏览器 UA

必须在任何其他 import 之前执行。
"""
import os

# 1. 清除系统代理（通过环境变量）
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ[proxy_var] = ''

# 设置 NO_PROXY 阻止 curl_cffi 读取 Windows 系统代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

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
        kwargs['impersonate'] = 'chrome'
        super().__init__(*args, **kwargs)
        self.verify = False
        self.headers.update(_HEADERS)
        self.trust_env = False
        # 底层 curl handle 级别禁用代理
        self.curl.setopt(113, 1)  # CURLOPT_NOPROXY = 1 (禁用代理检测)

    def mount(self, prefix, adapter):
        """禁用 mount，阻止 akshare 的 HTTPAdapter 覆盖 curl_cffi 适配器"""
        pass

    def get(self, url, **kwargs):
        kwargs.pop('proxies', None)
        return super().get(url, **kwargs)

    def request(self, method, url, **kwargs):
        kwargs.pop('proxies', None)
        return super().request(method, url, **kwargs)

# 替换 requests.Session
requests.Session = PatchedSession

# 4. 同时 patch requests.get / requests.request
#    akshare 内部使用 requests.get() 直接调用，不走 Session
#    需要确保这些函数也使用 curl_cffi Session
_original_get = requests.get
_original_request = requests.request

# 创建全局 Session 对象（复用，避免每次创建）
_global_session = PatchedSession()

def _patched_get(url, **kwargs):
    """requests.get 补丁：使用全局 curl_cffi Session，显式禁用代理"""
    kwargs['proxies'] = {}  # 显式禁用代理，避免 curl_cffi 读取系统代理
    return _global_session.get(url, **kwargs)

def _patched_request(method, url, **kwargs):
    """requests.request 补丁：使用全局 curl_cffi Session，显式禁用代理"""
    kwargs['proxies'] = {}  # 显式禁用代理
    return _global_session.request(method, url, **kwargs)

requests.get = _patched_get
requests.request = _patched_request

# 4. 禁用 SSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)