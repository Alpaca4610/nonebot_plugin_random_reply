from pydantic import BaseModel
from typing import Optional, Union, List

class Config(BaseModel):
    oneapi_key: Optional[str] = ""  # API KEY
    oneapi_url: Optional[str] = ""  # API地址
    oneapi_model: Optional[str] = "deepseek-chat" # 使用的语言大模型，建议使用ds-v3模型兼顾质量和成本
    random_re_g: List[str] = [""]  # 启用随机回复的白名单
    
    reply_lens: int = 30 # 参考的聊天记录长度
    reply_pro: float = 0.08   # 随机回复概率
    reply_prompt: str = ""

class ConfigError(Exception):
    pass