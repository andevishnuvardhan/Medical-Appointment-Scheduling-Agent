import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import os
from openai import OpenAI
from anthropic import Anthropic

from .prompts import (
    SYSTEM_PROMPT,
    FAQ_PROMPT,
    SLOT_SUGGESTION_PROMPT,
    CONFIRMATION_PROMPT,
    BOOKING_SUCCESS_PROMPT
)
from ..rag.faq_rag import FAQRAG
from ..tools.availability_tool import AvailabilityTool
from ..tools.booking_tool import BookingTool
from ..models.schemas import ConversationState, ChatMessage, PatientInfo

logger = logging.getLogger(__name__)


class SchedulingAgent:
    """Main conversational agent for appointment scheduling"""

    def __init__(
        self,
        llm_provider: str = "openai",
        llm_model: str = "gpt-4-turbo",
        api_key: Optional[str] = None,
        faq_rag: Optional[FAQRAG] = None,
        availability_tool: Optional[AvailabilityTool] = None,
        booking_tool: Optional[BookingTool] = None
    ):
        """
        Initialize the scheduling agent

        Args:
            llm_provider: LLM provider ("openai" or "anthropic")
            llm_model: Model name
            api_key: API key for the LLM provider
            faq_rag: FAQ RAG system
            availability_tool: Availability checking tool
            booking_tool: Booking management tool
        """
        self.llm_provider = llm_provider.lower()
        self.llm_model = llm_model
        self.faq_rag = faq_rag
        self.availability_tool = availability_tool
        self.booking_tool = booking_tool

        # Initialize LLM client
        if self.llm_provider == "openai":
            self.llm_client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        elif self.llm_provider == "anthropic":
            self.llm_client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

        # Store active conversations
        self.conversations: Dict[str, ConversationState] = {}

        logger.info(f"Initialized SchedulingAgent with {llm_provider}/{llm_model}")

    def _call_llm(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict:
        """
        Call the LLM with messages

        Args:
            messages: List of message dictionaries
            tools: Optional tool definitions

        Returns:
            LLM response
        """
        if self.llm_provider == "openai":
            kwargs = {
                "model": self.llm_model,
                "messages": messages,
                "temperature": 0.7
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = self.llm_client.chat.completions.create(**kwargs)

            # Parse response
            message = response.choices[0].message
            result = {
                "content": message.content or "",
                "tool_calls": []
            }

            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments)
                    })

            return result

        elif self.llm_provider == "anthropic":
            kwargs = {
                "model": self.llm_model,
                "max_tokens": 2000,
                "messages": messages,
                "temperature": 0.7
            }
            if tools:
                kwargs["tools"] = tools

            response = self.llm_client.messages.create(**kwargs)

            # Parse response
            result = {
                "content": "",
                "tool_calls": []
            }

            for block in response.content:
                if block.type == "text":
                    result["content"] += block.text
                elif block.type == "tool_use":
                    result["tool_calls"].append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input
                    })

            return result

    def _get_tool_definitions(self) -> List[Dict]:
        """Get tool definitions for function calling"""
        if self.llm_provider == "openai":
            return [
                {
                    "type": "function",
                    "function": {
                        "name": "check_availability",
                        "description": "Check available appointment slots for a specific date",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "date": {
                                    "type": "string",
                                    "description": "Date in YYYY-MM-DD format"
                                },
                                "appointment_type": {
                                    "type": "string",
                                    "enum": ["consultation", "followup", "physical", "specialist"],
                                    "description": "Type of appointment"
                                },
                                "time_preference": {
                                    "type": "string",
                                    "enum": ["morning", "afternoon", "evening", "any"],
                                    "description": "Preferred time of day"
                                }
                            },
                            "required": ["date", "appointment_type"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "suggest_slots",
                        "description": "Get suggested time slots based on patient preferences",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "preferred_date": {
                                    "type": "string",
                                    "description": "Preferred date in YYYY-MM-DD format (optional)"
                                },
                                "appointment_type": {
                                    "type": "string",
                                    "enum": ["consultation", "followup", "physical", "specialist"],
                                    "description": "Type of appointment"
                                },
                                "time_preference": {
                                    "type": "string",
                                    "enum": ["morning", "afternoon", "evening", "any"],
                                    "description": "Preferred time of day"
                                },
                                "num_suggestions": {
                                    "type": "integer",
                                    "description": "Number of suggestions to return (default 5)"
                                }
                            },
                            "required": ["appointment_type"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "book_appointment",
                        "description": "Book an appointment - ONLY use after patient explicitly confirms all details",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "appointment_type": {
                                    "type": "string",
                                    "enum": ["consultation", "followup", "physical", "specialist"]
                                },
                                "date": {
                                    "type": "string",
                                    "description": "Date in YYYY-MM-DD format"
                                },
                                "start_time": {
                                    "type": "string",
                                    "description": "Start time in HH:MM format"
                                },
                                "patient_name": {
                                    "type": "string"
                                },
                                "patient_email": {
                                    "type": "string"
                                },
                                "patient_phone": {
                                    "type": "string"
                                },
                                "reason": {
                                    "type": "string"
                                }
                            },
                            "required": ["appointment_type", "date", "start_time", "patient_name", "patient_email", "patient_phone", "reason"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "answer_faq",
                        "description": "Search the clinic knowledge base to answer questions about the clinic, policies, insurance, etc.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "question": {
                                    "type": "string",
                                    "description": "The patient's question"
                                }
                            },
                            "required": ["question"]
                        }
                    }
                }
            ]
        else:  # anthropic
            return [
                {
                    "name": "check_availability",
                    "description": "Check available appointment slots for a specific date",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Date in YYYY-MM-DD format"
                            },
                            "appointment_type": {
                                "type": "string",
                                "enum": ["consultation", "followup", "physical", "specialist"],
                                "description": "Type of appointment"
                            },
                            "time_preference": {
                                "type": "string",
                                "enum": ["morning", "afternoon", "evening", "any"],
                                "description": "Preferred time of day"
                            }
                        },
                        "required": ["date", "appointment_type"]
                    }
                },
                {
                    "name": "suggest_slots",
                    "description": "Get suggested time slots based on patient preferences",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "preferred_date": {
                                "type": "string",
                                "description": "Preferred date in YYYY-MM-DD format (optional)"
                            },
                            "appointment_type": {
                                "type": "string",
                                "enum": ["consultation", "followup", "physical", "specialist"],
                                "description": "Type of appointment"
                            },
                            "time_preference": {
                                "type": "string",
                                "enum": ["morning", "afternoon", "evening", "any"],
                                "description": "Preferred time of day"
                            },
                            "num_suggestions": {
                                "type": "integer",
                                "description": "Number of suggestions to return (default 5)"
                            }
                        },
                        "required": ["appointment_type"]
                    }
                },
                {
                    "name": "book_appointment",
                    "description": "Book an appointment - ONLY use after patient explicitly confirms all details",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "appointment_type": {
                                "type": "string",
                                "enum": ["consultation", "followup", "physical", "specialist"]
                            },
                            "date": {
                                "type": "string",
                                "description": "Date in YYYY-MM-DD format"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start time in HH:MM format"
                            },
                            "patient_name": {
                                "type": "string"
                            },
                            "patient_email": {
                                "type": "string"
                            },
                            "patient_phone": {
                                "type": "string"
                            },
                            "reason": {
                                "type": "string"
                            }
                        },
                        "required": ["appointment_type", "date", "start_time", "patient_name", "patient_email", "patient_phone", "reason"]
                    }
                },
                {
                    "name": "answer_faq",
                    "description": "Search the clinic knowledge base to answer questions",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The patient's question"
                            }
                        },
                        "required": ["question"]
                    }
                }
            ]

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """Execute a tool call"""
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")

        try:
            if tool_name == "check_availability":
                result = self.availability_tool.check_availability(
                    date_str=arguments['date'],
                    appointment_type=arguments['appointment_type'],
                    time_preference=arguments.get('time_preference')
                )
                return {"success": True, "data": result}

            elif tool_name == "suggest_slots":
                result = self.availability_tool.suggest_slots(
                    preferred_date=arguments.get('preferred_date'),
                    appointment_type=arguments['appointment_type'],
                    time_preference=arguments.get('time_preference'),
                    num_suggestions=arguments.get('num_suggestions', 5)
                )
                return {"success": True, "data": result}

            elif tool_name == "book_appointment":
                result = self.booking_tool.create_booking(
                    appointment_type=arguments['appointment_type'],
                    date=arguments['date'],
                    start_time=arguments['start_time'],
                    patient_name=arguments['patient_name'],
                    patient_email=arguments['patient_email'],
                    patient_phone=arguments['patient_phone'],
                    reason=arguments['reason']
                )
                return {"success": result['status'] == 'confirmed', "data": result}

            elif tool_name == "answer_faq":
                context = self.faq_rag.get_context_for_question(arguments['question'])
                return {"success": True, "data": {"context": context, "question": arguments['question']}}

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {"success": False, "error": str(e)}

    def chat(self, message: str, conversation_id: Optional[str] = None) -> Dict:
        """
        Process a chat message

        Args:
            message: User message
            conversation_id: Optional conversation ID (creates new if not provided)

        Returns:
            Dictionary with response and conversation_id
        """
        # Create or get conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            self.conversations[conversation_id] = ConversationState(
                conversation_id=conversation_id,
                phase="greeting",
                messages=[]
            )

        conversation = self.conversations.get(conversation_id)
        if not conversation:
            conversation = ConversationState(
                conversation_id=conversation_id,
                phase="greeting",
                messages=[]
            )
            self.conversations[conversation_id] = conversation

        # Add user message
        user_msg = ChatMessage(role="user", content=message)
        conversation.messages.append(user_msg)

        # Build messages for LLM
        llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for msg in conversation.messages:
            llm_messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Get tools
        tools = self._get_tool_definitions()

        # Call LLM
        response = self._call_llm(llm_messages, tools=tools)

        # Handle tool calls
        if response["tool_calls"]:
            for tool_call in response["tool_calls"]:
                tool_result = self._execute_tool(tool_call["name"], tool_call["arguments"])

                # Add tool result to conversation context
                tool_msg = f"[Tool: {tool_call['name']} executed. Result: {json.dumps(tool_result)}]"
                llm_messages.append({"role": "assistant", "content": tool_msg})

                # Get final response with tool results
                response = self._call_llm(llm_messages, tools=tools)

        # Add assistant response to conversation
        assistant_msg = ChatMessage(role="assistant", "content"=response["content"])
        conversation.messages.append(assistant_msg)

        return {
            "message": response["content"],
            "conversation_id": conversation_id,
            "metadata": {
                "phase": conversation.phase,
                "message_count": len(conversation.messages)
            }
        }
