
import os
import time
import logging
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APITimeoutError
from openai import APIConnectionError, APIStatusError


# Load settings from .env
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")

INPUT_FILE = "questions.csv"
OUTPUT_FILE = "output.csv"
LOG_FILE = "log.csv"
MAX_RETRIES = 3

# Stop if the API key is missing
if not API_KEY or API_KEY == "your_new_secret_key_here":
    raise SystemExit(
        "Error: Add your actual OpenAI API key to the .env file."
    )

# Disable SDK retries so our retry logic is easy to understand
client = OpenAI(
    api_key=API_KEY,
    timeout=30.0,
    max_retries=0
)

# Configure logging
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_answer(question):
    """Send one question to the OpenAI API and return its answer."""

    for attempt in range(MAX_RETRIES + 1):
        start_time = time.time()

        try:
            response = client.responses.create(
                model=MODEL,
                input=question
            )

            answer = response.output_text.strip()
            latency = round(time.time() - start_time, 2)

            if not answer:
                raise ValueError("The API returned an empty answer.")

            usage = response.usage
            input_tokens = usage.input_tokens if usage else 0
            output_tokens = usage.output_tokens if usage else 0

            return {
                "response": answer,
                "status": "success",
                "error": "",
                "latency_seconds": latency,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }

        except RateLimitError as error:
            logging.warning("Rate limit: %s", error)

            if attempt == MAX_RETRIES:
                break

            wait_seconds = 2 ** attempt
            time.sleep(wait_seconds)

        except APITimeoutError as error:
            logging.warning("Request timed out: %s", error)

            if attempt == MAX_RETRIES:
                return failed_result("Request timed out")

            time.sleep(2 ** attempt)

        except APIConnectionError as error:
            logging.error("Connection error: %s", error)
            return failed_result("Connection error")

        except APIStatusError as error:
            logging.error("API status error: %s", error)
            return failed_result(
                f"API error: HTTP {error.status_code}"
            )

        except ValueError as error:
            logging.error("Invalid response: %s", error)
            return failed_result(str(error))

        except Exception:
            logging.exception("Unexpected error")
            return failed_result("Unexpected error; check app.log")

    return failed_result("Rate limit reached after retries")


def failed_result(message):
    """Return a consistent result when a request fails."""

    return {
        "response": "",
        "status": "failed",
        "error": message,
        "latency_seconds": "",
        "input_tokens": 0,
        "output_tokens": 0
    }


def main():
    """Read questions, call the API, and save the results."""

    try:
        questions_df = pd.read_csv(INPUT_FILE)
    except (FileNotFoundError, pd.errors.EmptyDataError) as error:
        print(f"Cannot read {INPUT_FILE}: {error}")
        return

    if "question" not in questions_df.columns:
        print("Error: questions.csv must have a 'question' column.")
        return

    questions_df = questions_df.dropna(subset=["question"])
    results = []
    logs = []

    for index, question in enumerate(
        questions_df["question"], start=1
    ):
        question = str(question).strip()

        if not question:
            continue

        print(f"Processing question {index}...")

        result = get_answer(question)

        results.append({
            "question": question,
            **result
        })

        logs.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "question_index": index,
            "latency_seconds": result["latency_seconds"],
            "status": result["status"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"]
        })

        print(f"Status: {result['status']}")

    # Save answers, including failed requests
    pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)
    pd.DataFrame(logs).to_csv(LOG_FILE, index=False)

    successful = sum(
        result["status"] == "success" for result in results
    )

    print("\nAssignment run finished.")
    print(f"Questions processed: {len(results)}")
    print(f"Successful answers: {successful}")
    print(f"Failed answers: {len(results) - successful}")
    print(f"Answers saved to: {OUTPUT_FILE}")
    print(f"API logs saved to: {LOG_FILE}")


if __name__ == "__main__":
    main()
