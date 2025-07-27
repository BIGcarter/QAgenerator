"""
文档分析节点
"""
import logging
import re
from typing import List, Dict, Any
from schemas import GraphState
from prompts import DocumentAnalysisPrompt
from llm_service import get_llm_service

logger = logging.getLogger(__name__)


class DocumentAnalyzerNode:
    """文档分析节点 - 负责提取关键点和主题"""
    
    def __init__(self):
        self.llm_service = get_llm_service()
        self.analysis_prompt = DocumentAnalysisPrompt.get_prompt()
    
    async def process(self, state: GraphState) -> GraphState:
        """
        分析文档，提取关键点和主题
        
        Args:
            state: 包含处理后文档的状态
            
        Returns:
            包含分析结果的状态
        """
        try:
            logger.info("开始分析文档...")
            
            # 检查输入状态
            if not state.document:
                raise ValueError("状态中缺少文档信息")
            
            if state.current_step == "error":
                return state
            
            document = state.document
            
            # 构建分析Prompt
            prompt = self.analysis_prompt.format(
                title=document.title,
                content=document.content
            )
            
            # 调用LLM进行分析
            logger.info("调用LLM进行文档分析...")
            response = await self.llm_service.invoke_with_fallback(prompt)
            
            # 解析分析结果
            topics, key_points = self._parse_analysis_result(response)
            
            # 更新状态
            state.topics = topics
            state.key_points = key_points
            state.current_step = "document_analyzed"
            
            logger.info(f"文档分析完成，识别主题: {len(topics)}个，关键点: {len(key_points)}个")
            
        except Exception as e:
            error_msg = f"文档分析失败: {str(e)}"
            logger.error(error_msg)
            state.error_message = error_msg
            state.current_step = "error"
        
        return state
    
    def _parse_analysis_result(self, response: str) -> tuple[List[str], List[str]]:
        """
        解析LLM分析结果
        
        Args:
            response: LLM返回的分析结果
            
        Returns:
            (主题列表, 关键点列表)
        """
        topics = []
        key_points = []
        
        try:
            # 按节分割响应
            sections = response.split('##')
            
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                
                # 提取主题
                if section.startswith('主要主题') or 'topic' in section.lower():
                    topics = self._extract_list_items(section)
                
                # 提取关键点
                elif section.startswith('关键知识点') or 'key' in section.lower() or '知识点' in section:
                    key_points = self._extract_list_items(section)
            
            # 如果解析失败，尝试备用解析方法
            if not topics and not key_points:
                topics, key_points = self._fallback_parse(response)
            
            # 验证结果
            if not topics:
                topics = [state.document.title if hasattr(self, 'state') else "文档主题"]
            
            if not key_points:
                # 如果没有提取到关键点，从文档内容中简单提取
                key_points = self._extract_fallback_keypoints(
                    getattr(self, '_current_document_content', '')
                )
            
        except Exception as e:
            # 提供默认值
            topics = ["文档主题"]
            key_points = ["文档内容概述"]
        
        return topics, key_points
    
    def _extract_list_items(self, text: str) -> List[str]:
        """
        从文本中提取列表项
        
        Args:
            text: 包含列表的文本
            
        Returns:
            列表项列表
        """
        items = []
        
        # 匹配不同格式的列表项
        patterns = [
            r'^\s*[-*+]\s*(.+)$',  # - 或 * 或 + 开头
            r'^\s*\d+[.)]\s*(.+)$',  # 数字编号
            r'^(.+)$'  # 简单行项目
        ]
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            for pattern in patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    item = match.group(1).strip()
                    if item and len(item) > 3:  # 过滤过短的项目
                        items.append(item)
                    break
        
        return items[:12]  # 限制数量
    
    def _fallback_parse(self, response: str) -> tuple[List[str], List[str]]:
        """
        备用解析方法
        
        Args:
            response: LLM响应
            
        Returns:
            (主题列表, 关键点列表)
        """
        # 简单的关键词提取
        topics = []
        key_points = []
        
        # 按段落分割
        paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
        
        for paragraph in paragraphs:
            if len(paragraph) > 100:  # 过长的段落可能包含关键信息
                # 提取句子作为关键点
                sentences = [s.strip() for s in paragraph.split('。') if s.strip()]
                key_points.extend(sentences[:3])  # 每段最多3个句子
        
        # 如果仍然没有内容，使用基本的文本分析
        if not key_points:
            key_points = response.split('\n')[:5]  # 前5行
        
        topics = ["提取的主题"] if not topics else topics
        
        return topics, key_points
    
    def _extract_fallback_keypoints(self, content: str) -> List[str]:
        """
        从文档内容中提取备用关键点
        
        Args:
            content: 文档内容
            
        Returns:
            关键点列表
        """
        if not content:
            return ["文档内容分析"]
        
        # 简单的句子分割和筛选
        sentences = []
        
        # 按句子分割
        for sentence in content.split('。'):
            sentence = sentence.strip()
            if len(sentence) > 10 and len(sentence) < 200:  # 合适长度的句子
                sentences.append(sentence)
        
        # 返回前8个句子作为关键点
        return sentences[:8] if sentences else ["文档内容概述"] 