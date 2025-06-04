from fusionrest import get_current_image_path
import os
import h5py
import numpy as np
import matplotlib.pyplot as plt


def imaris_image_reader(file):
    """

    Read a 3D imaris image as a numpy array.

    * .ims: imaris file using h5py, highest resolution and first time point is loaded

    :param file: str, path to image file, can be relative or absolute.
    :return: np.array, image data, shape: (x, y, (z))

    """

    file_path, file_extension = os.path.splitext(file)

    if file_extension == '.ims':

        img = h5py.File(file, 'r')['DataSet']['ResolutionLevel 0']['TimePoint 0']['Channel 0']['Data'][()]

    else:
        raise TypeError("File is not an .ims file")

    if len(img.shape) == 3:
        img = np.swapaxes(img, 0, 2)

    return img


def get_current_image_3d():
    print("Loading image", get_current_image_path())
    im = imaris_image_reader(get_current_image_path())
    return im


def get_current_image_2d():
    return np.max(get_current_image_3d(), axis=2)


def show_projection_of_current_image():
    proj = get_current_image_2d()
    plt.imshow(proj)
    plt.show()
    return
