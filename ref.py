# app.py
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, Optional, List
import subprocess
import uuid
import time
from datetime import datetime
import os
import re
from pydantic import BaseModel
import asyncio
import uvicorn
from sqlalchemy import create_engine, Column, String, Integer, JSON, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session


# Database setup
SQLALCHEMY_DATABASE_URL = "postgresql://username:password@localhost/cli_wrapper_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="pending")
    command = Column(String)
    parameters = Column(JSON)
    stdout = Column(Text, default="")
    stderr = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    progress = Column(Integer, default=0)
    exit_code = Column(Integer, nullable=True)

Base.metadata.create_all(bind=engine)

# Models
class DeploymentRequest(BaseModel):
    cluster_name: str
    node_count: int
    flags: Optional[Dict[str, Any]] = {}

class JobStatus(BaseModel):
    id: str
    status: str
    command: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    progress: int = 0
    exit_code: Optional[int] = None

# FastAPI app
app = FastAPI(title="CLI Wrapper API")

# Add static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# In-memory job tracker (for quick access)
jobs_cache = {}

# CLI execution function
async def run_cli_command(job_id: str, command: str, db: Session):
    try:
        # Update job status to running
        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = "running"
        db.commit()
        
        # Execute command
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Process stdout in real-time
        while True:
            line = await process.stdout.readline()
            if not line:
                break
                
            line_str = line.decode('utf-8')
            
            # Update job stdout
            job = db.query(Job).filter(Job.id == job_id).first()
            job.stdout += line_str
            
            # Parse progress if possible
            progress = parse_progress_from_output(line_str)
            if progress is not None:
                job.progress = progress
                
            db.commit()
        
        # Wait for process to complete
        stdout, stderr = await process.communicate()
        
        # Update final status
        job = db.query(Job).filter(Job.id == job_id).first()
        job.stderr += stderr.decode('utf-8')
        job.exit_code = process.returncode
        job.status = "completed" if process.returncode == 0 else "failed"
        db.commit()
        
    except Exception as e:
        # Update job with error
        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = "failed"
        job.stderr += f"Internal error: {str(e)}"
        job.exit_code = -1
        db.commit()

def parse_progress_from_output(output: str) -> Optional[int]:
    """Parse progress information from CLI output"""
    # Example pattern: "Progress: 45%" or similar
    progress_match = re.search(r'Progress:\s*(\d+)%', output)
    if progress_match:
        return int(progress_match.group(1))
    
    # You may need different patterns depending on your CLI's output format
    return None

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/create", response_class=HTMLResponse)
async def create_form(request: Request):
    return templates.TemplateResponse("create_deployment.html", {"request": request})

@app.post("/api/deploy")
async def deploy_cluster(
    deployment: DeploymentRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Construct command with proper escaping
    command = f"nkp create cluster --name {deployment.cluster_name} --node-count {deployment.node_count}"
    
    # Add flags
    for key, value in deployment.flags.items():
        if isinstance(value, bool):
            if value:
                command += f" --{key}"
        elif value is not None:
            command += f" --{key}={value}"
    
    # Create job record
    db_job = Job(
        id=job_id,
        command=command,
        parameters=deployment.dict(),
        status="pending"
    )
    db.add(db_job)
    db.commit()
    
    # Start background task
    background_tasks.add_task(run_cli_command, job_id, command, db)
    
    return {"job_id": job_id, "status": "started"}

@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(
        id=job.id,
        status=job.status,
        command=job.command,
        parameters=job.parameters,
        stdout=job.stdout,
        stderr=job.stderr,
        created_at=job.created_at,
        updated_at=job.updated_at,
        progress=job.progress,
        exit_code=job.exit_code
    )

@app.get("/jobs", response_class=HTMLResponse)
async def list_jobs(request: Request, db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return templates.TemplateResponse("jobs.html", {"request": request, "jobs": jobs})

@app.get("/jobs/{job_id}", response_class=HTMLResponse)
async def view_job(job_id: str, request: Request, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse("job_details.html", {"request": request, "job": job})

@app.post("/deploy", response_class=RedirectResponse)
async def handle_form_submission(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    cluster_name: str = Form(...),
    node_count: int = Form(...),
    high_availability: bool = Form(False),
    region: str = Form(None),
    custom_network: str = Form(None)
):
    # Create flags dictionary
    flags = {}
    if high_availability:
        flags["high-availability"] = True
    if region:
        flags["region"] = region
    if custom_network:
        flags["custom-network"] = custom_network
    
    # Create deployment request
    deployment = DeploymentRequest(
        cluster_name=cluster_name,
        node_count=node_count,
        flags=flags
    )
    
    # Call deploy API
    result = await deploy_cluster(deployment, background_tasks, db)
    
    # Redirect to job details page
    return RedirectResponse(url=f"/jobs/{result['job_id']}", status_code=303)

if __name__ == "__main__":
    # Make sure the templates and static directories exist
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    
    # Create minimal template files if they don't exist
    if not os.path.exists("templates/index.html"):
        with open("templates/index.html", "w") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>CLI Wrapper UI</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container">
        <h1>CLI Wrapper UI</h1>
        <div class="actions">
            <a href="/create" class="button">Create New Cluster</a>
            <a href="/jobs" class="button secondary">View All Jobs</a>
        </div>
    </div>
</body>
</html>
            """)
    
    if not os.path.exists("templates/create_deployment.html"):
        with open("templates/create_deployment.html", "w") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Create Cluster | CLI Wrapper UI</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <script>
        function toggleAdvanced() {
            const advancedOptions = document.getElementById('advanced-options');
            advancedOptions.style.display = advancedOptions.style.display === 'none' ? 'block' : 'none';
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>Deploy New Management Cluster</h1>
        <form action="/deploy" method="post">
            <div class="form-group">
                <label for="cluster_name">Cluster Name</label>
                <input type="text" id="cluster_name" name="cluster_name" required>
            </div>
            
            <div class="form-group">
                <label for="node_count">Node Count</label>
                <input type="number" id="node_count" name="node_count" min="1" value="3" required>
            </div>
            
            <button type="button" onclick="toggleAdvanced()" class="button secondary">Show/Hide Advanced Options</button>
            
            <div id="advanced-options" style="display: none">
                <div class="form-group checkbox">
                    <input type="checkbox" id="high_availability" name="high_availability">
                    <label for="high_availability">High Availability Mode</label>
                </div>
                
                <div class="form-group">
                    <label for="region">Region</label>
                    <select id="region" name="region">
                        <option value="">-- Select Region --</option>
                        <option value="us-west-1">US West (N. California)</option>
                        <option value="us-west-2">US West (Oregon)</option>
                        <option value="us-east-1">US East (N. Virginia)</option>
                        <option value="eu-west-1">EU (Ireland)</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="custom_network">Custom Network (optional)</label>
                    <input type="text" id="custom_network" name="custom_network">
                </div>
            </div>
            
            <div class="form-actions">
                <button type="submit" class="button">Deploy Cluster</button>
                <a href="/" class="button secondary">Cancel</a>
            </div>
        </form>
    </div>
</body>
</html>
            """)
    
    if not os.path.exists("templates/jobs.html"):
        with open("templates/jobs.html", "w") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>All Jobs | CLI Wrapper UI</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container">
        <h1>Deployment Jobs</h1>
        
        <div class="actions">
            <a href="/create" class="button">Create New Cluster</a>
            <a href="/" class="button secondary">Home</a>
        </div>
        
        <table class="jobs-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Cluster Name</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for job in jobs %}
                <tr>
                    <td>{{ job.id[:8] }}...</td>
                    <td>{{ job.parameters.get('cluster_name', 'N/A') }}</td>
                    <td class="status-{{ job.status }}">{{ job.status.upper() }}</td>
                    <td>{{ job.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                    <td><a href="/jobs/{{ job.id }}">View Details</a></td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="5">No jobs found</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
            """)
    
    if not os.path.exists("templates/job_details.html"):
        with open("templates/job_details.html", "w") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Job Details | CLI Wrapper UI</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <script>
        // Auto-refresh if job is still running
        function checkAndReload() {
            const status = document.getElementById('job-status').dataset.status;
            if (status === 'running' || status === 'pending') {
                setTimeout(() => window.location.reload(), 5000);
            }
        }
        window.onload = checkAndReload;
    </script>
</head>
<body>
    <div class="container">
        <div class="job-header">
            <h1>Deployment: {{ job.parameters.get('cluster_name', 'N/A') }}</h1>
            <div id="job-status" class="status-badge status-{{ job.status }}" data-status="{{ job.status }}">
                {{ job.status.upper() }}
            </div>
        </div>
        
        <div class="job-info">
            <p><strong>Job ID:</strong> {{ job.id }}</p>
            <p><strong>Created:</strong> {{ job.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
            <p><strong>Updated:</strong> {{ job.updated_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
            {% if job.exit_code is not none %}
            <p><strong>Exit Code:</strong> {{ job.exit_code }}</p>
            {% endif %}
        </div>
        
        {% if job.progress > 0 and job.progress < 100 and job.status == 'running' %}
        <div class="progress-container">
            <div class="progress-bar" style="width: {{ job.progress }}%">{{ job.progress }}%</div>
        </div>
        {% endif %}
        
        <h2>Command</h2>
        <pre class="command-box">{{ job.command }}</pre>
        
        <h2>Parameters</h2>
        <div class="params-box">
            <p><strong>Cluster Name:</strong> {{ job.parameters.get('cluster_name', 'N/A') }}</p>
            <p><strong>Node Count:</strong> {{ job.parameters.get('node_count', 'N/A') }}</p>
            
            {% if job.parameters.get('flags') %}
            <h3>Flags</h3>
            <ul>
                {% for key, value in job.parameters.get('flags', {}).items() %}
                <li><strong>{{ key }}:</strong> {{ value }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        
        <h2>Output</h2>
        <pre class="output-box">{{ job.stdout }}</pre>
        
        {% if job.stderr %}
        <h2>Errors</h2>
        <pre class="error-box">{{ job.stderr }}</pre>
        {% endif %}
        
        <div class="actions">
            <a href="/jobs" class="button">Back to All Jobs</a>
            <a href="/" class="button secondary">Home</a>
        </div>
    </div>
</body>
</html>
            """)
    
    if not os.path.exists("static/css/styles.css"):
        with open("static/css/styles.css", "w") as f:
            f.write("""
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f5f5f5;
    padding: 20px;
}

.container {
    max-width: 1000px;
    margin: 0 auto;
    background-color: #fff;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

h1 {
    margin-bottom: 20px;
    color: #2c3e50;
}

h2 {
    margin: 20px 0 10px;
    color: #34495e;
}

.form-group {
    margin-bottom: 15px;
}

label {
    display: block;
    margin-bottom: 5px;
    font-weight: 500;
}

input[type="text"],
input[type="number"],
select {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 16px;
}

.checkbox {
    display: flex;
    align-items: center;
}

.checkbox input {
    margin-right: 10px;
}

.checkbox label {
    margin-bottom: 0;
}

.button {
    display: inline-block;
    background-color: #3498db;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 16px;
    text-decoration: none;
    margin-right: 10px;
}

.button:hover {
    background-color: #2980b9;
}

.button.secondary {
    background-color: #95a5a6;
}

.button.secondary:hover {
    background-color: #7f8c8d;
}

.form-actions {
    margin-top: 20px;
}

/* Jobs table */
.jobs-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}

.jobs-table th,
.jobs-table td {
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

.jobs-table th {
    background-color: #f2f2f2;
}

/* Status badges */
.status-badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 4px;
    font-weight: bold;
    color: white;
}

.status-pending {
    background-color: #f39c12;
}

.status-running {
    background-color: #3498db;
}

.status-completed {
    background-color: #2ecc71;
}

.status-failed {
    background-color: #e74c3c;
}

/* Job details */
.job-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.job-info {
    background-color: #f9f9f9;
    padding: 15px;
    border-radius: 4px;
    margin-bottom: 20px;
}

.command-box,
.output-box,
.error-box {
    background-color: #f8f8f8;
    border: 1px solid #ddd;
    padding: 15px;
    border-radius: 4px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    margin-bottom: 20px;
    max-height: 400px;
    overflow-y: auto;
}

.error-box {
    background-color: #fff5f5;
    border-color: #ffcccc;
}

.params-box {
    background-color: #f8f8f8;
    border: 1px solid #ddd;
    padding: 15px;
    border-radius: 4px;
    margin-bottom: 20px;
}

.progress-container {
    background-color: #eee;
    border-radius: 4px;
    height: 20px;
    overflow: hidden;
    margin-bottom: 20px;
}

.progress-bar {
    height: 100%;
    background-color: #3498db;
    text-align: center;
    color: white;
    font-size: 12px;
    line-height: 20px;
}

.actions {
    margin: 20px 0;
}
            """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)