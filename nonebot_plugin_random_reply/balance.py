import httpx
from typing import List, Optional

async def get_current_balance(token: str, timeout: int = 30) -> float:
    url = "https://api.siliconflow.cn/v1/user/info"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()

        if not (result.get("status") and result.get("code") == 20000):
            raise RuntimeError(f"API返回异常: {result.get('message', '未知错误')}")
    
        balance_str = result["data"].get("balance")
        if not balance_str:
            raise ValueError("API响应中缺少balance字段")
        return float(balance_str)
    


class BalanceAlert:
    def __init__(self, thresholds: List[float] = [10.0, 5.0, 2.0]):
        # 阈值去重并按从高到低排序，确保阶梯式检查
        self.thresholds = sorted(list(set(thresholds)), reverse=True)
        # 记录已触发的阈值（初始为空集合）
        self._triggered_thresholds = set()

    async def check_and_alert(
        self,
        token: str,
    ) -> List[str]:
        current_balance = await get_current_balance(token)
    
        new_alerts = []
        for threshold in self.thresholds:
            # 仅当：余额低于阈值 且 该阈值未触发过
            if current_balance < threshold and threshold not in self._triggered_thresholds:
                new_alerts.append(f"⚠️ 当前余额{current_balance}元，已跌破{threshold}元阈值")
                self._triggered_thresholds.add(threshold)
        return new_alerts