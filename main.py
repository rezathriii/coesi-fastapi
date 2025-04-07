from fastapi import FastAPI, HTTPException, APIRouter, Response
from pydantic import BaseModel
from typing import Optional, Literal
import json

app = FastAPI()

api_router = APIRouter(prefix="/api/v1")

JSON_FILE_PATH = "./dummy-format-1.json"


class DeleteModelRequest(BaseModel):
    model_id: str


def read_json_file() -> dict:
    """Read and return the content of the JSON file"""
    try:
        with open(JSON_FILE_PATH, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Data file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON data")


def write_json_file(data: dict):
    """Write data to the JSON file"""
    try:
        with open(JSON_FILE_PATH, 'w') as file:
            json.dump(data, file, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write data: {str(e)}")


@api_router.get("/health", status_code=200)
async def health_check():
    """Health check endpoint for Docker and monitoring"""
    try:
        read_json_file()
        return {"status": "healthy", "message": "Service is operational"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "error": str(e)}
        )


@api_router.get("/models/")
async def get_models(
        filter: Optional[Literal["models", "composite-models"]] = None
):
    """
    Get all models or composite-models from the JSON file.
    If filter is provided ('models' or 'composite-models'), only return that specific section.
    """
    data = read_json_file()

    if filter:
        if filter not in data:
            raise HTTPException(status_code=400, detail=f"Invalid filter. Must be 'models' or 'composite-models'")
        return {filter: data[filter]}

    return data


@api_router.delete("/models/")
async def delete_model(request: DeleteModelRequest):
    """
    Delete a model or composite-model by ID from the JSON file.
    """
    model_id = request.model_id
    data = read_json_file()

    models = data.get("models", [])
    updated_models = [model for model in models if model["id"] != model_id]

    composite_models = data.get("composite-models", [])
    updated_composite_models = [cm for cm in composite_models if cm["id"] != model_id]

    # Check if the model was found and removed
    if (len(models) == len(updated_models) and
            len(composite_models) == len(updated_composite_models)):
        raise HTTPException(status_code=404, detail="Model not found")

    data["models"] = updated_models
    data["composite-models"] = updated_composite_models

    write_json_file(data)

    return {"message": "Model deleted successfully", "model_id": model_id}


app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=808)
