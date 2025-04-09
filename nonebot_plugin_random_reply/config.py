from pydantic import BaseModel
from typing import Optional, Union, List

class Config(BaseModel):
    oneapi_key: Optional[str] = ""  # OneAPI KEY
    oneapi_url: Optional[str] = ""  # API地址
    oneapi_model: Optional[str] = "deepseek-chat" # 使用的语言大模型，建议使用ds-v3模型兼顾质量和成本

    gemini_model: Optional[str] = "gemini-2.0-flash" # Gemini模型
    gemini_key: Optional[str] = ""  # Gemini KEY

    random_re_g: List[str] = [""]  # 启用随机回复的白名单
    
    reply_lens: int = 30 # 参考的聊天记录长度
    reply_pro: float = 0.08   # 随机回复概率
    reply_prompt_url: str = ""
    
    ## 表情包
    random_meme_url: str = "" # 用于llm选择表情包的glm-free-api地址
    random_meme_token : str = "" # glm-free-api的token

class ConfigError(Exception):
    pass