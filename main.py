# -*- coding: utf-8 -*-
"""
Author: Xiaofeng Mai, vibe coding with cursor.
AI教育题目生成应用 - 主程序入口
基于LangGraph和通义千问的智能题目生成系统
"""
import asyncio
import json
import logging
import argparse
import warnings
from datetime import datetime
from pathlib import Path

from schemas import GraphState, DocumentContent
from nodes import DocumentProcessorNode
from question_generator_graph import QuestionGeneratorGraph
from config import get_settings

# 取消所有warning显示
warnings.filterwarnings("ignore")


# 配置日志 - 只显示ERROR级别以上的日志
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('question_generation.log', encoding='utf-8')
    ]
)

# 设置特定logger的级别
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


class QuestionGeneratorApp:
    """题目生成应用主类"""
    
    def __init__(self):
        self.settings = get_settings()
        # 检查API密钥
        self._check_api_keys()
        
        # 初始化LLM服务并测试连接
        try:
            from llm_service import get_llm_service
            self.llm_service = get_llm_service()
            print("🎉 LLM服务初始化完成\n")
        except Exception as e:
            print(f"\n❌ LLM服务初始化失败: {e}")
            print("请检查API密钥设置和网络连接")
            raise
        
        self.graph = QuestionGeneratorGraph()
        self.document_processor = DocumentProcessorNode()
    
    def _check_api_keys(self):
        """检查API密钥设置"""
        import os
        ali_key = os.environ.get("ALI_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")
        
        if not ali_key and not openai_key:
            print("\n⚠️  警告：未检测到API密钥环境变量")
            print("请设置以下环境变量之一：")
            print("1. ALI_API_KEY=your_ali_api_key (推荐)")
            print("2. OPENAI_API_KEY=your_openai_api_key (备选)")
            print("\n示例：")
            print("export ALI_API_KEY=sk-xxxxxxxxxxxx")
            print("或者")
            print("export OPENAI_API_KEY=sk-xxxxxxxxxxxx")
            print()
        elif ali_key:
            print(f"✅ 检测到ALI_API_KEY: {ali_key[:10]}...")
        elif openai_key:
            print(f"✅ 检测到OPENAI_API_KEY: {openai_key[:10]}...")
    
    async def generate_from_file(self, file_path: str, output_path: str = None) -> dict:
        """
        从文件生成题目
        
        Args:
            file_path: 输入文档文件路径
            output_path: 输出文件路径（可选）
            
        Returns:
            生成结果字典
        """
        try:
            logger.info(f"开始处理文件: {file_path}")
            
            # 加载文档
            document = self.document_processor.load_from_file(file_path)
            
            # 创建初始状态
            initial_state = GraphState(
                document=document,
                current_step="start"
            )
            
            # 运行工作流
            result_state = await self.graph.run(initial_state)
            
            # 处理结果
            if result_state.current_step == "completed":
                logger.info("题目生成成功完成")
                
                # 获取格式化输出
                output = self.graph.output_formatter.get_formatted_output(result_state)
                
                # 保存到文件
                if output_path:
                    success = self.graph.output_formatter.save_to_file(result_state, output_path)
                    if success:
                        logger.info(f"结果已保存到: {output_path}")
                
                return {
                    "success": True,
                    "output": output,
                    "file_path": output_path
                }
            else:
                logger.error(f"题目生成失败: {result_state.error_message}")
                return {
                    "success": False,
                    "error": result_state.error_message
                }
                
        except Exception as e:
            error_msg = f"处理文件时发生错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def generate_from_text(self, title: str, content: str, output_path: str = None) -> dict:
        """
        从文本生成题目
        
        Args:
            title: 文档标题
            content: 文档内容
            output_path: 输出文件路径（可选）
            
        Returns:
            生成结果字典
        """
        try:
            logger.info(f"开始处理文本: {title}")
            
            # 创建文档
            document = self.document_processor.create_from_text(title, content)
            
            # 创建初始状态
            initial_state = GraphState(
                document=document,
                current_step="start"
            )
            
            # 运行工作流
            result_state = await self.graph.run(initial_state)
            
            # 处理结果
            if result_state.current_step == "completed":
                logger.info("题目生成成功完成")
                
                # 获取格式化输出
                output = self.graph.output_formatter.get_formatted_output(result_state)
                
                # 保存到文件
                if output_path:
                    success = self.graph.output_formatter.save_to_file(result_state, output_path)
                    if success:
                        logger.info(f"结果已保存到: {output_path}")
                
                return {
                    "success": True,
                    "output": output,
                    "file_path": output_path
                }
            else:
                logger.error(f"题目生成失败: {result_state.error_message}")
                return {
                    "success": False,
                    "error": result_state.error_message
                }
                
        except Exception as e:
            error_msg = f"处理文本时发生错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def print_graph_info(self):
        """打印工作流信息"""
        print("\n=== AI教育题目生成系统 ===")
        print("基于LangGraph和通义千问的智能题目生成")
        print("\n工作流程图:")
        print(self.graph.get_graph_visualization())
        print("\n支持的题目类型:")
        print("1. 选择题 (Multiple Choice)")
        print("2. 填空题 (Fill-in-the-Blank)")
        print("3. 连线题 (Matching)")
        print("\n📊 图结构可视化功能:")
        print("  --graph              显示详细的图结构信息（ASCII + Mermaid）")
        print("  --save-graph ./imgs  保存图结构可视化文件到指定目录")
        print("\n💡 使用示例:")
        print("  python main.py --graph                   # 查看图结构")
        print("  python main.py --save-graph ./output     # 保存图片文件")
        print("  python main.py --sample                  # 生成示例题目")
    
    def create_sample_document(self, filename: str = "sample_document.md"):
        """创建示例文档"""
        sample_content = """# 机器学习基础

## 什么是机器学习

机器学习是人工智能的一个重要分支，它使计算机能够在不被明确编程的情况下进行学习。机器学习算法通过分析数据来识别模式，并基于这些模式做出预测或决策。

## 主要类型

### 监督学习
监督学习使用标记的训练数据来学习从输入到输出的映射。常见的监督学习任务包括：
- **分类**：预测离散的类别标签
- **回归**：预测连续的数值

### 无监督学习
无监督学习从未标记的数据中发现隐藏的模式。主要包括：
- **聚类**：将相似的数据点分组
- **降维**：减少数据的特征数量
- **关联规则学习**：发现变量之间的关系

### 强化学习
强化学习通过与环境的交互来学习最优策略。智能体通过试错来学习如何在特定环境中采取行动以最大化累积奖励。

## 常用算法

1. **线性回归**：用于预测连续值的基础算法
2. **逻辑回归**：用于二分类问题的线性模型
3. **决策树**：基于树结构进行决策的算法
4. **随机森林**：集成多个决策树的算法
5. **支持向量机**：在高维空间中寻找最优分离超平面
6. **神经网络**：模拟人脑神经元的网络结构

## 应用领域

机器学习在各个领域都有广泛应用：
- 图像识别和计算机视觉
- 自然语言处理
- 推荐系统
- 金融风险评估
- 医疗诊断
- 自动驾驶

## 关键概念

- **特征**：用于训练模型的输入变量
- **标签**：监督学习中的目标输出
- **训练集**：用于训练模型的数据
- **测试集**：用于评估模型性能的数据
- **过拟合**：模型在训练数据上表现很好但在新数据上表现较差
- **欠拟合**：模型过于简单，无法捕获数据中的模式
"""
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(sample_content)
            logger.info(f"示例文档已创建: {filename}")
            return filename
        except Exception as e:
            logger.error(f"创建示例文档失败: {e}")
            return None



async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI教育题目生成系统")
    parser.add_argument('--file', '-f', type=str, help='输入文档文件路径')
    parser.add_argument('--output', '-o', type=str, help='输出文件路径')
    parser.add_argument('--title', '-t', type=str, help='文档标题（用于文本输入）')
    parser.add_argument('--content', '-c', type=str, help='文档内容（用于文本输入）')
    parser.add_argument('--sample', '-s', action='store_true', help='创建并使用示例文档')
    parser.add_argument('--info', action='store_true', help='显示系统信息')

    parser.add_argument('--graph', action='store_true', help='显示图结构信息（ASCII和Mermaid）')
    parser.add_argument('--save-graph', type=str, metavar='DIR', help='保存图结构可视化文件到指定目录')
    
    args = parser.parse_args()
    
    # 创建应用实例，如果失败则退出
    try:
        app = QuestionGeneratorApp()
    except Exception as e:
        print(f"\n💥 应用初始化失败，程序退出")
        print("\n💡 可能的解决方案：")
        print("1. 检查API密钥是否正确设置")
        print("2. 检查网络连接是否正常")
        print("3. 查看图结构：python main.py --graph")
        return
    
    # 显示系统信息
    if args.info:
        app.print_graph_info()
        return
    
    # 显示图结构
    if args.graph:
        app.graph.print_graph_structure()
        return
    
    # 保存图结构可视化
    if args.save_graph:
        output_dir = args.save_graph
        print(f"🔍 正在保存图结构可视化到目录: {output_dir}")
        files_saved = app.graph.save_graph_visualization(output_dir)
        
        if files_saved:
            print(f"\n✅ 图结构可视化保存完成，共保存 {len(files_saved)} 个文件:")
            for file_type, file_path in files_saved.items():
                print(f"   • {file_type}: {file_path}")
        else:
            print("\n⚠️  未能保存任何图结构文件")
        return
    

    
    # 处理示例文档
    if args.sample:
        sample_file = app.create_sample_document()
        if sample_file:
            print(f"\n使用示例文档: {sample_file}")
            args.file = sample_file
            if not args.output:
                args.output = f"sample_questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # 生成默认输出文件名
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f"generated_questions_{timestamp}.json"
    
    # 处理文件输入
    if args.file:
        if not Path(args.file).exists():
            print(f"错误: 文件不存在 - {args.file}")
            return
        
        print(f"正在处理文件: {args.file}")
        result = await app.generate_from_file(args.file, args.output)
        
        if result["success"]:
            print(f"\n✅ 题目生成成功!")
            print(f"📁 输出文件: {result.get('file_path', args.output)}")
            
            # 显示统计信息
            output = result["output"]
            if "metadata" in output and "statistics" in output["metadata"]:
                stats = output["metadata"]["statistics"]
                print(f"\n📊 生成统计:")
                print(f"   总题目数: {stats['total_questions']}")
                print(f"   选择题: {stats['multiple_choice_count']}")
                print(f"   填空题: {stats['fill_in_the_blank_count']}")
                print(f"   连线题: {stats['matching_count']}")
        else:
            print(f"\n❌ 题目生成失败: {result['error']}")
    
    # 处理文本输入
    elif args.title and args.content:
        print(f"正在处理文本: {args.title}")
        result = await app.generate_from_text(args.title, args.content, args.output)
        
        if result["success"]:
            print(f"\n✅ 题目生成成功!")
            print(f"📁 输出文件: {result.get('file_path', args.output)}")
        else:
            print(f"\n❌ 题目生成失败: {result['error']}")
    
    else:
        print("请提供输入文件 (--file) 或文本内容 (--title 和 --content)")
        print("\n可用选项：")
        print("  --sample, -s    创建并处理示例文档")
        print("  --info          查看系统信息")
        print("  --graph         显示图结构信息（ASCII和Mermaid）")
        print("  --save-graph    保存图结构可视化文件")
        print("  --help          查看完整帮助")
        print("\n💡 可以先使用示例文档查看效果：")
        print("     python main.py --sample")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n程序运行异常: {e}")
        logger.exception("程序异常退出") 