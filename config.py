from pydantic import BaseModel
from typing import Optional


class Config(BaseModel):
    oneapi_key: Optional[str] = ""  # API KEY
    oneapi_url: Optional[str] = ""  # API地址
    oneapi_model: Optional[str] = "deepseek-reasoner" # 使用的语言大模型，中文建议r1
    reply_lens: int = 30 # 参考的聊天记录长度
    reply_pro: float = 0.1   # 随机回复概率

class ConfigError(Exception):
    pass