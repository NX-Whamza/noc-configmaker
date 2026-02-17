from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import yaml, subprocess, tempfile, os, shutil, asyncio, sys
import logging

logger = logging.getLogger(__name__)

app = APIRouter(prefix="/api/7250config")

CONFIG_BASE = "/opt/base_configs"
GEN         = "/opt/netlaunch-tools-backend/device_io/nokia7250_config.py"
TEMPLATE    = os.path.join(CONFIG_BASE, "Nokia", "7250", "7250-bng-config.j2")
COMMON      = os.path.join(CONFIG_BASE, "Nokia", "7250", "7250-common.yaml")

@app.post("/generate", response_class=FileResponse)
async def generate(body: dict, background_tasks: BackgroundTasks):
    if 'backhauls' in body:
        body['backhauls'] = [b for b in body['backhauls'] if b.get('name') or b.get('ip')]
    if 'uplinks' in body:
        body['uplinks'] = [u for u in body['uplinks'] if u.get('name')]
    
    fd, tmp_yaml = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        yaml.safe_dump(body, f)
    
    outdir = tempfile.mkdtemp(prefix="7250_")
    
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            [
                sys.executable, GEN,
                "-c", COMMON,
                "-i", tmp_yaml,
                "-t", TEMPLATE,
                "-o", outdir,
                "-d", "RTR-7250",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode != 0:
            logger.error(f"Config generation failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Config generation failed: {result.stderr}"
            )
            
    except Exception as e:
        logger.exception("Unexpected error during config generation")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )
    finally:
        os.remove(tmp_yaml)
    
    try:
        fname = next(iter(os.listdir(outdir)))
    except StopIteration:
        logger.error("No output file generated")
        shutil.rmtree(outdir, ignore_errors=True)
        raise HTTPException(500, "Generation failed—no output file created")
    
    fpath = os.path.join(outdir, fname)
    background_tasks.add_task(shutil.rmtree, outdir, ignore_errors=True)
    
    return FileResponse(fpath, filename=fname, media_type="text/plain")