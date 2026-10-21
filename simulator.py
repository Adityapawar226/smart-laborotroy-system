import requests
import json
import hashlib

RECEIVER_URL = "http://127.0.0.1:5055/api/analyzer/receive"

API_KEY = "dev-analyzer-key-change-me"

# Failure logging test packet
packet = {
    "message_id": "SIM-RECOVERY-0001",
    "analyzer_id": "ANALYZER_DEMO_001",
    "sample_id": "SMP-2026-9ABC4B61",
    "test_code": "CBC",
    "results": {
        "HB": 14.2,
        "WBC_COUNT": 7200,
        "PLATELET_COUNT": 265000
    }
}


def calculate_packet_hash(data):
    """Generate a stable hash for the packet."""
    canonical_data = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )

    return hashlib.sha256(
        canonical_data.encode("utf-8")
    ).hexdigest()


def main():
    try:
        packet_hash = calculate_packet_hash(packet)

        headers = {
            "X-Analyzer-Key": API_KEY,
            "Content-Type": "application/json"
        }

        print("=" * 50)
        print("ANALYZER SIMULATOR - FAILURE TEST")
        print("=" * 50)
        print("Message ID:", packet["message_id"])
        print("Analyzer ID:", packet["analyzer_id"])
        print("Sample ID:", packet["sample_id"])
        print("Test Code:", packet["test_code"])
        print("Packet Hash:", packet_hash)
        print("-" * 50)

        response = requests.post(
            RECEIVER_URL,
            json=packet,
            headers=headers,
            timeout=10
        )

        print("HTTP Status:", response.status_code)

        try:
            response_data = response.json()
            print(
                "Receiver Response:",
                json.dumps(response_data, indent=4)
            )
        except ValueError:
            print("Receiver Response:", response.text)

        if response.status_code == 404:
            print("\nEXPECTED: Invalid sample rejected.")

        elif response.status_code == 200:
            print(
                "\nNOTICE: Request returned HTTP 200. "
                "Check the response body to understand why."
            )

        elif response.status_code == 409:
            print("\nCONFLICT: Check packet or existing results.")

        else:
            print("\nReview receiver response and server logs.")

    except requests.Timeout:
        print("ERROR: Receiver timed out.")

    except requests.ConnectionError:
        print(
            "ERROR: Could not connect to receiver. "
            "Check whether analyzer_receiver.py is running."
        )

    except requests.RequestException as error:
        print("Request failed:", error)


if __name__ == "__main__":
    main()