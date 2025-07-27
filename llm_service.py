"""
LLM服务模块 - 封装通义千问和OpenAI的调用
"""
import os
import sys
import json
import logging
import warnings
from typing import Optional, Dict, Any, List

try:
    from langchain_core.language_models import BaseLanguageModel
except ImportError:
    try:
        from langchain.base_language import BaseLanguageModel
    except ImportError:
        from langchain.schema.language_model import BaseLanguageModel

from config import get_settings

# 取消warning显示
warnings.filterwarnings("ignore")

# 设置日志级别为ERROR
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


class LLMService:
    """LLM服务类，支持通义千问和OpenAI"""
    
    def __init__(self):
        self.settings = get_settings()
        self._primary_llm = None
        self._backup_llm = None
        self._initialize_llms()
    
    def _initialize_llms(self):
        """初始化LLM实例"""
        # 检查并尝试初始化通义千问
        ali_api_key = self.settings.dashscope_api_key

        if ali_api_key and ali_api_key.strip():
            try:
                self._primary_llm = self._create_dashscope_llm()
                print("✅ 通义千问LLM初始化成功")
                # 不要直接return，需要测试API连接
            except Exception as e:
                print(f"⚠️  通义千问初始化失败: {e}")
        else:
            print("⚠️  未设置ALI_API_KEY环境变量")
        
        # 尝试初始化OpenAI作为备选（只有通义千问没有初始化成功时才尝试）
        if not self._primary_llm:
            openai_api_key = self.settings.openai_api_key  
            if openai_api_key and openai_api_key.strip():
                try:
                    self._backup_llm = self._create_openai_llm()
                    print("✅ OpenAI LLM初始化成功(备选方案)")
                except Exception as e:
                    print(f"⚠️  OpenAI初始化失败: {e}")
            else:
                print("⚠️  未设置OPENAI_API_KEY环境变量")
        
        if not self._primary_llm and not self._backup_llm:
            raise ValueError("❌ 无法初始化任何LLM，请设置ALI_API_KEY或OPENAI_API_KEY环境变量")
        
        # 🔍 重要：总是测试API连接
        self._test_api_connection()
    
    def _test_api_connection(self):
        """测试API连接是否正常"""
        print("🔍 测试API连接...")
        
        test_prompt = "滴滴滴，请问能收到我这边的信息吗？收到的话请回复收到收到。"
        
        # 测试主LLM
        if self._primary_llm:
            try:
                print("   测试通义千问连接...")
                response = self._primary_llm.invoke(test_prompt)
                if response:
                    response_text = response if isinstance(response, str) else response.content
                    print("✅ 通义千问API连接正常")
                    print(f"📤 发送: {test_prompt}")
                    print(f"📥 回复: {response_text}")
                    return  # 主LLM可用，无需测试备选
                else:
                    print("⚠️  通义千问返回空响应")
            except Exception as e:
                print(f"❌ 通义千问API连接失败: {e}")
                self._primary_llm = None  # 标记为不可用
        
        # 如果主LLM失败，测试备选LLM
        if self._backup_llm:
            try:
                print("   测试OpenAI连接...")
                response = self._backup_llm.invoke(test_prompt)
                if response:
                    response_text = response if isinstance(response, str) else response.content
                    print("✅ OpenAI API连接正常(备选方案)")
                    print(f"📤 发送: {test_prompt}")
                    print(f"📥 回复: {response_text}")
                    return
                else:
                    print("⚠️  OpenAI返回空响应")
            except Exception as e:
                print(f"❌ OpenAI API连接失败: {e}")
                self._backup_llm = None  # 标记为不可用
        
        # 如果所有API都失败
        if not self._primary_llm and not self._backup_llm:
            print("\n❌ 所有API连接测试失败！")
            print("📋 可能的原因：")
            print("   1. API密钥无效或过期")
            print("   2. 网络连接问题")
            print("   3. API服务暂时不可用")
            print("\n💡 解决建议：")
            print("   1. 检查API密钥是否正确")
            print("   2. 确认API密钥有足够权限和额度")
            print("   3. 检查网络连接")
            raise ValueError("❌ 所有API连接测试失败，请检查API密钥和网络连接")
    
    def _create_dashscope_llm(self) -> BaseLanguageModel:
        """创建通义千问LLM实例"""
        # 直接使用ChatTongyi，简化实现
        from langchain_community.chat_models.tongyi import ChatTongyi
        
        return ChatTongyi(
            dashscope_api_key=self.settings.dashscope_api_key,
            model_name=self.settings.default_model,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            streaming=False
        )
    

    
    def _create_openai_llm(self) -> BaseLanguageModel:
        """创建OpenAI LLM实例"""
        try:
            # 尝试新版本的导入
            try:
                from langchain_openai import ChatOpenAI
            except ImportError:
                # 备选：旧版本的导入
                try:
                    from langchain.chat_models import ChatOpenAI
                except ImportError:
                    from langchain.llms import OpenAI as ChatOpenAI
            
            return ChatOpenAI(
                openai_api_key=self.settings.openai_api_key,
                openai_api_base=self.settings.openai_base_url,
                model_name=self.settings.backup_model,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens
            )
        except ImportError as e:
            logger.error(f"OpenAI模块导入失败: {e}")
            raise
    
    def get_llm(self, prefer_backup: bool = False) -> BaseLanguageModel:
        """获取LLM实例"""
        if prefer_backup and self._backup_llm:
            return self._backup_llm
        elif self._primary_llm:
            return self._primary_llm
        elif self._backup_llm:
            return self._backup_llm
        else:
            raise ValueError("没有可用的LLM实例")
    
    async def invoke_with_fallback(self, prompt: str, **kwargs) -> str:
        """带降级的LLM调用"""
        last_error = None
        
        # 首先尝试主LLM
        if self._primary_llm:
            try:
                response = self._primary_llm.invoke(prompt)
                return response if isinstance(response, str) else response.content
            except Exception as e:
                last_error = e
                print(f"⚠️  通义千问调用失败: {e}")
        
        # 如果主LLM失败，尝试备选LLM
        if self._backup_llm:
            try:
                response = self._backup_llm.invoke(prompt)
                return response if isinstance(response, str) else response.content
            except Exception as e:
                last_error = e
                print(f"⚠️  OpenAI调用失败: {e}")
        
        error_msg = f"所有LLM都不可用: {last_error}" if last_error else "没有可用的LLM实例"
        raise ValueError(error_msg)
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析LLM返回的JSON响应"""
        try:
            # 提取JSON部分
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()
            
            # 尝试解析JSON
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"原始响应: {response}")
            raise ValueError(f"无法解析LLM返回的JSON: {e}")


# 全局LLM服务实例
_llm_service = None


def get_llm_service() -> LLMService:
    """获取全局LLM服务实例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service 