"""
文档处理节点
"""
import logging
import markdown
from typing import Dict, Any
from schemas import GraphState, DocumentContent

logger = logging.getLogger(__name__)


class DocumentProcessorNode:
    """文档处理节点 - 负责加载和预处理文档"""
    
    def __init__(self):
        self.markdown_processor = markdown.Markdown(
            extensions=['meta', 'toc', 'tables', 'fenced_code']
        )
    
    async def process(self, state: GraphState) -> GraphState:
        """
        处理文档内容
        
        Args:
            state: 包含原始文档信息的状态
            
        Returns:
            处理后的状态，包含结构化的文档内容
        """
        try:
            logger.info("开始处理文档...")
            
            # 检查输入状态
            if not state.document:
                raise ValueError("状态中缺少文档信息")
            
            document = state.document
            
            # 处理Markdown文档
            if document.content.strip():
                processed_content = self._process_markdown_content(document.content)
                
                # 更新文档内容
                processed_document = DocumentContent(
                    title=document.title,
                    content=processed_content,
                    source=document.source,
                    metadata={
                        **document.metadata,
                        "processed": True,
                        "content_length": len(processed_content),
                        "original_length": len(document.content)
                    }
                )
                
                # 更新状态
                state.document = processed_document
                state.current_step = "document_processed"
                
                logger.info(f"文档处理完成，内容长度: {len(processed_content)}")
                
            else:
                raise ValueError("文档内容为空")
                
        except Exception as e:
            error_msg = f"文档处理失败: {str(e)}"
            logger.error(error_msg)
            state.error_message = error_msg
            state.current_step = "error"
        
        return state
    
    def _process_markdown_content(self, content: str) -> str:
        """
        处理Markdown内容
        
        Args:
            content: 原始Markdown内容
            
        Returns:
            处理后的纯文本内容
        """
        try:
            # 转换Markdown为HTML，然后提取纯文本
            html = self.markdown_processor.convert(content)
            
            # 简单的HTML标签清理
            import re
            
            # 移除HTML标签
            clean_text = re.sub(r'<[^>]+>', '', html)
            
            # 清理多余的空白字符
            clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
            clean_text = re.sub(r'[ \t]+', ' ', clean_text)
            
            # 移除过多的空行
            lines = clean_text.split('\n')
            processed_lines = []
            empty_line_count = 0
            
            for line in lines:
                if line.strip():
                    processed_lines.append(line.strip())
                    empty_line_count = 0
                else:
                    empty_line_count += 1
                    if empty_line_count <= 1:  # 最多保留一个空行
                        processed_lines.append('')
            
            return '\n'.join(processed_lines).strip()
            
        except Exception as e:
            return content
    
    def load_from_file(self, file_path: str) -> DocumentContent:
        """
        从文件加载文档
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            文档内容对象
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取文件名作为标题
            import os
            title = os.path.splitext(os.path.basename(file_path))[0]
            
            return DocumentContent(
                title=title,
                content=content,
                source=file_path,
                metadata={
                    "file_path": file_path,
                    "file_size": len(content)
                }
            )
            
        except Exception as e:
            logger.error(f"文件加载失败: {e}")
            raise
    
    def create_from_text(self, title: str, content: str, source: str = None) -> DocumentContent:
        """
        从文本创建文档
        
        Args:
            title: 文档标题
            content: 文档内容
            source: 文档来源
            
        Returns:
            文档内容对象
        """
        return DocumentContent(
            title=title,
            content=content,
            source=source or "直接输入",
            metadata={
                "content_length": len(content),
                "created_from": "text"
            }
        ) 