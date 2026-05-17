from pdf_parser import extract_text
import os

sample_dir = r"c:\Users\regre\Downloads\procureshieldAI Demo - Copy\sample_data"
files = [
    "1258102019.pdf",
    "298032025.pdf",
    "370052020.pdf",
    "Filled_Model_Bidder_Submission_CRPF_Polymer_Based_Pistol_Tender.pdf",
    "Tender notice 898092025-520.pdf"
]

results_file = "all_samples_test.txt"

with open(results_file, "w", encoding="utf-8") as f:
    for filename in files:
        filepath = os.path.join(sample_dir, filename)
        f.write(f"\n{'='*20} TESTING: {filename} {'='*20}\n")
        if os.path.exists(filepath):
            try:
                text, method, page_count = extract_text(filepath)
                f.write(f"Method: {method}\n")
                f.write(f"Page Count: {page_count}\n")
                f.write(f"Text Length: {len(text)}\n")
                f.write("-" * 50 + "\n")
                f.write(text[:3000]) # First 3000 chars
                f.write("\n... [snippet end] ...\n")
            except Exception as e:
                f.write(f"ERROR: {e}\n")
        else:
            f.write(f"File not found: {filepath}\n")

print(f"Results written to {results_file}")
