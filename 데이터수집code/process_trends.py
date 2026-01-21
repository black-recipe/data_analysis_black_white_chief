import pandas as pd
import os
import glob

base_path = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\흑백요리사트렌드추이"

def clean_google_csv(file_path):
    print(f"Processing Google CSV: {file_path}")
    # Read first couple lines to check format
    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        second_line = f.readline()
    
    # Check if it needs cleaning
    needs_cleaning = False
    if "카테고리" in first_line:
        needs_cleaning = True
    
    if not needs_cleaning:
        print(" -> Already clean.")
        return

    # Process
    try:
        df = pd.read_csv(file_path, header=1)
        # Columns should be ['일', 'Name: (...)']
        # Rename columns
        new_cols = []
        for col in df.columns:
            if col == '일':
                new_cols.append('일')
            else:
                # Extract name "최강록: (대한민국)" -> "최강록"
                name = col.split(':')[0]
                new_cols.append(name)
        
        df.columns = new_cols
        
        # Save back to csv (or new file? User implies finding all and organizing them)
        # I'll overwrite to match the 'im_google.csv' format exactly
        df.to_csv(file_path, index=False, encoding='utf-8-sig') # utf-8-sig for excel compatibility if needed, or just utf-8
        print(f" -> Cleaned and saved.")
        
    except Exception as e:
        print(f" -> Error processing {file_path}: {e}")

def convert_naver_excel(file_path):
    print(f"Processing Naver Excel: {file_path}")
    try:
        # Read excel
        df = pd.read_excel(file_path)
        
        # Find header row
        header_row_idx = None
        for i, row in df.iterrows():
            # Check if '날짜' is in the values (converted to string)
            row_str = row.astype(str).values
            if '날짜' in row_str:
                header_row_idx = i
                break
        
        if header_row_idx is None:
            print(" -> Could not find '날짜' header.")
            return

        # Reload with correct header
        # Actually we can just slice format
        # Get header values
        headers = df.iloc[header_row_idx].values
        # Data is below
        data = df.iloc[header_row_idx+1:].copy()
        data.columns = headers
        
        # Keep only relevant columns: '날짜' and the name column(s)
        # Usually Naver Excel has '날짜', 'NAME', 'NAME', ...
        # Ensure '날짜' is first
        cols = list(data.columns)
        if '날짜' not in cols:
             print(" -> '날짜' column missing after slice.")
             return
             
        # Reset index
        data = data.reset_index(drop=True)
        
        # Convert '날짜' to standard format if needed (YYYY-MM-DD)
        # Naver usually gives YYYY-MM-DD
        
        # Generate new filename: replace .xlsx with .csv
        new_file_path = file_path.replace('.xlsx', '.csv')
        
        # Save
        data.to_csv(new_file_path, index=False, encoding='utf-8-sig')
        print(f" -> Converted to {new_file_path}")
        
    except Exception as e:
        print(f" -> Error processing {file_path}: {e}")

# 1. Process Google CSVs
google_files = glob.glob(os.path.join(base_path, "*_google.csv"))
# Also '구글.csv'
google_files += glob.glob(os.path.join(base_path, "*_구글.csv"))

for f in google_files:
    clean_google_csv(f)

# 2. Process Naver Excels
excel_files = glob.glob(os.path.join(base_path, "*_datalab.xlsx"))
# Also any other xlsx?
excel_files += glob.glob(os.path.join(base_path, "*.xlsx"))
excel_files = list(set(excel_files)) # Dedupe

for f in excel_files:
    convert_naver_excel(f)

# 3. Check Naver CSVs (like 아기맹수_네이버.csv) to ensure they are clean?
# '아기맹수_네이버.csv' was already clean (Columns: ['날짜', '아기맹수']).
# Assuming they are fine if they are already csv and not headers.
