#!/bin/bash

cd input_zips || exit 1

while IFS=, read -r yr_mo link; do
    # Skip header
    [ "$yr_mo" = "yr-mo" ] && continue

    # Remove Windows CR if present
    link="${link//$'\r'/}"

    if [ -f "${yr_mo}.zip" ]; then
        echo "${yr_mo}.zip already exists, skipping download."
    else
        echo "Downloading ${yr_mo}.zip from $link..."
        wget -c -O "${yr_mo}.zip" "$link"
    fi
done < /data/fwieckowiak/PatentME-Generator/links_EP_fulltext.csv