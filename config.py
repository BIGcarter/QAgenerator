"""
配置管理模块
"""
import os
from typing import Optional

try:
    from pydantic import BaseSettings
except ImportError:
    from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置设置"""
    
    # 通义千问API配置 - 直接从环境变量读取
    dashscope_api_key: Optional[str] = None
    # OpenAI API配置 (备选方案)
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    
    # 应用配置
    debug: bool = True
    log_level: str = "INFO"
    
    # 模型配置
    default_model: str = "qwen-plus"  # 通义千问模型
    backup_model: str = "gpt-3.5-turbo"  # 备选OpenAI模型
    
    # 题目生成配置
    max_questions_per_type: int = 5
    temperature: float = 0.7
    max_tokens: int = 10000
    
    def __init__(self, **kwargs):
        """直接从环境变量读取API密钥确保一致性"""
        super().__init__(**kwargs)
        # 强制从环境变量读取，覆盖任何其他源
        self.dashscope_api_key = os.environ.get("ALI_API_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()

# 强制重新读取环境变量（确保一致性）
settings.dashscope_api_key = os.environ.get("ALI_API_KEY")
settings.openai_api_key = os.environ.get("OPENAI_API_KEY")

# 调试：打印实际读取的API密钥
# print(f"✅ Settings最终的API密钥: {settings.dashscope_api_key}")


def get_settings() -> Settings:
    """获取配置实例"""
    return settings 