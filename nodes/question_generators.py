"""
题目生成器节点
"""
import logging
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
from schemas import (
    GraphState, QuestionSet, QuestionType,
    MultipleChoiceQuestion, FillInTheBlankQuestion, MatchingQuestion, MatchingPair
)
from prompts import MultipleChoicePrompt, FillInTheBlankPrompt, MatchingPrompt
from llm_service import get_llm_service

logger = logging.getLogger(__name__)


class BaseQuestionGenerator:
    """题目生成器基类"""
    
    def __init__(self):
        self.llm_service = get_llm_service()
    
    def _generate_question_id(self, prefix: str) -> str:
        """生成题目ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"{prefix}_{timestamp}_{short_uuid}"


class MultipleChoiceGeneratorNode(BaseQuestionGenerator):
    """选择题生成器节点"""
    
    def __init__(self):
        super().__init__()
        self.prompt_template = MultipleChoicePrompt.get_prompt()
    
    async def process(self, state: GraphState) -> GraphState:
        """
        生成选择题
        
        Args:
            state: 包含分析结果的状态
            
        Returns:
            包含选择题的状态
        """
        try:
            logger.info("开始生成选择题...")
            
            if state.current_step == "error":
                return state
            
            if not state.key_points:
                return state
            
            # 选择适合的关键点（前5个）
            selected_points = state.key_points[:5]
            topic = state.topics[0] if state.topics else state.document.title
            
            # 构建Prompt
            prompt = self.prompt_template.format(
                topic=topic,
                key_points='\n'.join([f"- {point}" for point in selected_points])
            )
            
            # 调用LLM生成题目
            logger.info("调用LLM生成选择题...")
            response = await self.llm_service.invoke_with_fallback(prompt)
            
            # 解析响应
            questions = self._parse_multiple_choice_response(response, topic)
            
            # 初始化QuestionSet如果还没有
            if not state.question_set:
                state.question_set = QuestionSet(
                    document_title=state.document.title,
                    generated_at=datetime.now().isoformat()
                )
            
            # 添加选择题
            state.question_set.multiple_choice = questions
            
            logger.info(f"成功生成 {len(questions)} 道选择题")
            
        except Exception as e:
            error_msg = f"选择题生成失败: {str(e)}"
            logger.error(error_msg)
            state.error_message = error_msg
            state.current_step = "error"
        
        return state
    
    def _parse_multiple_choice_response(self, response: str, topic: str) -> List[MultipleChoiceQuestion]:
        """解析选择题响应"""
        questions = []
        
        try:
            # 解析JSON响应
            json_data = self.llm_service.parse_json_response(response)
            
            if isinstance(json_data, list):
                question_data_list = json_data
            else:
                question_data_list = [json_data]
            
            for i, data in enumerate(question_data_list):
                try:
                    question = MultipleChoiceQuestion(
                        question_id=data.get('question_id', self._generate_question_id("mc")),
                        question_text=data['question_text'],
                        options=data['options'],
                        correct_answer=data['correct_answer'],
                        topic=data.get('topic', topic),
                        difficulty=data.get('difficulty', 'medium'),
                        explanation=data.get('explanation', '')
                    )
                    questions.append(question)
                except Exception as e:
                    continue
            
        except Exception as e:
            logger.error(f"选择题JSON解析失败: {e}")
            # 创建一个默认题目
            questions.append(self._create_fallback_multiple_choice(topic))
        
        return questions
    
    def _create_fallback_multiple_choice(self, topic: str) -> MultipleChoiceQuestion:
        """创建备用选择题"""
        return MultipleChoiceQuestion(
            question_id=self._generate_question_id("mc"),
            question_text=f"关于{topic}的以下说法，哪一个是正确的？",
            options=["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
            correct_answer="A. 选项1",
            topic=topic,
            difficulty="medium",
            explanation="这是一道示例题目"
        )


class FillInTheBlankGeneratorNode(BaseQuestionGenerator):
    """填空题生成器节点"""
    
    def __init__(self):
        super().__init__()
        self.prompt_template = FillInTheBlankPrompt.get_prompt()
    
    async def process(self, state: GraphState) -> GraphState:
        """
        生成填空题
        
        Args:
            state: 包含分析结果的状态
            
        Returns:
            包含填空题的状态
        """
        try:
            logger.info("开始生成填空题...")
            
            if state.current_step == "error":
                return state
            
            if not state.key_points:
                return state
            
            # 选择适合的关键点（中间部分）
            start_idx = min(3, len(state.key_points) // 3)
            selected_points = state.key_points[start_idx:start_idx+5]
            topic = state.topics[0] if state.topics else state.document.title
            
            # 构建Prompt
            prompt = self.prompt_template.format(
                topic=topic,
                key_points='\n'.join([f"- {point}" for point in selected_points])
            )
            
            # 调用LLM生成题目
            logger.info("调用LLM生成填空题...")
            response = await self.llm_service.invoke_with_fallback(prompt)
            
            # 解析响应
            questions = self._parse_fill_blank_response(response, topic)
            
            # 确保QuestionSet存在
            if not state.question_set:
                state.question_set = QuestionSet(
                    document_title=state.document.title,
                    generated_at=datetime.now().isoformat()
                )
            
            # 添加填空题
            state.question_set.fill_in_the_blank = questions
            
            logger.info(f"成功生成 {len(questions)} 道填空题")
            
        except Exception as e:
            error_msg = f"填空题生成失败: {str(e)}"
            logger.error(error_msg)
            state.error_message = error_msg
            state.current_step = "error"
        
        return state
    
    def _parse_fill_blank_response(self, response: str, topic: str) -> List[FillInTheBlankQuestion]:
        """解析填空题响应"""
        questions = []
        
        try:
            # 解析JSON响应
            json_data = self.llm_service.parse_json_response(response)
            
            if isinstance(json_data, list):
                question_data_list = json_data
            else:
                question_data_list = [json_data]
            
            for i, data in enumerate(question_data_list):
                try:
                    question = FillInTheBlankQuestion(
                        question_id=data.get('question_id', self._generate_question_id("fb")),
                        question_text=data['question_text'],
                        blanks=data['blanks'],
                        topic=data.get('topic', topic),
                        difficulty=data.get('difficulty', 'medium'),
                        explanation=data.get('explanation', '')
                    )
                    questions.append(question)
                except Exception as e:
                    continue
            
        except Exception as e:
            logger.error(f"填空题JSON解析失败: {e}")
            # 创建一个默认题目
            questions.append(self._create_fallback_fill_blank(topic))
        
        return questions
    
    def _create_fallback_fill_blank(self, topic: str) -> FillInTheBlankQuestion:
        """创建备用填空题"""
        return FillInTheBlankQuestion(
            question_id=self._generate_question_id("fb"),
            question_text=f"{topic}的核心概念是____，它的主要特点包括____。",
            blanks=[
                {"position": 1, "correct_answer": "核心概念", "hint": "主要概念"},
                {"position": 2, "correct_answer": "特点", "hint": "主要特征"}
            ],
            topic=topic,
            difficulty="medium",
            explanation="这是一道示例填空题"
        )


class MatchingGeneratorNode(BaseQuestionGenerator):
    """连线题生成器节点"""
    
    def __init__(self):
        super().__init__()
        self.prompt_template = MatchingPrompt.get_prompt()
    
    async def process(self, state: GraphState) -> GraphState:
        """
        生成连线题
        
        Args:
            state: 包含分析结果的状态
            
        Returns:
            包含连线题的状态
        """
        try:
            logger.info("开始生成连线题...")
            
            if state.current_step == "error":
                return state
            
            if not state.key_points:
                return state
            
            # 选择适合的关键点（后面部分，通常更复杂）
            start_idx = max(0, len(state.key_points) - 6)
            selected_points = state.key_points[start_idx:]
            topic = state.topics[0] if state.topics else state.document.title
            
            # 构建Prompt
            prompt = self.prompt_template.format(
                topic=topic,
                key_points='\n'.join([f"- {point}" for point in selected_points])
            )
            
            # 调用LLM生成题目
            logger.info("调用LLM生成连线题...")
            response = await self.llm_service.invoke_with_fallback(prompt)
            
            # 解析响应
            questions = self._parse_matching_response(response, topic)
            
            # 确保QuestionSet存在
            if not state.question_set:
                state.question_set = QuestionSet(
                    document_title=state.document.title,
                    generated_at=datetime.now().isoformat()
                )
            
            # 添加连线题
            state.question_set.matching = questions
            
            logger.info(f"成功生成 {len(questions)} 道连线题")
            
        except Exception as e:
            error_msg = f"连线题生成失败: {str(e)}"
            logger.error(error_msg)
            state.error_message = error_msg
            state.current_step = "error"
        
        return state
    
    def _parse_matching_response(self, response: str, topic: str) -> List[MatchingQuestion]:
        """解析连线题响应"""
        questions = []
        
        try:
            # 解析JSON响应
            json_data = self.llm_service.parse_json_response(response)
            
            if isinstance(json_data, list):
                question_data_list = json_data
            else:
                question_data_list = [json_data]
            
            for i, data in enumerate(question_data_list):
                try:
                    # 构建MatchingPair对象
                    pairs = []
                    for pair_data in data['correct_pairs']:
                        pair = MatchingPair(
                            left_item=pair_data['left_item'],
                            right_item=pair_data['right_item']
                        )
                        pairs.append(pair)
                    
                    question = MatchingQuestion(
                        question_id=data.get('question_id', self._generate_question_id("mt")),
                        question_text=data['question_text'],
                        left_items=data['left_items'],
                        right_items=data['right_items'],
                        correct_pairs=pairs,
                        topic=data.get('topic', topic),
                        difficulty=data.get('difficulty', 'hard'),
                        explanation=data.get('explanation', '')
                    )
                    questions.append(question)
                except Exception as e:
                    continue
            
        except Exception as e:
            logger.error(f"连线题JSON解析失败: {e}")
            # 创建一个默认题目
            questions.append(self._create_fallback_matching(topic))
        
        return questions
    
    def _create_fallback_matching(self, topic: str) -> MatchingQuestion:
        """创建备用连线题"""
        left_items = ["概念A", "概念B", "概念C", "概念D"]
        right_items = ["定义1", "定义2", "定义3", "定义4"]
        
        pairs = [
            MatchingPair(left_item="概念A", right_item="定义1"),
            MatchingPair(left_item="概念B", right_item="定义2"),
            MatchingPair(left_item="概念C", right_item="定义3"),
            MatchingPair(left_item="概念D", right_item="定义4")
        ]
        
        return MatchingQuestion(
            question_id=self._generate_question_id("mt"),
            question_text=f"请将下列关于{topic}的概念与其定义进行匹配：",
            left_items=left_items,
            right_items=right_items,
            correct_pairs=pairs,
            topic=topic,
            difficulty="hard",
            explanation="这是一道示例连线题"
        ) 