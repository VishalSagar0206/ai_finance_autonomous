from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import uuid
import logging

from core.graph import adk_app
from core.state import ADKState, UserRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

app = FastAPI(title="ADK v4.0 Autonomous Trading API", version="1.0.0")

class DeployRequest(BaseModel):
    asset_class: str
    risk_tolerance: str
    time_horizon: str
    tickers: list[str]

async def event_streamer(initial_state: dict, thread_config: dict):
    """
    Asynchronous generator that streams LangGraph events via Server-Sent Events (SSE).
    """
    try:
        # LangGraph's astream runs the underlying sync nodes in a ThreadPoolExecutor
        async for event in adk_app.astream(initial_state, config=thread_config):
            for node_name, state_update in event.items():
                logger.info(f"Completed Node: {node_name}")
                
                # Check for HITL Interrupt
                state_snapshot = adk_app.get_state(thread_config)
                is_hitl = "execution" in state_snapshot.next
                
                payload = {
                    "node": node_name,
                    "status": "completed",
                    "requires_approval": is_hitl
                }
                yield f"data: {json.dumps(payload)}\n\n"
                
                if is_hitl:
                    yield f"data: {json.dumps({'node': 'SYSTEM', 'status': 'HALTED_FOR_APPROVAL'})}\n\n"
                    return # Pause stream

        # Graph finished naturally without HITL (e.g., rejected)
        state_vals = adk_app.get_state(thread_config).values
        yield f"data: {json.dumps({'node': 'SYSTEM', 'status': 'TERMINATED', 'final_report': state_vals.get('final_report', 'No report')})}\n\n"

    except Exception as e:
        logger.error(f"Stream Error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.post("/api/v1/orchestrate")
async def deploy_strategy(req: DeployRequest):
    """
    Initiates the multi-agent graph and returns an SSE stream.
    """
    thread_id = str(uuid.uuid4())
    thread_config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = ADKState(
        request=UserRequest(
            asset_class=req.asset_class,
            risk_tolerance=req.risk_tolerance,
            time_horizon=req.time_horizon,
            tickers=req.tickers,
        )
    ).model_dump()
    
    logger.info(f"Deploying Strategy Session: {thread_id}")
    
    return StreamingResponse(
        event_streamer(initial_state, thread_config),
        media_type="text/event-stream"
    )

@app.post("/api/v1/approve/{thread_id}")
async def approve_strategy(thread_id: str):
    """
    Resumes the graph from the HITL interrupt to execute trades.
    """
    thread_config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = adk_app.get_state(thread_config)
    
    if "execution" not in state_snapshot.next:
        raise HTTPException(status_code=400, detail="Thread is not waiting for execution approval.")
    
    # Resume the graph async
    logger.info(f"Executing Approved Strategy: {thread_id}")
    async for _ in adk_app.astream(None, config=thread_config):
        pass # Let it finish
        
    return {"status": "Execution Complete"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
