import httpx
import asyncio

async def test_api():
    url = "https://ds.yovole.com/api/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer sk-833480880d9d417fbcc7ce125ca7d78b"
    }
    payload = {
        "model": "DeepSeek-R1",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"}
        ],
        "stream": True
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())