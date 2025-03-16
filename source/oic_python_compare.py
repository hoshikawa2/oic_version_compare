import os
import zipfile
import shutil
import re
import tempfile
import json
import xml.etree.ElementTree as ET
import pandas as pd
from tabulate import tabulate

# Set the path of the temporary directory
directory_temp = 'temp'

def create_copy_temporary(file):
    # Create a temporary file
    fd, nome_file_temp = tempfile.mkstemp(dir=directory_temp, suffix='.zip')
    os.close(fd)

    # Copy the contents of the original file to the temporary file
    with open(file, 'rb') as f_orig, open(nome_file_temp, 'wb') as f_temp:
        f_temp.write(f_orig.read())

    return nome_file_temp

def extract_file(file, directory_destino):
    # Rename the file to .zip
    nome_file_zip = file.replace('.iar', '.zip')
    os.rename(file, nome_file_zip)

    # Extract the zip file to the destination directory
    with zipfile.ZipFile(nome_file_zip, 'r') as zip_ref:
        zip_ref.extractall(directory_destino)

    # Remove the temporary zip file
    os.remove(nome_file_zip)

def rename_folders_with_version(directory):
    for root, dirs, files in os.walk(directory):
        for dir in dirs:
            if re.search(r'\d+\.\d+\.\d+', dir):
                novo_nome = re.sub(r'\d+\.\d+\.\d+', '_VERSION', dir)
                os.rename(os.path.join(root, dir), os.path.join(root, novo_nome))

def compare_files(file1, file2):
    try:
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()

            differences = []
            for i in range(max(len(lines1), len(lines2))):
                if i >= len(lines1):
                    differences.append(f'+ {lines2[i].strip()}')
                elif i >= len(lines2):
                    differences.append(f'- {lines1[i].strip()}')
                elif lines1[i] != lines2[i]:
                    differences.append(f'- {lines1[i].strip()}')
                    differences.append(f'+ {lines2[i].strip()}')

            if differences:
                return '\n'.join(differences)
            else:
                return None
    except Exception as e:
        print(f"Error in compare files: {e}")
        return None

def compare_properties(file1, file2):
    try:
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            props1 = {}
            props2 = {}
            for line in f1.readlines():
                wkey, valor = line.strip().split('=')
                props1[wkey] = valor
            for line in f2.readlines():
                wkey, valor = line.strip().split('=')
                props2[wkey] = valor

            differences = []
            for wkey in set(list(props1.keys()) + list(props2.keys())):
                if wkey not in props1:
                    differences.append(f'+ {wkey}={props2[wkey]}')
                elif wkey not in props2:
                    differences.append(f'- {wkey}={props1[wkey]}')
                elif props1[wkey] != props2[wkey]:
                    differences.append(f'- {wkey}={props1[wkey]}')
                    differences.append(f'+ {wkey}={props2[wkey]}')

            if differences:
                return '\n'.join(differences)
            else:
                return None
    except Exception as e:
        print(f"Error when comparing properties: {e}")
        return None

def compare_json(file1, file2):
    try:
        import json
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            json1 = json.load(f1)
            json2 = json.load(f2)

            differences = []
            def compare_json_recursive(obj1, obj2, path=''):
                if isinstance(obj1, dict) and isinstance(obj2, dict):
                    wkeys = set(list(obj1.keys()) + list(obj2.keys()))
                    for wkey in wkeys:
                        if wkey not in obj1:
                            differences.append(f'+ {path}{wkey}={obj2[wkey]}')
                        elif wkey not in obj2:
                            differences.append(f'- {path}{wkey}={obj1[wkey]}')
                        elif obj1[wkey] != obj2[wkey]:
                            differences.append(f'- {path}{wkey}={obj1[wkey]}')
                            differences.append(f'+ {path}{wkey}={obj2[wkey]}')
                            if isinstance(obj1[wkey], dict) and isinstance(obj2[wkey], dict):
                                compare_json_recursive(obj1[wkey], obj2[wkey], path+f'[{wkey}].')
                elif isinstance(obj1, list) and isinstance(obj2, list):
                    for i in range(max(len(obj1), len(obj2))):
                        if i >= len(obj1):
                            differences.append(f'+ {path}[{i}]={obj2[i]}')
                        elif i >= len(obj2):
                            differences.append(f'- {path}[{i}]={obj1[i]}')
                        elif obj1[i] != obj2[i]:
                            differences.append(f'- {path}[{i}]={obj1[i]}')
                            differences.append(f'+ {path}[{i}]={obj2[i]}')
                            if isinstance(obj1[i], dict) and isinstance(obj2[i], dict):
                                compare_json_recursive(obj1[i], obj2[i], path+f'[{i}].')
            compare_json_recursive(json1, json2)
            if differences:
                return '\n'.join(differences)
            else:
                return None
    except Exception as e:
        print(f"Error comparing JSON: {e}")
        return None

def compare_xml(file1, file2):
    try:
        import xml.etree.ElementTree as ET
        tree1 = ET.parse(file1)
        tree2 = ET.parse(file2)

        differences = []
        def compare_xml_recursive(elem1, elem2, path=''):
            if elem1.tag != elem2.tag:
                differences.append(f'- {path}{elem1.tag}')
                differences.append(f'+ {path}{elem2.tag}')
            elif elem1.attrib != elem2.attrib:
                for wkey in set(list(elem1.attrib.keys()) + list(elem2.attrib.keys())):
                    if wkey not in elem1.attrib:
                        differences.append(f'+ {path}@{wkey}={elem2.attrib[wkey]}')
                    elif wkey not in elem2.attrib:
                        differences.append(f'- {path}@{wkey}={elem1.attrib[wkey]}')
                    elif elem1.attrib[wkey] != elem2.attrib[wkey]:
                        differences.append(f'- {path}@{wkey}={elem1.attrib[wkey]}')
                        differences.append(f'+ {path}@{wkey}={elem2.attrib[wkey]}')
            if elem1.text != elem2.text:
                differences.append(f'- {path}={elem1.text}')
                differences.append(f'+ {path}={elem2.text}')
            for child1, child2 in zip(elem1, elem2):
                compare_xml_recursive(child1, child2, path+f'/{child1.tag}')
        compare_xml_recursive(tree1.getroot(), tree2.getroot())
        if differences:
            return '\n'.join(differences)
        else:
            return None
    except Exception as e:
        print(f"Error comparing XML: {e}")
        return None

def compare_directories(directory1, directory2):
    print(f"Comparing {directory1} and {directory2}")

    result_lists = []
    files = []

    # Get the list of files and folders in directory 1
    pasta1 = os.listdir(directory1)

    # Get the list of files and folders in directory 2
    pasta2 = os.listdir(directory2)

    # Compare files and folders
    for item in pasta1:
        if item not in pasta2:
            result_lists.append(f"Item {item} not found in {directory2}")
            files.append(directory1 + item)
        else:
            path_item1 = os.path.join(directory1, item)
            path_item2 = os.path.join(directory2, item)

            if os.path.isfile(path_item1) and os.path.isfile(path_item2):
                # Compare the files
                if item.endswith('.properties'):
                    differences = compare_properties(path_item1, path_item2)
                elif item.endswith('.json'):
                    differences = compare_json(path_item1, path_item2)
                elif item.endswith('.xml'):
                    differences = compare_xml(path_item1, path_item2)
                else:
                    differences = compare_files(path_item1, path_item2)

                if differences:
                    result_lists.append(f"Differences found in {path_item1} and {path_item2}:")
                    files.append(path_item1 + " - " + path_item2)

                    x = differences.split('\n')
                    result_lists.extend(x)
                    for y in x:
                        files.append("")

            elif os.path.isdir(path_item1) and os.path.isdir(path_item2):
                # Compare directories recursively
                x, w = compare_directories(path_item1, path_item2)
                result_lists.extend(x)
                item_idx = 0
                for y in x:
                    files.append(w[item_idx])
                    item_idx = item_idx + 1

    # Create a table to store the result_lists
    table_result_lists = {
        "File/Folder": [],
        "Differences": []
    }

    item_idx = 0
    # Add the result_lists to the table
    for item in result_lists:
        if item.startswith("Differences found"):
            table_result_lists["File/Folder"].append(files[item_idx])
            table_result_lists["Differences"].append("\n".join(result_lists[result_lists.index(item)+1:result_lists.index(item)+10]))
        else:
            table_result_lists["File/Folder"].append(files[item_idx])
            table_result_lists["Differences"].append("")
        item_idx = item_idx + 1

    # Create a DataFrame from the table
    df = pd.DataFrame(table_result_lists)

    # Save the result_list to a TXT file
    with open('../result_list.txt', 'w') as f:
        f.write(tabulate(df, headers="keys", tablefmt="psql"))

    return result_lists, files

def main():
    # Defina os nomes dos artifacts
    artifact1 = 'MIGRATE_TO_APIGW_01.00.0003.iar'
    artifact2 = 'MIGRATE_TO_APIGW_01.00.0007.iar'

    # Create the temporary directory if it does not exist
    if not os.path.exists(directory_temp):
        os.makedirs(directory_temp)

    # Create temporary copies of artifacts
    file_temp1 = create_copy_temporary(artifact1)
    file_temp2 = create_copy_temporary(artifact2)

    # Create temporary directories for each artifact
    directory_temp1 = os.path.join(directory_temp, artifact1.replace('.iar', ''))
    directory_temp2 = os.path.join(directory_temp, artifact2.replace('.iar', ''))

    # Create temporary directories if they do not exist
    if not os.path.exists(directory_temp1):
        os.makedirs(directory_temp1)
    if not os.path.exists(directory_temp2):
        os.makedirs(directory_temp2)

    # Extract the temporary artifacts
    extract_file(file_temp1, directory_temp1)
    extract_file(file_temp2, directory_temp2)

    # Rename folders with version
    rename_folders_with_version(directory_temp1)
    rename_folders_with_version(directory_temp2)

    # Compare directories
    compare_directories(directory_temp1, directory_temp2)

    # Remove temporary files
    try:
        os.remove(file_temp1)
    except:
        None
    try:
        os.remove(file_temp2)
    except:
        None

    # Remove temporary directories
    try:
        shutil.rmtree(directory_temp1)
    except:
        None
    try:
        shutil.rmtree(directory_temp2)
    except:
        None

    # Remove the temporary directory
    try:
        shutil.rmtree(directory_temp)
    except:
        None

if __name__ == '__main__':
    main()