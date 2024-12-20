#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio
from datetime import datetime
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.cartesia import CartesiaTTSService, Language
from pipecat.services.deepgram import DeepgramSTTService, LiveOptions
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.services.daily import (
    DailyParams,
    DailyTransport,
    DailyTranscriptionSettings,
)

from patient import Patient, summarize

sys.path.append(str(Path(__file__).parent.parent))
from cal import create_event, init_calendar, free_times
from runner import configure

from pipecat_flows import FlowArgs, FlowConfig, FlowManager, FlowResult

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


cal = init_calendar(os.getenv("EMAIL_ID", ""))


patient_details: Dict[str, Any] = {}


class DepartmentsResult(FlowResult):
    departments: List[str]


class AvailableDatesResult(FlowResult):
    dates: Iterable[str]


departments = ["Cardiologie", "Kinésithérapie", "Dentiste"]


async def get_departments() -> DepartmentsResult:
    return {"departments": departments, "status": "success"}


async def get_available_dates() -> AvailableDatesResult:
    dates = free_times(cal)
    return {"status": "success", "dates": dates}


async def record_personal_details(args: FlowArgs) -> FlowResult:
    patient_details["name"] = args["name"]
    patient_details["date_of_birth"] = args["date_of_birth"]
    return {"status": "success"}


async def record_user_visit_date(args: FlowArgs) -> FlowResult:
    logger.debug("Inside the record_user_visit_date function")
    logger.debug(f"Got visit date: {args['visit_date']}")
    patient_details["visit_date"] = args["visit_date"]
    p: Patient = Patient(**patient_details)
    logger.debug("Converted patient data into class")
    formatted_date = datetime.strptime(p["visit_date"], "%Y-%m-%d")
    logger.debug("Formatted date")
    try:
        create_event(cal, formatted_date, summarize(p))
        return {"status": "success"}
    except Exception as e:
        logger.exception(f"Failed creating event: {e}")
        return {"status": "failure", "error": str(e)}


async def record_prescriptions(args: FlowArgs) -> FlowResult:
    """Handler for recording prescriptions."""
    patient_details["prescriptions"] = args["prescriptions"]
    return {"status": "success"}
    # In a real app, this would store in patient records


async def record_allergies(args: FlowArgs) -> FlowResult:
    """Handler for recording allergies."""
    patient_details["allergies"] = args["allergies"]
    return {"status": "success"}
    # In a real app, this would store in patient records


async def record_conditions(args: FlowArgs) -> FlowResult:
    """Handler for recording medical conditions."""
    patient_details["conditions"] = args["conditions"]
    return {"status": "success"}


async def record_visit_reasons(args: FlowArgs) -> FlowResult:
    """Handler for recording visit reasons."""
    reasons_list = ", ".join([reason["name"] for reason in args["visit_reasons"]])
    patient_details["visit_reasons"] = reasons_list
    return {"status": "success"}


flow_config: FlowConfig = {
    "initial_node": "start",
    "initial_system_message": [
        {
            "role": "system",
            "content": "Vous êtes Jérome, un réceptionniste pour une centre médicale Léo Lagrange qui est chargé de prendre rendez-vous chez un médecin. Votre travail consiste à collecter des informations importantes auprès de l’utilisateur et la date de rendez-vous avant sa visite chez le médecin. Vous n'êtes pas un professionnel de la santé, vous ne devez donc donner aucun conseil. Gardez vos réponses courtes. Votre travail consiste à collecter des informations à remettre à un médecin. Ne faites pas d'hypothèses sur les valeurs à intégrer dans les fonctions. Demandez des éclaircissements si la réponse d'un utilisateur est ambiguë. N'oubliez pas de toujours avancer la conversation et de passer à l'étape suivante sans que l'utilisateur n'intervienne. C'est a dire, toujours faire un appel vers une fonction donnée.",
        }
    ],
    "nodes": {
        "start": {
            "messages": [
                {
                    "role": "system",
                    "content": "Commencez par vous présenter avec votre nom (Jérome). Demandez ensuite à l’utilisateur son prénom, nom et sa date de naissance, y compris l’année. Lorsqu'ils répondent avec les informations requises, appelez la fonction record_personal_details. Notez bien que l'utilisateur a le droit de vous donner une date dans un format quelquonque, mais c'est votre tache de reformater en AAAA-MM-JJ. Après procédez vers l'étape pour recolter les informations des prescriptions de l'utilisateur.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "record_personal_details",
                        "handler": record_personal_details,
                        "description": "fonction pour enregistrer et vérifier les détails d'un utilisateur.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "le prenom et nom de l'utilisateur",
                                },
                                "date_of_birth": {
                                    "type": "string",
                                    "description": "la date de naissance de l'utilisateur",
                                },
                            },
                            "required": ["name", "date_of_birth"],
                        },
                        "transition_to": "get_prescriptions",
                    },
                },
            ],
        },
        "get_prescriptions": {
            "messages": [
                {
                    "role": "system",
                    "content": "Demandez à l'utilisateur une liste des ordonnances qu'il prend actuellement. Une fois que l'utilisateur a fourni une liste de ses médicaments sur ordonnance ou confirmé qu'ils n'en ont pas, appelez cette fonction : record_prescriptions et avancez vers la prochaine étape pour enregistrer les allergies de l'utilisateur",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "record_prescriptions",
                        "handler": record_prescriptions,
                        "description": "Une fonction pour enregistrer une liste de prescriptions pour un utilisateur donné.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "prescriptions": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "medication": {
                                                "type": "string",
                                                "description": "le nom du médicament",
                                            },
                                            "dosage": {
                                                "type": "string",
                                                "description": "le dosage du médicament",
                                            },
                                        },
                                        "required": ["medication", "dosage"],
                                    },
                                }
                            },
                            "required": ["prescriptions"],
                        },
                        "transition_to": "get_allergies",
                    },
                },
            ],
        },
        "get_allergies": {
            "messages": [
                {
                    "role": "system",
                    "content": "Demandez à l'utilisateur s'il a des allergies. Une fois qu'ils ont répertorié leurs allergies ou confirmé qu'ils n'en ont pas, appelez la fonction record_allergies et avancez vers l'étape pour enregistrer les conditions médicales de l'utilisateur",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "record_allergies",
                        "handler": record_allergies,
                        "description": "Enregistrez les allergies de l'utilisateur. Une fois confirmé, l’étape suivante consiste à recueillir les conditions médicales.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "allergies": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "le nom d'allergie de l'utilisateur",
                                            },
                                        },
                                        "required": ["name"],
                                    },
                                }
                            },
                            "required": ["allergies"],
                        },
                        "transition_to": "get_conditions",
                    },
                },
            ],
        },
        "get_conditions": {
            "messages": [
                {
                    "role": "system",
                    "content": "Recueillir des informations sur l’état de santé apart la raison de visite. Renseignez-vous sur leurs problèmes de santé si l'utilisateur en posède. Après avoir enregistré les conditions (ou confirmé aucune), passez à l'étape suivante pour recueillir les raisons de visite chez le médecin.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "record_conditions",
                        "handler": record_conditions,
                        "description": "Enregistrez les conditions médicales de l’utilisateur. Une fois confirmée, l'étape suivante consiste à collecter les raisons de la visite.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "conditions": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "La condition médicale de l'utilisateur",
                                            },
                                        },
                                        "required": ["name"],
                                    },
                                }
                            },
                            "required": ["conditions"],
                        },
                        "transition_to": "get_visit_reasons",
                    },
                },
            ],
        },
        "get_visit_reasons": {
            "messages": [
                {
                    "role": "system",
                    "content": "Recueillir des informations sur la raison de leur visite. Vérifiez bien que les raisons de visite concerne bien les départements de santé présent dans le centre médicale en appelant la fonction get_departments. Si la raison ne concerne pas les départements présents, informet l'utilisateur de prendre un rendez-vous dans un autre centre médicale. Demandez-leur ce qui les amène chez le médecin aujourd'hui. Après avoir enregistré leurs raisons, procédez à la planification du jour et de la date de la visite.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_departments",
                        "handler": get_departments,
                        "description": "Recueillir les départements / domaines de santé disponibles dans le centre médicale.",
                        "parameters": {"type": "object", "properties": {}},
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "record_visit_reasons",
                        "handler": record_visit_reasons,
                        "description": "Enregistrez les raisons de leur visite. Une fois confirmée, l'étape suivante consiste à fixer la date du rendez-vous.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "visit_reasons": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "La raison de la visite de l'utilisateur",
                                            },
                                        },
                                        "required": ["name"],
                                    },
                                }
                            },
                            "required": ["visit_reasons"],
                        },
                        # "transition_to": "get_available_dates",
                    },
                },
            ],
        },
        "get_available_dates": {
            "messages": [
                {
                    "role": "system",
                    "content": "Obtenez les dates disponibles dans le calendrier et demandez au patient quelle date il préfère, puis procédez vers l'étape pour confirmer la date de la visite.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_available_dates",
                        "handler": get_available_dates,
                        "description": "Obtenez les dates disponibles pour une visite dans les prochaines semaines.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                        },
                        "transition_to": "get_user_visit_date",
                    },
                },
            ],
        },
        "get_user_visit_date": {
            "messages": [
                {
                    "role": "system",
                    "content": "Collectez la date de visite souhaitée auprès de l'utilisateur. Notez bien que l'utilisateur a le droit de vous donner une date dans un format quelquonque, mais c'est votre tache de reformater en AAAA-MM-JJ. après avoir formatté la date, appelez la fonction record_user_visit_date",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "record_user_visit_date",
                        "handler": record_user_visit_date,
                        "description": "Enregistrez la date de visite de l’utilisateur. Notez bien que l'utilisateur a le droit de vous donner une date dans un format quelquonque, mais c'est votre tache de reformater en AAAA-MM-JJ.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "visit_date": {
                                    "type": "string",
                                    "description": "la date de visite de l'utilisateur",
                                }
                            },
                        },
                        "transition_to": "confirm",
                    },
                },
            ],
        },
        "confirm": {
            "messages": [
                {
                    "role": "system",
                    "content": "Informez à l'utilisateur que la date est bien pris en compte. Une fois confirmé, remerciez-les, puis utilisez la fonction complete_intake pour mettre fin à la conversation.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "complete_intake",
                        "description": "Terminez le processus d’admission",
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": "end",
                    },
                },
            ],
        },
        "end": {
            "messages": [
                {
                    "role": "system",
                    "content": "Remerciez-les pour leur temps et mettez fin à la conversation.",
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
    },
}


async def handle_transition(function_name: str, args: Dict[str, Any], flow_manager):
    if function_name == "get_departments":
        if args["department"] not in departments:
            await flow_manager.set_node("end")


async def main():
    """Main function to set up and run the patient intake bot."""
    async with aiohttp.ClientSession() as session:
        (room_url, _) = await configure(session)

        transport = DailyTransport(
            room_url,
            None,
            "Jérome",
            DailyParams(
                audio_out_enabled=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                vad_audio_passthrough=True,
                transcription_enabled=True,
                transcription_settings=DailyTranscriptionSettings(
                    language="fr",
                ),
            ),
        )

        stt = DeepgramSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY", ""),
            live_options=LiveOptions(language=Language.FR),
        )
        tts = CartesiaTTSService(
            params=CartesiaTTSService.InputParams(language=Language.FR),
            api_key=os.getenv("CARTESIA_API_KEY", ""),
            voice_id="0418348a-0ca2-4e90-9986-800fb8b3bbc0",  # French man
        )
        llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")

        context = OpenAILLMContext()
        context_aggregator = llm.create_context_aggregator(context)

        pipeline = Pipeline(
            [
                transport.input(),  # Transport input
                stt,
                context_aggregator.user(),  # User responses
                llm,  # LLM
                tts,  # TTS
                transport.output(),  # Transport output
                context_aggregator.assistant(),  # Assistant responses
            ]
        )

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

        # Initialize flow manager with LLM
        flow_manager = FlowManager(
            task=task,
            llm=llm,
            tts=tts,
            flow_config=flow_config,
            transition_callback=handle_transition,
        )

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            # Initialize the flow processor
            await flow_manager.initialize([])
            # Kick off the conversation using the context aggregator
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        runner = PipelineRunner()
        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
