@'
# Week 2: APIs & Data Assignment

## Overview
This project reads questions from questions.csv, sends them to an LLM API, and saves responses and request logs.

## Features
- Read questions from a CSV file
- Send questions to an LLM API
- Handle API errors and limited retries
- Save results in output.csv
- Record request details in log.csv
- Record diagnostic messages in app.log
- Keep API credentials in a local .env file

## Prerequisites
- Python installed
- An API key for the selected provider
- An accessible model and available API credits

## Installation
Install the required packages:

```bash
python -m pip install openai pandas python-dotenv