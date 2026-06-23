#%%
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import zipfile
import shutil
import argparse
import xml.etree.ElementTree as ET
import pandas as pd
from PIL import Image
from pathlib import Path
from tqdm import tqdm


def process_single_zip(zip_path, output_dir):
    """
    Process a single ZIP file: extract, parse XML/images, return list of dicts
    """
    temp_extract_dir = output_dir / "temp_extract"
    if temp_extract_dir.exists():
        shutil.rmtree(temp_extract_dir)
    temp_extract_dir.mkdir(parents=True, exist_ok=True)

    # Extract ZIP
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_extract_dir)


    DOC_folder = temp_extract_dir / "DOC"
    if not DOC_folder.exists() or not DOC_folder.is_dir():
        print(f"Error: DOC folder not found in {temp_extract_dir}")

    #there are a few big folders in DOC, and in all of them there are ZIPS starting with EP, we need to process all of them

    data_list = []

    for subfolder in tqdm(DOC_folder.iterdir(), desc="Processing subfolders"):
        if not subfolder.is_dir():
            continue
        zip_folders = [f for f in subfolder.iterdir() if f.name.startswith("EP")]
        for folder in zip_folders:
            #unzip it , the EP folder is a zip file, we need to unzip it in place
            if folder.suffix == ".zip":
                with zipfile.ZipFile(folder, 'r') as zip_ref:
                    zip_ref.extractall(folder.parent / folder.stem)
                
                folder.unlink()

                folder = folder.parent / folder.stem
            #if they are no images in the folder, delete it and skip it
            if not any(f.suffix == '.tif' for f in folder.iterdir()):
                shutil.rmtree(folder)
                continue

            # create folder for images
            ep_image_folder = output_dir / "images" / folder.name / "all_images"
            ep_image_folder.mkdir(parents=True, exist_ok=True)

            # find XML
            #keep only if the xml starts with EP
            xml_files = [f for f in folder.iterdir() if f.suffix == ".xml" and f.name.startswith("EP")]
            if not xml_files:
                continue

            xml_file_path = xml_files[0]
            try:
                tree = ET.parse(xml_file_path)
                root = tree.getroot()
            except Exception as e:
                print(f"Warning: cannot parse XML {xml_file_path}: {e}")
                continue
            # iterate maths
            maths_list = root.findall('.//maths')
            #if there are no maths, skip this folder and delete the images
            if not maths_list:
                shutil.rmtree(folder)
                #and remove as well the created image folder
                shutil.rmtree( output_dir / "images" / folder.name)
                continue

            for maths in tqdm(maths_list, desc=f"Processing {folder.name}", leave=False):    
                math_id = maths.get('id')
                math_tag = maths.find('math')
                display_type = math_tag.get('display') if math_tag is not None else None
                img_tag = maths.find('img')
                if img_tag is None:
                    continue

                img_file = img_tag.get('file')
                img_width = img_tag.get('wi')
                img_height = img_tag.get('he')
                img_content = img_tag.get('img-content')
                img_format = img_tag.get('img-format')

                mml_content = ET.tostring(math_tag, encoding='unicode') if math_tag is not None else ''
                mml_content = mml_content.replace('\n', ' ').replace('\r', ' ').strip()
                # remove multiple spaces
                mml_content = ' '.join(mml_content.split())

                #if the mml content is empty skip this entry
                if not mml_content:
                    continue

                # get real image size
                img_path = folder / img_file
                try:
                    opened_img = Image.open(img_path)
                    real_img_width, real_img_height = opened_img.size
                except Exception as e:
                    print(f"Warning: cannot open image {img_path}: {e}")
                    real_img_width, real_img_height = None, None

                # copy image to processed folder
                dest_img_path = ep_image_folder / img_file
                try:
                    shutil.copy2(img_path, dest_img_path)
                except Exception as e:
                    print(f"Warning: cannot copy image {img_path} to {dest_img_path}: {e}")

                data_list.append({
                    'image_path': str(dest_img_path).strip("../"),
                    'patent_number': folder.name,
                    'math_id': math_id,
                    'display_type': display_type,
                    'img_file': img_file,
                    'img_width': img_width,
                    'img_height': img_height,
                    'real_img_width': real_img_width,
                    'real_img_height': real_img_height,
                    'img_content': img_content,
                    'img_format': img_format,
                    'img_id': f"{folder.name}_{img_file}",
                    'mathml': mml_content
                })

    # cleanup temp extraction
    shutil.rmtree(temp_extract_dir)
    return data_list


def process_all_zips(zip_folder, output_dir):
    """
    Process all ZIP files in zip_folder and merge results
    """
    zip_folder = Path(zip_folder)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_data = []

    zip_files = list(zip_folder.glob("*.zip"))
    print(f"Found {len(zip_files)} zip files.")

    for zip_file in tqdm(zip_files, desc="Processing ZIP files"):
        data_list = process_single_zip(zip_file, output_dir)
        all_data.extend(data_list)

    # save CSV
    df = pd.DataFrame(all_data)
    df['mathml'] = df['mathml'].str.replace('<mtext> </mtext>', '<mtext>\u00A0</mtext>')
    csv_path = output_dir / "raw_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV: {csv_path}")

def analyze_zips(zip_folder):
    """
    Count total EP zip files inside all main ZIPs
    + compute total size of main ZIPs in Go (GB)
    """
    zip_folder = Path(zip_folder)

    zip_files = list(zip_folder.glob("*.zip"))
    total_ep_zips = 0

    print(f"Found {len(zip_files)} main zip files.")
    total_size_bytes = 0

    for zip_file in tqdm(zip_files, desc="Analyzing ZIPs"):
        total_size_bytes += zip_file.stat().st_size

        try:
            with zipfile.ZipFile(zip_file, 'r') as z:
                # count EP*.zip inside DOC/
                for name in z.namelist():
                    if "DOC/" in name and name.endswith(".zip") and Path(name).name.startswith("EP"):
                        total_ep_zips += 1
        except Exception as e:
            print(f"Error reading {zip_file}: {e}")

    total_size_go = total_size_bytes / (1024 ** 3)

    print(f"Total EP zip files: {total_ep_zips}")
    print(f"Total size of main zips: {total_size_go:.2f} Go")

    return total_ep_zips, total_size_go

def analyze_resulting_csv(path_to_csv):
    df = pd.read_csv(path_to_csv)
    total_patents = df['patent_number'].nunique()
    total_math_expressions = len(df)
    print(f"Total unique patents: {total_patents}")
    print(f"Total math expressions: {total_math_expressions}")



#%%
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process multiple Patent Math Expression ZIPs")
    parser.add_argument("--zip_folder", type=str, required=False, help="Folder containing ZIP files"
                        ,default="../input_zips")
    parser.add_argument("--output_dir", type=str, required=False,
                        default="../processed_data",
                        help="Output directory for CSV and images")
    args = parser.parse_args()



    process_all_zips(args.zip_folder, args.output_dir)
    analyze_resulting_csv("../processed_data/raw_data.csv")
    analyze_zips("../input_zips")

#%%