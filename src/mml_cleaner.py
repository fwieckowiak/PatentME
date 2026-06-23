#%%

import os
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import numpy as np
import sys
import os
 

def remove_unknown_tags(mml):
    valid=['mrow','mtext','mi','mo','mn','msup','msub','mfrac','msqrt',
                       'mroot','msubsup','munder', 'mover', 'munderover',
                       'mtd', 'mtable', 'mtr','semantics','mmultiscripts','mprescripts']
    invalid=[]
    for subtree in mml.findChildren(): 
        tag=subtree.name
        if tag not in valid:
            invalid.append(tag)
    if len(invalid)>0:
        print('invalid tags found', invalid)

    #check if semantics exist
    #new_mml=mml.findChildren()[1] if 'semantics' in invalid else mml
    new_mml=mml
    for tag in invalid:
        for item in new_mml.select(tag):
            item.decompose()
            
    return new_mml



def remove_mstyle(mml):
    #if  find mstyletag, remove the tag but keep the children
    for mstyle in mml.find_all('mstyle'):
        mstyle.unwrap()
    return mml

# def replace_mstyle_with_mrow(mml):
#     for mstyle in mml.find_all('mstyle'):
#         mrow = BeautifulSoup('<mrow></mrow>', 'lxml').mrow
#         mrow.extend(mstyle.contents)  # Déplacer les enfants dans mrow
#         mstyle.replace_with(mrow)  # Remplacer mstyle par mrow
#     return mml


# def replace_mstyle_with_mrow(mml):
#     for mstyle in mml.find_all('mstyle'):
#         mstyle.unwrap()
#     return mml
# from bs4 import BeautifulSoup
from bs4 import BeautifulSoup

def replace_mstyle_with_mrow_leg(mml_tag):
    """
    Replace all <mstyle> with <mrow> safely, without needing the root soup.
    """
    for mstyle in mml_tag.find_all('mstyle'):
        # create a new <mrow> by parsing a minimal snippet
        mrow = BeautifulSoup('<mrow></mrow>', 'xml').mrow

        # move all children of mstyle into the new mrow
        for child in list(mstyle.contents):
            mrow.append(child)

        # replace mstyle with mrow
        mstyle.replace_with(mrow)

    return mml_tag

from bs4 import BeautifulSoup

def replace_mstyle_with_mrow(mml_tag):
    """
    Replace all <mstyle> with <mrow>.
    If an <mstyle> has a mathvariant attribute, propagate it to descendant <mi>
    elements that do not already have a mathvariant, then replace <mstyle> by <mrow>.
    """
    for mstyle in mml_tag.find_all('mstyle'):
        # propagate mathvariant from mstyle to contained mi tags
        if mstyle.has_attr('mathvariant'):
            variant = mstyle['mathvariant']

            for mi in mstyle.find_all('mi'):
                if not mi.has_attr('mathvariant'):
                    mi['mathvariant'] = variant

        # create replacement mrow
        mrow = BeautifulSoup('<mrow></mrow>', 'xml').mrow

        # move all children into mrow
        for child in list(mstyle.contents):
            mrow.append(child)

        # replace mstyle with mrow
        mstyle.replace_with(mrow)

    return mml_tag

def remove_mpadded(mml):
    for mpadded in mml.find_all('mpadded'):
        mpadded.unwrap()
    return mml

def remove_dsplaystyle(mml):
    # Remove display attribute ("block" or "inline") in the first <math> tag
    if mml.name == 'math' and mml.has_attr('display'):
        del mml['display']
    return mml


def add_mrow(mml):
    # Create a new mrow element
    new_mrow = BeautifulSoup('<mrow></mrow>', 'lxml').mrow
    
    # Get all children of the input mml (the entire MathML content)
    children = mml.find_all(recursive=False)
    
    # Append each child to the new mrow
    for child in children:
        new_mrow.append(child)
    
    # Clear the original mml and replace it with the new mrow
    mml.clear()  # Clear all contents of mml
    mml.append(new_mrow)  # Add the new mrow to mml
    
    return mml

def remove_double_mrow(mml):
    """If the MathML expression is wrapped in two nested <mrow> tags, remove the outer one."""
    if mml.name == 'math':
        # Handle the common case <math><mrow><mrow>...</mrow></mrow></math>
        if len(mml.contents) == 1 and mml.contents[0].name == 'mrow':
            inner = mml.contents[0]
            if len(inner.contents) == 1 and inner.contents[0].name == 'mrow':
                innermost = inner.contents[0]
                inner.replace_with(innermost)
    elif mml.name == 'mrow':
        # Handle nested <mrow><mrow>...</mrow></mrow> directly
        if len(mml.contents) == 1 and mml.contents[0].name == 'mrow':
            inner = mml.contents[0]
            mml.clear()
            for child in inner.contents:
                mml.append(child)
    return mml


def convert_mfenced(mml):
    for mfenced in mml.find_all('mfenced'):
        open_delim = mfenced.get('open', '(')
        close_delim = mfenced.get('close', ')')
        separators = mfenced.get('separators', ",")
        
        # Get the children inside mfenced (the enclosed content)
        children = mfenced.find_all(recursive=False)
        
        # Create the new structure
        new_content = BeautifulSoup('<mrow></mrow>', 'lxml').mrow
        
        # Add the opening delimiter as a <mo> element
        open_mo = BeautifulSoup('<mo>{}</mo>'.format(open_delim), 'lxml').mo
        new_content.append(open_mo)
        
        # Add children separated by the proper operator if separators exist
        for i, child in enumerate(children):
            new_content.append(child)
            if separators and i < len(children) - 1:
                sep_mo = BeautifulSoup('<mo>{}</mo>'.format(separators[i] if i < len(separators) else separators[-1]), 'lxml').mo
                new_content.append(sep_mo)
        
        # Add the closing delimiter as a <mo> element
        close_mo = BeautifulSoup('<mo>{}</mo>'.format(close_delim), 'lxml').mo
        new_content.append(close_mo)
        
        # Replace the mfenced with the new mrow
        mfenced.replace_with(new_content)
    
    return mml

def remove_stretchy(mml):
    for mo in mml.find_all('mo'):
        if mo.has_attr('stretchy'):
            del mo['stretchy']
    return mml

from bs4 import NavigableString

def normalize_spaces_in_mi_to_mtext(mml):
    """
    Convert all raw spaces inside <mi> into <mtext> &#x00A0;
    to prevent loss during merge_adjacent_mi and normalization steps.
    """

    for mi in mml.find_all("mi"):

        # cas texte pur dans mi
        if mi.string:

            txt = str(mi.string)

            # si uniquement espace ou contient espace
            if " " in txt:

                parts = []
                buffer = ""

                for c in txt:
                    if c == " ":
                        if buffer:
                            parts.append(("mi", buffer))
                            buffer = ""
                        parts.append(("space", None))
                    else:
                        buffer += c

                if buffer:
                    parts.append(("mi", buffer))

                new_nodes = []

                for typ, val in parts:
                    if typ == "mi":
                        new_mi = BeautifulSoup("<mi></mi>", "xml").mi
                        new_mi.string = val
                        new_nodes.append(new_mi)

                    else:
                        mtext = BeautifulSoup("<mtext>&#x00A0;</mtext>", "xml").mtext
                        new_nodes.append(mtext)

                # remplacement
                for n in reversed(new_nodes):
                    mi.insert_after(n)

                mi.decompose()

    return mml


def merge_adjacent_mi(mml):
    def merge_in_node(node):
        if not hasattr(node, 'contents'):
            return

        if getattr(node, "name", None) == "mrow":
            i = 0
            while i < len(node.contents) - 1:
                current = node.contents[i]
                nxt = node.contents[i + 1]

                if getattr(current, "name", None) == "mi" and getattr(nxt, "name", None) == "mi":
                    curr_text = current.string or ""
                    next_text = nxt.string or ""
                    merged_text = curr_text + next_text

                    is_mono = (len(curr_text) == 1 and len(next_text) == 1)

                    curr_var = current.get("mathvariant")
                    next_var = nxt.get("mathvariant")

                    if is_mono:
                        # aucun attribut → italic
                        if not curr_var and not next_var:
                            current["mathvariant"] = "italic"

                        # bold + bold → bold-italic
                        elif curr_var == "bold" and next_var == "bold":
                            current["mathvariant"] = "bold-italic"

                        # gestion générique (optionnelle) : fusion des styles
                        elif curr_var or next_var:
                            styles = set()
                            if curr_var:
                                styles.update(curr_var.split("-"))
                            if next_var:
                                styles.update(next_var.split("-"))
                            if styles:
                                current["mathvariant"] = "-".join(sorted(styles))

                    current.string = merged_text
                    nxt.decompose()
                else:
                    i += 1

        for child in list(node.contents):
            merge_in_node(child)

    merge_in_node(mml)
    return mml








def remove_useless_mrow(mml):
    #make sure to not remove the mrow that  have multiple children
    for mrow in mml.find_all('mrow'):
        if len(mrow.contents) == 1:
            child = mrow.contents[0]
            mrow.replace_with(child)
    return mml

# def remove_variant_italic(mml):
#     for mi in mml.find_all('mi'):
#         if mi.has_attr('mathvariant') and mi['mathvariant'] == 'italic':
#             del mi['mathvariant']
#     return mml
def replace_mspace_with_mtext(body):
    # body = un tag <math> ou <mrow> déjà extrait depuis BeautifulSoup
    for mspace in body.find_all("mspace"):
        width = mspace.get("width", "1ex")

        # ---- extraction du nombre d'ex ----
        if width.endswith("ex"):
            try:
                n = float(width[:-2])
            except:
                n = 1.0
        else:
            n = 1.0

        # ---- convertir X ex → X espaces mtext ----
        count = max(1, int(round(n)))

        # ---- créer la séquence <mtext> </mtext> × count ----
        rep = BeautifulSoup("", "lxml")
        for _ in range(count):
            rep.append(BeautifulSoup("<mtext>&#160;</mtext>", "lxml").mtext)

        # ---- remplacer proprement ----
        mspace.replace_with(rep)

    return body




def replace_none_tag(body):
    #replace None tag with mtext with empty space
    #if you find <none></none>
    # replace it with <mtext> </mtext>
    for none_tag in body.find_all('none'):
        mtext = BeautifulSoup('<mtext>&#160;</mtext>', 'lxml').mtext
        none_tag.replace_with(mtext)
        
    return body
import unicodedata
from bs4 import BeautifulSoup, NavigableString

tag_factory = BeautifulSoup("", "lxml")

VARIANT_KEYWORDS = {
    "DOUBLE-STRUCK": "double-struck",
    "ITALIC": "italic",
    "BOLD": "bold",
    "SCRIPT": "script",
    "FRAKTUR": "fraktur",
    "SANS-SERIF": "sans-serif",
}

SPECIAL_MATH_CHARS = {
    "ℝ": ("R", "double-struck"),
    "ℤ": ("Z", "double-struck"),
    "ℂ": ("C", "double-struck"),
    "ℕ": ("N", "double-struck"),
    "ℚ": ("Q", "double-struck"),
    "ℍ": ("H", "double-struck"),
    "ⅆ": ("d", "italic"),
    "ℓ": ("l", "script"),
}


def normalize_math_char(c):

    if c in SPECIAL_MATH_CHARS:
        return SPECIAL_MATH_CHARS[c]

    name = unicodedata.name(c, "")

    variant = None
    for k in VARIANT_KEYWORDS:
        if k in name:
            variant = VARIANT_KEYWORDS[k]
            break

    if variant is None:
        return c, None

    base = unicodedata.normalize("NFKD", c)

    if len(base) == 1:
        return base, variant

    return c, None


def normalize_math_unicode(body):

    for text_node in list(body.find_all(string=True)):

        chars = list(text_node)
        new_nodes = []

        for c in chars:

            base, variant = normalize_math_char(c)

            if variant:

                mi = tag_factory.new_tag("mi")
                mi["mathvariant"] = variant
                mi.string = base

                new_nodes.append(mi)

            else:

                new_nodes.append(NavigableString(c))

        if len(new_nodes) == 1 and isinstance(new_nodes[0], NavigableString):
            continue

        for node in reversed(new_nodes):
            text_node.insert_after(node)

        text_node.extract()

    return body
def clean_a_soup(soup):
    #remove mfcened
    if soup('math'):
        body=soup('math')[0]
        DEBUG = 0


        #mremoving mfenced
        # print(input_path)
        # print("*"*20)
        # print('before mstyle and mpadded and mrow')
        # print(body)
        if DEBUG == 1:
            print("starting")

        body = remove_dsplaystyle(body)
        if DEBUG == 1:
            print("a")
            print(body)
        body=replace_mstyle_with_mrow(body)
        if DEBUG == 1:
            print("b")
            print(body)
        body = remove_mpadded(body)
        if DEBUG == 1:
            print("c")
            print(body)
        body = add_mrow(body)
        if DEBUG == 1:
            print(body)
        body = replace_none_tag(body)
        if DEBUG == 1:
            print(body)
            print("n")
        # print('after mstyle and mpadded and mrow')
        # print(body)

        # print("before mfenced")
        # print(body)
        body=convert_mfenced(body)
        if DEBUG == 1:
            print(body)
        # print('after mfenced')
        # print(body)
        # print("*"*20)
        body = replace_mspace_with_mtext(body)
        if DEBUG == 1:
            print(body)
        #remove any strecthy attribute
        body = remove_stretchy(body)
        if DEBUG == 1:
            print(body)
        #print(body)
        body = normalize_spaces_in_mi_to_mtext(body)
        body = merge_adjacent_mi(body)
        if DEBUG == 1:
            print(body)
        #print(body)
        

        body = normalize_math_unicode(body)
        
        body = remove_useless_mrow(body)
        if DEBUG == 1:
            print(body)
        #print(body)
        # body = remove_variant_italic(body)
        # print("*"*20)
        clean_mml = remove_unknown_tags(body)
        if DEBUG == 1:
            print(body)
        clean_mml = remove_double_mrow(clean_mml)
        if DEBUG == 1:
            print(body)



        if DEBUG == 1:
            print("Done")
        try:
            return clean_mml
        except Exception as e:
            print('error in writing: ',name)
            print('clean mml: ',clean_mml)
            print('error: ',e)
            #stop the process
            #save the name in a txt : error_files.txt
            with open('error_files.txt','a') as f:
                f.write(name+'\n')

    else:
        print('math tag not found for: ',name)

# Parse the MathML
    #root = ET.fromstring(mathml)

def clean_mathml(input_path):
    """Cleans the MathML content by removing unnecessary tags and restructuring it."""
    name = input_path.split('/')[-1]
    soup = BeautifulSoup(open(input_path),'lxml')
    clean_mml = clean_a_soup(soup)
    return clean_mml


import re


def remove_spaces_outside_tags(mml_string):
    # pattern qui capture :
    # 1) les blocs <mtext> </mtext>
    # 2) les autres tags <...>
    # 3) le texte hors tags
    #je veux catch que les mtext avec un unique espace entre les deux mtext
    pattern = re.compile(r'<mtext> </mtext>|<[^>]+>|[^<]+')

    def replacer(match):
        text = match.group(0)

        # préserver intégralement <mtext>...</mtext>
        if text.startswith("<mtext>"):
            return text

        # préserver les autres tags
        if text.startswith("<"):
            return text

        # supprimer les espaces ailleurs
        return text.replace(" ", "")

    return "".join(replacer(m) for m in pattern.finditer(mml_string))


def clean_mathml_from_string(mathml_string):
    """Cleans the MathML content from a string input."""
    soup = BeautifulSoup(mathml_string, 'lxml')
    clean_mml = clean_a_soup(soup)
    #use remove_spaces_outside_tags to remove spaces that are not between < and >
    clean_mml_str = str(clean_mml)
    clean_mml_str = remove_spaces_outside_tags(clean_mml_str)
    return clean_mml_str
    
#%%
def process_mathml_files(input_folder, output_folder):
    """Processes all MathML files in the input folder and saves cleaned versions in the output folder."""
    os.makedirs(output_folder, exist_ok=True)
    
    for filename in os.listdir(input_folder):
        if filename.endswith(".mml"):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            
            with open(input_path, "r", encoding="utf-8") as file:
                mathml_content = file.read()
            
            cleaned_mathml = clean_mathml(input_path)
            #cleaned_mathml is a soup, so convert to str
            cleaned_mathml = str(cleaned_mathml)
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(cleaned_mathml)
            
            print(f"Processed: {filename}")

    print("Processing completed.")


import pandas as pd


def process_csv_file(csv_path):
    df = pd.read_csv(csv_path)
    # Assuming the MathML content is in a column named 'mathml'
    cleaned_mathml_list = []
    from tqdm import tqdm
    for mathml in tqdm(df['mathml'], desc="Cleaning MathML"):
        cleaned_mathml = clean_mathml_from_string(mathml)
        cleaned_mathml_list.append(cleaned_mathml)

    df['cleaned_mathml'] = cleaned_mathml_list
    output_csv = csv_path.replace(".csv", "_cleaned.csv")
    df.to_csv(output_csv, index=False)
    print(f"Cleaned CSV saved to {output_csv}")


if __name__ == "__main__":
    input_path = sys.argv[1]

    if os.path.isdir(input_path):
        output_folder = input_path + "_cleaned"
        process_mathml_files(input_path, output_folder)
    elif input_path.endswith(".csv"):
        process_csv_file(input_path)
    else:
        print("Input must be a folder or a .csv file.")

#usage : python mml_cleaner.py path_to_mml_files OR a csv file with a column named 'mathml' containing MathML content.
# The cleaned MathML will be saved in the same folder with '_cleaned' suffix for folders or '_cleaned.csv' for CSV files.
#%%
