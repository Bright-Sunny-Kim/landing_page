import requests

url = "http://127.0.0.1:5000/api/dify/retrieval"
payload = {"query": "재고자산 저가법"}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        records = data.get("records", [])
        print(f"Found {len(records)} records.")
        if records:
            print(f"Top Score: {records[0].get('score')}")
            print(f"Top Content Preview: {records[0].get('content')[:100]}...")
    else:
        print(response.text)
except Exception as e:
    print(f"Failed to connect: {e}")
