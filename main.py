import os
import uuid
import boto3
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from botocore.exceptions import ClientError
from dotenv import load_dotenv

try:
    from x402.middleware.fastapi import x402_middleware
except ImportError:
    x402_middleware = None

load_dotenv()

app = FastAPI(title="x402 Storage", version="1.0.0")

EVM_ADDRESS = os.getenv("EVM_ADDRESS", "")
FACILITATOR_URL = os.getenv("FACILITATOR_URL", "https://x402.org/facilitator")
NETWORK = os.getenv("NETWORK", "eip155:84532")
PRICE_PER_MB = float(os.getenv("PRICE_PER_MB", "0.001"))
MAX_FILE_SIZE_MB = 100

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "x402-storage")

# Lazy S3 client — initialized on first use, not at startup
_s3_client = None

def get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
    return _s3_client


@app.get("/")
def root():
    return {
        "service": "x402-storage",
        "status": "ok",
        "description": "Pay-per-use file storage. $0.001/MB to store and retrieve.",
        "endpoints": ["/store", "/retrieve/{file_id}", "/health"],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "x402-storage",
        "wallet": EVM_ADDRESS,
        "network": NETWORK,
        "price_per_mb": f"${PRICE_PER_MB}",
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "facilitator": FACILITATOR_URL,
        "r2_configured": bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY),
    }


@app.post("/store")
async def store_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        size_bytes = len(contents)
        size_mb = size_bytes / (1024 * 1024)

        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum {MAX_FILE_SIZE_MB}MB, got {size_mb:.2f}MB.",
            )

        file_id = str(uuid.uuid4())
        original_filename = file.filename or "unknown"
        content_type = file.content_type or "application/octet-stream"

        get_s3().put_object(
            Bucket=R2_BUCKET_NAME,
            Key=file_id,
            Body=contents,
            ContentType=content_type,
            Metadata={"original_filename": original_filename},
        )

        return {
            "file_id": file_id,
            "original_filename": original_filename,
            "size_bytes": size_bytes,
            "size_mb": round(size_mb, 4),
            "content_type": content_type,
            "retrieve_url": f"/retrieve/{file_id}",
        }

    except HTTPException:
        raise
    except ClientError:
        raise HTTPException(status_code=500, detail="Storage backend error.")
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error during upload.")


@app.get("/retrieve/{file_id}")
async def retrieve_file(file_id: str):
    try:
        response = get_s3().get_object(Bucket=R2_BUCKET_NAME, Key=file_id)
        content_type = response.get("ContentType", "application/octet-stream")
        original_filename = response.get("Metadata", {}).get("original_filename", file_id)
        body = response["Body"]

        return StreamingResponse(
            body,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{original_filename}"'},
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="File not found.")
        raise HTTPException(status_code=500, detail="Storage backend error.")
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error during retrieval.")


# Apply x402 payment middleware if available
if x402_middleware and EVM_ADDRESS:
    app.add_middleware(
        x402_middleware,
        wallet_address=EVM_ADDRESS,
        routes={
            "/store": {"price": str(PRICE_PER_MB), "network": NETWORK, "description": f"File storage - ${PRICE_PER_MB}/MB"},
            "/retrieve/{file_id}": {"price": str(PRICE_PER_MB), "network": NETWORK, "description": f"File retrieval - ${PRICE_PER_MB}/MB"},
        },
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)