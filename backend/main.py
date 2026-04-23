from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from sse_starlette.sse import EventSourceResponse
import json
from graph import graph
from keyword_generator import generate_keyword_batch

app = FastAPI(title="ContentForge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunRequest(BaseModel):
    keyword: str
    api_key: str
    custom_instructions: str = ""

class GenerateRequest(BaseModel):
    api_key: str

@app.post("/api/generate-keywords")
async def api_generate_keywords(req: GenerateRequest):
    try:
        batch = generate_keyword_batch(req.api_key)
        return {"keywords": [k.dict() for k in batch.keywords]}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/run")
async def run_workflow(req: RunRequest):
    # This is a streaming endpoint using SSE
    async def event_generator():
        initial_state = {
            "keyword": req.keyword,
            "api_key": req.api_key,
            "custom_instructions": req.custom_instructions,
            "status": "Starting up...",
            "is_viable": False,
            "score_reasoning": "",
            "outlines": [],
            "approved_outlines": [],
            "generated_articles": [],
            "reviews": [],
            "final_articles": []
        }
        
        # We will stream updates from LangGraph
        # LangGraph's .stream yields updates as each node finishes
        try:
            for output in graph.stream(initial_state):
                node_name = list(output.keys())[0]
                node_state = output[node_name]
                
                def serialize(obj):
                    if hasattr(obj, "dict"):
                        return obj.dict()
                    return obj

                safe_state = {k: serialize(v) if not isinstance(v, list) else [serialize(i) for i in v] 
                              for k, v in node_state.items()}
                
                payload = {
                    "node": node_name,
                    "state": safe_state
                }
                yield {
                    "event": "update",
                    "data": json.dumps(payload)
                }
                await asyncio.sleep(0.5)
                
            yield {
                "event": "complete",
                "data": "done"
            }
        except Exception as e:
            yield {
                "event": "error",
                "data": str(e)
            }

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
