import os
import argparse
from PIL import Image
from itertools import product


from sklearn.datasets import load_sample_image
from sklearn.feature_extraction import image


def tile(filename, dir_in, dir_out, d):
    name, ext = os.path.splitext(filename)
    img = Image.open(os.path.join(dir_in, filename))
    w, h = img.size
    
    grid = product(range(0, h-h%d, d), range(0, w-w%d, d))
    for i, j in grid:
        box = (j, i, j+d, i+d)
        i /= 256
        j /= 256
        out = os.path.join(dir_out, f'{name}_{i}_{j}{ext}')
        img.crop(box).save(out)


def tile_scikit(filename, dir_in, dir_out, d):
    name, ext = os.path.splitext(filename)
    img = load_sample_image(os.path.join(dir_in, filename))
    print('Image shape: {}'.format(img.shape))

    patches = image.extract_patches_2d(img, (256, 256))
    print('Patches shape: {}'.format(patches.shape))

    print(patches)


parser = argparse.ArgumentParser(description='Patchify images')
parser.add_argument('--source', type = str,
					help='Path to folder containing the image files')
parser.add_argument('--dest', type = str,
					help='Path to folder for storing the patches')
parser.add_argument('--patch_size', type = int, default=256,
					help='patch_size')


if __name__ == '__main__':
	args = parser.parse_args()

	input_dir = args.source
	output_dir = args.dest
	patch_size = args.patch_size

	if not os.path.isdir(output_dir):
		os.mkdir(output_dir)
	
	for filename in os.listdir(input_dir):
		name, ext = os.path.splitext(filename)
		output_patches_dir = os.path.join(output_dir, name)
		
		if not os.path.isdir(output_patches_dir):
			os.mkdir(output_patches_dir)

		tile_scikit(filename, input_dir, output_patches_dir, patch_size)
