from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    id: str
    timestamp: datetime
    type: str
    agent: str
    title: str
    summary: str
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationState(BaseModel):
    scenario_id: str
    customer_id: str
    order_id: str
    known_need_by: str
    active_agent: Optional[str] = None
    current_intent: Optional[str] = None
    offered_options: List[str] = Field(default_factory=list)
    last_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    pending_confirmation: Optional[Dict[str, Any]] = None
    pending_recommendation: Optional[bool] = False
    completed_actions: List[str] = Field(default_factory=list)
    conversation_summary: str = ""
    messages: List[Dict[str, str]] = Field(default_factory=list)
    refund_issued: bool = False
    expedited_replacement_created: bool = False
    escalation_created: bool = False
    preferred_channel: Optional[str] = None
    order_value: Optional[float] = None
