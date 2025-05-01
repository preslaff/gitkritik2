# core/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class FileContext(BaseModel):
    path: str
    before: Optional[str] = None
    after: Optional[str] = None
    diff: Optional[str] = None
    strategy: str = "hybrid"
    # NEW: Store fetched context from ReAct agent
    symbol_definitions: Optional[Dict[str, str]] = Field(default_factory=dict, description="Definitions fetched by Context Agent")

class Comment(BaseModel):
    file: str
    line: int
    message: str
    agent: Optional[str] = None
    # Reasoning might be less needed if messages are comprehensive
    # reasoning: Optional[str] = None

# New model for structured LLM output for review agents
class LLMReviewResponse(BaseModel):
    comments: List[Comment] = Field(description="A list of review comments found, with file and line number relative to the new file version.")

class AgentResult(BaseModel):
    agent_name: str
    comments: List[Comment] # Parsed comments
    reasoning: Optional[str] = None # For summary agent or general reasoning
    raw_llm_response: Optional[str] = None # Optional: store raw for debugging

class Settings(BaseModel): # Kept for config loading clarity, but state holds runtime values
    platform: str
    model: str
    strategy: str
    repo: Optional[str] = None
    pr_number: Optional[str] = None
    llm_provider: Optional[str] = None

class ReviewState(BaseModel):
    # Configuration / Setup Info
    platform: Optional[str] = None
    model: Optional[str] = None
    strategy: Optional[str] = None
    repo: Optional[str] = None
    pr_number: Optional[str] = None
    llm_provider: Optional[str] = None
    config_file_path: Optional[str] = None # From CLI --config
    # API keys (Loaded from env/config, used by get_llm)
    openai_api_key: Optional[str] = Field(None, exclude=True) # Exclude from logs/dumps
    anthropic_api_key: Optional[str] = Field(None, exclude=True)
    gemini_api_key: Optional[str] = Field(None, exclude=True)
    # LLM configuration
    temperature: float = 0.3
    max_tokens: int = 2048
    # CLI Flags / Runtime settings
    is_ci_mode: bool = False
    dry_run: bool = False
    show_inline_locally: bool = False
    side_by_side_display: bool = False
    review_unstaged: bool = False # For detect_changes logic
    review_all_files: bool = False # For detect_changes logic
    # Core Data
    changed_files: List[str] = Field(default_factory=list)
    file_contexts: Dict[str, FileContext] = Field(default_factory=dict) # Includes symbol_definitions now
    agent_results: Dict[str, AgentResult] = Field(default_factory=dict)
    inline_comments: List[Comment] = Field(default_factory=list) # Merged comments
    summary_review: Optional[str] = None
    # Debugging / Advanced
    react_agent_workings: Optional[Dict[str, List[str]]] = Field(default_factory=dict, description="Debugging info from ReAct steps per file")

    class Config:
        # Optional: if you want Pydantic models passed between nodes
        # instead of dicts (requires graph definition change)
        # arbitrary_types_allowed = True
        pass