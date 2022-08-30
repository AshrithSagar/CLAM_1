# To glue between create_patches.py and extract_features.py

import os
import argparse

parser = argparse.ArgumentParser(description='Initialize .h5 files')
parser.add_argument('--source', type = str,
                    help='Path to folder containing the image folders of patches')

if __name__ == '__main__':
    args = parser.parse_args()

    patch_dir = args.source

    for folder in os.listdir(patch_dir):
        patch_folder = os.path.join(patch_dir, folder)
        for patch in os.listdir(patch_folder):
            name = patch
            file_path = os.path.join(save_path, name)+'.h5'
            file = h5py.File(file_path, "w")

            file.close()
