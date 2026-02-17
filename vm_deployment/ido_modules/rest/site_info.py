from fastapi import APIRouter, Header, HTTPException, Depends
import httpx
import os

app = APIRouter()

TARGET_API_URL = (
    "https://pop-services.nextlinkinternet.com/api/v1/popapp/sites?SearchKeyword=%s"
)
POPAPP_API_KEY = os.getenv("POPAPP_API_KEY")


async def get_bearer_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")
    return authorization[len("Bearer ") :]


@app.get("/api/sites")
async def site_info(
    site_name: str = "A", bearer_token: str = Depends(get_bearer_token)
):
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "ApiKey": POPAPP_API_KEY,
        "accept": "text/plain",
        "Content-Type": "application/json-patch+json",
    }

    body = {
        "preferredColumns": [
            "site_details.site_name",
            "site_details.lat",
            "site_details.long",
            "site_details.install_zone",
            "site_details.infra_zone",
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            TARGET_API_URL % site_name, headers=headers, json=body
        )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    site_data = response.json()

    # if site_data.get("totalCount") == 0:
    #     raise HTTPException(
    #         status_code=404, detail=f"{site_data.get("totalCount")} sites found"
    #     )

    # if site_data.get("totalCount") > 1:
    #     matches = list(
    #         filter(lambda x: x.get("siteName") == site_name, site_data.get("sites"))
    #     )
    #     if matches:
    #         return matches[0]
    #
    #     raise HTTPException(
    #         status_code=404, detail=f"{site_data.get("totalCount")} sites found"
    #     )

    return site_data.get("sites")
