from typing import Optional, Dict, Any, Union
from playwright.async_api import Page
from pydantic import BaseModel

class StagehandPage:
    """Wrapper around Playwright Page that integrates with Stagehand server"""
    
    def __init__(self, page: Page, stagehand_client):
        self.page = page
        self._stagehand = stagehand_client
        
    async def goto(self, url: str, **kwargs):
        """Navigate to URL using Playwright directly"""
        return await self.page.goto(url, **kwargs)

    async def navigate(
        self, 
        url: str, 
        *, 
        referer: Optional[str] = None,
        timeout: Optional[int] = None, 
        wait_until: Optional[str] = None
    ):
        """
        Navigate to URL using Stagehand server
        
        Args:
            url: The URL to navigate to
            referer: Optional referer URL
            timeout: Optional navigation timeout in milliseconds
            wait_until: Optional wait until condition ('load'|'domcontentloaded'|'networkidle'|'commit')
        """
        options = {}
        if referer is not None:
            options["referer"] = referer
        if timeout is not None:
            options["timeout"] = timeout
        if wait_until is not None:
            options["waitUntil"] = wait_until
            
        payload = {"url": url}
        if options:
            payload["options"] = options
            
        return await self._stagehand._execute("navigate", payload)
    
    async def act(self, action: str):
        """Execute AI action via Stagehand server"""
        return await self._stagehand._execute("act", [{"action": action}])
        
    async def observe(self, options: Optional[Dict[str, Any]] = None):
        """Make AI observation via Stagehand server"""
        return await self._stagehand._execute("observe", [options or {}])
        
    async def extract(self, instruction: str, schema: Union[Dict[str, Any], type(BaseModel)], **kwargs):
        """Extract data using AI via Stagehand server"""
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            schema_definition = schema.schema()
        elif isinstance(schema, dict):
            schema_definition = schema
        else:
            raise ValueError("schema must be a dict or Pydantic model class")
            
        args = {"instruction": instruction, "schemaDefinition": schema_definition}
        args.update(kwargs)
        return await self._stagehand._execute("extract", [args])

    # Forward other Page methods to underlying Playwright page
    def __getattr__(self, name):
        return getattr(self.page, name)