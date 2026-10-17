import hashlib
import json


from pydantic import BaseModel

def create_request_hash(data:BaseModel) -> str:
    payload = data.model_dump(mode="json")



    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",",":")
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()
