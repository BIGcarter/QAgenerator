"""
题目生成Prompt模板
"""
from langchain.prompts import PromptTemplate

try:
    from langchain_core.prompts import BasePromptTemplate
except ImportError:
    try:
        from langchain.schema import BasePromptTemplate
    except ImportError:
        from langchain.prompts.base import BasePromptTemplate


class DocumentAnalysisPrompt:
    """文档分析Prompt"""
    
    TEMPLATE = """
你是一位经验丰富的教育专家，请分析以下教学文档，提取关键知识点和主题。

文档标题: {title}
文档内容:
{content}

请按照以下格式输出分析结果：

## 主要主题
请列出3-5个文档的主要主题，每行一个。

## 关键知识点
请提取8-12个重要的知识点，这些知识点应该：
1. 具有教学价值
2. 适合出题考察
3. 涵盖不同难度层次
4. 知识点之间有一定的关联性

每个知识点单独一行，格式为：
- 知识点内容

## 难度分层
请将上述知识点按难度分为三层：
- 基础层（易）：适合选择题
- 应用层（中）：适合填空题
- 综合层（难）：适合连线题

输出格式要求：严格按照上述结构输出，不要添加额外的解释。
"""

    @classmethod
    def get_prompt(cls) -> BasePromptTemplate:
        """获取文档分析Prompt模板"""
        return PromptTemplate(
            input_variables=["title", "content"],
            template=cls.TEMPLATE
        )


class MultipleChoicePrompt:
    """选择题生成Prompt"""
    
    TEMPLATE = """
你是一位专业的题目设计师，请根据以下知识点生成选择题。

文档主题: {topic}
知识点列表:
{key_points}

请为每个知识点生成1道选择题，要求：

1. 题目描述清晰、准确
2. 提供4个选项（A、B、C、D）
3. 只有一个正确答案
4. 错误选项具有一定的迷惑性
5. 包含简要的答案解释

输出格式（JSON）：
```json
[
  {{
    "question_id": "mc_001",
    "question_text": "题目描述",
    "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
    "correct_answer": "A. 选项1",
    "topic": "相关主题",
    "difficulty": "easy",
    "explanation": "答案解释"
  }}
]
```

重要提醒：
- 输出必须是有效的JSON格式
- 选项格式统一为 "字母. 内容"
- 正确答案必须与选项列表中的某项完全匹配
- 每道题的question_id必须唯一
"""

    @classmethod 
    def get_prompt(cls) -> BasePromptTemplate:
        """获取选择题生成Prompt模板"""
        return PromptTemplate(
            input_variables=["topic", "key_points"],
            template=cls.TEMPLATE
        )


class FillInTheBlankPrompt:
    """填空题生成Prompt"""
    
    TEMPLATE = """
你是一位专业的题目设计师，请根据以下知识点生成填空题。

文档主题: {topic}
知识点列表:
{key_points}

请为每个知识点生成1道填空题，要求：

1. 题目描述中用____表示空白处
2. 每道题包含1-3个空白
3. 空白处应该是关键词或核心概念
4. 提供每个空白的标准答案
5. 可以提供提示信息（可选）

输出格式（JSON）：
```json
[
  {{
    "question_id": "fb_001", 
    "question_text": "在机器学习中，____是一种监督学习算法，它通过____来预测目标变量。",
    "blanks": [
      {{
        "position": 1,
        "correct_answer": "线性回归",
        "hint": "一种预测连续值的算法"
      }},
      {{
        "position": 2, 
        "correct_answer": "线性关系",
        "hint": "特征与目标之间的关系"
      }}
    ],
    "topic": "相关主题",
    "difficulty": "medium",
    "explanation": "详细解释"
  }}
]
```

重要提醒：
- 输出必须是有效的JSON格式
- 空白处用____表示（4个下划线）
- blanks数组中的position从1开始编号
- 每道题的question_id必须唯一
"""

    @classmethod
    def get_prompt(cls) -> BasePromptTemplate:
        """获取填空题生成Prompt模板"""
        return PromptTemplate(
            input_variables=["topic", "key_points"],
            template=cls.TEMPLATE
        )


class MatchingPrompt:
    """连线题生成Prompt"""
    
    TEMPLATE = """
你是一位专业的题目设计师，请根据以下知识点生成连线题。

文档主题: {topic}
知识点列表:
{key_points}

请基于这些知识点生成连线题，要求：

1. 每道题包含4-6对匹配项
2. 左侧可以是概念、术语、人物等
3. 右侧可以是定义、特征、作品等
4. 确保匹配关系明确、唯一
5. 避免模糊或有争议的匹配

输出格式（JSON）：
```json
[
  {{
    "question_id": "mt_001",
    "question_text": "请将下列概念与其对应的定义进行匹配：",
    "left_items": ["概念1", "概念2", "概念3", "概念4"],
    "right_items": ["定义A", "定义B", "定义C", "定义D"],
    "correct_pairs": [
      {{
        "left_item": "概念1",
        "right_item": "定义A"
      }},
      {{
        "left_item": "概念2", 
        "right_item": "定义B"
      }},
      {{
        "left_item": "概念3",
        "right_item": "定义C"
      }},
      {{
        "left_item": "概念4",
        "right_item": "定义D"
      }}
    ],
    "topic": "相关主题",
    "difficulty": "hard",
    "explanation": "匹配关系解释"
  }}
]
```

重要提醒：
- 输出必须是有效的JSON格式
- 左右两侧项目数量必须相等
- correct_pairs中的项目必须在对应的列表中存在
- 每道题的question_id必须唯一
- 确保所有匹配关系都是一对一的
"""

    @classmethod
    def get_prompt(cls) -> BasePromptTemplate:
        """获取连线题生成Prompt模板"""
        return PromptTemplate(
            input_variables=["topic", "key_points"],
            template=cls.TEMPLATE
        ) 