## PatentME-Generator

## Usage

scan_OPS_for_mml.py checks the OPS API for the presence of MML data in patents and saves the APN numbers, and generate the commands to donwnload the patents from the expert service website

Once we have the zips from the expert service website, we use process_zip_file.py to extract the MML data and save it in a structured format : with image folders and a csv file containing the metadata and the path to the images.

then we do
python3 /data/fwieckowiak/public_PIEMER/bench_mer_hf/conversions/mml_cleaner.py /data/fwieckowiak/PatentME-Generator/processed_data/raw_data.csv

Then we use prepare_data.py to :
clean the mathml
generate the vocab
tokenize
save as paquet train test val split






# PatentME
