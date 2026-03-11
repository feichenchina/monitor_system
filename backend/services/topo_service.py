import os
import zipfile
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from sqlmodel import Session, select
from database import engine
from models import Machine
from services.monitor_service import create_ssh_client, execute_command
from logger import logger

# Path to the library
# Assuming the script runs from c:\ms_temp\backend
LIB_PATH = (Path(__file__).parent.parent.parent / "libs" / "PCIETopoPainter").resolve()

def create_tool_zip() -> bytes:
    """Creates a zip file of the PCIETopoPainter library in memory."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Walk relative to LIB_PATH
        for root, dirs, files in os.walk(LIB_PATH):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", "DEV", "web_demo", "tests", "results", "venv", ".idea"]]
            
            for file in files:
                if file.endswith(".pyc") or file.endswith(".git") or file.endswith(".DS_Store"):
                    continue
                
                file_path = Path(root) / file
                # Calculate relative path for archive
                archive_name = file_path.relative_to(LIB_PATH)
                zip_file.write(file_path, str(archive_name))
    
    buffer.seek(0)
    return buffer.getvalue()

def update_machine_topo(machine_id: int):
    """Updates the PCIe topology for a specific machine."""
    with Session(engine) as session:
        machine = session.get(Machine, machine_id)
        if not machine:
            logger.error(f"Machine {machine_id} not found for topo update")
            return

        if machine.status != "Online":
            logger.warning(f"Machine {machine.ip} is not Online, skipping topo update")
            return

        logger.info(f"Starting topo update for {machine.ip}")
        
        try:
            client = create_ssh_client(machine.ip, machine.port, machine.username, machine.password)
            if not client:
                logger.error(f"Failed to connect to {machine.ip}")
                return

            # 1. Prepare remote directory
            remote_dir = "/tmp/pcietopo_tool"
            execute_command(client, f"mkdir -p {remote_dir}")

            # 2. Upload zip
            zip_content = create_tool_zip()
            sftp = client.open_sftp()
            with sftp.file(f"{remote_dir}/tool.zip", "wb") as f:
                f.write(zip_content)
            sftp.close()

            # 3. Unzip and Run
            # Using python3 -m zipfile to avoid dependency on unzip
            # Using --all to avoid aggressive pruning which might lead to empty results
            # Using --formats svg to avoid overwriting pci_topology.json with Graphviz xdot output (if dot is present)
            # Capture stderr to help debugging
            cmd = (
                f"cd {remote_dir} && "
                f"python3 -m zipfile -e tool.zip . > /dev/null 2>&1 && "
                f"python3 -m pcietopo topo --output . --formats svg && "
                f"if [ -f pci_topology.json ]; then cat pci_topology.json; else echo 'ERROR: pci_topology.json not found'; fi"
            )
            
            # Increase timeout to 60s for topo generation
            output, error = execute_command(client, cmd, timeout=60)
            
            if "ERROR:" in output:
                 logger.error(f"Error generating topo on {machine.ip}. Output: {output}")
                 execute_command(client, f"rm -rf {remote_dir}")
                 return

            if not output.strip():
                 logger.error(f"Empty output from topo command on {machine.ip}. Stderr: {error}")
                 execute_command(client, f"rm -rf {remote_dir}")
                 return

            # If output is not json, something went wrong
            try:
                # Validate JSON
                topo_data = json.loads(output)
                
                # Check if it's empty even with --all
                if not topo_data.get('nodes'):
                    logger.warning(f"Topo data for {machine.ip} contains 0 nodes even with --all")

                # Save as string
                machine.pci_topo_json = json.dumps(topo_data)
                session.add(machine)
                session.commit()
                logger.info(f"Successfully updated topo for {machine.ip}")
            except json.JSONDecodeError:
                # Log more info about what was actually received
                preview = output[:500] if output else "EMPTY OUTPUT"
                logger.error(f"Failed to parse topo JSON from {machine.ip}. Received: {preview}. Stderr: {error}")

            # Cleanup
            execute_command(client, f"rm -rf {remote_dir}")
            client.close()

        except Exception as e:
            logger.error(f"Exception during topo update for {machine.ip}: {e}")

def trigger_topo_update_async(machine_id: int):
    """Triggers topology update in a background thread."""
    threading.Thread(target=update_machine_topo, args=(machine_id,)).start()

def update_all_machines_topo():
    """Updates the PCIe topology for all online machines."""
    logger.info("Starting global topo update for all online machines...")
    with Session(engine) as session:
        # Select all online machines
        statement = select(Machine).where(Machine.status == "Online")
        machines = session.exec(statement).all()
        machine_ids = [m.id for m in machines]
    
    if not machine_ids:
        logger.info("No online machines found for topo update.")
        return

    logger.info(f"Found {len(machine_ids)} online machines to update topo.")
    
    # Use ThreadPoolExecutor to run updates in parallel
    # Limit max_workers to avoid resource exhaustion
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(update_machine_topo, machine_ids)
    
    logger.info("Global topo update completed.")

