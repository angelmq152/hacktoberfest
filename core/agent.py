from shared.contracts import IncomingRequest, BotResponse, Confirmation, OutFile

async def handle(req: IncomingRequest) -> BotResponse:
    """Mock for core.agent.handle"""
    # Mock inicial: handle devuelve un BotResponse fijo con speech, text y un PDF de ejemplo.
    if req.source == "callback" and req.confirm_action_id:
        return BotResponse(
            chat_id=req.chat_id,
            speech="Acción confirmada.",
            text="✅ La acción ha sido ejecutada."
        )
        
    return BotResponse(
        chat_id=req.chat_id,
        speech="Tienes cuatro contenedores, tres en marcha y uno caído, el worker.",
        text="Estado de los contenedores:\n\n- nginx: Up\n- redis: Up\n- postgres: Up\n- worker: Exited",
        # We can add mock files or confirmation if we want
        # confirmation=Confirmation(action_id="123", prompt="¿Reinicio el worker?")
    )
