from pdf_parser import extract_text
import os

sample_dir = r"c:\Users\regre\Downloads\procureshieldAI Demo - Copy\sample_data"
files = [
    "1258102019.pdf",
    "370052020.pdf",
    "Tender notice 898092025-520.pdf",
    "298032025.pdf"
]

results_file = "samples_inspection.txt"

with open(results_file, "w", encoding="utf-8") as f:
    for filename in files:
        filepath = os.path.join(sample_dir, filename)
        f.write(f"\n{'='*30} INSPECTING: {filename} {'='*30}\n")
        if os.path.exists(filepath):
            try:
                text, method, page_count = extract_text(filepath)
                f.write(f"Method: {method}, Pages: {page_count}, Chars: {len(text)}\n")
                
                # Sample start, middle, and end
                pages = text.split("--- PAGE ")
                if len(pages) > 1:
                    f.write("\n[FIRST PAGE SNIPPET]\n")
                    f.write(pages[1][:2000])
                    
                    if len(pages) > 3:
                        f.write("\n\n[MIDDLE PAGE SNIPPET]\n")
                        mid = len(pages) // 2
                        f.write(pages[mid][:2000])
                    
                    f.write("\n\n[LAST PAGE SNIPPET]\n")
                    f.write(pages[-1][:2000])
                else:
                    f.write(text[:5000])
                    
                f.write("\n" + "-"*80 + "\n")
            except Exception as e:
                f.write(f"ERROR: {e}\n")
        else:
            f.write(f"File not found: {filepath}\n")

print(f"Inspection summary written to {results_file}")
