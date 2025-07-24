"""
Jira API endpoints.

Provides REST API endpoints for Jira operations including issue management,
project status, transitions, and bulk operations.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging

from leoslab_toolkit import JiraClient
from leoslab_toolkit.common.exceptions import JiraError, AuthenticationError, ConfigurationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jira", tags=["jira"])


class IssueResponse(BaseModel):
    """Jira issue response."""
    key: str
    summary: str
    status: str
    assignee: Optional[str] = None
    created: str
    updated: str
    description: Optional[str] = None
    fields: Dict[str, Any]


class SearchResponse(BaseModel):
    """Jira search response."""
    total: int
    issues: List[IssueResponse]
    jql: str


class TransitionResponse(BaseModel):
    """Transition response."""
    issue_key: str
    transition: str
    success: bool
    message: str


class BulkTransitionResponse(BaseModel):
    """Bulk transition response."""
    total: int
    successful: List[str]
    failed: List[Dict[str, str]]
    transition: str


class ProjectStatusResponse(BaseModel):
    """Project status response."""
    project: str
    total_issues: int
    status_counts: Dict[str, int]


class CreateIssueRequest(BaseModel):
    """Create issue request."""
    project_key: str = Field(..., description="Project key (e.g., INFRA, WM)")
    summary: str = Field(..., description="Issue summary")
    description: str = Field(..., description="Issue description")
    issue_type: str = Field(default="Task", description="Issue type")
    assignee: Optional[str] = Field(None, description="Assignee account ID")


class CreateIssueResponse(BaseModel):
    """Create issue response."""
    key: str
    url: str
    success: bool


class TransitionRequest(BaseModel):
    """Transition request."""
    transition: str = Field(..., description="Transition name or ID")


class BulkTransitionRequest(BaseModel):
    """Bulk transition request."""
    issue_keys: List[str] = Field(..., description="List of issue keys to transition")
    transition: str = Field(..., description="Transition name or ID")


@router.get("/auth/test")
async def test_jira_authentication(project: Optional[str] = Query(None, description="Project key to test with")):
    """
    Test Jira authentication.
    
    Args:
        project: Optional project key to initialize client with.
        
    Returns:
        Authentication status and user information.
        
    Raises:
        HTTPException: If authentication fails.
    """
    try:
        client = JiraClient(project=project)
        
        return {
            "authenticated": True,
            "jira_url": client.jira_url,
            "email": client.email,
            "project": client.project,
            "message": "Jira authentication successful"
        }
        
    except AuthenticationError as e:
        logger.error(f"Jira authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Authentication test error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication test failed: {str(e)}")


@router.get("/issues/{issue_key}", response_model=IssueResponse)
async def get_issue(
    issue_key: str,
    expand: Optional[List[str]] = Query(None, description="Fields to expand")
):
    """
    Get issue details by key.
    
    Args:
        issue_key: Jira issue key (e.g., INFRA-123).
        expand: Optional fields to expand.
        
    Returns:
        Issue details.
        
    Raises:
        HTTPException: If issue retrieval fails.
    """
    try:
        client = JiraClient()
        issue = client.get_issue(issue_key, expand)
        
        fields = issue.get("fields", {})
        assignee = fields.get("assignee")
        
        return IssueResponse(
            key=issue["key"],
            summary=fields.get("summary", ""),
            status=fields.get("status", {}).get("name", ""),
            assignee=assignee.get("displayName") if assignee else None,
            created=fields.get("created", ""),
            updated=fields.get("updated", ""),
            description=_extract_description(fields.get("description")),
            fields=fields
        )
        
    except JiraError as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Issue {issue_key} not found")
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"Jira authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get issue {issue_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Issue retrieval failed: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_issues(
    jql: str = Body(..., description="JQL query string"),
    fields: Optional[List[str]] = Body(None, description="Fields to include"),
    max_results: int = Body(50, description="Maximum number of results")
):
    """
    Search issues using JQL.
    
    Args:
        jql: JQL query string.
        fields: Optional fields to include.
        max_results: Maximum number of results.
        
    Returns:
        Search results.
        
    Raises:
        HTTPException: If search fails.
    """
    try:
        client = JiraClient()
        results = client.search_issues(jql, fields, max_results)
        
        issues = []
        for issue in results.get("issues", []):
            fields_data = issue.get("fields", {})
            assignee = fields_data.get("assignee")
            
            issues.append(IssueResponse(
                key=issue["key"],
                summary=fields_data.get("summary", ""),
                status=fields_data.get("status", {}).get("name", ""),
                assignee=assignee.get("displayName") if assignee else None,
                created=fields_data.get("created", ""),
                updated=fields_data.get("updated", ""),
                description=_extract_description(fields_data.get("description")),
                fields=fields_data
            ))
        
        return SearchResponse(
            total=results.get("total", 0),
            issues=issues,
            jql=jql
        )
        
    except JiraError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"Jira authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to search issues: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/issues/{issue_key}/transition", response_model=TransitionResponse)
async def transition_issue(issue_key: str, request: TransitionRequest):
    """
    Transition an issue to a new status.
    
    Args:
        issue_key: Issue key to transition.
        request: Transition request with transition name/ID.
        
    Returns:
        Transition result.
        
    Raises:
        HTTPException: If transition fails.
    """
    try:
        client = JiraClient()
        client.transition_issue(issue_key, request.transition)
        
        return TransitionResponse(
            issue_key=issue_key,
            transition=request.transition,
            success=True,
            message=f"Successfully transitioned {issue_key} to {request.transition}"
        )
        
    except JiraError as e:
        if "not available" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"Jira authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to transition issue {issue_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transition failed: {str(e)}")


@router.post("/bulk-transition", response_model=BulkTransitionResponse)
async def bulk_transition_issues(request: BulkTransitionRequest):
    """
    Transition multiple issues to the same status.
    
    Args:
        request: Bulk transition request.
        
    Returns:
        Bulk transition results.
        
    Raises:
        HTTPException: If bulk transition fails.
    """
    try:
        client = JiraClient()
        results = client.bulk_transition(request.issue_keys, request.transition)
        
        return BulkTransitionResponse(
            total=results["total"],
            successful=results["successful"],
            failed=results["failed"],
            transition=request.transition
        )
        
    except JiraError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"Jira authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to bulk transition issues: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk transition failed: {str(e)}")


@router.get("/projects/{project_key}/status", response_model=ProjectStatusResponse)
async def get_project_status(project_key: str):
    """
    Get project status summary.
    
    Args:
        project_key: Project key (e.g., INFRA, WM).
        
    Returns:
        Project status with issue counts by status.
        
    Raises:
        HTTPException: If status retrieval fails.
    """
    try:
        client = JiraClient(project=project_key)
        status = client.get_project_status()
        
        return ProjectStatusResponse(
            project=status["project"],
            total_issues=status["total_issues"],
            status_counts=status["status_counts"]
        )
        
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"Jira authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get project status for {project_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")


@router.post("/issues", response_model=CreateIssueResponse)
async def create_issue(request: CreateIssueRequest):
    """
    Create a new Jira issue.
    
    Args:
        request: Issue creation request.
        
    Returns:
        Created issue information.
        
    Raises:
        HTTPException: If issue creation fails.
    """
    try:
        client = JiraClient()
        result = client.create_issue(
            project_key=request.project_key,
            summary=request.summary,
            description=request.description,
            issue_type=request.issue_type,
            assignee=request.assignee
        )
        
        issue_key = result.get("key")
        
        return CreateIssueResponse(
            key=issue_key,
            url=f"https://leoslab.atlassian.net/browse/{issue_key}",
            success=True
        )
        
    except JiraError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"Jira authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create issue: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Issue creation failed: {str(e)}")


@router.get("/issues/{issue_key}/transitions")
async def get_issue_transitions(issue_key: str):
    """
    Get available transitions for an issue.
    
    Args:
        issue_key: Issue key to get transitions for.
        
    Returns:
        Available transitions.
        
    Raises:
        HTTPException: If transition retrieval fails.
    """
    try:
        client = JiraClient()
        transitions = client.get_transitions(issue_key)
        
        return {
            "issue_key": issue_key,
            "transitions": transitions
        }
        
    except JiraError as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Issue {issue_key} not found")
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"Jira authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get transitions for {issue_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transition retrieval failed: {str(e)}")


def _extract_description(description_field: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Extract plain text from Atlassian Document Format description.
    
    Args:
        description_field: ADF description field.
        
    Returns:
        Plain text description or None.
    """
    if not description_field or not isinstance(description_field, dict):
        return None
    
    def extract_text(node):
        if isinstance(node, dict):
            if node.get('type') == 'text':
                return node.get('text', '')
            elif 'content' in node:
                return ''.join(extract_text(child) for child in node['content'])
        elif isinstance(node, list):
            return ''.join(extract_text(item) for item in node)
        return ''
    
    text = extract_text(description_field).strip()
    return text if text else None