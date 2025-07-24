"""
Infrastructure API endpoints.

Provides REST API endpoints for infrastructure management including
Kubernetes, Terraform, and Ansible operations.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging

from leoslab_toolkit import KubernetesClient, TerraformClient, AnsibleClient
from leoslab_toolkit.common.exceptions import InfrastructureError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])


class ClusterInfoResponse(BaseModel):
    """Kubernetes cluster info response."""
    cluster_info: str
    nodes: List[Dict[str, Any]]
    namespaces: List[str]
    current_context: str
    current_namespace: str


class PodResponse(BaseModel):
    """Kubernetes pod response."""
    name: str
    namespace: str
    status: str
    node: Optional[str] = None
    ready: bool
    restarts: int
    age: str


class TerraformPlanRequest(BaseModel):
    """Terraform plan request."""
    working_dir: str = Field(..., description="Terraform working directory")
    var_file: Optional[str] = Field(None, description="Variables file path")
    targets: Optional[List[str]] = Field(None, description="Specific resources to target")


class TerraformApplyRequest(BaseModel):
    """Terraform apply request."""
    working_dir: str = Field(..., description="Terraform working directory")
    var_file: Optional[str] = Field(None, description="Variables file path")
    plan_file: Optional[str] = Field(None, description="Plan file to apply")
    auto_approve: bool = Field(False, description="Auto-approve changes")
    targets: Optional[List[str]] = Field(None, description="Specific resources to target")


class AnsiblePlaybookRequest(BaseModel):
    """Ansible playbook request."""
    playbook_path: str = Field(..., description="Path to playbook file")
    inventory_file: Optional[str] = Field(None, description="Inventory file path")
    limit: Optional[str] = Field(None, description="Limit to specific hosts")
    tags: Optional[List[str]] = Field(None, description="Tags to run")
    extra_vars: Optional[Dict[str, Any]] = Field(None, description="Extra variables")
    check_mode: bool = Field(False, description="Run in check mode")


# Kubernetes endpoints
@router.get("/k8s/cluster", response_model=ClusterInfoResponse)
async def get_cluster_info(
    context: Optional[str] = Query(None, description="Kubernetes context"),
    namespace: str = Query("default", description="Default namespace")
):
    """
    Get Kubernetes cluster information.
    
    Args:
        context: Optional kubernetes context.
        namespace: Default namespace.
        
    Returns:
        Cluster information including nodes and namespaces.
        
    Raises:
        HTTPException: If cluster access fails.
    """
    try:
        client = KubernetesClient(context=context, namespace=namespace)
        cluster_info = client.get_cluster_info()
        
        return ClusterInfoResponse(**cluster_info)
        
    except InfrastructureError as e:
        logger.error(f"Failed to get cluster info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting cluster info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cluster access failed: {str(e)}")


@router.get("/k8s/pods")
async def get_pods(
    namespace: Optional[str] = Query(None, description="Namespace to query"),
    label_selector: Optional[str] = Query(None, description="Label selector")
):
    """
    Get pods in namespace.
    
    Args:
        namespace: Namespace to query.
        label_selector: Label selector for filtering.
        
    Returns:
        List of pods.
        
    Raises:
        HTTPException: If pod retrieval fails.
    """
    try:
        client = KubernetesClient()
        pods = client.get_pods(namespace=namespace, label_selector=label_selector)
        
        # Transform pods for response
        pod_list = []
        for pod in pods:
            metadata = pod.get("metadata", {})
            status = pod.get("status", {})
            
            # Calculate ready status
            ready = False
            restarts = 0
            if "containerStatuses" in status:
                ready = all(cs.get("ready", False) for cs in status["containerStatuses"])
                restarts = sum(cs.get("restartCount", 0) for cs in status["containerStatuses"])
            
            pod_list.append({
                "name": metadata.get("name", ""),
                "namespace": metadata.get("namespace", ""),
                "status": status.get("phase", "Unknown"),
                "node": status.get("hostIP"),
                "ready": ready,
                "restarts": restarts,
                "age": metadata.get("creationTimestamp", ""),
                "full_spec": pod
            })
        
        return {"pods": pod_list}
        
    except InfrastructureError as e:
        logger.error(f"Failed to get pods: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting pods: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pod retrieval failed: {str(e)}")


@router.get("/k8s/pods/{pod_name}/logs")
async def get_pod_logs(
    pod_name: str,
    namespace: Optional[str] = Query(None, description="Pod namespace"),
    container: Optional[str] = Query(None, description="Container name"),
    lines: int = Query(100, description="Number of lines to retrieve")
):
    """
    Get logs from a pod.
    
    Args:
        pod_name: Name of the pod.
        namespace: Pod namespace.
        container: Container name for multi-container pods.
        lines: Number of lines to retrieve.
        
    Returns:
        Pod logs.
        
    Raises:
        HTTPException: If log retrieval fails.
    """
    try:
        client = KubernetesClient()
        logs = client.get_logs(
            pod_name=pod_name,
            namespace=namespace,
            container=container,
            lines=lines
        )
        
        return {
            "pod_name": pod_name,
            "namespace": namespace or "default",
            "container": container,
            "lines": lines,
            "logs": logs
        }
        
    except InfrastructureError as e:
        logger.error(f"Failed to get logs for pod {pod_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Log retrieval failed: {str(e)}")


# Terraform endpoints
@router.post("/terraform/plan")
async def terraform_plan(request: TerraformPlanRequest):
    """
    Create a Terraform execution plan.
    
    Args:
        request: Terraform plan request.
        
    Returns:
        Plan execution results.
        
    Raises:
        HTTPException: If plan creation fails.
    """
    try:
        client = TerraformClient(
            working_dir=request.working_dir,
            var_file=request.var_file
        )
        
        # Initialize first
        client.init()
        
        # Create plan
        result = client.plan(targets=request.targets, detailed_exitcode=True)
        
        return {
            "working_dir": request.working_dir,
            "success": result["success"],
            "output": result["stdout"],
            "errors": result["stderr"],
            "has_changes": result["returncode"] == 2
        }
        
    except InfrastructureError as e:
        logger.error(f"Terraform plan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in terraform plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Terraform plan failed: {str(e)}")


@router.post("/terraform/apply")
async def terraform_apply(request: TerraformApplyRequest):
    """
    Apply Terraform configuration.
    
    Args:
        request: Terraform apply request.
        
    Returns:
        Apply execution results.
        
    Raises:
        HTTPException: If apply fails.
    """
    try:
        client = TerraformClient(
            working_dir=request.working_dir,
            var_file=request.var_file
        )
        
        result = client.apply(
            plan_file=request.plan_file,
            auto_approve=request.auto_approve,
            targets=request.targets
        )
        
        return {
            "working_dir": request.working_dir,
            "success": result["success"],
            "output": result["stdout"],
            "errors": result["stderr"]
        }
        
    except InfrastructureError as e:
        logger.error(f"Terraform apply failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in terraform apply: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Terraform apply failed: {str(e)}")


@router.get("/terraform/{working_dir}/output")
async def terraform_output(working_dir: str):
    """
    Get Terraform outputs.
    
    Args:
        working_dir: Terraform working directory.
        
    Returns:
        Terraform outputs.
        
    Raises:
        HTTPException: If output retrieval fails.
    """
    try:
        client = TerraformClient(working_dir=working_dir)
        outputs = client.output()
        
        return {
            "working_dir": working_dir,
            "outputs": outputs
        }
        
    except InfrastructureError as e:
        logger.error(f"Failed to get terraform outputs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting terraform outputs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Output retrieval failed: {str(e)}")


# Ansible endpoints
@router.post("/ansible/playbook")
async def run_ansible_playbook(request: AnsiblePlaybookRequest):
    """
    Run an Ansible playbook.
    
    Args:
        request: Ansible playbook request.
        
    Returns:
        Playbook execution results.
        
    Raises:
        HTTPException: If playbook execution fails.
    """
    try:
        client = AnsibleClient(inventory_file=request.inventory_file)
        
        result = client.run_playbook(
            playbook_path=request.playbook_path,
            limit=request.limit,
            tags=request.tags,
            extra_vars=request.extra_vars,
            check_mode=request.check_mode
        )
        
        return {
            "playbook_path": request.playbook_path,
            "success": result["success"],
            "output": result["stdout"],
            "errors": result["stderr"],
            "check_mode": request.check_mode
        }
        
    except InfrastructureError as e:
        logger.error(f"Ansible playbook failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error running ansible playbook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Playbook execution failed: {str(e)}")


@router.post("/ansible/ping")
async def ansible_ping(
    hosts: str = Body("all", description="Host pattern to ping"),
    inventory_file: Optional[str] = Body(None, description="Inventory file path")
):
    """
    Ping hosts using Ansible.
    
    Args:
        hosts: Host pattern to ping.
        inventory_file: Optional inventory file.
        
    Returns:
        Ping results.
        
    Raises:
        HTTPException: If ping fails.
    """
    try:
        client = AnsibleClient(inventory_file=inventory_file)
        result = client.ping_hosts(hosts)
        
        return {
            "hosts": hosts,
            "success": result["success"],
            "output": result["stdout"],
            "errors": result["stderr"]
        }
        
    except InfrastructureError as e:
        logger.error(f"Ansible ping failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in ansible ping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ping failed: {str(e)}")


@router.get("/ansible/inventory")
async def check_ansible_inventory(inventory_file: Optional[str] = Query(None, description="Inventory file path")):
    """
    Check Ansible inventory.
    
    Args:
        inventory_file: Optional inventory file path.
        
    Returns:
        Inventory information.
        
    Raises:
        HTTPException: If inventory check fails.
    """
    try:
        client = AnsibleClient(inventory_file=inventory_file)
        result = client.check_inventory()
        
        return {
            "inventory_file": inventory_file,
            "success": result["success"],
            "inventory": result.get("inventory", {}),
            "errors": result["stderr"]
        }
        
    except InfrastructureError as e:
        logger.error(f"Ansible inventory check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error checking ansible inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Inventory check failed: {str(e)}")