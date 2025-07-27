"""
输出格式化节点
"""
import json
import logging
from typing import Dict, Any
from schemas import GraphState

logger = logging.getLogger(__name__)


class OutputFormatterNode:
    """输出格式化节点 - 负责生成最终的JSON输出"""
    
    def __init__(self):
        pass
    
    async def process(self, state: GraphState) -> GraphState:
        """
        格式化输出结果
        
        Args:
            state: 包含所有生成题目的状态
            
        Returns:
            包含格式化输出的状态
        """
        try:
            logger.info("开始格式化输出...")
            
            if state.current_step == "error":
                return state
            
            if not state.question_set:
                state.error_message = "没有生成任何题目"
                state.current_step = "error"
                return state
            
            # 生成统计信息
            question_set = state.question_set
            stats = {
                "total_questions": question_set.total_questions(),
                "multiple_choice_count": len(question_set.multiple_choice),
                "fill_in_the_blank_count": len(question_set.fill_in_the_blank),
                "matching_count": len(question_set.matching),
                "generation_timestamp": question_set.generated_at
            }
            
            # 验证题目质量
            validation_result = self._validate_questions(question_set)
            
            # 构建完整的输出结构
            formatted_output = {
                "metadata": {
                    "document_title": question_set.document_title,
                    "generated_at": question_set.generated_at,
                    "statistics": stats,
                    "validation": validation_result
                },
                "questions": {
                    "multiple_choice": [q.dict() for q in question_set.multiple_choice],
                    "fill_in_the_blank": [q.dict() for q in question_set.fill_in_the_blank],
                    "matching": [q.dict() for q in question_set.matching]
                },
                "document_analysis": {
                    "topics": state.topics,
                    "key_points": state.key_points
                }
            }
            
            # 保存到状态的元数据中
            if not state.document.metadata:
                state.document.metadata = {}
            
            state.document.metadata["formatted_output"] = formatted_output
            state.current_step = "completed"
            
            logger.info(f"输出格式化完成，共生成 {stats['total_questions']} 道题目")
            
        except Exception as e:
            error_msg = f"输出格式化失败: {str(e)}"
            logger.error(error_msg)
            state.error_message = error_msg
            state.current_step = "error"
        
        return state
    
    def _validate_questions(self, question_set) -> Dict[str, Any]:
        """
        验证题目质量
        
        Args:
            question_set: 题目集合
            
        Returns:
            验证结果字典
        """
        validation_result = {
            "valid": True,
            "issues": [],
            "quality_score": 0.0
        }
        
        total_questions = 0
        valid_questions = 0
        
        # 验证选择题
        for question in question_set.multiple_choice:
            total_questions += 1
            issues = self._validate_multiple_choice(question)
            if not issues:
                valid_questions += 1
            else:
                validation_result["issues"].extend([f"选择题 {question.question_id}: {issue}" for issue in issues])
        
        # 验证填空题
        for question in question_set.fill_in_the_blank:
            total_questions += 1
            issues = self._validate_fill_blank(question)
            if not issues:
                valid_questions += 1
            else:
                validation_result["issues"].extend([f"填空题 {question.question_id}: {issue}" for issue in issues])
        
        # 验证连线题
        for question in question_set.matching:
            total_questions += 1
            issues = self._validate_matching(question)
            if not issues:
                valid_questions += 1
            else:
                validation_result["issues"].extend([f"连线题 {question.question_id}: {issue}" for issue in issues])
        
        # 计算质量分数
        if total_questions > 0:
            validation_result["quality_score"] = valid_questions / total_questions
            validation_result["valid"] = validation_result["quality_score"] >= 0.8  # 80%以上有效
        
        return validation_result
    
    def _validate_multiple_choice(self, question) -> list:
        """验证选择题"""
        issues = []
        
        if not question.question_text.strip():
            issues.append("题目描述为空")
        
        if len(question.options) < 2:
            issues.append("选项数量少于2个")
        
        if question.correct_answer not in question.options:
            issues.append("正确答案不在选项列表中")
        
        # 检查选项重复
        if len(set(question.options)) != len(question.options):
            issues.append("存在重复选项")
        
        return issues
    
    def _validate_fill_blank(self, question) -> list:
        """验证填空题"""
        issues = []
        
        if not question.question_text.strip():
            issues.append("题目描述为空")
        
        if not question.blanks:
            issues.append("没有空白信息")
        
        blank_count = question.question_text.count("____")
        if blank_count != len(question.blanks):
            issues.append(f"空白标记数量({blank_count})与空白信息数量({len(question.blanks)})不匹配")
        
        for i, blank in enumerate(question.blanks):
            if not isinstance(blank, dict):
                issues.append(f"第{i+1}个空白信息格式错误")
                continue
            
            if 'correct_answer' not in blank:
                issues.append(f"第{i+1}个空白缺少正确答案")
            elif not blank['correct_answer'].strip():
                issues.append(f"第{i+1}个空白答案为空")
        
        return issues
    
    def _validate_matching(self, question) -> list:
        """验证连线题"""
        issues = []
        
        if not question.question_text.strip():
            issues.append("题目描述为空")
        
        if len(question.left_items) < 3:
            issues.append("左侧项目少于3个")
        
        if len(question.right_items) < 3:
            issues.append("右侧项目少于3个")
        
        if len(question.left_items) != len(question.right_items):
            issues.append("左右两侧项目数量不相等")
        
        if not question.correct_pairs:
            issues.append("没有正确匹配对")
        
        # 检查匹配对的有效性
        left_items_in_pairs = set()
        right_items_in_pairs = set()
        
        for pair in question.correct_pairs:
            if pair.left_item not in question.left_items:
                issues.append(f"匹配对中的左侧项目'{pair.left_item}'不在左侧列表中")
            
            if pair.right_item not in question.right_items:
                issues.append(f"匹配对中的右侧项目'{pair.right_item}'不在右侧列表中")
            
            left_items_in_pairs.add(pair.left_item)
            right_items_in_pairs.add(pair.right_item)
        
        # 检查是否所有项目都有匹配
        if len(left_items_in_pairs) != len(question.left_items):
            issues.append("不是所有左侧项目都有匹配")
        
        if len(right_items_in_pairs) != len(question.right_items):
            issues.append("不是所有右侧项目都有匹配")
        
        return issues
    
    def get_formatted_output(self, state: GraphState) -> Dict[str, Any]:
        """
        获取格式化的输出结果
        
        Args:
            state: 图状态
            
        Returns:
            格式化的输出字典
        """
        if state.document and state.document.metadata and "formatted_output" in state.document.metadata:
            return state.document.metadata["formatted_output"]
        else:
            return {"error": "没有找到格式化的输出结果"}
    
    def save_to_file(self, state: GraphState, filename: str) -> bool:
        """
        保存结果到文件
        
        Args:
            state: 图状态
            filename: 输出文件名
            
        Returns:
            是否保存成功
        """
        try:
            output = self.get_formatted_output(state)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            logger.info(f"结果已保存到文件: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            return False 