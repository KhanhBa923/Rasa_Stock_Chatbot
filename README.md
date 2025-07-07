# Rasa Stock Chatbot

## Overview
This is a conversational AI chatbot built using Rasa that provides stock market information and insights to users.

## Features
- Stock price retrieval
- Company information lookup
- Market trend analysis
- Interactive conversational interface

## Prerequisites
- Python 3.10+
- Rasa Open Source
- pip (Python package manager)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/KhanhBa923/Rasa_Stock_Chatbot.git
cd Rasa_Stock_Chatbot
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Train the Rasa Model
```bash
rasa train
```

## Running the Chatbot

### Start the Action Server
```bash
rasa run actions
```

### Run the Rasa Shell
```bash
rasa shell
```
OR
### Run the Rasa API
```bash
rasa run --enable-api --cors "*"
```

### Run the Rasa FE
```bash
python -m http.server 8000
```
Open : http://localhost:8000/chatbot.html

## Project Structure
- `data/`: Training data for Rasa NLU
- `actions/`: Custom action implementations
- `models/`: Trained Rasa models
- `config.yml`: Rasa configuration
- `domain.yml`: Defines intents, entities, slots, and responses
- `credentials.yml`: External service credentials

## Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
Distributed under the MIT License. See `LICENSE` for more information.

## Contact
Project Maintainer: KhanhBa923
GitHub: [https://github.com/KhanhBa923/Rasa_Stock_Chatbot](https://github.com/KhanhBa923/Rasa_Stock_Chatbot)
  
