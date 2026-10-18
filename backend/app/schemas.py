from pydantic import BaseModel,Field
from typing import Literal



class WorkItemCreate(BaseModel):
    title:str=Field(min_length=3,max_length=200)
    description:str = Field(min_length=1)
    item_type : Literal[
        "incident",
        "customer_issue",
        "payment",
        "compliance",
        "task"
    ]
    priority:Literal[
        "low",
        "medium",
        "high",
        "critical"
       
    ]="medium"
    team_id:int= Field(gt=0)




class LoginRequest(BaseModel):
    email:str
    password:str


class TokenResponse(BaseModel):
    access_token:str
    token_type:str = "bearer"



class WorkItemUpdate(BaseModel):
    title:str|None = Field(
        default=None,
        min_length=3,
        max_length=200
    )

    description :str|None= Field(
        default=None,
        min_length=1
    )
    priority:Literal[
        "low","medium","high","critical"
    ] |None = None

    expected_version :int =Field(ge=1)



class WorkItemAssign(BaseModel):
    assignee_id:int = Field(gt=0)
    expected_version:int = Field(ge=1)



class WorkItemClaim(BaseModel):
    expected_version: int = Field(ge=1)


class WorkItemStatusUpdate(BaseModel):
    status:Literal["open","in_progress","resolved","closed"]
    expected_version:int=Field(ge=1)



class CommentCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=2000
    )
