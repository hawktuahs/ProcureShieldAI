from pdf_parser import extract_text
import os

filepath = r"c:\Users\regre\Downloads\procureshieldAI Demo - Copy\sample_data\298032025.pdf"
if os.path.exists(filepath):
    text, method, page_count = extract_text(filepath)
    with open("parser_output.txt", "w", encoding="utf-8") as f:
        f.write(f"Method: {method}\n")
        f.write(f"Page Count: {page_count}\n")
        f.write(f"Text Length: {len(text)}\n")
        f.write("-" * 50 + "\n")
        f.write(text)
    print(f"Output written to parser_output.txt")
else:
    print(f"File not found: {filepath}")
