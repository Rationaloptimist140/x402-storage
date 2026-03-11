# x402 Storage

A pay-per-use file storage API built with FastAPI and the [x402 payment protocol](https://x402.org). Pay **$0.001 USDC per MB** to store and retrieve files — no accounts, no subscriptions.

## What It Does

- Upload any file and get back a unique file ID
- Retrieve any stored file by its ID
- Charges **$0.001 USDC per MB** per operation, paid via x402
- Returns HTTP 402 Payment Required to non-paying clients
- Stores files on Cloudflare R2 (S3-compatible, zero egress fees)

**Payment wallet:** `0x7c2e102FC6D1FbCd3E62C936d3d394Bd55C949f2`
**Network:** Base Sepolia (`eip155:84532`) — testnet
**Price:** $0.001 USDC per MB

---

## Endpoints

| Method | Path | Description | Payment |
|--------|------|-------------|---------||
| GET | `/` | Service info | Free |
| GET | `/health` | Health + config check | Free |
| POST | `/store` | Upload a file | $0.001/MB |
| GET | `/retrieve/{file_id}` | Download a file | $0.001/MB |

---

## Usage

### Check the service
```bash
curl https://your-service.up.railway.app/health
```

### Upload without payment (expect 402)
```bash
curl -X POST https://your-service.up.railway.app/store \
  -F "file=@document.pdf"
```

### Upload with x402 Python client
```python
import httpx
from x402.client import wrap

client = wrap(httpx.Client(), private_key="YOUR_PRIVATE_KEY")

with open("document.pdf", "rb") as f:
    response = client.post(
        "https://your-service.up.railway.app/store",
        files={"file": f},
    )

data = response.json()
print(f"File stored! ID: {data['file_id']}")
print(f"Size: {data['size_mb']} MB")
```

### Retrieve a stored file
```python
response = client.get(
    f"https://your-service.up.railway.app/retrieve/{file_id}"
)

with open("downloaded_file.pdf", "wb") as f:
    f.write(response.content)
```

---

## Deploy on Railway

### 1. Clone the repo
```bash
git clone https://github.com/Rationaloptimist140/x402-storage.git
cd x402-storage
```

### 2. Create a Cloudflare R2 bucket
1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → R2
2. Create a bucket named `x402-storage`
3. Create an API token with R2 read/write permissions
4. Note your Account ID, Access Key ID, and Secret Access Key

### 3. Connect to Railway
1. Go to [railway.app](https://railway.app) and create a new project
2. Choose **Deploy from GitHub repo** and select `x402-storage`

### 4. Set environment variables

| Variable | Value | Notes |
|----------|-------|-------|
| `EVM_ADDRESS` | Your wallet address | Receives USDC payments |
| `FACILITATOR_URL` | `https://x402.org/facilitator` | x402 facilitator |
| `NETWORK` | `eip155:84532` | Base Sepolia testnet |
| `PRICE_PER_MB` | `0.001` | Price per MB in USDC |
| `R2_ACCOUNT_ID` | Your Cloudflare Account ID | From R2 dashboard |
| `R2_ACCESS_KEY_ID` | Your R2 Access Key | From R2 API token |
| `R2_SECRET_ACCESS_KEY` | Your R2 Secret Key | From R2 API token |
| `R2_BUCKET_NAME` | `x402-storage` | Your R2 bucket name |

> `PORT` is set automatically by Railway — do not override it.

### 5. Deploy
Railway auto-detects Python via Nixpacks and starts the server.

---

## File Size Limits
- Maximum upload: **100 MB**
- Minimum charge: **0.01 MB** (to cover tiny files)

## Prerequisites (client)
```bash
pip install x402 httpx
```
Plus a wallet with USDC on Base Sepolia — get test funds at [faucet.circle.com](https://faucet.circle.com).

---

## x402 Resources
- Protocol spec: [x402.org](https://x402.org)
- Python client: [x402-py on GitHub](https://github.com/coinbase/x402)
- Facilitator: [x402.org/facilitator](https://x402.org/facilitator)

---

**License:** MIT