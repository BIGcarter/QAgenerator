"""
题目数据模型定义
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator


class QuestionType(str, Enum):
    """题目类型枚举"""
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_THE_BLANK = "fill_in_the_blank" 
    MATCHING = "matching"


class BaseQuestion(BaseModel):
    """题目基础模型"""
    question_id: str = Field(..., description="题目唯一标识")
    question_type: QuestionType = Field(..., description="题目类型")
    question_text: str = Field(..., description="题目描述")
    difficulty: str = Field(default="medium", description="难度等级: easy, medium, hard")
    topic: str = Field(..., description="题目所属主题")
    explanation: Optional[str] = Field(None, description="答案解释")


class MultipleChoiceQuestion(BaseQuestion):
    """选择题模型"""
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    options: List[str] = Field(..., min_items=2, max_items=6, description="选项列表")
    correct_answer: str = Field(..., description="正确答案")
    
    @validator('correct_answer')
    def validate_correct_answer(cls, v, values):
        """验证正确答案是否在选项中"""
        if 'options' in values and v not in values['options']:
            raise ValueError("正确答案必须在选项列表中")
        return v


class FillInTheBlankQuestion(BaseQuestion):
    """填空题模型"""
    question_type: QuestionType = QuestionType.FILL_IN_THE_BLANK
    blanks: List[Dict[str, Any]] = Field(..., description="空白处信息")
    # 每个blank包含: {"position": int, "correct_answer": str, "hint": str}
    
    @validator('blanks')
    def validate_blanks(cls, v):
        """验证填空信息格式"""
        for blank in v:
            if not all(key in blank for key in ['position', 'correct_answer']):
                raise ValueError("每个空白处必须包含position和correct_answer字段")
        return v


class MatchingPair(BaseModel):
    """连线对模型"""
    left_item: str = Field(..., description="左侧项目")
    right_item: str = Field(..., description="右侧项目")


class MatchingQuestion(BaseQuestion):
    """连线题模型"""
    question_type: QuestionType = QuestionType.MATCHING
    left_items: List[str] = Field(..., min_items=3, description="左侧项目列表")
    right_items: List[str] = Field(..., min_items=3, description="右侧项目列表")
    correct_pairs: List[MatchingPair] = Field(..., description="正确的匹配对")
    
    @validator('correct_pairs')
    def validate_pairs(cls, v, values):
        """验证匹配对的有效性"""
        if 'left_items' in values and 'right_items' in values:
            left_items = values['left_items']
            right_items = values['right_items']
            
            for pair in v:
                if pair.left_item not in left_items:
                    raise ValueError(f"左侧项目 '{pair.left_item}' 不在左侧列表中")
                if pair.right_item not in right_items:
                    raise ValueError(f"右侧项目 '{pair.right_item}' 不在右侧列表中")
        return v


class DocumentContent(BaseModel):
    """文档内容模型"""
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="文档内容")
    source: Optional[str] = Field(None, description="文档来源")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="文档元数据")


class QuestionSet(BaseModel):
    """题目集合模型"""
    document_title: str = Field(..., description="源文档标题")
    multiple_choice: List[MultipleChoiceQuestion] = Field(default_factory=list, description="选择题列表")
    fill_in_the_blank: List[FillInTheBlankQuestion] = Field(default_factory=list, description="填空题列表")
    matching: List[MatchingQuestion] = Field(default_factory=list, description="连线题列表")
    generated_at: str = Field(..., description="生成时间")
    
    def total_questions(self) -> int:
        """返回总题目数量"""
        return len(self.multiple_choice) + len(self.fill_in_the_blank) + len(self.matching)
    
    def to_json_dict(self) -> Dict[str, Any]:
        """转换为JSON字典格式"""
        return {
            "document_title": self.document_title,
            "generated_at": self.generated_at,
            "total_questions": self.total_questions(),
            "questions": {
                "multiple_choice": [q.dict() for q in self.multiple_choice],
                "fill_in_the_blank": [q.dict() for q in self.fill_in_the_blank], 
                "matching": [q.dict() for q in self.matching]
            }
        }


class GraphState(BaseModel):
    """LangGraph状态模型"""
    document: Optional[DocumentContent] = Field(None, description="输入文档")
    key_points: List[str] = Field(default_factory=list, description="提取的关键点")
    topics: List[str] = Field(default_factory=list, description="文档主题")
    question_set: Optional[QuestionSet] = Field(None, description="生成的题目集合")
    current_step: str = Field(default="start", description="当前处理步骤")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        arbitrary_types_allowed = True 