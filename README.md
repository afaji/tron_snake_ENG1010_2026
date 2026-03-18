# Tron Snake - ENG1010 (2026)

Welcome to the Tron Snake project. This repository contains the codebase for the ENG1010 Algorithm and Data Structure course assignment. Follow the instructions below to set up your environment and run the game.

## Prerequisites

- **Python 3.11** installed on your machine.
- **Git** configured with your SSH keys.

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone git@github.com:afaji/tron_snake_ENG1010_2026.git
   ```

2. **Navigate to the project directory:**
   ```bash
   cd tron_snake_ENG1010_2026
   ```

3. **Create a virtual environment:**
   ```bash
   python3.11 -m venv .venv
   ```

4. **Activate the environment:**
   - **macOS / Linux:** `source .venv/bin/activate`
   - **Windows:** `.venv\Scripts\activate`

5. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## How to Play & Evaluate

Code your bot and put it inside the `bots` folder.

### Run the Game (with GUI)
To launch the game with the graphical interface:
```bash
python main.py
```

### Run the Game (without GUI)
To run the simulation in the terminal or see available CLI options:
```bash
python runner.py -h
```

### Run Evaluation
To test your implementation against the public test cases, use the provided shell script:
```bash
./evaluate.sh
```
