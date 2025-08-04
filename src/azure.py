"""
Azure AI Agent interface module.
Provides high-level functions for interacting with Azure AI Agents.
"""

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
from typing import List, Dict, Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class AzureAgentClient:
    """High-level interface for Azure AI Agent interactions."""
    
    def __init__(self, endpoint: str, agent_id: str):
        """
        Initialize the Azure Agent client.
        
        Args:
            endpoint: Azure AI project endpoint URL
            agent_id: ID of the Azure AI agent to use
        """
        self.endpoint = endpoint
        self.agent_id = agent_id
        
        # Initialize the project client
        self.project = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=endpoint
        )
        
        # Store active thread
        self.current_thread = None
        
        # We'll get the agent lazily
        self._agent = None
    
    async def _get_agent(self):
        """Get the agent asynchronously, caching the result."""
        if self._agent is None:
            try:
                self._agent = await self.project.agents.get_agent(self.agent_id)
                logger.info(f"Successfully connected to agent: {self.agent_id}")
            except Exception as e:
                logger.error(f"Failed to connect to agent {self.agent_id}: {e}")
                raise
        return self._agent
    
    async def create_new_conversation(self) -> str:
        """
        Create a new conversation thread.
        
        Returns:
            Thread ID of the new conversation
        """
        try:
            self.current_thread = await self.project.agents.threads.create()
            logger.info(f"Created new thread: {self.current_thread.id}")
            return self.current_thread.id
        except Exception as e:
            logger.error(f"Failed to create thread: {e}")
            raise
    
    async def send_message(self, content: str, thread_id: Optional[str] = None) -> Dict[str, str]:
        """
        Send a message to the agent and get the response.
        
        Args:
            content: Message content to send
            thread_id: Optional thread ID. If not provided, uses current thread.
        
        Returns:
            Dictionary with 'status', 'response', and optionally 'error'
        """
        # Use provided thread_id or current thread
        if thread_id:
            target_thread_id = thread_id
        elif self.current_thread:
            target_thread_id = self.current_thread.id
        else:
            # Create new thread if none exists
            await self.create_new_conversation()
            target_thread_id = self.current_thread.id if self.current_thread else None
            if not target_thread_id:
                return {
                    "status": "error",
                    "error": "Failed to create conversation thread",
                    "response": "Sorry, I couldn't start a new conversation. Please try again."
                }
        
        try:
            # Create the user message
            message = await self.project.agents.messages.create(
                thread_id=target_thread_id,
                role="user",
                content=content
            )
            logger.info(f"Sent message to thread {target_thread_id}")
            
            # Get the agent
            agent = await self._get_agent()
            
            # Run the agent using the async method
            run = await self.project.agents.runs.create_and_process(
                thread_id=target_thread_id,
                agent_id=agent.id
            )
            
            if run.status == "failed":
                error_msg = f"Agent run failed: {run.last_error}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error": error_msg,
                    "response": "Sorry, I encountered an error while processing your request."
                }
            
            # Get the response messages
            messages = self.project.agents.messages.list(
                thread_id=target_thread_id, 
                order=ListSortOrder.ASCENDING
            )
            
            # Find the latest assistant response
            latest_response = None
            async for msg in messages:
                if msg.role == "assistant" and msg.text_messages:
                    latest_response = msg.text_messages[-1].text.value
            
            if latest_response:
                logger.info("Successfully got agent response")
                return {
                    "status": "success",
                    "response": latest_response
                }
            else:
                return {
                    "status": "error",
                    "error": "No response received from agent",
                    "response": "I'm sorry, I didn't receive a proper response. Please try again."
                }
                
        except Exception as e:
            error_msg = f"Error communicating with agent: {e}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "response": "Sorry, I encountered an error while processing your request."
            }
    
    async def get_conversation_history(self, thread_id: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get the conversation history for a thread.
        
        Args:
            thread_id: Optional thread ID. If not provided, uses current thread.
        
        Returns:
            List of messages with 'role' and 'content' keys
        """
        # Use provided thread_id or current thread
        if thread_id:
            target_thread_id = thread_id
        elif self.current_thread:
            target_thread_id = self.current_thread.id
        else:
            return []
        
        try:
            messages = self.project.agents.messages.list(
                thread_id=target_thread_id,
                order=ListSortOrder.ASCENDING
            )
            
            history = []
            async for msg in messages:
                if msg.text_messages:
                    history.append({
                        "role": msg.role,
                        "content": msg.text_messages[-1].text.value
                    })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    async def send_message_streaming(self, content: str, thread_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Send a message to the agent and stream the response using the Azure async APIs.
        
        Args:
            content: Message content to send
            thread_id: Optional thread ID. If not provided, uses current thread.
        
        Yields:
            Chunks of the response as they become available
        """
        # Use provided thread_id or current thread
        if thread_id:
            target_thread_id = thread_id
        elif self.current_thread:
            target_thread_id = self.current_thread.id
        else:
            # Create new thread if none exists
            await self.create_new_conversation()
            target_thread_id = self.current_thread.id if self.current_thread else None
            if not target_thread_id:
                error_msg = "Sorry, I couldn't start a new conversation. Please try again."
                yield error_msg
                return
        
        try:
            # Create the user message
            message = await self.project.agents.messages.create(
                thread_id=target_thread_id,
                role="user",
                content=content
            )
            logger.info(f"Sent message to thread {target_thread_id}")
            
            # Get the agent
            agent = await self._get_agent()
            
            # Use the async create_and_process method which handles the run lifecycle
            run = await self.project.agents.runs.create_and_process(
                thread_id=target_thread_id,
                agent_id=agent.id
            )
            
            if run.status == "failed":
                error_msg = f"Sorry, I encountered an error while processing your request: {run.last_error}"
                logger.error(f"Agent run failed: {run.last_error}")
                yield error_msg
                return
            
            # Get the response messages
            messages = self.project.agents.messages.list(
                thread_id=target_thread_id, 
                order=ListSortOrder.ASCENDING
            )
            
            # Find the latest assistant response
            latest_response = None
            async for msg in messages:
                if msg.role == "assistant" and msg.text_messages:
                    latest_response = msg.text_messages[-1].text.value
            
            if latest_response:
                logger.info("Successfully got agent response, streaming...")
                yield latest_response
            else:
                error_msg = "I'm sorry, I didn't receive a proper response. Please try again."
                yield error_msg
                
        except Exception as e:
            error_msg = f"Sorry, I encountered an error while processing your request: {str(e)}"
            logger.error(f"Error communicating with agent: {e}")
            yield error_msg


# Default configuration based on snippet.py
DEFAULT_ENDPOINT = "https://hackathon-group7-resource.services.ai.azure.com/api/projects/hackathon-group7"
DEFAULT_AGENT_ID = "asst_Npta2BcwtSASqC4SLTHSsQUZ"

# Global client instance
_client = None

async def get_azure_client() -> AzureAgentClient:
    """Get or create the global Azure client instance."""
    global _client
    if _client is None:
        _client = AzureAgentClient(DEFAULT_ENDPOINT, DEFAULT_AGENT_ID)
    return _client

async def send_message_to_agent_async(content: str) -> str:
    """
    Async function to send a message to the Azure agent.
    
    Args:
        content: Message to send
    
    Returns:
        Agent's response as a string
    """
    client = await get_azure_client()
    result = await client.send_message(content)
    return result["response"]

async def create_new_conversation_async() -> str:
    """Create a new conversation and return the thread ID."""
    client = await get_azure_client()
    return await client.create_new_conversation()

async def send_message_to_agent_streaming(content: str) -> AsyncGenerator[str, None]:
    """
    Simple async function to send a message to the Azure agent and stream the response.
    
    Args:
        content: Message to send
    
    Yields:
        Chunks of the agent's response as they become available
    """
    client = await get_azure_client()
    async for chunk in client.send_message_streaming(content):
        yield chunk
