import os
import json
import base64
import requests
from pathlib import Path
from azure.identity import DefaultAzureCredential

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

IMAGE_ENDPOINT = os.getenv('IMAGE_ENDPOINT')
IMAGE_DEPLOYMENT = os.getenv('IMAGE_DEPLOYMENT')
IMAGE_AUTH_METHOD = os.getenv('IMAGE_AUTH_METHOD', 'entra_id')
IMAGE_API_VERSION = os.getenv('IMAGE_API_VERSION')

def test_image_generation():
    """Smoke test for gpt-image-2 deployment"""
    
    url = f"{IMAGE_ENDPOINT}/openai/deployments/{IMAGE_DEPLOYMENT}/images/generations?api-version={IMAGE_API_VERSION}"
    
    # Use Entra ID authentication
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": "test banner",
        "size": "1024x1024",
        "n": 1
    }
    
    print(f"Testing image generation at {IMAGE_ENDPOINT}")
    print(f"Deployment: {IMAGE_DEPLOYMENT}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        
        data = response.json()
        
        # gpt-image-2 returns b64_json
        if 'data' in data and len(data['data']) > 0:
            image_data = data['data'][0]
            
            if 'b64_json' in image_data:
                b64_string = image_data['b64_json']
                image_bytes = base64.b64decode(b64_string)
                
                output_path = Path(__file__).parent.parent / 'output' / 'smoke_test.png'
                with open(output_path, 'wb') as f:
                    f.write(image_bytes)
                
                print(f"✅ SUCCESS: Image generated and saved to {output_path}")
                print(f"   Size: {len(image_bytes)} bytes")
                return True
            else:
                print(f"❌ FAIL: No b64_json in response: {data}")
                return False
        else:
            print(f"❌ FAIL: Invalid response structure: {data}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Request error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_image_generation()
    exit(0 if success else 1)
