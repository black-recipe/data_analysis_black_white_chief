import pandas as pd
import os
from tqdm import tqdm
from 실시간인구데이터수집코드 import ENGLISH_TO_KOREAN_DONG, ENGLISH_TO_KOREAN_GU, translate_name
OUTPUT_FILE = "seoul_floating_pop_raw3.csv"

def apply_mappings():
    print(f"Loading {OUTPUT_FILE}...")
    if not os.path.exists(OUTPUT_FILE):
        print("File not found.")
        return

    # Read the file
    df = pd.read_csv(OUTPUT_FILE)
    print(f"Loaded {len(df)} rows.")

    # Apply mappings
    print("Applying mappings...")
    
    # Clean GU (Autonomous District)
    # We use a lambda to apply translate_name
    tqdm.pandas(desc="Translating Gu")
    df['AUTONOMOUS_DISTRICT'] = df['AUTONOMOUS_DISTRICT'].progress_apply(
        lambda x: translate_name(str(x), ENGLISH_TO_KOREAN_GU)
    )

    # Clean Dong (Administrative District)
    tqdm.pandas(desc="Translating Dong")
    df['ADMINISTRATIVE_DISTRICT'] = df['ADMINISTRATIVE_DISTRICT'].progress_apply(
        lambda x: translate_name(str(x), ENGLISH_TO_KOREAN_DONG)
    )

    # Save back
    # We'll save to a temp file first then rename to be safe
    temp_file = OUTPUT_FILE + ".tmp"
    print(f"Saving to {temp_file}...")
    df.to_csv(temp_file, index=False, encoding='utf-8-sig')
    
    print("Replacing original file...")
    os.replace(temp_file, OUTPUT_FILE)
    print("Done!")

    # Check for remaining English characters to see if we missed anything
    remaining_english = df[df['ADMINISTRATIVE_DISTRICT'].str.contains('[a-zA-Z]', na=False)]
    if not remaining_english.empty:
        print(f"Warning: {len(remaining_english)} rows still contain English in ADMINISTRATIVE_DISTRICT.")
        print("Sample of unmapped values:")
        print(remaining_english['ADMINISTRATIVE_DISTRICT'].unique()[:20])
    else:
        print("All English names appear to be mapped!")

if __name__ == "__main__":
    apply_mappings()
