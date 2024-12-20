# Rendez-vous patient: Agent vocal

## Projet

L'objectif est simple: Prendre un faux rendez-vous chez un médecin et bloquer la date de réservation en utilisant le framework [pipecat-ai](https://github.com/pipecat-ai/pipecat).

## Methodologie

- D'abord j'ai pris connaisance du bibliothèque pipecat en testant quelques exemples données dans le répo.
- Il y avait déjà une `patient_intake` qui est un boilerplate avec quelques questions de screening pour prendre les informations d'un patient avant une visite chez le médecin et elle est une bonne base pour commencer ce projet.
- Alors, la prèmiere étape est de créer un flow:

  1. Quelques sont les questions à poser?
  2. Comment stocker toutes ces informations?
  3. Vérifier qu'il y a une disponibilité dans l'agenda pour les deux semaines suivantes.
  4. Informer le patient que la date de visite souhaité est confirmé.

- Pour le côté server, j'ai gardé le même code d'une exemple: notamment pour lancer l'app FastAPI et de rediriger vers le Daily room.
- Pour stocker les infos, j'ai utilisé une dictionnaire pour representer un state d'une conversation.
- J'ai ajouté l'agenda google pour vérifier s'il y a une disponibilité

## Environment

Vous allez trouver un fichier `.env-dist` qui contiendra tous les placeholders pour les clés API à mettre.
Additionellement,
if faut que vous vous connectez votre agenda google, avec une application OAuth.
[Voici le lien](https://console.developers.google.com/apis/credentials) pour acceder au console google.
Et puis, aller vers API & services > OAuth Consent screen > Créer un nouveau consent screen
Prochainement: API & Services > Credentials > Create client ID et telecharger le fichier `nom_de_app.json`
Ensuite,
bougez le fichier `.json` vers `~/.credentials/nom_de_app.json`

Et finalement:

```sh
python server.py
```

va lancer le serveur pour tester

## Testing

Pour l'instant j'ai uniquement une teste unitaire qui teste si le résume d'un patient se génère correctement. Je discute ce topic plus vers la fin du readme.

## Challenges rencontrées

- La fonctionnement de STT et TTS n'est pas très claire. Dans quelques exemples, le transcription service de Daily est suffisant pour faire le STT, mais pour d'autres exemples (notamment dans les pipecat-flows), il faut utiliser Deepgram. Cette tendence est très ambiguë.
- C'était un peu dur à passer vers français:

  1. En anglais, le flow était évident: Une étape après l'autre, la transition était rapide + claire.
  2. Problème de compréhension des dates. Je me suis retrouvé plusiers fois avec un message vocale du bot: "N'hésitez pas à me dire le date en format quelquonque. Je m'occupe de le reformatter." ou des fois l'IA ne comprends pas du tout la date si c'est donnée dans un autre format apart AAAA-MM-DD, même avec une instruction spécific. Ça m'a posé un peu de problème de convertir vers le objet `datetime` pour chercher les dates disponibles dans l'agenda.

- Un "footgun" dans le bibliothèque qui peut poser un peu de problème:

```py
async def handler_no_args() -> FlowResult:
    """Handler that doesn't need arguments."""
    result = await fetch_data()
    return {
        "status": "success",
        "data": result
    }
```

Depuis le doc, toutes les fonctions doit avoir la signature comme au dessus. Sauf, il ne mentionne jamais que le champs "data" n'existe pas sur le class `FlowResult`. Et sans un linter / ou meme avec, une petite faut va jeter un `KeyError` qui va faire arreter le frame et le bot n'avencera pas sur l'etape suivante.

j'ai trouvé la bonne manière de le faire dans l'un des exemples du répo:

```py
class MyCustomResult(FlowResult):
    my_custom_field: MyCustomType

async def my_custom_handler() -> MyCustomResult:
    print("all ok now!")
    return {"status": "success", "my_custom_field": "custom_data"}
```

## Améliorations

- Tout d'abord vous allez noter que cette infrastructure est très dur à tester. Actuellement j'ai uniquement des testes unitaires pour les 'handlers' utilisées dans les flows. Mais je pense que ça vaut le coup de créer une autre environment teste avec les clés APIs différents (si possible) pour créer des 'micro flows': chaque étape d'un flow, séparé dans les parties.

- La récuperation des dates disponibles ne vérifie pas si c'est le weekend ou pas. Et il n'a pas encore la fonctionalité de vérifier qu'un créneau aussi est disponible.

- On a aussi un Grand dictionnaire python qui dans le code; ce n'est pas du tout éfficace pour faire les modifications + ça risque de faire un peu de "clutter" dans le code.
  Ce qu'on peut faire c'est de stocker un fichier JSON pour chaque établissement clinique: `nom_du_clinique_flow.json` dans une base de données. Et la récuperer vers le début et remplir les handlers avec une classe Python potentiel: `FlowConfigBuilder`

- Cette abstraction de créer un `FlowConfigBuilder` peut être util même pour tester, par exemple:

```py

# Tester un micro flow
json = await api_request("http://database_url/flows/[flow-id]")
flow = FlowConfigBuilder.from_json(json)
for step in flow:
    step.test()

```

Ou pour créer et exporter un Flow dans une base de données.

```py
# Ajouter une nouvelle étape dans un flow
import os
from typing import ParamSpec, TypeVar, Dict, Callable

P = ParamSpec("P")
T = TypeVar("T")
# Ajouter un step dans un flow
async def sample_handler(name: str) -> Dict[str, str]:
    return {"name": name}

handlers: List[Callable[P, T]] = [sample_handler]
messages: List[ChatCompletionMessageParam] = [{"role": "system", "content": "youre a helpful bot"}]

flow = FlowConfigBuilder(database_url=os.getenv("DB_URL", ""))

flow.add_step("get_prescriptions", messages, handlers, transition_from="start")
flow.export() # Il va faire une requête API POST pour sauvegarder le flow dans une base.
```

Cette méthode aussi permet de versionner les prompts.
