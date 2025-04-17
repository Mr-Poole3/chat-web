from typing import Any, Optional

from pydantic import Field, BaseModel


class ResponseModel(BaseModel):
    """
    Response Model
    """

    code: int = Field(200, description="status code")
    msg: Optional[str] = Field("", description="status message")
    data: Optional[Any] = Field(None, description="Response data")
    log_id: Optional[Any] = Field(None, description="log id")


class QueryRequestModel(BaseModel):
    query: str = Field(default="", description="user query")
