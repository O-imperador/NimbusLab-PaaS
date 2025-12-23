from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess, threading, time, os
import paramiko
from proxmoxer import ProxmoxAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

PROXMOX_NODE = os.getenv("PROXMOX_NODE", "proxhost")
PROXMOX_IP = os.getenv("PROXMOX_IP", "192.168.100.10")
PROXMOX_USER = os.getenv("PROXMOX_USER", "root@pam")
PROXMOX_PASS = os.getenv("PROXMOX_PASS")

UBUNTU_USER = os.getenv("UBUNTU_USER", "ubuntu")
UBUNTU_PASSWORD = os.getenv("VM_PASSWORD")

TERRAFORM_DIR_VM = os.path.join(os.getcwd(), "terraform", "vm")
TERRAFORM_DIR_LXC = os.path.join(os.getcwd(), "terraform", "lxc")
SCRIPTS_DIR = os.path.join(os.getcwd(), "scripts")

PORT_REGISTRY_FILE = "ports.json"
USED_PORTS = set()
DEPLOY_LOGS = {}

import json

def load_ports():
    global USED_PORTS
    if os.path.exists(PORT_REGISTRY_FILE):
        try:
            with open(PORT_REGISTRY_FILE, "r") as f:
                data = json.load(f)
                USED_PORTS = set(data.get("used_ports", []))
        except:
            USED_PORTS = set()

def save_ports():
    with port_lock:
        with open(PORT_REGISTRY_FILE, "w") as f:
            json.dump({"used_ports": list(USED_PORTS)}, f)

load_ports()

# Initialize Proxmox API
proxmox = None
try:
    if all([PROXMOX_IP, PROXMOX_USER, PROXMOX_PASS]):
        proxmox = ProxmoxAPI(
            PROXMOX_IP, 
            user=PROXMOX_USER, 
            password=PROXMOX_PASS, 
            verify_ssl=False
        )
    else:
        print("Warning: Proxmox credentials missing in environment variables.")
except Exception as e:
    print(f"Error connecting to Proxmox: {e}")

port_lock = threading.Lock()

def get_free_port():
    with port_lock:
        for port in range(PORT_START, PORT_END):
            if port not in USED_PORTS:
                USED_PORTS.add(port)
                save_ports()
                return port
    raise Exception("No free ports available")

def get_lxc_ip(container_name, timeout=120):
    if not proxmox: return None
    node = PROXMOX_NODE
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            for lxc in proxmox.nodes(node).lxc.get():
                if lxc['name'] == container_name:
                    config = proxmox.nodes(node).lxc(lxc['vmid']).config.get()
                    net0 = config.get('net0', '')
                    if 'ip=' in net0:
                        ip = net0.split(',')[0].split('=')[1]
                        if ip != 'dhcp':
                            return ip
        except Exception as e:
            print(f"Error fetching LXC IP: {e}")
        time.sleep(5)
    return None

def get_vm_ip(vm_name):
    if not proxmox: return None
    node = PROXMOX_NODE
    try:
        for vm in proxmox.nodes(node).qemu.get():
            if vm['name'] == vm_name:
                try:
                    agent = proxmox.nodes(node).qemu(vm['vmid']).agent.get(timeout=5)
                    return agent['ip-addresses'][0]['ip-address']
                except:
                    return None
    except Exception as e:
        print(f"Error fetching VM IP: {e}")
    return None

def create_ssh_client(ip):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for i in range(12): # Increased retries (1 min total)
        try:
            ssh.connect(ip, username=UBUNTU_USER, password=UBUNTU_PASSWORD, timeout=10)
            return ssh
        except Exception as e:
            print(f"SSH attempt {i+1} failed: {e}")
            time.sleep(5)
    return None

def deploy_app_task(app_name, framework, repo, infra_type):
    DEPLOY_LOGS[app_name] = [f"Deployment started for {app_name}..."]
    
    # Prepare Terraform Variables
    proxmox_url = f"https://{PROXMOX_IP}:8006/api2/json"
    
    if infra_type == "VM":
        tfvars_content = f"""
vm_name = "{app_name}"
vm_password = "{UBUNTU_PASSWORD}"
proxmox_api_url = "{proxmox_url}"
proxmox_api_token_id = "{PROXMOX_USER}"
proxmox_api_token_secret = "{PROXMOX_PASS}"
"""
    else:
        tfvars_content = f"""
lxc_name = "{app_name}-lxc"
lxc_password = "{UBUNTU_PASSWORD}"
proxmox_api_url = "{proxmox_url}"
proxmox_api_token_id = "{PROXMOX_USER}"
proxmox_api_token_secret = "{PROXMOX_PASS}"
"""

    terraform_dir = TERRAFORM_DIR_VM if infra_type == "VM" else TERRAFORM_DIR_LXC
    tfvars_file = os.path.join(terraform_dir, "terraform.tfvars")
    
    try:
        with open(tfvars_file, "w") as f:
            f.write(tfvars_content)
        
        DEPLOY_LOGS[app_name].append("Running Terraform init...")
        subprocess.run(["terraform", "init"], cwd=terraform_dir, check=True, capture_output=True, text=True)
        
        DEPLOY_LOGS[app_name].append("Running Terraform apply...")
        subprocess.run(["terraform", "apply", "-auto-approve"], cwd=terraform_dir, check=True, capture_output=True, text=True)
        DEPLOY_LOGS[app_name].append("Infrastructure provisioned successfully")
    except subprocess.CalledProcessError as e:
        DEPLOY_LOGS[app_name].append(f"Terraform failed: {e.stderr if e.stderr else str(e)}")
        return
    except Exception as e:
        DEPLOY_LOGS[app_name].append(f"Error during infrastructure setup: {str(e)}")
        return

    DEPLOY_LOGS[app_name].append("Waiting for resource to boot...")
    time.sleep(10) # Initial wait for boot
    
    ip = get_vm_ip(app_name) if infra_type == "VM" else get_lxc_ip(f"{app_name}-lxc")
    if not ip:
        DEPLOY_LOGS[app_name].append("CRITICAL: Failed to detect IP address after infrastructure setup.")
        return

    DEPLOY_LOGS[app_name].append(f"IP detected: {ip}")
    app_port = get_free_port()
    DEPLOY_LOGS[app_name].append(f"Assigned internal port: {app_port}")

    DEPLOY_LOGS[app_name].append("Establishing SSH connection...")
    ssh = create_ssh_client(ip)
    if not ssh:
        DEPLOY_LOGS[app_name].append("CRITICAL: SSH connection timeout. Check networking/firewall.")
        return

    try:
        sftp = ssh.open_sftp()
        sftp.put(os.path.join(SCRIPTS_DIR, "install_framework.sh"), "/home/ubuntu/install_framework.sh")
        sftp.put(os.path.join(SCRIPTS_DIR, "deploy_app.sh"), "/home/ubuntu/deploy_app.sh")
        sftp.close()
        ssh.exec_command("chmod +x /home/ubuntu/*.sh")
        DEPLOY_LOGS[app_name].append("Deployment scripts uploaded")

        DEPLOY_LOGS[app_name].append("Framework installation started (this may take a while)...")
        stdin, stdout, stderr = ssh.exec_command(f"/home/ubuntu/install_framework.sh {framework}")
        for line in iter(stdout.readline, ""):
            DEPLOY_LOGS[app_name].append(f"[Setup] {line.strip()}")
        
        DEPLOY_LOGS[app_name].append("Application deployment started...")
        stdin, stdout, stderr = ssh.exec_command(f"/home/ubuntu/deploy_app.sh {repo} {app_name} {framework} {app_port}")
        
        while not stdout.channel.exit_status_ready():
            for line in stdout.readlines():
                DEPLOY_LOGS[app_name].append(f"[Deploy] {line.strip()}")
            time.sleep(1)

        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            DEPLOY_LOGS[app_name].append(f"SUCCESS: Deployment completed! Access at http://{ip}:{app_port}")
        else:
            DEPLOY_LOGS[app_name].append(f"ERROR: Deployment script failed with status {exit_status}")
    
    except Exception as e:
        DEPLOY_LOGS[app_name].append(f"Error during deployment execution: {str(e)}")
    finally:
        ssh.close()

@app.route("/deploy", methods=["POST"])
def deploy():
    data = request.json
    framework = data.get("framework", "React").lower()
    repo = data.get("repo")
    infra_type = data.get("type", "LXC")
    
    if not repo:
        return jsonify({"error": "Repository URL is required"}), 400
        
    app_name = repo.split("/")[-1].replace(".git","")
    thread = threading.Thread(target=deploy_app_task, args=(app_name, framework, repo, infra_type))
    thread.start()
    return jsonify({"status":"started", "app_name": app_name})

@app.route("/status/<app_name>", methods=["GET"])
def status(app_name):
    logs = DEPLOY_LOGS.get(app_name, ["No logs found for this application"])
    return jsonify({"logs": logs})

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("DEBUG", "True") == "True"
    app.run(port=port, debug=debug)
