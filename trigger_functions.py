from get_current_image import get_current_image_3d
import numpy as np


def image_max_intensity_trigger():
    # returns the maximum of the last image (calculated in 3D)
    return np.max(get_current_image_3d())


def image_99_perc_trigger():
    # returns the 99 percentile of the last image (calculated in 3D)
    return np.percentile(get_current_image_3d(), 99)


"""
def random_trigger_for_testing_returns_1_to_3():
    import random
    # returns a random value between 1 and 3, can be used for testing
    value = random.uniform(0, 3)
    return value
"""