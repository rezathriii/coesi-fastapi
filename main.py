from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from typing import Literal, List, Optional, Dict, Any
import json

app = FastAPI()

api_router = APIRouter(prefix="/api/v1")

JSON_FILE_PATH = "./dummy-format-1.json"


class DeleteModelRequest(BaseModel):
    model_id: str


class ModelInput(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str]
    solver: Optional[str] = None
    model_execution_cmd: Optional[str] = None
    simulator_names: Optional[List[str]] = []
    simulation_parameters: Optional[List[Dict[str, Any]]] = []
    input_variables: Optional[List[Dict[str, Any]]] = []
    output_variables: Optional[List[Dict[str, Any]]] = []
    model_parameters: Optional[List[Dict[str, Any]]] = []
    ports: Optional[List[Dict[str, Any]]] = []
    components: Optional[List[str]] = []
    connections: Optional[List[Dict[str, Any]]] = []


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
@api_router.get("/health/", status_code=200)
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


@api_router.get("/models")
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


@api_router.delete("/models")
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


@api_router.post("/models", status_code=201)
@api_router.post("/models/", status_code=201)
async def add_model(model_data: ModelInput):
    """
    Add a new model or composite-model to the JSON file.
    Automatically classifies based on presence of components/connections.
    """
    data = read_json_file()

    model_dict = model_data.model_dump(exclude_unset=True)

    is_composite = (len(model_dict.get('components', [])) > 0 or
                    len(model_dict.get('connections', [])) > 0)

    if is_composite:
        if 'composite-models' not in data:
            data['composite-models'] = []
        data['composite-models'].append(model_dict)
    else:
        if 'models' not in data:
            data['models'] = []
        data['models'].append(model_dict)

    write_json_file(data)

    return {
        "message": "Model added successfully",
        "type": "composite-model" if is_composite else "model",
        "id": model_dict['id']
    }


app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
