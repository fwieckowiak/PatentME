## PatentME-Generator

this repository contains scripts to download, process, and generate datasets from EPO patent documents. The processing pipeline includes cleaning, tokenization, and vocabulary generation. It is the code uszed in the paper "PatentME: A Dataset and Reference-Free Post-OCR Verification Task for Printed Mathematical Expression Recognition" accepted at ICDAR 2026 :

https://hal.science/hal-05660080 

### How to download patents

1. Download patents using the provided script:
    ```bash
    ./download.sh
    ```
    Patents will be saved to `input_zips/`

You can add custom download links to `links_EP_fulltext.csv` for additional patents from the EPO website at publication-bdds.apps.epo.org/raw-data/products/public/product/32

### Processing

Run the processing pipeline:
```bash
./run.sh
```

This processes the downloaded patent files and generates:
- Cleaned and tokenized datasets in `processed_data/`
- Vocabulary files and token mappings
- Patent images organized by identifier

### Project Structure

- `src/` - Processing scripts (vocabulary generation, data cleaning, zip extraction)
- `processed_data/` - Output datasets and vocabularies
- `input_zips/` - Downloaded patent files



