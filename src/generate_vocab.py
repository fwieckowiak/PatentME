# %%
import pandas as pd
import re
import unicodedata
from lxml import etree
from tqdm import tqdm
from collections import defaultdict
import json

# normalize mspace
def normalize_mspace(root):

    for mtext in root.xpath("//mtext"):

        if not (mtext.text and mtext.text.strip()):

            parent = mtext.getparent()
            idx = parent.index(mtext)

            mspace = etree.Element("mspace")

            parent.insert(idx, mspace)
            parent.remove(mtext)

    for mspace in root.xpath("//mspace"):
        mspace.attrib.clear()


def tokenize_example(mml):

    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(mml.encode(), parser=parser)

    normalize_mspace(root)

    tokens = tokenize_mathml(root)

    # split the tokens that are not XML tags into characters
    # using the split_text_token function defined earlier
    split_tokens = []
    for tok in tokens:
        if re.match(r"<.*?>", tok):
            split_tokens.append(tok)
        else:
            split_tokens.extend(list(tok))

    # add <SOS> at the beginning and <EOS> at the end
    split_tokens = ["<SOS>"] + split_tokens + ["<EOS>"]
    token_ids = [token_to_id.get(tok, token_to_id["<UNK>"]) for tok in split_tokens]

    return token_ids


def detokenize_example(token_ids):

    tokens = [
        id_to_token[idx]
        for idx in token_ids
        if idx in id_to_token and id_to_token[idx] not in {"<PAD>", "<SOS>", "<EOS>"}
    ]

    return "".join(tokens).replace("<mspace/>", "<mtext>\u00a0</mtext>")


# tokenizer
def tokenize_mathml(root):

    tokens = []

    def visit(node):

        if node.tag == "mspace":
            tokens.append("<mspace/>")
            return

        attrs = " ".join(f'{k}="{v}"' for k, v in node.attrib.items())

        if attrs:
            tokens.append(f"<{node.tag} {attrs}>")
        else:
            tokens.append(f"<{node.tag}>")

        if node.text and node.text.strip():

            text_tokens = re.findall(r"[A-Za-z]+|\d+|[^\s]", node.text)

            tokens.extend(text_tokens)

        for child in node:

            visit(child)

            if child.tail and child.tail.strip():

                tail_tokens = re.findall(r"[A-Za-z]+|\d+|[^\s]", child.tail)

                tokens.extend(tail_tokens)

        tokens.append(f"</{node.tag}>")

    visit(root)

    return tokens


def split_text_token(token):
    # if it is a XML tag, return it as is
    if re.match(r"<.*?>", token):
        return [token]
        # otherwise, split it into characters

        return list(token)


if __name__ == "__main__":

    #add an arg parser to specify the path to the processed data
    #before using it !! do data cleaning
    #python3 mml_cleaner.py raw_data.csv
    #using the script python3 mml_cleaner.py "path_to_raw_data"
    #then use this one :
    #python3 generate_vocab.py --processed_data_path "processed_data_v1"
    import argparse
    parser = argparse.ArgumentParser(description="Generate vocab from cleaned data")
    parser.add_argument(
        "--processed_data_path",
        type=str,
        default="../processed_data",
        help="Path to the processed data",
    )
    parser.add_argument(
        "--min_token_freq",
        type=int,
        default=1,
        help="Minimum frequency for a token to be included in the vocab",   
    )
    args = parser.parse_args()

    processed_data_path = args.processed_data_path
    raw_data_cleaned_path = f"{processed_data_path}/raw_data_cleaned.csv"

    df = pd.read_csv(raw_data_cleaned_path)

    #before tokenize !! i need to do a test, val, train split of the data, and save the info in a new column in the dataframe
    #and then we do the tokenization only on the train set, to avoid data leakage
    from sklearn.model_selection import train_test_split
    TRAIN_SIZE = 0.8
    VAL_SIZE = 0.1
    TEST_SIZE = 0.1
    df_train, df_temp = train_test_split(df, test_size=1 - TRAIN_SIZE, random_state=42)
    df_val, df_test = train_test_split(df_temp, test_size=TEST_SIZE / (TEST_SIZE + VAL_SIZE), random_state=42)
    df_train["split"] = "train"
    df_val["split"] = "val"
    df_test["split"] = "test"
    df = pd.concat([df_train, df_val, df_test], ignore_index=True)



    all_tokens = []

    reverse_index = defaultdict(list)

    for idx, mml in tqdm(enumerate(df_train["cleaned_mathml"]), total=len(df_train)):

        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(mml.encode(), parser=parser)

        normalize_mspace(root)

        tokens = tokenize_mathml(root)

        all_tokens.extend(tokens)

        for tok in set(tokens):
            reverse_index[tok].append(idx)

    # save a count of the tokens in a json file
    

    token_counts = {tok: len(idxs) for tok, idxs in reverse_index.items()}
    with open(f"{processed_data_path}/token_counts.json", "w") as f:
        json.dump(token_counts, f)


    token_freq = {tok: len(idxs) for tok, idxs in reverse_index.items()}
    sorted_tokens = sorted(token_freq.items(), key=lambda x: x[1], reverse=True)
    tokens, freqs = zip(*sorted_tokens)

    mini_token_count = {}

    final_tokens = set()

    for tok in all_tokens:

        if re.match(r"<.*?>", tok):
            final_tokens.add(tok)
            mini_token_count[tok] = mini_token_count.get(tok, 0) + 1
        else:
            for char in tok:
                final_tokens.add(char)
                mini_token_count[char] = mini_token_count.get(char, 0) + 1
                
    print("vocab size before filtering:", len(final_tokens))

    # filter tokens by frequency
    #remove from the vocab tokens that have a mini count less than the min_token_freq
    final_tokens = {tok for tok in final_tokens if mini_token_count.get(tok, 0) >= args.min_token_freq}
    print("vocab size after filtering:", len(final_tokens))
    

    #save mini_token_count
    with open(f"{processed_data_path}/mini_token_count.json", "w") as f:
        json.dump(mini_token_count, f)




    # maintenant que j'ai le vocab, je dois le sauvergarder en ajoutant les
    # tokens spéciaux et en créant un mapping token -> id
    special_tokens = ["<PAD>", "<UNK>", "<SOS>", "<EOS>"]
    vocab = special_tokens + sorted(final_tokens)
    token_to_id = {tok: idx for idx, tok in enumerate(vocab)}
    # save vocab and token_to_id

    with open(f"{processed_data_path}/vocab.json", "w") as f:
        json.dump(vocab, f)
    with open(f"{processed_data_path}/token_to_id.json", "w") as f:
        json.dump(token_to_id, f)

    special_tokens = ["<PAD>", "<UNK>", "<SOS>", "<EOS>"]
    vocab = special_tokens + sorted(final_tokens)

    token_to_id = {tok: idx for idx, tok in enumerate(vocab)}
    id_to_token = {idx: tok for tok, idx in token_to_id.items()}

    # test
    example_mml = df["cleaned_mathml"].iloc[0]
    example_mml = "<math><mn>10</mn></math>"

    token_ids = tokenize_example(example_mml)

    print("token ids:", token_ids)

    detokenized = detokenize_example(token_ids)

    print("detokenized:", detokenized)
    print("original:", example_mml)

    # so the final step is to tokenize all the examples and save the token ids in a new column in the dataframe, then save the dataframe as a new csv file
    token_ids_list = []
    for mml in tqdm(df["cleaned_mathml"], total=len(df)):
        token_ids = tokenize_example(mml)
        detokenized = detokenize_example(token_ids)
        # in the orignial replace lt, gt and amp by their corresponding characters
        original = mml.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

        if detokenized != original:
            #find the first index where the two strings differ and print the original and detokenized strings around that index
            i   = 0
            while i < min(len(detokenized), len(original)) and detokenized[i] == original[i]:
                i += 1
            print(f"Mismatch at index {i}:")
            print("Original   :", original)
            print("Detokenized:", detokenized)
            # find the exact position of the mismatch
            for j in range(min(len(original), len(detokenized))):
                if original[j] != detokenized[j]:
                    print(
                        f"Mismatch at position {j}: '{original[j]}' vs '{detokenized[j]}'"
                    )
                    print(
                        "ord of original char:",
                        ord(original[j]),
                        "ord of detokenized char:",
                        ord(detokenized[j]),
                    )
                    break

        token_ids_list.append(token_ids)
    df["tokenized_mathml"] = token_ids_list
    df.to_csv(f"{processed_data_path}/raw_data_tokenized.csv", index=False)

    print("Tokenization complete and saved to raw_data_tokenized.csv")
    # %%
