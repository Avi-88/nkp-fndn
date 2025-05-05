from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import asyncio
from fastapi.templating import Jinja2Templates


app = FastAPI()

templates = Jinja2Templates(directory="templates")

def handle_command_creation(deployment: dict):
    flags = {
        # Control plane

        "cluster-name": {"required": True},
        "control-plane-endpoint-ip": {"required": True},
        "control-plane-prism-element-cluster": {"required": True},
        "control-plane-subnets": {"required": True},
        "control-plane-vm-image": {"required": True},
        # "control-plane-cores-per-vcpu": {"required": False},
        # "control-plane-disk-size": {"required": False},
        # "control-plane-endpoint-port": {"required": False},
        # "control-plane-memory": {"required": False},
        # "control-plane-pc-project": {"required": False},
        # "control-plane-vcpus": {"required": False},
        # "control-plane-replicas": {"required": False},

        
        # CSI

        "csi-storage-container":{"required": True},
        
        # Endpoint for Prism central

        "endpoint": {"required": True},

        # Kubernetes

        "kubernetes-service-load-balancer-ip-range": {"required": True},
        # "kubernetes-pod-network-cidr": {"required": False},
        # "kubernetes-service-cidr": {"required": False},
        # "kubernetes-version": {"required": False},
        # "namespace": {"required": False},
        
        # Registry

        # "registry-cacert": {"required": False},
        # "registry-mirror-cacert": {"required": False},
        # "registry-mirror-password": {"required": False},
        # "registry-mirror-url": {"required": False},
        # "registry-mirror-username": {"required": False},
        "registry-password": {"required": True},
        "registry-url": {"required": True},
        "registry-username": {"required": True},
        
        # Cluster management

        # "ssh-public-key-file":{"required": False},
        # "ssh-username": {"required": False},

        # Timeout

        # "timeout":{"required": False},

        # VM image

        "vm-image": {"required": True},

        # Worker

        # "worker-cores-per-vcpu":{"required": False},
        # "worker-disk-size": {"required": False},
        # "worker-memory": {"required": False},
        # "worker-pc-categories": {"required": False},
        # "worker-pc-project": {"required": False},
        # "worker-replicas": {"required": False},
        # "worker-vcpus": {"required": False},
        "worker-prism-element-cluster": {"required": True},
        "worker-subnets": {"required": True},
        "worker-vm-image":{"required": True},
    }
    missing = [flag for flag, prop in flags.items() if prop["required"] and flag not in deployment]

    if "vm-image" in deployment:
        missing = [m for m in missing if m not in ("worker-vm-image", "control-plane-vm-image")]

    # Remove "vm-image" from missing if both "worker-vm-image" and "control-plane-vm-image" are present
    elif "worker-vm-image" in deployment and "control-plane-vm-image" in deployment:
        if "vm-image" in missing:
            missing.remove("vm-image")

    if missing:
        raise ValueError(f"Missing required flags: {" ".join(missing)}")

    # Step 2: Build the command
    base_command = ["nkp", "create", "cluster", "nutanix "]  # Example
    for flag, value in deployment.items():
        base_command.append(f"--{flag}={value}")

    base_command.append("--insecure")
    base_command.append("--self-managed")

    # Final command string
    final_command = " ".join(base_command) 
    print(final_command)
    return final_command

def deploy_cluster(command: str):
    try:
        async def command_stream():
            try:
                # Open the file for writing
                # with open("deployment.log", 'w') as file:
                    # Create the process
                cmd = ["bash", "-c", command]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                # Yield SSE format for start message
                yield f"data: Command started: {' '.join(command)}"
                
                # Read output line by line
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    
                    # Decode the line
                    line_str = line.decode('utf-8')
                    
                    # Write to file
                    # file.write(line_str)
                    # file.flush()
                    
                    # Yield in SSE format
                    yield f"data: {line_str.strip()}\n\n"
                    
                stderr_data = await process.stderr.read()
                if stderr_data:
                    yield f"ERROR: {stderr_data.decode('utf-8')}"
                
                # Wait for the process to complete
                return_code = await process.wait()
                
                # Yield completion message with return code
                yield f"data: Command completed with return code: {return_code}\n\n"
                yield f"data: Output saved to deployment.log\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"Exception occurred: {str(e)}"

        return StreamingResponse(
            command_stream(),
            media_type="text/event-stream"
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/")
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/deploy/management")
def handle_deployment(deployment: dict):
    command = handle_command_creation(deployment)
    return deploy_cluster(command)