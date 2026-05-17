import requests
import time
import os
import sys

BACKEND_URL = "http://localhost:8000"
SAMPLE_DATA_DIR = r"c:\Users\regre\Downloads\procureshieldAI Demo - Copy\sample_data"

def upload_and_wait(filename):
    filepath = os.path.join(SAMPLE_DATA_DIR, filename)
    print(f"\n--- Testing {filename} ---")
    
    with open(filepath, 'rb') as f:
        files = {'file': (filename, f, 'application/pdf')}
        r = requests.post(f"{BACKEND_URL}/api/tenders/upload", files=files)
    
    if r.status_code != 200:
        print(f"Upload failed: {r.text}")
        return
    
    tender_id = r.json()['tender_id']
    print(f"Uploaded. Tender ID: {tender_id}. Waiting for analysis...")
    
    while True:
        r = requests.get(f"{BACKEND_URL}/api/tenders/{tender_id}")
        status = r.json()['status']
        if status == 'ready':
            print("Analysis complete!")
            break
        elif status == 'error':
            print("Analysis failed!")
            return
        time.sleep(5)
    
    # Check analysis results
    r = requests.get(f"{BACKEND_URL}/api/tenders/{tender_id}/analysis")
    analysis = r.json()
    
    print(f"Summary for {filename}:")
    print(f"- Criteria count (database): {len(r.json().get('criteria', []))}") # Note: /analysis doesn't return criteria from database
    
    # Check directly from tender endpoint which returns criteria
    r = requests.get(f"{BACKEND_URL}/api/tenders/{tender_id}")
    tender_data = r.json()
    print(f"- Criteria count (Criteria table): {tender_data.get('criteria_count', 0)}")
    
    print(f"- Overview: {analysis.get('overview', {}).get('work_description', 'N/A')}")
    print(f"- Documents: {len(analysis.get('documents', []))}")
    print(f"- Scope items: {len(analysis.get('scope_of_work', []))}")
    print(f"- Eligibility items: {len(analysis.get('eligibility', []))}")
    print(f"- Items: {len(analysis.get('items', []))}")

if __name__ == "__main__":
    files_to_test = [
        "1258102019.pdf",
        "298032025.pdf",
        "370052020.pdf",
        "Tender notice 898092025-520.pdf"
    ]
    
    # Check if backend is running
    try:
        requests.get(f"{BACKEND_URL}/api/health")
    except:
        print("Backend is not running at http://localhost:8000. Please start it first.")
        sys.exit(1)
        
    for f in files_to_test:
        upload_and_wait(f)
