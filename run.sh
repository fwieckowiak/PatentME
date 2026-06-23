#!/bin/bash
#read links_EP_fulltext.csv

cd src

#python3 process_zip_file.py
python3 mml_cleaner.py ../processed_data/raw_data.csv
python3 generate_vocab.py