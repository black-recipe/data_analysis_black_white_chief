import os
import pandas as pd
import glob

# Paths
source_dir = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\트렌드분석"
output_dir = r"c:\Users\USER\Documents\웅진씽크빅kdt\흑백요리사\흑백요리사트렌드추이"
output_file = os.path.join(output_dir, "merged_trends_long.csv")

# Ensure output directory exists (though it seems it exists)
os.makedirs(output_dir, exist_ok=True)

# Get list of files
files = glob.glob(os.path.join(source_dir, "*.csv"))

all_data = []

for file_path in files:
    filename = os.path.basename(file_path)
    
    # Check if datalab (though user said ignore, and they might not be there)
    if "datalab" in filename:
        continue
        
    # Extract keyword and source from filename
    # Expected format: {keyword}_{source}.csv
    try:
        name_part = os.path.splitext(filename)[0]
        # Split by last underscore to separate source
        parts = name_part.rpartition('_')
        keyword = parts[0]
        source = parts[2]
        
        if not keyword or not source:
            print(f"Skipping file with unexpected name format: {filename}")
            continue
            
    except Exception as e:
        print(f"Error parsing filename {filename}: {e}")
        continue

    print(f"Processing {filename} -> Keyword: {keyword}, Source: {source}")

    # Read CSV
    # Based on inspection:
    # Line 1: Metadata (Category)
    # Line 2: Empty (or skipped)
    # Line 3: Header (Date column)
    # Using header=1 seems to correctly identify the header row based on testing
    try:
        df = pd.read_csv(file_path, header=1)
        
        # Verify columns
        if len(df.columns) < 2:
            print(f"Skipping {filename}: Not enough columns")
            continue
            
        # Rename columns standardly
        # First column is usually '일' (Date)
        # Second column is the value (Search volume)
        df.columns = ['date', 'search_volume']
        
        # Convert date
        df['date'] = pd.to_datetime(df['date'])
        
        # Handle 'search_volume' - Google Trends sometimes puts '<1'
        # Convert to string first to handle replace
        df['search_volume'] = df['search_volume'].astype(str).replace('<1', '0')
        # Remove any commas if present (though prob not in CSV)
        df['search_volume'] = df['search_volume'].str.replace(',', '')
        df['search_volume'] = pd.to_numeric(df['search_volume'], errors='coerce').fillna(0)
        
        # Add metadata columns
        df['keyword'] = keyword
        df['source'] = source
        
        # Filter columns
        df = df[['date', 'keyword', 'source', 'search_volume']]
        
        all_data.append(df)
        
    except Exception as e:
        print(f"Error processing content of {filename}: {e}")

# Merge all
if all_data:
    final_df = pd.concat(all_data, ignore_index=True)
    
    # Sort nicely
    final_df = final_df.sort_values(by=['keyword', 'source', 'date'])
    
    # Save
    final_df.to_csv(output_file, index=False, encoding='utf-8-sig') # utf-8-sig for Korean support in Excel
    print(f"Successfully saved merged data to {output_file}")
    print(final_df.head())
    print(f"Total rows: {len(final_df)}")
else:
    print("No data found to merge.")
