# csv_utils.py

import csv
import chardet

def detect_encoding(file_obj):
    file_obj.seek(0)
    result = chardet.detect(file_obj.read(1024))
    file_obj.seek(0)
    return result['encoding']

def detect_delimiter(file_obj, encoding='utf-8'):
    file_obj.seek(0)
    sample = file_obj.read(2048).decode(encoding)
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample)
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ','  # Default fallback
    file_obj.seek(0)
    return delimiter
