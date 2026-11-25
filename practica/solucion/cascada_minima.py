"""Solución: una cascada de voz desde cero, con Pipecat y sin el grafo de Ondo.

    python -m practica.solucion.cascada_minima                    # abre http://localhost:7860/client
    python -m practica.solucion.cascada_minima --traza            # los frames de cada turno
    python -m practica.solucion.cascada_minima --tiempos          # en qué se va el tiempo de cada respuesta
    python -m practica.solucion.cascada_minima --voz elevenlabs   # la parte opcional: otra voz

Siete piezas en fila. El audio entra por el transporte, el STT lo convierte en
texto, el agregador del cliente decide cuándo ha terminado su turno y añade lo
que ha dicho a la conversación, el LLM contesta, el TTS lo convierte en voz,
el transporte lo manda al navegador y el agregador del agente guarda lo que
llegó a decir:

    transporte.input() → STT → turno del cliente → LLM → TTS → transporte.output() → turno del agente
"""

import argparse
import os

from dotenv import load_dotenv

load_dotenv()  # la clave de OpenAI (y la de ElevenLabs, si la usas) sale del .env

from pipecat.audio.vad.silero import SileroVADAnalyzer  # noqa: E402
from pipecat.frames.frames import LLMRunFrame  # noqa: E402
from pipecat.pipeline.pipeline import Pipeline  # noqa: E402
from pipecat.pipeline.worker import PipelineParams, PipelineWorker  # noqa: E402
from pipecat.processors.aggregators.llm_context import LLMContext  # noqa: E402
from pipecat.processors.aggregators.llm_response_universal import (  # noqa: E402
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments  # noqa: E402
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService  # noqa: E402
from pipecat.services.openai.llm import OpenAILLMService  # noqa: E402
from pipecat.services.openai.stt import OpenAISTTService  # noqa: E402
from pipecat.services.openai.tts import OpenAITTSService  # noqa: E402
from pipecat.transcriptions.language import Language  # noqa: E402
from pipecat.transports.base_transport import TransportParams  # noqa: E402
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport  # noqa: E402
from pipecat.workers.runner import WorkerRunner  # noqa: E402

from canales.observar import observadores  # noqa: E402

PROMPT = """Eres el asistente de voz de Ondo, una tienda online de bicicletas eléctricas. El cliente te oye, \
no te lee: contesta con frases cortas, sin listas, sin formato y con los números dichos como se dicen. \
En esta prueba no tienes acceso a pedidos, citas ni devoluciones: si te los piden, dilo y ofrece ayuda general. \
Si la conversación acaba de empezar, saluda en una frase y di en qué puedes ayudar."""


async def bot(runner_args: RunnerArguments):
    """Una conversación: Pipecat llama a esta función cada vez que alguien pulsa Connect en el navegador."""
    cli = runner_args.cli_args
    transporte = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )

    # 1. Voz → texto. El STT de OpenAI transcribe cada fragmento de voz que le marca el detector.
    stt = OpenAISTTService(
        api_key=os.getenv("OPENAI_API_KEY"),
        settings=OpenAISTTService.Settings(language=Language.ES),
    )

    # 2. El cerebro: un LLM de OpenAI con un prompt para el oído. Contesta en streaming, trozo a trozo.
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        settings=OpenAILLMService.Settings(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            system_instruction=PROMPT,
        ),
    )

    # 3. Texto → voz. Parte opcional: --voz elevenlabs cambia solo esta pieza.
    if cli.voz == "elevenlabs":
        tts = ElevenLabsTTSService(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            settings=ElevenLabsTTSService.Settings(
                voice=os.getenv("ELEVENLABS_VOICE_ID"),
                model=os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5"),
            ),
        )
    else:
        tts = OpenAITTSService(
            api_key=os.getenv("OPENAI_API_KEY"),
            settings=OpenAITTSService.Settings(voice="coral"),
        )

    # 4. La conversación y sus dos agregadores. El del cliente lleva el detector de voz (Silero) y decide
    #    cuándo ha terminado el turno; entonces añade lo que ha dicho y manda la conversación entera al LLM.
    #    El del agente guarda lo que el agente llegó a decir (si le interrumpen, solo lo dicho).
    contexto = LLMContext()
    turno_cliente, turno_agente = LLMContextAggregatorPair(
        contexto, user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer())
    )

    # 5. La tubería: el orden es el camino que hace cada frame.
    pipeline = Pipeline([
        transporte.input(),    # audio del navegador
        stt,                   # voz → texto
        turno_cliente,         # ¿ha terminado de hablar? → conversación al LLM
        llm,                   # piensa la respuesta
        tts,                   # texto → voz
        transporte.output(),   # audio al navegador
        turno_agente,          # guarda lo que el agente ha dicho
    ])

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True),
        observers=observadores(traza=cli.traza, tiempos=cli.tiempos),
    )
    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)
    await runner.add_workers(worker)

    @transporte.event_handler("on_client_connected")
    async def al_conectar(transport, client):
        # El agente habla primero: pide al LLM que conteste a la conversación vacía (el prompt le dice que salude).
        await worker.queue_frames([LLMRunFrame()])

    @transporte.event_handler("on_client_disconnected")
    async def al_colgar(transport, client):
        await runner.cancel()

    await runner.run()


if __name__ == "__main__":
    from pipecat.runner.run import main

    parser = argparse.ArgumentParser(description="Cascada de voz mínima")
    parser.add_argument("--traza", action="store_true", help="imprime los frames de cada turno")
    parser.add_argument("--tiempos", action="store_true", help="imprime en qué se va el tiempo de cada respuesta")
    parser.add_argument("--voz", choices=("openai", "elevenlabs"), default="openai", help="quién pone la voz")
    main(parser)
