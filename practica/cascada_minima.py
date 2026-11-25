"""Práctica del día 3: una cascada de voz desde cero, con Pipecat y sin el grafo de Ondo.

    python -m practica.cascada_minima              # abre http://localhost:7860/client y pulsa Connect
    python -m practica.cascada_minima --traza      # los frames de cada turno, con su hora
    python -m practica.cascada_minima --tiempos    # en qué se va el tiempo de cada respuesta

Tal como está, el audio entra y sale, pero nadie lo escucha: el agente ni oye ni
habla. Tu trabajo es montar la tubería, siete piezas en fila:

    transporte.input() → STT → turno del cliente → LLM → TTS → transporte.output() → turno del agente

- transporte.input() / transporte.output(): el audio que llega del navegador y el que vuelve. Ya están creados.
- STT: convierte la voz del cliente en texto (OpenAI, en español).
- Turno del cliente: el agregador del cliente. Lleva el detector de voz (Silero), decide cuándo ha terminado
  de hablar el cliente, añade lo que ha dicho a la conversación y se la pasa entera al LLM.
- LLM: el cerebro (OpenAI, el modelo de OPENAI_MODEL del .env, con PROMPT como instrucción de sistema).
- TTS: convierte la respuesta en voz (OpenAI, voz "coral").
- Turno del agente: el agregador del agente. Guarda en la conversación lo que el agente llegó a decir.

Los dos agregadores comparten la misma conversación (LLMContext) y se crean juntos. Si te atascas, la
solución está en practica/solucion/cascada_minima.py.
"""

import argparse
import os

from dotenv import load_dotenv

load_dotenv()  # la clave de OpenAI sale del .env

from pipecat.frames.frames import LLMRunFrame  # noqa: E402
from pipecat.pipeline.pipeline import Pipeline  # noqa: E402
from pipecat.pipeline.worker import PipelineParams, PipelineWorker  # noqa: E402
from pipecat.runner.types import RunnerArguments  # noqa: E402
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

    # ─── Tu tubería ─────────────────────────────────────────────────────────────────────────────
    # Crea aquí el STT, el LLM, el TTS, la conversación con sus dos agregadores, y ponlo todo en orden
    # en el Pipeline. De momento solo entra y sale audio.
    pipeline = Pipeline([
        transporte.input(),
        transporte.output(),
    ])
    # ────────────────────────────────────────────────────────────────────────────────────────────

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
    main(parser)
