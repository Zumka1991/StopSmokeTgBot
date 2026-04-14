from share_card import create_share_card
from datetime import timedelta, datetime
import logging
import os

logging.basicConfig(level=logging.INFO)

def test_gen():
    try:
        path = create_share_card(
            first_name="Дмитрий",
            delta=timedelta(days=15, seconds=3600*5),
            savings=2500.0,
            cigarettes=300,
            quit_date_str="30.03.2024",
            output_path="data/test_share_card.png"
        )
        print(f"Success! Card saved to: {path}")
        if os.path.exists(path):
            print(f"File size: {os.path.getsize(path)} bytes")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gen()
