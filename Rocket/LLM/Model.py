""" Pydantic models for LLM configurations and responses makes type safe and easy to manage LLM interactions. """
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UsageMetadata(BaseModel):
    """Metadata about token usage in LLM responses."""
    prompt_tokens: int = Field(default=0, description="Number of tokens in the prompt.")
    completion_tokens: int = Field(default=0, description="Number of tokens in the completion.")
    total_tokens: int = Field(default=0, description="Total number of tokens used.")
    
    def __str__(self) -> str:
        return (f"UsageMetadata(prompt_tokens={self.prompt_tokens}, "
                f"completion_tokens={self.completion_tokens}, "
                f"total_tokens={self.total_tokens})")
class LLMResponse(BaseModel):
    """Standardized LLM Calls response model and get responses from gemini."""
    text: str = Field(..., description="The main text content of the LLM response.")
    model: str = Field(..., description="The model used to generate the response.")
    usage: UsageMetadata = Field(default_factory=UsageMetadata, description="Token usage metadata.")
    timeStamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the response.")
    finish_reason: Optional[str] = Field(None, description="Reason for finishing the response generation.")
    
    class Config:
        """Pydantic Config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    def __str__(self) -> str:
        """Pretty print for debugging."""
        return (f"LLMResponse(text={self.text}, model={self.model}, "
                f"usage={self.usage}, timeStamp={self.timeStamp}, "
                f"finish_reason={self.finish_reason})")

class LLMERROR(BaseModel):
    """Error model for LLM interactions."""
    error: str = Field(..., description="Error message.")
    model: str = Field(..., description="The model used to generate the response.")
    message: str = Field(..., description="Detailed error message Human Readable.")
    usage: UsageMetadata = Field(default_factory=UsageMetadata, description="Token usage metadata.")
    timeStamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the error.")
    
    def __str__(self) -> str:
        """Pretty print for debugging."""
        return (f"LLMERROR(error={self.error}, model={self.model}, "
                f"message={self.message}, usage={self.usage}, "
                f"timeStamp={self.timeStamp})")