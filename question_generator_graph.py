"""
题目生成LangGraph工作流
"""
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from schemas import GraphState
from nodes import (
    DocumentProcessorNode,
    DocumentAnalyzerNode,
    MultipleChoiceGeneratorNode,
    FillInTheBlankGeneratorNode,
    MatchingGeneratorNode,
    OutputFormatterNode
)

logger = logging.getLogger(__name__)


class QuestionGeneratorGraph:
    """题目生成工作流图"""
    
    def __init__(self):
        self.graph = None
        self._initialize_nodes()
        self._build_graph()
    
    def _initialize_nodes(self):
        """初始化所有节点"""
        self.document_processor = DocumentProcessorNode()
        self.document_analyzer = DocumentAnalyzerNode()
        self.mc_generator = MultipleChoiceGeneratorNode()
        self.fib_generator = FillInTheBlankGeneratorNode()
        self.matching_generator = MatchingGeneratorNode()
        self.output_formatter = OutputFormatterNode()
    
    def _build_graph(self):
        """构建LangGraph工作流"""
        
        # 创建状态图
        workflow = StateGraph(GraphState)
        
        # 添加节点
        workflow.add_node("document_processor", self._process_document)
        workflow.add_node("document_analyzer", self._analyze_document)
        workflow.add_node("generate_multiple_choice", self._generate_multiple_choice)
        workflow.add_node("generate_fill_blank", self._generate_fill_blank)
        workflow.add_node("generate_matching", self._generate_matching)
        workflow.add_node("format_output", self._format_output)
        workflow.add_node("error_handler", self._handle_error)
        
        # 设置入口点
        workflow.set_entry_point("document_processor")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "document_processor",
            self._route_after_processing,
            {
                "analyze": "document_analyzer",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "document_analyzer", 
            self._route_after_analysis,
            {
                "generate_questions": "generate_multiple_choice",
                "error": "error_handler"
            }
        )
        
        # 题目生成节点之间的顺序连接
        workflow.add_edge("generate_multiple_choice", "generate_fill_blank")
        workflow.add_edge("generate_fill_blank", "generate_matching")
        workflow.add_edge("generate_matching", "format_output")
        
        # 输出节点到结束
        workflow.add_conditional_edges(
            "format_output",
            self._route_after_formatting,
            {
                "end": END,
                "error": "error_handler"
            }
        )
        
        # 错误处理节点到结束
        workflow.add_edge("error_handler", END)
        
        # 编译图
        self.graph = workflow.compile()
    
    # 节点处理函数
    async def _process_document(self, state: GraphState) -> GraphState:
        """文档处理节点"""
        logger.info("执行文档处理节点...")
        return await self.document_processor.process(state)
    
    async def _analyze_document(self, state: GraphState) -> GraphState:
        """文档分析节点"""
        logger.info("执行文档分析节点...")
        return await self.document_analyzer.process(state)
    
    async def _generate_multiple_choice(self, state: GraphState) -> GraphState:
        """选择题生成节点"""
        logger.info("执行选择题生成节点...")
        return await self.mc_generator.process(state)
    
    async def _generate_fill_blank(self, state: GraphState) -> GraphState:
        """填空题生成节点"""
        logger.info("执行填空题生成节点...")
        return await self.fib_generator.process(state)
    
    async def _generate_matching(self, state: GraphState) -> GraphState:
        """连线题生成节点"""
        logger.info("执行连线题生成节点...")
        return await self.matching_generator.process(state)
    
    async def _format_output(self, state: GraphState) -> GraphState:
        """输出格式化节点"""
        logger.info("执行输出格式化节点...")
        return await self.output_formatter.process(state)
    
    async def _handle_error(self, state: GraphState) -> GraphState:
        """错误处理节点"""
        logger.error(f"工作流出现错误: {state.error_message}")
        state.current_step = "error_handled"
        return state
    
    # 路由条件函数
    def _route_after_processing(self, state: GraphState) -> str:
        """文档处理后的路由"""
        if state.current_step == "error":
            return "error"
        elif state.current_step == "document_processed":
            return "analyze"
        else:
            return "error"
    
    def _route_after_analysis(self, state: GraphState) -> str:
        """文档分析后的路由"""
        if state.current_step == "error":
            return "error"
        elif state.current_step == "document_analyzed":
            return "generate_questions"
        else:
            return "error"
    
    def _route_after_formatting(self, state: GraphState) -> str:
        """输出格式化后的路由"""
        if state.current_step == "error":
            return "error"
        elif state.current_step == "completed":
            return "end"
        else:
            return "error"
    
    async def run(self, initial_state: GraphState) -> GraphState:
        """
        运行题目生成工作流
        
        Args:
            initial_state: 初始状态，包含文档信息
            
        Returns:
            最终状态，包含生成的题目
        """
        try:
            logger.info("开始运行题目生成工作流...")
            
            # 运行图 - 兼容不同版本的API
            try:
                # 新版本API
                result = await self.graph.ainvoke(initial_state)
                # 确保返回的是GraphState对象
                if isinstance(result, dict):
                    final_state = GraphState(**result)
                else:
                    final_state = result
            except AttributeError:
                # 如果没有ainvoke方法，尝试其他方式
                try:
                    # 一些版本使用invoke
                    result = self.graph.invoke(initial_state)
                    if isinstance(result, dict):
                        final_state = GraphState(**result)
                    else:
                        final_state = result
                except AttributeError:
                    # 使用流式处理
                    final_state = initial_state
                    async for state in self.graph.astream(initial_state):
                        if isinstance(state, dict):
                            final_state = GraphState(**state)
                        else:
                            final_state = state
            
            if final_state.current_step == "completed":
                pass  # 成功完成，静默处理
            elif final_state.current_step in ["error", "error_handled"]:
                logger.error(f"题目生成工作流失败: {final_state.error_message}")
            else:
                pass  # 未知状态，静默处理
            
            return final_state
            
        except Exception as e:
            logger.error(f"工作流运行异常: {e}")
            initial_state.error_message = str(e)
            initial_state.current_step = "error"
            return initial_state
    
    def get_graph_visualization(self) -> str:
        """
        获取图的可视化表示
        
        Returns:
            图的Mermaid格式字符串
        """
        mermaid_graph = """
graph TD
    A[Document Processor] --> B{Processing OK?}
    B -->|Yes| C[Document Analyzer]
    B -->|No| H[Error Handler]
    
    C --> D{Analysis OK?}
    D -->|Yes| E[Generate Multiple Choice]
    D -->|No| H
    
    E --> F[Generate Fill-in-the-Blank]
    F --> G[Generate Matching]
    G --> I[Format Output]
    
    I --> J{Formatting OK?}
    J -->|Yes| K[End]
    J -->|No| H
    
    H --> K
    
    style A fill:#e1f5fe
    style C fill:#f3e5f5
    style E fill:#fff3e0
    style F fill:#fff3e0
    style G fill:#fff3e0
    style I fill:#e8f5e8
    style H fill:#ffebee
    style K fill:#f1f8e9
"""
        return mermaid_graph
    
    def get_node_status(self, state: GraphState) -> Dict[str, str]:
        """
        获取各节点状态
        
        Args:
            state: 当前状态
            
        Returns:
            节点状态字典
        """
        status = {
            "document_processor": "pending",
            "document_analyzer": "pending", 
            "generate_multiple_choice": "pending",
            "generate_fill_blank": "pending",
            "generate_matching": "pending",
            "format_output": "pending"
        }
        
        current_step = state.current_step
        
        if current_step in ["document_processed", "document_analyzed", "completed"]:
            status["document_processor"] = "completed"
        
        if current_step in ["document_analyzed", "completed"]:
            status["document_analyzer"] = "completed"
        
        if state.question_set:
            if state.question_set.multiple_choice:
                status["generate_multiple_choice"] = "completed"
            if state.question_set.fill_in_the_blank:
                status["generate_fill_blank"] = "completed"
            if state.question_set.matching:
                status["generate_matching"] = "completed"
        
        if current_step == "completed":
            status["format_output"] = "completed"
        
        if current_step in ["error", "error_handled"]:
            # 将所有未完成的节点标记为错误
            for node, node_status in status.items():
                if node_status == "pending":
                    status[node] = "error"
        
        return status
    
    def save_graph_visualization(self, output_dir: str = ".") -> Dict[str, str]:
        """
        保存图结构的可视化文件
        
        Args:
            output_dir: 输出目录
            
        Returns:
            保存的文件路径字典
        """
        import os
        from datetime import datetime
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        files_saved = {}
        
        try:
            # 1. 保存Mermaid PNG图片
            try:
                from IPython.display import Image
                from langchain_core.runnables.graph import MermaidDrawMethod
                
                png_data = self.graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
                png_path = os.path.join(output_dir, f"langgraph_structure.png")
                
                with open(png_path, "wb") as f:
                    f.write(png_data)
                files_saved["mermaid_png"] = png_path
                print(f"✅ Mermaid PNG图片已保存: {png_path}")
                
            except Exception as e:
                print(f"⚠️  保存Mermaid PNG失败: {e}")
                # 尝试保存Mermaid源码
                try:
                    mermaid_code = self.graph.get_graph().draw_mermaid()
                    mermaid_path = os.path.join(output_dir, f"langgraph_structure.mmd")
                    
                    with open(mermaid_path, "w", encoding="utf-8") as f:
                        f.write(mermaid_code)
                    files_saved["mermaid_code"] = mermaid_path
                    print(f"✅ Mermaid源码已保存: {mermaid_path}")
                    
                except Exception as e2:
                    print(f"⚠️  保存Mermaid源码也失败: {e2}")
            
            # 2. 保存ASCII结构
            try:
                ascii_structure = self.graph.get_graph().print_ascii()
                ascii_path = os.path.join(output_dir, f"langgraph_ascii.txt")
                
                with open(ascii_path, "w", encoding="utf-8") as f:
                    f.write(ascii_structure)
                files_saved["ascii_structure"] = ascii_path
                print(f"✅ ASCII结构图已保存: {ascii_path}")
                
            except Exception as e:
                print(f"⚠️  保存ASCII结构失败: {e}")
            
            # 3. 保存自定义Mermaid图（备用）
            try:
                custom_mermaid = self.get_graph_visualization()
                custom_path = os.path.join(output_dir, f"langgraph_custom.mmd")
                
                with open(custom_path, "w", encoding="utf-8") as f:
                    f.write(custom_mermaid)
                files_saved["custom_mermaid"] = custom_path
                print(f"✅ 自定义Mermaid图已保存: {custom_path}")
                
            except Exception as e:
                print(f"⚠️  保存自定义Mermaid图失败: {e}")
            
        except Exception as e:
            print(f"❌ 保存图结构时出现错误: {e}")
        
        return files_saved
    
    def print_graph_structure(self):
        """
        打印图结构信息
        """
        print("=" * 60)
        print("🔍 LangGraph 结构信息")
        print("=" * 60)
        
        try:
            # 打印ASCII结构
            print("\n📊 ASCII 结构图:")
            print("-" * 40)
            ascii_output = self.graph.get_graph().print_ascii()
            print(ascii_output)
            
        except Exception as e:
            print(f"⚠️  获取ASCII结构失败: {e}")
        
        try:
            # 打印Mermaid代码
            print("\n🎨 Mermaid 图形代码:")
            print("-" * 40)
            mermaid_code = self.graph.get_graph().draw_mermaid()
            print(mermaid_code)
            
        except Exception as e:
            print(f"⚠️  获取Mermaid代码失败: {e}")
        
        # 打印节点信息
        print("\n📋 节点详细信息:")
        print("-" * 40)
        nodes_info = [
            ("document_processor", "📄 文档处理器", "加载和预处理Markdown文档"),
            ("document_analyzer", "🔍 文档分析器", "提取关键点和主题"),
            ("generate_multiple_choice", "📝 选择题生成器", "生成多选题"),
            ("generate_fill_blank", "✏️ 填空题生成器", "生成填空题"),
            ("generate_matching", "🔗 连线题生成器", "生成匹配题"),
            ("format_output", "📊 输出格式化器", "格式化JSON输出和质量验证"),
            ("error_handler", "⚠️ 错误处理器", "处理和记录错误")
        ]
        
        for node_id, name, desc in nodes_info:
            print(f"  • {name}: {desc}")
        
        print("\n🔄 条件分支:")
        print("-" * 40)
        conditions = [
            ("document_processor", "处理成功? → 文档分析器 | 错误处理器"),
            ("document_analyzer", "分析成功? → 选择题生成器 | 错误处理器"), 
            ("format_output", "格式化成功? → 结束 | 错误处理器")
        ]
        
        for node, condition in conditions:
            print(f"  • {node}: {condition}")
        
        print("=" * 60) 