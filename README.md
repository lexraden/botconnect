# Bot Connect - Telegram Bot Constructor

Bot Connect is a Telegram bot constructor that allows users to create and manage feedback bots with ease. This repository contains the source code for the Bot Connect application.

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- Create and manage multiple Telegram bots.
- Configure bot settings such as greetings, menus, and subscriptions.
- Support for handling user feedback and messages.
- Subscription system for additional features (e.g., ad-free experience, increased message limits).
- Scalable architecture using `aiogram` and `FastAPI`.

---

## Prerequisites

Before running the application, ensure you have the following installed:

- Python 3.9 or higher
- PostgreSQL database (or any other supported database)
- `pip` package manager
- `uvicorn` for running the FastAPI application

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Fluorouacil/bot_construct.git
   cd bot-connect
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the database**:
   - Create a PostgreSQL database or use an existing one.
   - Update the database connection details in `config.py` (see [Configuration](#configuration)).

---

## Configuration

All configuration settings are stored in the `config.py` file. You need to update the following fields:

### Required Settings

- **Telegram API Token**:
  ```python
  TELEGRAM_API_TOKEN = "your_telegram_bot_api_token"
  ```
  Replace `your_telegram_bot_api_token` with the token provided by [@BotFather](https://t.me/BotFather).

- **Database Connection String**:
  ```python
  DATABASE_URL = "postgresql+asyncpg://username:password@localhost:5432/your_database_name"
  ```
  Replace `username`, `password`, and `your_database_name` with your PostgreSQL credentials.

- **Webhook URL**:
  ```python
  WEBHOOK_URL = "https://yourdomain.com/webhook"
  ```
  Replace `https://yourdomain.com/webhook` with the public URL where Telegram will send updates.

### Optional Settings

- **Other Custom Settings**:
  Add any additional settings required for your application.

---

## Running the Application

To start the application, use the following command:

```bash
uvicorn main:app --host 127.0.0.1 --port <WEBHOOK_PORT>
```

Replace `<WEBHOOK_PORT>` with the port number specified in `config.py`.

For example:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Notes:
- Ensure that the webhook URL (`WEBHOOK_URL`) is accessible from the internet.
- If you're running the application locally for testing, you can use tools like [ngrok](https://ngrok.com/) to expose your local server to the internet.

---

## Contributing

We welcome contributions! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Commit your changes and push them to your fork.
4. Submit a pull request with a detailed description of your changes.

---

Thank you for using Bot Connect! 🚀
