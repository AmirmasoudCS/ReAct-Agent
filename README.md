# 🤖 ReAct-Agent

A local ReAct (Reasoning and Acting) agent powered by Ollama. It uses a language model to select tools, process their observations, and generate answers. The project includes a FastAPI backend and a React frontend with streaming responses and persistent conversations.

## ✨ Features

The agent supports tool-assisted reasoning with a calculator, date and time utility, weather lookup, Wikipedia search, and web search. Conversations can be created, resumed, renamed, and deleted, while context management summarizes older history to help fit within the model's context window.

The web interface provides streaming responses, visible tool activity, and configurable model settings. The agent can also run through a command-line interface.

## 🛠️ Tech Stack

**Backend:** Python, FastAPI, Ollama, OpenAI Python SDK

**Frontend:** React, Vite, JavaScript

## 🚀 Installation and Getting Started

### 📋 Prerequisites

Install [Python](https://www.python.org/), [Node.js](https://nodejs.org/), and [Ollama](https://ollama.com/) before starting. Then clone the repository and open a terminal in the project root.

### 1. 🧠 Set Up Ollama

Start Ollama and download the default model:

```bash
ollama pull gemma4:e4b
```

To use a different compatible model, change `OLLAMA_MODEL` in the backend `.env` file.

### 2. 🐍 Install and Configure the Backend

Create and activate a virtual environment from the project root.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a `.env` file in the **project root**, alongside `api.py` and `requirements.txt`. This file must be created locally.

Add the following values:

```dotenv
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=gemma4:e4b
OLLAMA_API_KEY=ollama
DEBUG=1
OLLAMA_DEBUG=1
```

Start the API server:

```bash
uvicorn api:app --reload
```

The backend will be available at `http://127.0.0.1:8000`.

### 3. ⚛️ Install and Configure the Frontend

Open a separate terminal and navigate to the frontend directory:

```bash
cd frontend
npm install
```

Create another `.env` file **inside `frontend/`**, alongside `package.json`. Add:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api
VITE_APP_NAME=ReAct Agent
```

Start the frontend development server:

```bash
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`.

**Important:** Keep Ollama and the backend running while using the frontend. Both `.env` files must be created locally because the application does not provide them by default.

## ⚙️ Configuration

`config.yaml` controls the LLM parameters, maximum agent steps, tool timeout, and context-management settings. The backend `.env` file configures the Ollama connection and debugging options. The frontend `.env` file controls the API URL and application name.

Keep local environment files out of version control.

## 🧪 Testing

Run the backend test suite from the project root with the virtual environment activated:

```bash
pytest
```

To lint and build the frontend, run these commands from `frontend/`:

```bash
npm run lint
npm run build
```

## 📂 Project Structure

```text
📁
├── 📁 frontend
│   ├── 📁 public
│   └── 📁 src
│       ├── 📁 api
│       ├── 📁 components
│       ├── 📁 hooks
│       └── 📁 utils
├── 📁 llm
├── 📁 prompts
├── 📁 tests
├── 📁 tools
├── 📁 utils
├── 🐍 agent.py
├── 🐍 api.py
├── 📄 config.yaml
├── ⚖️ LICENSE
├── 🐍 main.py
├── 📄 pytest.ini
├── 📘 README.md
└── 📝 requirements.txt
```

> Generated using [Tree Printer](https://github.com/AmirmasoudCS/Tree-Printer.git)

## ⚖️ License

See [LICENSE](LICENSE) for licensing information.
