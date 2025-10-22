#!/usr/bin/env python3
"""
dbt Guard MCP Server
Safe dbt Cloud operations with confirmation prompts and guardrails
"""

import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Load environment variables from .env file
load_dotenv()


class DbtCloudClient:
    """dbt Cloud API client with safety features"""
    
    def __init__(self):
        self.base_url = os.getenv("DBT_BASE_URL", "https://cloud.getdbt.com")
        self.api_token = os.getenv("DBT_API_TOKEN")
        self.account_id = os.getenv("DBT_ACCOUNT_ID")
        
        if not self.api_token:
            raise ValueError("DBT_API_TOKEN environment variable is required")
        if not self.account_id:
            raise ValueError("DBT_ACCOUNT_ID environment variable is required")
        
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, api_version: str = "v2", **kwargs) -> Dict:
        """Make authenticated request to dbt Cloud API
        
        Uses API v2 for job and run operations (v3 is for administrative operations)
        """
        url = f"{self.base_url}/api/{api_version}/accounts/{self.account_id}/{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                **kwargs
            )
            
            if response.status_code != 200:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")
            
            return response.json()
    
    async def get_projects(self) -> List[Dict]:
        """Get all projects"""
        response = await self._make_request("GET", "projects/")
        return response.get("data", [])
    
    async def get_jobs(self, project_id: Optional[int] = None) -> List[Dict]:
        """Get jobs (filtered by project if specified)"""
        endpoint = "jobs/"
        if project_id:
            endpoint += f"?project_id={project_id}"
        
        response = await self._make_request("GET", endpoint)
        return response.get("data", [])
    
    async def get_runs(self, job_id: Optional[int] = None, project_id: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Get runs for a job or project"""
        params = {"limit": limit}
        if job_id:
            params["job_definition_id"] = job_id
        if project_id:
            params["project_id"] = project_id
        
        response = await self._make_request("GET", "runs/", params=params)
        return response.get("data", [])
    
    async def trigger_job(self, job_id: int, cause: str = "Triggered via MCP") -> Dict:
        """Trigger a dbt Cloud job"""
        payload = {
            "cause": cause
        }
        
        response = await self._make_request("POST", f"jobs/{job_id}/run/", json=payload)
        return response.get("data", {})
    
    async def search_in_project(self, query: str, project_id: int) -> Dict:
        """Search for artifacts in a project (simplified approach)"""
        # Get jobs for the project
        jobs = await self.get_jobs(project_id)
        
        # Get recent runs to find artifacts
        runs = await self.get_runs(project_id=project_id, limit=5)
        
        results = {
            "query": query,
            "project_id": project_id,
            "jobs": [],
            "recent_runs": []
        }
        
        # Filter jobs by query
        for job in jobs:
            if (query.lower() in job.get("name", "").lower() or 
                query.lower() in job.get("description", "").lower()):
                results["jobs"].append(job)
        
        # Add recent runs info
        results["recent_runs"] = runs[:3]  # Show last 3 runs
        
        return results


# Initialize the server and client
server = Server("dbt-guard-mcp")
dbt_client = DbtCloudClient()


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="search_in_project", 
            description="Search for jobs and artifacts in a dbt project",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for job names or descriptions"
                    },
                    "project_id": {
                        "type": "integer", 
                        "description": "Project ID to search in (use 351878080626727 for snowflake)",
                        "default": 351878080626727
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_recent_runs",
            description="Get recent job runs for a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID (default: snowflake project)",
                        "default": 351878080626727
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of runs to retrieve",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                }
            }
        ),
        Tool(
            name="preview_model",
            description="Preview model data (safe read-only operation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID"
                    },
                    "model_name": {
                        "type": "string",
                        "description": "Model name"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of rows to preview",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["project_id", "model_name"]
            }
        ),
        Tool(
            name="trigger_job_with_confirmation",
            description="Trigger a dbt Cloud job (REQUIRES EXPLICIT CONFIRMATION - potentially dangerous)",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "integer",
                        "description": "Job ID to trigger"
                    },
                    "cause": {
                        "type": "string",
                        "description": "Reason for triggering the job",
                        "default": "Triggered via MCP"
                    },
                    "confirm_execution": {
                        "type": "boolean",
                        "description": "REQUIRED: Must be true to confirm you want to execute this potentially dangerous operation",
                        "default": False
                    }
                },
                "required": ["job_id", "confirm_execution"]
            }
        ),
        Tool(
            name="list_projects",
            description="List all available dbt projects",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="list_jobs",
            description="List dbt jobs (optionally filtered by project)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Optional project ID to filter jobs"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls with safety checks"""
    
    try:
        if name == "search_in_project":
            return await search_in_project(arguments)
        elif name == "get_recent_runs":
            return await get_recent_runs(arguments)
        elif name == "preview_model":
            return await preview_model(arguments)
        elif name == "trigger_job_with_confirmation":
            return await trigger_job_with_confirmation(arguments)
        elif name == "list_projects":
            return await list_projects(arguments)
        elif name == "list_jobs":
            return await list_jobs(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def search_in_project(arguments: Dict[str, Any]) -> List[TextContent]:
    """Search for jobs and artifacts in a project"""
    query = arguments["query"]
    project_id = arguments.get("project_id", 351878080626727)  # Default to snowflake
    
    results = await dbt_client.search_in_project(query, project_id)
    
    result_text = f"Search results for '{query}' in project {project_id}:\n\n"
    
    # Show matching jobs
    jobs = results.get("jobs", [])
    if jobs:
        result_text += f"**Matching Jobs ({len(jobs)}):**\n"
        for job in jobs:
            result_text += f"  - **{job['name']}** (ID: {job['id']})\n"
            if job.get('description'):
                result_text += f"    Description: {job['description']}\n"
            result_text += f"    Environment: {job.get('environment_id', 'N/A')}\n"
            result_text += f"    State: {job.get('state', 'Unknown')}\n"
            result_text += "\n"
    else:
        result_text += f"**No jobs found matching '{query}'**\n\n"
    
    # Show recent runs
    runs = results.get("recent_runs", [])
    if runs:
        result_text += f"**Recent Runs (last {len(runs)}):**\n"
        for run in runs:
            result_text += f"  - Run ID: {run['id']}\n"
            result_text += f"    Job: {run.get('job', {}).get('name', 'Unknown')}\n"
            result_text += f"    Status: {run.get('status_humanized', 'Unknown')}\n"
            result_text += f"    Started: {run.get('created_at', 'N/A')}\n"
            result_text += "\n"
    
    return [TextContent(type="text", text=result_text)]


async def get_recent_runs(arguments: Dict[str, Any]) -> List[TextContent]:
    """Get recent runs for a project"""
    project_id = arguments.get("project_id", 351878080626727)  # Default to snowflake
    limit = arguments.get("limit", 10)
    
    runs = await dbt_client.get_runs(project_id=project_id, limit=limit)
    
    if not runs:
        return [TextContent(type="text", text=f"No recent runs found for project {project_id}")]
    
    result_text = f"Recent Runs for Project {project_id} (last {len(runs)}):\n\n"
    
    for run in runs:
        result_text += f"**Run ID: {run['id']}**\n"
        result_text += f"  Job: {run.get('job', {}).get('name', 'Unknown')}\n"
        result_text += f"  Status: {run.get('status_humanized', 'Unknown')}\n"
        result_text += f"  Started: {run.get('created_at', 'N/A')}\n"
        result_text += f"  Finished: {run.get('finished_at', 'N/A')}\n"
        if run.get('trigger', {}).get('cause'):
            result_text += f"  Trigger: {run['trigger']['cause']}\n"
        result_text += "\n"
    
    return [TextContent(type="text", text=result_text)]


async def preview_model(arguments: Dict[str, Any]) -> List[TextContent]:
    """Preview model data (safe operation)"""
    project_id = arguments["project_id"]
    model_name = arguments["model_name"]
    limit = arguments.get("limit", 100)
    
    preview_data = await dbt_client.preview_model(project_id, model_name, limit)
    
    result_text = f"🔍 Model Preview: {model_name}\n\n"
    result_text += f"✅ This is a SAFE read-only operation\n\n"
    result_text += f"**Model Information:**\n"
    result_text += f"  Name: {preview_data['model']['name']}\n"
    result_text += f"  ID: {preview_data['model']['id']}\n"
    result_text += f"  Package: {preview_data['model'].get('package_name', 'N/A')}\n"
    result_text += f"  Limit: {limit} rows\n\n"
    result_text += f"**Note:** {preview_data['preview_note']}\n"
    result_text += f"**Warning:** {preview_data['warning']}\n"
    
    return [TextContent(type="text", text=result_text)]


async def trigger_job_with_confirmation(arguments: Dict[str, Any]) -> List[TextContent]:
    """Trigger job with confirmation requirement"""
    job_id = arguments["job_id"]
    cause = arguments.get("cause", "Triggered via MCP")
    confirm_execution = arguments.get("confirm_execution", False)
    
    if not confirm_execution:
        result_text = f"🚨 **DANGEROUS OPERATION BLOCKED** 🚨\n\n"
        result_text += f"You attempted to trigger job ID {job_id} without confirmation.\n\n"
        result_text += f"**This operation would:**\n"
        result_text += f"  - Trigger dbt Cloud job: {job_id}\n"
        result_text += f"  - Cause: {cause}\n"
        result_text += f"  - Potentially run dbt models and modify data in your data warehouse\n"
        result_text += f"  - Consume compute resources and may incur costs\n\n"
        result_text += f"**To proceed, you MUST:**\n"
        result_text += f"  1. Understand the risks of this operation\n"
        result_text += f"  2. Set 'confirm_execution' to true\n"
        result_text += f"  3. Re-run this command\n\n"
        result_text += f"⚠️  **WARNING: This will execute actual dbt operations that may modify your data!**\n"
        
        return [TextContent(type="text", text=result_text)]
    
    # If confirmed, proceed with the operation
    try:
        run_result = await dbt_client.trigger_job(job_id, cause)
        
        result_text = f"✅ **JOB TRIGGERED SUCCESSFULLY** ✅\n\n"
        result_text += f"**Job Details:**\n"
        result_text += f"  - Job ID: {job_id}\n"
        result_text += f"  - Run ID: {run_result.get('id', 'N/A')}\n"
        result_text += f"  - Status: {run_result.get('status_humanized', 'Unknown')}\n"
        result_text += f"  - Cause: {cause}\n\n"
        result_text += f"**Monitor the run in dbt Cloud dashboard for progress and results.**\n"
        
        return [TextContent(type="text", text=result_text)]
        
    except Exception as e:
        result_text = f"❌ **JOB TRIGGER FAILED** ❌\n\n"
        result_text += f"Failed to trigger job {job_id}: {str(e)}\n"
        return [TextContent(type="text", text=result_text)]


async def list_projects(arguments: Dict[str, Any]) -> List[TextContent]:
    """List all projects"""
    projects = await dbt_client.get_projects()
    
    if not projects:
        return [TextContent(type="text", text="No projects found")]
    
    result_text = f"Available dbt Projects ({len(projects)}):\n\n"
    
    for project in projects:
        result_text += f"**{project['name']}**\n"
        result_text += f"  ID: {project['id']}\n"
        result_text += f"  State: {project.get('state', 'Unknown')}\n"
        if project.get('repository_name'):
            result_text += f"  Repository: {project['repository_name']}\n"
        result_text += "\n"
    
    return [TextContent(type="text", text=result_text)]


async def list_jobs(arguments: Dict[str, Any]) -> List[TextContent]:
    """List jobs"""
    project_id = arguments.get("project_id")
    
    # Use the get_jobs method that we know exists
    if project_id:
        endpoint = f"jobs/?project_id={project_id}"
    else:
        endpoint = "jobs/"
    
    response = await dbt_client._make_request("GET", endpoint)
    jobs = response.get("data", [])
    
    if not jobs:
        filter_text = f" for project {project_id}" if project_id else ""
        return [TextContent(type="text", text=f"No jobs found{filter_text}")]
    
    filter_text = f" (filtered by project {project_id})" if project_id else ""
    result_text = f"Available dbt Jobs{filter_text} ({len(jobs)}):\n\n"
    
    for job in jobs:
        result_text += f"**{job['name']}**\n"
        result_text += f"  ID: {job['id']}\n"
        result_text += f"  Project ID: {job.get('project_id', 'N/A')}\n"
        result_text += f"  Environment ID: {job.get('environment_id', 'N/A')}\n"
        result_text += f"  State: {job.get('state', 'Unknown')}\n"
        if job.get('description'):
            result_text += f"  Description: {job['description']}\n"
        result_text += "\n"
    
    return [TextContent(type="text", text=result_text)]


async def main():
    """Main server function"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())