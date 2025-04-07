# core/models.py

from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class FileContext(BaseModel):
    path: str
    before: Optional[str] = None
    after: Optional[str] = None
    diff: Optional[str] = None
    strategy: str = "hybrid"

class Comment(BaseModel):
    file: str
    line: int
    message: str
    agent: Optional[str] = None
    reasoning: Optional[str] = None

class AgentResult(BaseModel):
    agent_name: str
    comments: List[Comment]
    reasoning: Optional[str] = None

class Settings(BaseModel):
    platform: str  # github, gitlab, etc.
    model: str
    strategy: str
    repo: Optional[str] = None
    pr_number: Optional[str] = None

class ReviewState(BaseModel):
    platform: Optional[str] = None
    model: Optional[str] = None
    strategy: Optional[str] = None
    repo: Optional[str] = None
    pr_number: Optional[str] = None
    llm_provider: Optional[str] = None
    context_chunks: Optional[List[str]] = None
    #API keys (optional or empty by default)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    #LLM configuration
    temperature: float = 0.3
    max_tokens: int = 2048
    
    changed_files: List[str] = []
    file_contexts: Dict[str, FileContext] = {}
    agent_results: Dict[str, AgentResult] = {}
    inline_comments: List[Comment] = []
    summary_review: Optional[str] = None

