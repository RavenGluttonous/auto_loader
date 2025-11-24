import datetime
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

from utils import http_request, logger


@dataclass
class XcopeToken:
    access_token: str
    expires_at: datetime.datetime

    @property
    def is_expired(self) -> bool:
        # 提前 60 秒刷新
        return datetime.datetime.utcnow() >= (self.expires_at - datetime.timedelta(seconds=60))


class XcopeClient:
    """Xcope REST API 客户端

    负责：
    - 获取并缓存 access_token
    - 调用获取报告列表接口
    - 下载报告 PDF
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        scope: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self._token_lock = threading.Lock()
        self._token: Optional[XcopeToken] = None

    # ----------------- token -----------------
    def _fetch_token(self) -> Optional[XcopeToken]:
        url = f"{self.base_url}/connect/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
            "grant_type": "client_credentials",
        }
        try:
            resp = http_request.get_response(
                "POST", url, 1, 3, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
        except requests.RequestException as e:
            logger.error(f"获取 Xcope access_token 请求异常: {e}")
            return None

        if resp is None:
            logger.error("获取 Xcope access_token 失败，响应为空")
            return None

        try:
            payload = resp.json()
        except Exception as e:
            logger.error(f"解析 Xcope token 响应失败: {e}, 原始内容: {resp.text[:500]}")
            return None

        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not access_token or not isinstance(expires_in, (int, float)):
            logger.error(f"Xcope token 响应缺少必要字段: {payload}")
            return None

        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=int(expires_in))
        token = XcopeToken(access_token=access_token, expires_at=expires_at)
        logger.info("成功获取 Xcope access_token")
        return token

    def get_access_token(self) -> Optional[str]:
        with self._token_lock:
            if self._token is None or self._token.is_expired:
                self._token = self._fetch_token()
            return self._token.access_token if self._token else None

    # ----------------- 报告列表 -----------------
    def get_today_report_list(self, max_result_count: int = 99999) -> List[Dict]:
        token = self.get_access_token()
        if not token:
            return []

        now = datetime.datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=0, microsecond=0)
        start_str = start.strftime("%Y-%m-%dT%H:%M")
        end_str = end.strftime("%Y-%m-%dT%H:%M")

        url = f"{self.base_url}/api/app/report-entries/entry-fields"
        params = {
            "startDate": start_str,
            "EndDate": end_str,
            "MaxResultCount": max_result_count,
        }
        headers = {"Authorization": f"Bearer {token}"}

        try:
            resp = http_request.get_response("GET", url, 1, 3, params=params, headers=headers)
        except requests.RequestException as e:
            logger.error(f"获取 Xcope 报告列表请求异常: {e}")
            return []

        if resp is None:
            logger.error("获取 Xcope 报告列表失败，响应为空")
            return []

        try:
            data = resp.json()
        except Exception as e:
            logger.error(f"解析 Xcope 报告列表响应失败: {e}, 原始内容: {resp.text[:500]}")
            return []

        items = data.get("items") or []
        if not isinstance(items, list):
            logger.error(f"Xcope 报告列表 items 字段格式异常: {type(items)}")
            return []
        return items

    # ----------------- 报告 PDF -----------------
    def download_report_pdf(self, report_id: str) -> Optional[bytes]:
        token = self.get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/api/app/reports/pdf"
        params = {"key": report_id}
        headers = {"Authorization": f"Bearer {token}"}

        try:
            resp = http_request.get_response("GET", url, 1, 3, params=params, headers=headers)
        except requests.RequestException as e:
            logger.error(f"下载 Xcope 报告 PDF 请求异常: {e}")
            return None

        if resp is None:
            logger.error(f"下载 Xcope 报告 PDF 失败，响应为空，report_id={report_id}")
            return None

        # 直接返回二进制内容
        return resp.content

