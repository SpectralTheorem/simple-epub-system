import requests
import json
import time
from pathlib import Path
import sys
import subprocess
import os

def log_output(message, file="output.txt"):
    print(message)
    with open(file, "a") as f:
        f.write(message + "\n")

def check_server_logs():
    """Check the server logs for any errors"""
    try:
        # Get the process ID of the running server
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        server_processes = [line for line in result.stdout.split('\n') if 'uvicorn' in line]
        
        if server_processes:
            log_output("\n=== Server Process Info ===")
            for proc in server_processes:
                log_output(proc)
                
            # Try to get application logs
            log_output("\n=== Application Logs ===")
            try:
                log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')
                if os.path.exists(log_file):
                    result = subprocess.run(['tail', '-n', '50', log_file], capture_output=True, text=True)
                    if result.stdout:
                        log_output(result.stdout)
                    else:
                        log_output("No recent application logs found")
                else:
                    log_output(f"Log file not found at {log_file}")
            except Exception as e:
                log_output(f"Error reading application logs: {e}")
        else:
            log_output("\nNo server process found running")
            
    except Exception as e:
        log_output(f"\nError checking server logs: {e}")

def main():
    base_url = "http://127.0.0.1:8000/api/v1"
    
    # Clear output.txt
    with open("output.txt", "w") as f:
        f.write("=== Troubleshooting Log ===\n\n")
    
    # Check server status
    check_server_logs()
    
    # Step 1: Clear database
    log_output("\n=== Clearing Database ===")
    response = requests.delete(f"{base_url}/database/clear")
    log_output(f"Clear DB Response: {response.status_code}")
    log_output(f"Response: {response.json()}")
    
    # Step 2: Upload file
    log_output("\n=== Uploading File ===")
    file_path = "Nixonland_ The Rise of a President and the - Rick Perlstein.epub"
    
    if not Path(file_path).exists():
        log_output(f"Error: File not found: {file_path}")
        return
    
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "application/epub+zip")}
        response = requests.post(f"{base_url}/documents/upload", files=files)
        log_output(f"Upload Response: {response.status_code}")
        upload_data = response.json()
        log_output(f"Response: {json.dumps(upload_data, indent=2)}")
        
        if response.status_code != 200:
            log_output("Error: Upload failed")
            return
            
    # Extract document ID from upload response message
    # Message format: "Processing started for document <doc_id>"
    doc_id = upload_data["message"].split("document ")[-1]
    log_output(f"\nExtracted Document ID: {doc_id}")
    
    # Step 3: Check processing status with retries
    log_output("\n=== Checking Processing Status ===")
    max_retries = 10
    retry_delay = 2  # seconds
    
    for i in range(max_retries):
        response = requests.get(f"{base_url}/documents/{doc_id}/status")
        status_data = response.json()
        log_output(f"\nStatus Check {i+1}/{max_retries}")
        log_output(f"Status Response: {response.status_code}")
        log_output(f"Response: {json.dumps(status_data, indent=2)}")
        
        if status_data.get("status") in ["completed", "failed"]:
            # Get document details if processing is done
            log_output("\n=== Getting Document Details ===")
            response = requests.get(f"{base_url}/documents/{doc_id}")
            log_output(f"Document Details Response: {response.status_code}")
            try:
                doc_details = response.json()
                log_output(f"Response: {json.dumps(doc_details, indent=2)}")
            except json.JSONDecodeError:
                log_output(f"Error: Could not decode JSON response")
                log_output(f"Response Text: {response.text}")
                
                # Check server logs for more details
                check_server_logs()
                break
            
            # Test chapter endpoint with the first chapter
            if doc_details.get("chapters"):
                first_chapter = doc_details["chapters"][0]
                chapter_id = first_chapter["id"]
                log_output("\n=== Testing Chapter Endpoint ===")
                response = requests.get(f"{base_url}/documents/{doc_id}/chapters/{chapter_id}")
                log_output(f"Chapter Response: {response.status_code}")
                if response.status_code == 200:
                    chapter_data = response.json()
                    log_output(f"Response: {json.dumps(chapter_data, indent=2)}")
                else:
                    log_output(f"Error Response: {response.text}")
            
            # Check server logs again after failure
            if status_data.get("status") == "failed":
                check_server_logs()
            break
            
        if i < max_retries - 1:
            log_output(f"Waiting {retry_delay} seconds before next check...")
            time.sleep(retry_delay)

if __name__ == "__main__":
    main()
