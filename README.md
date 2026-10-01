# OcéEns II

Plateforme d'évaluation des enseignements conçue pour l'école d'ingénieurs EPF.

## Aperçu

L'application **OcéEns II** permet aux responsables de programme, animateurs, directions de campus et administrateurs de créer et gérer des sondages d'évaluation pour les différentes filières de l'EPF, et aux étudiants d'y répondre. Les réponses peuvent être exportées, visualisées, et synthétisées via un LLM. L'interface est habillée de la charte graphique officielle de l'EPF.

### Stack technique

| Composant | Technologie |
|-----------|-------------|
| **Framework** | FastAPI (Python 3.12) |
| **Authentification** | Microsoft Entra ID (Azure AD) via OAuth2.0 / MSAL, Microsoft Graph |
| **Base de données** | SQLite (via SQLAlchemy + SQLModel) |
| **Templating** | Jinja2 (rendu serveur) |
| **Frontend** | HTML / CSS / JavaScript, sans framework |
| **Serveur** | Uvicorn |
| **Journalisation** | Module standard Python `logging`, via les handlers Uvicorn |
| **Exports** | Pandas (CSV) |
| **Synthèses de verbatims** | Daemon séparé, appel à un LLM (`requests-cache`, `markdown-it-py`) |

---

## Rôles

- `student` : répond aux sondages auxquels il est inscrit.
- `program_manager:<code>` : gère les sondages de sa/ses filière(s).
- `facilitator:<code>` : anime les sondages de sa/ses filière(s).
- `campus_manager:<campus>` : périmètre à l'échelle du campus.
- `admin` : administration générale.

Un utilisateur peut cumuler plusieurs rôles, chacun avec son propre périmètre (codes filière ou campus séparés par `;`).

---

## Pages et routes principales

| Route | Description |
|-------|-------------|
| `/` | Accueil, hub d'authentification. |
| `/login`, `/auth/callback`, `/logout` | Flux d'authentification Microsoft Entra ID. |
| `/dev/login` | Connexion de développement : page de choix de l'utilisateur en `GET`, connexion en `POST` (uniquement avec `AUTH_MODE=dev`, voir [Authentification en mode développement](#authentification-en-mode-développement)). |
| `/dashboard/student` | Dashboard étudiant. |
| `/dashboard/program-manager` | Dashboard responsable de programme. |
| `/dashboard/facilitator` | Dashboard animateur. |
| `/dashboard/campus-manager` | Dashboard direction de campus. |
| `/dashboard/teachers/analytics` | Score de satisfaction par enseignant, filtrable par année / semestre / formation. Accessible aux rôles `campus_manager` et `program_manager`, scopé au périmètre de chacun. |
| `/dashboard/admin` | Dashboard administrateur. |
| `/dashboard/survey-create` | Création / paramétrage d'un sondage. |
| `/api/surveys/{survey_id}` | Questionnaire (réponse au sondage). |
| `/api/surveys/{survey_id}/status` | Changement de statut d'un sondage. |
| `/api/surveys/{survey_id}/students` | Gestion des étudiants inscrits à un sondage. |
| `/api/surveys/{survey_id}/export` | Export CSV des réponses. |
| `/api/surveys/{survey_id}/visualisation` | Visualisation des réponses. Accepte `?teacher=<nom>` pour arriver déjà filtré sur un enseignant. |
| `/api/surveys/{survey_id}/generate-summaries` | Lancement de la génération de synthèses LLM. |
| `/api/surveys/{survey_id}/destroy-summaries` | Suppression des synthèses générées. |
| `/api/users/{user_id}/role` | Modification du rôle d'un utilisateur. |
| `/backend/prompts` | Liste des prompts LLM (admin uniquement). |
| `/backend/prompts/new` | Formulaire de création d'un prompt. |
| `/backend/prompts/{id}/edit` | Formulaire de modification d'un prompt. |
| `/api/prompts` | Création d'un prompt (POST, form). |
| `/api/prompts/{id}` | Modification (`PUT`) ou suppression (`DELETE`) d'un prompt, en fetch. Refusées (`409`) si le prompt est référencé dans `summaries`. |
| `/backend/templates` | Administration des modèles de sondage (admin uniquement). |
| `/backend/providers` | Fournisseurs LLM (admin uniquement, voir [Fournisseurs LLM](#fournisseurs-llm-synthèses-de-verbatims)). |
| `/backend/llm/prices`, `/backend/llm/costs` | Grille tarifaire et coût des synthèses (voir [Coût des synthèses](#coût-des-synthèses)). |

---

## Installation et démarrage

### Prérequis

- [`uv`](https://docs.astral.sh/uv/getting-started/installation/), qui installe au besoin Python 3.12 (la version de `.python-version` et de l'image Docker), ou Docker seul (Docker Desktop avec le backend WSL 2 sous Windows).
- Aucun credential : un clone neuf démarre en [connexion de développement](#authentification-en-mode-développement), sans Entra ni clé LLM.

### Premier démarrage : créer le `.env`

Le code est un package installable, `oceens`, dans `src/oceens/`. Il trouve ses `templates/`, `static/` et `import/` à côté de lui, et non dans le dossier courant. Les commandes ci-dessous sont données depuis la racine du dépôt. Depuis un autre dossier, ajouter `--project <chemin du clone>` à `uv run`.

```bash
cp .env.example .env                 # macOS / Linux
Copy-Item .env.example .env          # Windows (PowerShell)
```

`.env.example` livre `AUTH_MODE=dev` (aucune variable `ENTRA_*` nécessaire) et `LLM_API_KEY` vide : l'application démarre, seules les synthèses sont indisponibles. Chaque variable est décrite dans [Configuration](#configuration).

### Avec Docker Compose

```bash
docker compose up --build
```

Sans `.env`, la commande échoue avec `env file .env not found` : copiez d'abord `.env.example`. Le `.env` est lu via `env_file` au lancement et n'est jamais copié dans l'image (`.dockerignore`).

- La base SQLite est persistée sur l'hôte, dans `./database/` par défaut, ou dans le dossier indiqué par `LOCAL_DATABASE_DIR`.
- `./src/oceens/import/` est monté dans le conteneur (fichiers CSV du seed).
- L'image installe les dépendances depuis `uv.lock` (`uv sync --locked`), puis lance le point d'entrée `oceens` (Uvicorn sur `0.0.0.0:8000`) sans `--reload` : après une modification du code, relancer `docker compose up --build`.
- `restart: always` : le conteneur redémarre tant qu'il n'est pas arrêté par `docker compose down`.

### Sans Docker

Les dépendances sont déclarées dans `pyproject.toml` et figées dans `uv.lock`. `uv sync` crée `.venv` et y installe ces versions exactes, ainsi que le package `oceens` (en mode éditable : une modification du code est prise en compte sans réinstaller). Les commandes sont les mêmes sous macOS / Linux (bash) et sous Windows (PowerShell) :

```bash
uv sync --locked
uv run uvicorn oceens.main:app --port 8000
```

`uvicorn` n'écoute ici que sur `127.0.0.1`. Le point d'entrée `oceens`, qu'utilisent l'image Docker et `launch.sh`, écoute lui sur `0.0.0.0` : en `AUTH_MODE=dev`, il ouvrirait la connexion de développement à tout le réseau.

Ajouter `--reload` pour recharger l'application à chaque modification du code. `fastapi dev` ne fonctionne pas : il exige `fastapi[standard]`, absent de `pyproject.toml`.

Pour ajouter ou mettre à jour une dépendance : `uv add <paquet>==<version>`, qui met à jour `pyproject.toml` et `uv.lock`, à commiter ensemble.

Au démarrage, l'application crée la base `db_oceens.db` (dans `database/` à la racine du dépôt, ou dans `LOCAL_DATABASE_DIR`) et ses tables. Si la base ne contient aucun utilisateur, elle y insère un jeu de démonstration (utilisateurs, rôles, sondages, réponses depuis `src/oceens/import/`). Pour repartir de zéro, supprimer `db_oceens.db`.

Ouvrez ensuite **http://localhost:8000** : en mode `dev`, `/dev/login` liste les utilisateurs du jeu de démonstration (par exemple `antoine.gademer@epf.fr`, admin).

### Daemon de synthèses LLM (optionnel)

Les synthèses sont générées par le daemon `oceens-summaries` (`src/oceens/summaries_generator_daemon.py`), un processus séparé de l'application. Les deux ne communiquent que par la table `summaries`, qui sert de file d'attente :

- quand un responsable demande les synthèses d'un sondage, l'application y insère des lignes à `http_status = 0` ;
- le daemon les traite une par une, appelle le fournisseur LLM et réécrit chaque ligne : `200` en cas de succès, un autre code en cas d'échec, avec un message lisible dans `metadata_text`. Quand la file est vide, il revérifie toutes les 30 secondes.

Sans daemon, les demandes restent en attente à `http_status = 0`. Il lit le même `.env` et la même base que l'application, et met en cache les réponses du fournisseur dans `cache_llm.db`, dans le dossier courant :

```bash
uv run oceens-summaries
```

`Ctrl+C` l'arrête. Avec `RUN_SUMMARIES_DAEMON=1`, l'application lance elle-même le daemon au démarrage et l'arrête à la fermeture. Sous Docker Compose, c'est la seule façon de le lancer, puisque le conteneur n'exécute qu'Uvicorn. Avec `launch.sh`, il faut laisser la variable vide, car ce script lance déjà le daemon.

Sans `LLM_API_KEY`, le daemon ne contacte pas le fournisseur : chaque synthèse demandée est marquée en erreur de configuration (`http_status` 500, « variable d'environnement absente ou vide »).

### En production : `launch.sh`

`launch.sh` est écrit pour le serveur de l'école, où `uv` doit être installé : il se place dans `/home/mde-admin/OceENS`, synchronise `.venv` depuis `uv.lock` (`uv sync --locked`), puis lance les points d'entrée `oceens` (Uvicorn sur `0.0.0.0:8000`) et `oceens-summaries` dans deux sessions `screen`.

### Vérifier son installation

Voir [Validation avant contribution](#validation-avant-contribution) : la vérification de référence est le [smoke test manuel](docs/smoke-test.md).

---

## Journalisation

Les logs applicatifs utilisent le module standard Python `logging` et les
loggers d'Uvicorn : `uvicorn` (`core/auth.py`, `core/seed.py`,
`core/dependencies.py`) et `uvicorn.error` (`core/database.py` et `services/`).
Les messages de l'application reprennent ainsi le format, les couleurs et les
handlers déjà configurés par le serveur. Lancé seul, le daemon de synthèses
configure son propre handler (`logging.basicConfig`, niveau `INFO`, sur
`stderr`).

Les niveaux sont utilisés selon leur gravité :

| Niveau | Utilisation |
|--------|-------------|
| `DEBUG` | Informations détaillées utiles au développement et au seeding. |
| `INFO` | Démarrage, arrêt et opérations applicatives normales. |
| `WARNING` | Ressource attendue absente ou situation non bloquante. |
| `ERROR` / `EXCEPTION` | Échec d'une opération ; `logger.exception()` conserve la traceback. |
| `CRITICAL` | Configuration indispensable manquante, empêchant le démarrage. |

Exemple :

```python
import logging

logger = logging.getLogger("uvicorn")

logger.info("Opération terminée")

try:
    operation_risquee()
except Exception:
    logger.exception("Échec de l'opération")
```

Les nouveaux diagnostics doivent utiliser le logger approprié plutôt que
`print()`. Le logger `uvicorn` est réglé sur `DEBUG` dans
`core/dependencies.py`. Les logs applicatifs passent par le handler Uvicorn, généralement
écrit sur `stderr` ; avec une redirection séparée, utilisez par exemple
`2> error.log` pour les récupérer.

---

## Configuration

La configuration passe par des variables d'environnement. `.env.example` est le modèle de référence : copiez-le en `.env` à la racine du projet (voir [Premier démarrage](#premier-démarrage--créer-le-env)). L'application et le daemon lisent ce `.env` au démarrage (`load_dotenv()`), et une variable déjà définie dans l'environnement l'emporte sur celle du fichier. Docker Compose le transmet au conteneur via `env_file`.

Une configuration de démarrage invalide arrête l'application avec une erreur `CRITICAL` et le code de sortie 1.

| Variable | Rôle |
|----------|------|
| `AUTH_MODE` | `entra` (défaut si absente ou vide) : Microsoft Entra ID. `dev` : [connexion de développement](#authentification-en-mode-développement), à ne jamais utiliser en production. Casse et espaces ignorés ; toute autre valeur arrête l'application. `.env.example` livre `dev`. |
| `DEV_LOGIN_KEY` | Mode `dev` uniquement, optionnelle. Définie : chaque connexion doit la fournir (champ `key`), sinon `401`. Vide : connexion ouverte à tous. Ignorée, avec un avertissement, en `entra`. |
| `ALLOWED_DOMAINS` | Domaines mail autorisés, séparés par des virgules. À la connexion, un autre domaine reçoit `403`. En `entra`, sans valeur, **aucun** domaine n'est accepté ; en `dev`, la valeur par défaut est `epf.fr,epfedu.fr`. L'ajout d'utilisateurs et l'inscription d'étudiants utilisent `epf.fr,epfedu.fr` par défaut dans les deux modes. |
| `SECRET_KEY` | Signe les cookies de session : quiconque la connaît peut forger une session, admin comprise. **Obligatoire en `entra`** : absente ou vide, l'application refuse de démarrer. En `dev`, si elle est vide, une clé aléatoire est tirée à chaque démarrage (avec un avertissement) et les sessions sont perdues au redémarrage. Générer une valeur avec `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
| `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `ENTRA_TENANT_ID` | Application Entra ID. **Obligatoires en `entra`** : si l'une manque, l'application refuse de démarrer. Inutiles en `dev`. |
| `REDIRECT_URI` | URL de retour après la connexion Entra (`…/auth/callback`). Défaut : `https://localhost/auth/callback`. |
| `LOCAL_DATABASE_DIR` | Dossier de `db_oceens.db`, absolu ou relatif à la racine du projet ; créé s'il manque. Défaut : `database/`. Avec Docker Compose, dossier de l'hôte monté sur `/app/database`. |
| `LLM_API_KEY` | Clé du fournisseur LLM par défaut (Ollama EPF, clé personnelle sur <https://locallm.mde.epf.fr>). Vide : l'application démarre, mais les synthèses demandées sont marquées en erreur de configuration. |
| `RUN_SUMMARIES_DAEMON` | `1`, `true`, `yes` ou `on` : l'application lance et arrête elle-même le [daemon de synthèses](#daemon-de-synthèses-llm-optionnel). Vide avec `launch.sh`, qui le lance déjà. |
| `LLM_*`, `*_API_KEY` | Clés des autres [fournisseurs LLM](#fournisseurs-llm-synthèses-de-verbatims), sous le nom déclaré dans `/backend/providers`. |

> [!CAUTION]
> Ne jamais commiter le fichier `.env`. Il est déjà listé dans le `.gitignore`, tout comme les fichiers `*.db` (`database/db_oceens.db`, `cache_llm.db`).

---

## Fournisseurs LLM (synthèses de verbatims)

Les synthèses de verbatims sont générées par un LLM. Le fournisseur est
**configurable depuis l'interface** (`/backend/providers`, admin uniquement),
sans toucher au code. Le fournisseur par défaut est **Ollama EPF**
(`https://locallm.mde.epf.fr/ollama`, clé `LLM_API_KEY`, modèle `gemma4:26b`).
Il est créé au démarrage s'il n'existe pas déjà sous ce nom.

### Types d'API supportés

| `api_type` | Couvre |
|------------|--------|
| `ollama`    | Serveurs Ollama (local, EPF, tiers) |
| `openai`    | OpenAI **et tout endpoint compatible OpenAI** : vLLM, Groq, Mistral, LM Studio… |
| `anthropic` | API Claude (Anthropic) |

### Principe de sécurité : aucune clé en base

La base SQLite n'est pas chiffrée et part dans les sauvegardes. **Aucune clé
d'API n'y est donc stockée.** La table `llm_providers` ne contient que le *nom*
de la variable d'environnement (`api_key_env`, ex. `OPENAI_API_KEY`) ; la valeur
reste dans le `.env` et n'est résolue qu'au moment de l'appel. Ce nom doit
correspondre à `LLM_*` ou `*_API_KEY`. Une liste noire exclut en plus les secrets
de l'application (`SECRET_KEY`, `ENTRA_CLIENT_SECRET`…), pour qu'un fournisseur
ne puisse pas pointer vers eux.

### Ajouter un nouveau fournisseur

1. **Ajouter la clé au `.env`** avec un nom conforme (`LLM_*` ou `*_API_KEY`) :

   ```env
   OPENAI_API_KEY=sk-...
   ```

2. **Redémarrer l'application et le daemon** de synthèses : les variables du
   `.env` ne sont lues qu'au démarrage. L'application en a besoin pour
   l'indicateur de clé et le bouton **Tester**, le daemon pour générer.

3. **Créer le fournisseur** dans `/backend/providers` → *+ Nouveau fournisseur* :
   renseigner le nom, le type d'API, l'URL de base, le nom de la variable d'env
   (`OPENAI_API_KEY`), et un modèle par défaut. Dans la liste, la colonne
   **Variable de clé** indique **présente** ou **absente** : « présente » veut
   seulement dire que la variable est définie dans l'environnement de
   l'application, **même vide** (c'est le cas de `LLM_API_KEY=` livré par
   `.env.example`). Le bouton **Tester**
   vérifie que l'URL et la clé répondent, puis envoie une génération d'un token
   pour confirmer que le compte peut réellement générer (voir ci-dessous).

4. **Relier un prompt** au fournisseur : dans `/backend/prompts`, un `<select>`
   permet de choisir le fournisseur d'un prompt. Un prompt sans fournisseur
   (`provider_id` NULL) retombe automatiquement sur Ollama EPF.

> [!NOTE]
> Un fournisseur référencé par au moins un prompt ne peut pas être supprimé
> (pour ne pas casser la configuration de ces prompts) : la liste se recharge
> avec un message d'erreur.

### Crédit épuisé et autres erreurs de fournisseur

Chaque fournisseur signale ses pannes dans un format différent : un crédit
épuisé est un `429 insufficient_quota` chez OpenAI, mais un `400 « Your credit
balance is too low »` chez Anthropic. `services/llm_client.py` normalise ces
réponses en catégories (`quota`, `rate_limit`, `auth`, `model`, `server`) et en
tire un message lisible :

> ⚠️ Crédit ou quota épuisé chez le fournisseur : la clé est valide mais le
> compte ne peut plus générer. Rechargez le compte ou choisissez un autre
> fournisseur. (fournisseur OpenAI, modèle gpt-4o-mini, HTTP 429)

Ce message est écrit dans `Summary.metadata_text` à la place du JSON brut — il
est donc visible directement depuis l'interface quand une synthèse échoue. La
réponse brute du fournisseur reste dans les logs du daemon pour le diagnostic.

> [!IMPORTANT]
> Le bouton **Tester** ne se contente pas de lister les modèles (`GET /api/tags`
> chez Ollama, `GET /v1/models` chez OpenAI et Anthropic) : cette liste répond
> encore parfaitement avec un solde à zéro. Un ping de génération d'un token (coût négligeable) est donc
> envoyé ensuite — c'est le seul moyen de repérer un crédit épuisé **avant** de
> lancer une campagne de synthèses.

---

## Coût des synthèses

Le coût de chaque synthèse est **mesuré, pas estimé**. Au moment de la
génération, le daemon enregistre les compteurs de tokens renvoyés par le
fournisseur (`Summary.input_tokens`, `output_tokens`, `model_used`) : c'est la
seule occasion de les capturer, aucune API ne permet de les redemander après
coup. Le montant est ensuite obtenu en croisant ces compteurs avec la grille
tarifaire ; quand le tarif comporte un forfait en fourchette, le coût est une
fourchette.

> [!NOTE]
> Cette section remplace les anciens scripts `llm-utils/token-counting/`, qui
> comptaient les tokens du **code source du dépôt** et les multipliaient par un
> tarif codé en dur. Cette mesure ne disait rien de la dépense réelle de
> l'application. Le suivi porte désormais sur les appels effectivement facturés.

### Grille tarifaire — `/backend/llm/prices`

Les tarifs vivent en base (table `llm_model_prices`), **en euros**. Un tarif a
deux composantes, qui s'additionnent : un **forfait par synthèse** (fourchette
min–max) et un **prix au million de tokens** (entrée et sortie). Ils sont
éditables depuis l'administration : pas besoin de livrer une version pour
suivre une révision de prix, ni pour couvrir un fournisseur ajouté localement.
Un tarif peut être saisi en dollars : il est converti au taux USD → EUR
enregistré sur la même page (0,92 par défaut).

Sont pré-remplis au démarrage (`seed_model_prices`, idempotent — un tarif
corrigé à la main n'est jamais réécrit) :

| Modèle | Forfait par synthèse | Entrée €/M | Sortie €/M |
| --- | ---: | ---: | ---: |
| `gemma4:26b` (Ollama EPF, auto-hébergé) | 0,02 – 0,05 € | 0.00 | 0.00 |
| `claude-opus-5` | — | 4.60 | 23.00 |
| `claude-sonnet-5` | — | 2.76 | 13.80 |
| `claude-haiku-4-5` | — | 0.92 | 4.60 |

Le forfait du LLM de l'école couvre GPU, électricité et amortissement du
serveur : auto-hébergé ne veut pas dire gratuit. Les tarifs Claude sont la
grille publique en dollars, convertie au taux par défaut.

Les tarifs des autres fournisseurs (OpenAI, Mistral, Groq…) sont **à saisir** :
ils ne sont pas devinés. Un tarif spécifique à un fournisseur l'emporte sur un
tarif générique portant le même nom de modèle.

### Consultation

| Où | Quoi |
| --- | --- |
| `/backend/llm/costs` (bouton « Coût des synthèses 💰 » du dashboard admin) | Coût global, détaillé par modèle et par sondage (admin) |
| Bouton 💰 sur une ligne de sondage | Coût des synthèses de ce sondage (`GET /api/surveys/{id}/cost`) |

Le bouton 💰 apparaît dès qu'une synthèse du sondage est générée, sur les
dashboards qui permettent d'en lancer. Seul le rôle `admin` obtient le montant :
les autres rôles reçoivent « Accès refusé » (`403`). En effet, `COST_ROLES`
(`routers/llm/costs.py`) autorise `admin`, `rp` et `direction`, et les deux
derniers ne correspondent à aucun rôle de l'application.

### Ce qui n'est pas chiffré

Une synthèse n'est pas chiffrable quand ses compteurs manquent (générée avant
cette fonctionnalité, ou fournisseur qui ne les expose pas) ou quand son modèle
n'a pas de tarif enregistré. Elle est alors **comptée à part**, jamais estimée
ni ramenée à zéro : un montant inventé serait plus nuisible qu'un montant
absent, puisqu'il s'afficherait avec l'autorité d'un montant réel. Les écrans
signalent explicitement qu'un total est partiel.

À distinguer d'un coût **nul** : un modèle dont le tarif enregistré vaut 0 coûte
réellement 0,00 €, ce qui n'est pas la même information que « inconnu ».

> [!IMPORTANT]
> Le suivi démarre à la mise en service : les synthèses générées auparavant
> n'ont pas de compteurs en base et ne peuvent pas être chiffrées
> rétroactivement.

---

## Structure du projet

```
OceENS/
├── launch.sh                     # Script de lancement (production, sans Docker)
├── pyproject.toml                # Métadonnées, dépendances et points d'entrée du package
├── uv.lock                       # Versions exactes des dépendances (uv sync --locked)
├── .python-version               # Version de Python (3.12)
├── Dockerfile                    # Image Docker de l'application
├── docker-compose.yaml           # Lancement avec Docker Compose (lit .env)
├── .dockerignore                 # Fichiers exclus du build Docker
├── .env.example                  # Modèle du .env, référence des variables
├── .env                          # Variables d'environnement (⚠️ non commité)
├── .gitignore                    # Fichiers et dossiers ignorés par Git
├── CONTEXT.md                    # Vocabulaire du domaine
│
├── src/
│   └── oceens/                   # Package Python installable (`import oceens`)
│       ├── __init__.py
│       ├── main.py               # Fabrique FastAPI, middlewares, routeurs ; point d'entrée `oceens`
│       ├── sondage_loader.py     # Chargement d'un sondage complet pour l'export
│       ├── survey_loader_from_xlsx.py  # Import de sondages depuis un fichier Excel
│       ├── summaries_generator_daemon.py  # Daemon des synthèses LLM ; point d'entrée `oceens-summaries`
│       │
│       ├── core/                         # Accès bas niveau et sécurité
│       │   ├── auth.py                   #   Authentification Microsoft Entra ID (login, logout, callback) et connexion de développement
│       │   ├── database.py               #   Moteur SQLite et dépendance SessionDep
│       │   ├── security.py               #   Rôles, périmètres, contrôle d'accès
│       │   ├── dependencies.py           #   templates Jinja et logger partagés
│       │   └── seed.py                   #   Données initiales et synchronisation des formations
│       │
│       ├── models/                       # Schéma SQLModel, un fichier par table
│       │   ├── __init__.py               #   Ré-exporte toutes les classes (voir sa docstring)
│       │   └── User.py, Survey.py, ...
│       │
│       ├── routers/                      # Routes découpées par domaine métier
│       │   ├── pages.py                  #   Accueil et dashboards par rôle
│       │   ├── surveys.py                #   Sondages : CRUD, statut, export, visualisation
│       │   ├── students.py               #   Inscription des étudiants à un sondage
│       │   ├── users.py                  #   Gestion des rôles utilisateurs
│       │   ├── summaries.py              #   Déclenchement des synthèses LLM
│       │   ├── prompts.py                #   Administration des prompts
│       │   ├── survey_templates.py       #   Administration des modèles de sondage
│       │   ├── sections_questions.py     #   Administration des sections et questions
│       │   └── llm/                      #   Administration LLM (URLs inchangées)
│       │       ├── _access.py            #     Contrôle d'accès partagé des écrans LLM
│       │       ├── providers.py          #     Fournisseurs LLM (CRUD + test de connexion)
│       │       ├── prices.py             #     Grille tarifaire par modèle
│       │       └── costs.py              #     Coût global et coût par sondage
│       │
│       ├── services/                     # Logique métier
│       │   ├── helpers.py                # Navigation, statistiques, filtres, tri
│       │   ├── visualisation_data.py     # Agrégations et contexte de visualisation
│       │   ├── llm_client.py             # Client LLM multi-fournisseur (ollama/openai/anthropic)
│       │   ├── llm_costs.py              # Coût des synthèses (forfait + tokens mesurés × grille tarifaire)
│       │   ├── settings_store.py         # Réglages en base (taux USD → EUR)
│       │   └── export_csv.py             # Export CSV des réponses
│       │
│       ├── import/                       # CSV lus par le seed (formations, réponses de démonstration)
│       │
│       ├── templates/                    # Templates HTML (Jinja2)
│       │   ├── index.html                     # Page d'accueil / login
│       │   ├── dev_login.html                 # Connexion de développement (AUTH_MODE=dev)
│       │   ├── dashboard/
│       │   │   ├── admin.html
│       │   │   ├── student.html
│       │   │   ├── program_manager.html
│       │   │   ├── facilitator.html
│       │   │   ├── campus_manager.html
│       │   │   ├── teachers-analytics.html       # Satisfaction des enseignants (campus_manager, program_manager)
│       │   │   ├── survey.html                   # Réponse au sondage
│       │   │   ├── survey_create.html            # Création de sondage
│       │   │   └── visualisation.html            # Visualisation des réponses
│       │   ├── backend/                       # Pages d'administration (admin only)
│       │   │   ├── prompts.html               # Liste des prompts LLM
│       │   │   ├── prompt_form.html           # Formulaire create/edit partagé
│       │   │   ├── templates.html             # Modèles de sondage
│       │   │   └── llm/                       # Écrans LLM (fournisseurs, tarifs, coûts)
│       │   │       ├── providers.html
│       │   │       ├── provider_form.html
│       │   │       ├── prices.html            # Grille tarifaire éditable
│       │   │       └── costs.html             # Coût global et par sondage
│       │   └── template_parts/                # Fragments réutilisables entre dashboards
│       │       ├── part_site_header.html
│       │       ├── part_dashboard_navigation.html
│       │       ├── part_theme_switcher.html
│       │       └── ...
│       │
│       └── static/
│           ├── css/                      # admin.css, student.css, program_manager.css, survey.css,
│           │                              # survey_create.css, visualisation.css, prompt_form.css,
│           │                              # llm_backend.css (écrans LLM), theme.css, site_header.css,
│           │                              # dashboard_navigation.css, responsive.css
│           ├── js/
│           │   └── survey.js
│           └── img/
│
├── docs/
│   ├── smoke-test.md             # Smoke test manuel, avant toute contribution
│   ├── adr/                      # Décisions d'architecture
│   └── agents/                   # Consignes pour les agents (issues, labels, domaine)
│
├── database/                     # Dossier contenant la base de données (ignoré par Git)
│   └── db_oceens.db
│
├── llm-utils/                    # Outils LLM hors application
│   └── README.md                 # (le suivi des coûts est passé dans l'app, voir ci-dessus)
│
└── .venv/                        # Environnement virtuel Python (non commité)
```

---

## Authentification (OAuth 2.0)

Le flux d'authentification repose sur **Microsoft Entra ID** via la bibliothèque MSAL :

```
1. /login
   → FastAPI génère un state aléatoire (UUID) et le garde en session
   → Redirection vers la page de login Microsoft

2. L'utilisateur s'authentifie chez Microsoft
   → Microsoft redirige vers /auth/callback avec un code + state
   → Si la session contient un state, il doit correspondre (sinon 400)

3. Le serveur échange le code contre un token d'accès (MSAL)
   → Récupération du mail et du nom via Microsoft Graph (/v1.0/me)
   → Domaine hors ALLOWED_DOMAINS : 403
   → Utilisateur créé en base s'il n'existe pas (sans rôle = student)
   → Création de la session {name, email}
   → Redirection vers /, qui choisit le dashboard selon les rôles

4. À la déconnexion (/logout)
   → Suppression de la session
   → Déconnexion côté Microsoft
   → Retour à la racine de REDIRECT_URI
```

La session ne contient pas les rôles : ils sont relus en base à chaque requête. L'authentification seule n'autorise aucune action métier : chaque route vérifie ensuite le rôle et le périmètre (formation ou campus) via `require_roles()` et les helpers associés.

> [!NOTE]
> La vérification du `state` est sautée quand la session n'en contient pas (`core/auth.py`, `auth_callback`) : la protection CSRF n'est donc complète que si le cookie de session survit à l'aller-retour vers Microsoft.

---

## Authentification en mode développement

Pour travailler sur un fork sans application Azure, la **connexion de développement** permet de se connecter en tant que n'importe quel utilisateur, sans preuve d'identité. Elle ne doit **jamais** servir en production.

Elle s'active avec `AUTH_MODE=dev`, la valeur livrée par `.env.example`. `DEV_LOGIN_KEY`, `SECRET_KEY` et `ALLOWED_DOMAINS` y ont un comportement propre, décrit dans [Configuration](#configuration).

En mode `dev`, le cookie de session n'est plus limité à HTTPS (`http://localhost` fonctionne), `/login` redirige vers `/dev/login`, `/auth/callback` n'existe pas et `/logout` efface la session puis renvoie vers `/`. Un avertissement est journalisé au démarrage. Un bandeau rouge, non refermable, s'affiche en haut de chaque page incluant le header partagé : il rappelle l'adresse connectée, propose « Changer d'utilisateur » (`/dev/login`) et précise « accès ouvert à tous » quand `DEV_LOGIN_KEY` n'est pas définie.

`POST /dev/login` attend un formulaire avec `email`, `name` (optionnel) et `key` (si `DEV_LOGIN_KEY` est définie). L'utilisateur est récupéré ou créé comme au retour d'Entra : un mail inconnu devient un nouvel étudiant. Sans `name`, le nom affiché est construit depuis le mail (`bob.leponge@epfedu.fr` → « Bob Leponge »). Une nouvelle connexion remplace la session : c'est ainsi qu'on change d'utilisateur.

Dans un navigateur, `GET /dev/login` affiche la liste des utilisateurs de la base, regroupés par nom de rôle sans périmètre (un utilisateur sans rôle apparaît sous `student`, un utilisateur à plusieurs rôles sous chacun d'eux). Un clic connecte en tant que l'utilisateur choisi ; un champ libre permet d'utiliser une autre adresse, avec un nom optionnel. Si `DEV_LOGIN_KEY` est définie, un champ de clé unique s'affiche et sert à toutes les connexions de la page ; la clé n'est jamais stockée en session. On revient sur cette page pour changer d'utilisateur.

Exemple en bash, depuis la racine du dépôt :

```bash
AUTH_MODE=dev DEV_LOGIN_KEY=ma-cle uv run uvicorn oceens.main:app

# Se connecter en tant qu'admin du seed ; -c enregistre le cookie de session
curl -i -c cookies.txt \
  -d email=antoine.gademer@epf.fr -d key=ma-cle \
  http://localhost:8000/dev/login

# Réutiliser le cookie (-b) pour les requêtes suivantes
curl -b cookies.txt -c cookies.txt -L http://localhost:8000/
```

> [!WARNING]
> En mode `dev`, laisser `SECRET_KEY` vide est le choix sûr : la clé tirée au hasard n'est connue de personne. Si une `SECRET_KEY` connue est définie (partagée, copiée d'un exemple…), quiconque la connaît peut forger un cookie de session et contourner `DEV_LOGIN_KEY` : le mode `dev` l'accepte, car il ne sert qu'en local.

---

## Fonctionnalités notables

### Analytique des enseignants

La route `/dashboard/teachers/analytics` (`campus_manager`, `program_manager`) agrège le score de satisfaction par `(enseignant, sondage)` à partir des réponses `QCU_Satisfaction` renseignées d'un `Answer.teacher` (sections ME). La liste des enseignants est triée avec `teacher_sort_key()`, insensible à la casse et aux accents, et reste filtrable par année scolaire, semestre, formation et enseignant.

### Filtre par enseignant dans la visualisation

Un sélecteur côté client filtre la visualisation sans rechargement : seules les modules de l'enseignant choisi restent affichées, les sections Campus et Formation étant masquées. La page lit `?teacher=<nom>` au chargement pour se pré-filtrer ; les liens depuis l'analytique transmettent ce paramètre, si bien qu'un clic sur le score d'un enseignant ouvre directement sa vue.

### Sondages importés via Excel

Les sondages chargés par `survey_loader_from_xlsx.py` n'ont pas de question `QCU_Attendance` : `services/visualisation_data.py` utilise alors `satisfaction_responses_count` comme dénominateur de repli pour le score enseignant. Les noms d'enseignants sont normalisés en `.title()` à l'import comme à l'agrégation, pour fusionner les variantes de casse (`"GADEMER Antoine"` et `"Gademer Antoine"` = une seule entrée). Les questions sont triées par `question_id` dans le template, ce qui garantit les graphes avant les verbatims quel que soit l'ordre d'insertion.

### Périmètre de la direction de campus

Le dashboard `campus_manager` n'affiche que les sondages fermés ayant au moins un répondant. Le lien vers le questionnaire et le QR code y sont masqués (`can_view_survey_link=False`) : ce rôle consulte les résultats sans diffuser les sondages. Le garde `{% if can_view_survey_link | default(true) %}` laisse les autres dashboards inchangés.

### Nettoyage des étudiants orphelins

Lors de la suppression d'un sondage, les étudiants qui ne sont plus rattachés à
**aucun autre** sondage sont également supprimés, pour éviter d'accumuler des
comptes inutilisés (`services/helpers.py`, `_delete_orphan_students`). Un
garde-fou protège les utilisateurs à rôle privilégié (`admin`,
`program_manager`, `facilitator`, `campus_manager`) : un enseignant ou un
gestionnaire ayant répondu à un sondage n'est jamais effacé.

### Ajout d'un utilisateur par mail

L'onglet « Utilisateurs » du dashboard administrateur propose un bouton
**« + Ajouter un utilisateur »** : un mail suffit pour créer le compte, avec le
rôle `student` par défaut (`POST /api/users`, admin uniquement). Le mail est
validé (format + domaine autorisé) et les doublons sont refusés.

---

## Checklist de déploiement

- [ ] `.env` créé avec les vraies credentials Entra, `REDIRECT_URI`, `ALLOWED_DOMAINS` et une `SECRET_KEY` dédiée (voir [Configuration](#configuration))
- [ ] `AUTH_MODE` non défini ou `entra` (`.env.example` livre `dev`)
- [ ] Certificat SSL valide (Let's Encrypt ou équivalent)
- [ ] `https_only=True` dans le SessionMiddleware (automatique hors `AUTH_MODE=dev`)
- [ ] Base de production présente dans `database/` ou `LOCAL_DATABASE_DIR` (volume monté avec Docker) : sur une base vide, le démarrage insère le jeu de démonstration, **comptes admin compris**
- [ ] Variables d'environnement sécurisées, y compris `LLM_API_KEY`
- [ ] **Docker Compose** : `.env` chargé via `env_file`, jamais copié dans l'image ; `LOCAL_DATABASE_DIR` pointant vers le bon répertoire de base
- [ ] [Daemon de synthèses](#daemon-de-synthèses-llm-optionnel) lancé si les synthèses LLM sont utilisées (`launch.sh`, ou `RUN_SUMMARIES_DAEMON=1` sous Docker)

---

## Validation avant contribution

Le dépôt ne contient pas de suite de tests automatisés ni de CI. Avant de proposer un changement, dérouler le **[smoke test manuel](docs/smoke-test.md)** : il décrit les vérifications, les commandes pour Windows et macOS / Linux, et les résultats attendus.

---

## Ressources

- [FastAPI](https://fastapi.tiangolo.com/)
- [Guide du logging FastAPI et Uvicorn](https://apitally.io/blog/fastapi-logging-guide)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Microsoft Graph](https://learn.microsoft.com/en-us/graph/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Pandas](https://pandas.pydata.org/)

---

**Équipe OcéEns** — EPF
