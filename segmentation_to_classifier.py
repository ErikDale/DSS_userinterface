import math

import cv2
import numpy as np
import pytesseract
import torch
import torch.nn as nn
import torch.nn.functional as nnf
from PIL import Image
import image_straighten as imgStraighten


# Object for letters that contain the image, the coordinates, and the classification.
class Letter:
    def __init__(self, image, x, y, w, h):
        self.image = image
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.label = None
        self.confidence = None

    def add_label(self, label, confidence):
        self.label = label
        self.confidence = confidence


# Returns the confidence value of a letter as a boolean.
def class_letter_checker(image):
    classifier = Classifier("./default_2.model")
    _, confidence_value = classifier.SimplyClassify(image)
    return confidence_value


# Straightens the letters in an image
def image_straighten(image):
    img = image

    thresh = cv2.threshold(img, 127, 255, 1)[1]

    imgStraighten.deskew(thresh)
    sheared_img = imgStraighten.unshear(thresh)

    ret, thresh = cv2.threshold(sheared_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    return thresh


# Removes the white space over a letter
def image_cropper(img):
    h_img, w_img = img.shape
    if h_img >= 1 and w_img >= 1:
        edged = cv2.Canny(img, 30, 200)

        coords = cv2.findNonZero(edged)
        x, y, w, h = cv2.boundingRect(coords)
        crop = img[y:y + h, :]

        return crop
    else:
        return None


# Splits a word into letters
def word_splitter(word):
    image = image_straighten(word)

    size = np.size(image)
    skel = np.zeros(image.shape, np.uint8)

    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))

    # Skeletonizes the image
    while True:
        open = cv2.morphologyEx(image, cv2.MORPH_OPEN, element)
        temp = cv2.subtract(image, open)

        eroded = cv2.erode(image, element)
        skel = cv2.bitwise_or(skel, temp)
        image = eroded.copy()

        if cv2.countNonZero(image) == 0:
            break

    h_skel, w_skel = skel.shape

    # array for sum of vertical pixels
    amount_vert_pixels = []

    # counts the sum of vertical pixels in image
    for i in range(w_skel):
        col_pixels = int((sum(skel[:, i])) / 255)
        amount_vert_pixels.append(col_pixels)

    min_letter_width = 12
    seg_points = []

    index = len(amount_vert_pixels) - 1

    # Finds the segmentation points with the sum of vertical pixels
    while index > 0:
        if amount_vert_pixels[index] > 0:
            for j in range(index, -1, -1):
                if amount_vert_pixels[j] < 1:
                    if amount_vert_pixels[j - 1] < 1:
                        if (index - j) > min_letter_width:
                            seg_points.append(j)
                            index = j
                            break
                        else:
                            index = j
                            break
                if amount_vert_pixels[j] > 5:
                    if (index - j) > min_letter_width:
                        seg_points.append(j)
                        index = j
                        break
        index -= 1

    # adds segmentation point at the end so that last letter gets included
    if seg_points:
        if seg_points[-1] > min_letter_width / 2:
            seg_points.append(0)

    # crops the letter based on the segmentation point
    segmentation_index = len(amount_vert_pixels)
    segmented_letters_in_word = []
    for i in seg_points:
        extend_image = 2
        out_of_bounds = False

        # if the segmentation is on the right side of the image
        if segmentation_index > len(amount_vert_pixels) - 5:
            cropped_image = word[:, i:len(amount_vert_pixels)]
            cropped_image = image_cropper(cropped_image)

            confidence_value = 0
            best_extend_image = 0
            while True:
                new_confidence_value = class_letter_checker(cropped_image)

                # if the new confidence value is above 60 percent
                if new_confidence_value > 60:
                    break
                # checks if the image has extended further than minimum letter width distance /2
                # or if it has gone out of bounds
                elif extend_image > min_letter_width / 2 or out_of_bounds is True:
                    # Uses the best extend image value that has the highest confidence value
                    cropped_image = word[:, i - best_extend_image:len(amount_vert_pixels)]
                    cropped_image = image_cropper(cropped_image)
                    break

                else:
                    # checks if the iteration has a higher confidence value
                    if confidence_value < new_confidence_value:
                        confidence_value = new_confidence_value
                        best_extend_image = extend_image
                    # reached out of bounds
                    if i - extend_image < 0:
                        out_of_bounds = True
                    else:
                        # extends the image to the left until sufficient classification value
                        cropped_image = word[:, i - extend_image:len(amount_vert_pixels)]
                        cropped_image = image_cropper(cropped_image)
                        extend_image += 2
            cropped_letter = Letter(cropped_image, i, None, segmentation_index, None)
            segmented_letters_in_word.append(cropped_letter)

        # if the segmentation point is on the left side of the image
        elif i < 4:
            cropped_image = word[:, 0:segmentation_index]
            cropped_image = image_cropper(cropped_image)

            confidence_value = 0
            best_extend_image = 0
            while True:
                new_confidence_value = class_letter_checker(cropped_image)

                # if the new confidence value is above 60 percent
                if new_confidence_value > 60:
                    break
                # checks if the image has extended further than minimum letter width distance /2
                # or if it has gone out of bounds
                elif extend_image > min_letter_width / 2 or out_of_bounds is True:

                    # Uses the best extend image value that has the highest confidence value
                    cropped_image = word[:, 0:segmentation_index + best_extend_image]
                    cropped_image = image_cropper(cropped_image)
                    break
                else:
                    # Saves the best confidence value and its extend_image value
                    if confidence_value < new_confidence_value:
                        confidence_value = new_confidence_value
                        best_extend_image = extend_image
                    if segmentation_index + extend_image > len(amount_vert_pixels):
                        out_of_bounds = True
                    else:
                        # extends the image to the right until sufficient classification value
                        cropped_image = word[:, 0:segmentation_index + extend_image]
                        cropped_image = image_cropper(cropped_image)
                        extend_image += 2
            cropped_letter = Letter(cropped_image, i, None, segmentation_index, None)
            segmented_letters_in_word.append(cropped_letter)

        # if the segmentation point is in the middle of the image
        else:
            cropped_image = word[:, i - extend_image:segmentation_index + extend_image]
            cropped_image = image_cropper(cropped_image)

            confidence_value = 0
            best_extend_image = 0
            while True:
                new_confidence_value = class_letter_checker(cropped_image)

                # if the new confidence value is above 60 percent
                if new_confidence_value > 60:
                    # finished
                    break
                # checks if the image has extended further than minimum letter width distance /2
                # or if it has gone out of bounds
                elif extend_image > min_letter_width or out_of_bounds is True:
                    cropped_image = word[:, i - best_extend_image:segmentation_index + best_extend_image]
                    cropped_image = image_cropper(cropped_image)
                    break
                else:
                    # Saves the best confidence value and its extend_image value
                    if confidence_value < new_confidence_value:
                        confidence_value = new_confidence_value
                        best_extend_image = extend_image
                    # checks if the extend image goes out of bounds on either end
                    if i - extend_image < 0 or segmentation_index + extend_image > len(amount_vert_pixels):
                        out_of_bounds = True
                    else:
                        # extends the crop on both sides
                        cropped_image = word[:, i - extend_image:segmentation_index + extend_image]
                        cropped_image = image_cropper(cropped_image)
                        extend_image += 2
            cropped_letter = Letter(cropped_image, i, None, segmentation_index, None)
            segmented_letters_in_word.append(cropped_letter)
        segmentation_index = i

    # Reverses the order of the letters so that they are in the correct order
    segmented_letters_correct = segmented_letters_in_word[::-1]

    return segmented_letters_correct


class Segmentor:
    def __init__(self):
        return

    def segment_letters(self, image):
        # Necessary for running pytesseract
        # Info on how to get it running: https://github.com/tesseract-ocr/tesseract/blob/main/README.md
        pytesseract.pytesseract.tesseract_cmd = r'tesseract\tesseract.exe'

        # Crops the images around the letters/words
        # Saves the height and width of the images
        h_img, w_img = image.shape

        # array for the segmented letters
        segmented_letters = []

        # Makes a box around each letter/word on the scroll
        boxes = pytesseract.image_to_boxes(image, lang="heb")

        # For each box
        for b in boxes.splitlines():
            # Splits the values of the box into an array
            b = b.split(' ')
            # Save the coordinates of the box:
            # x = Distance between the top left corner of the box to the left frame
            # y = Distance between the top of the box to the bottom frame
            # w = Distance between the right side of the box to the left frame
            # h = Distance between the bottom of the box to the bottom frame
            x, y, w, h = int(b[1]), int(b[2]), int(b[3]), int(b[4])

            # Crop the image so that we only get the letter/word
            # Structure image[rows, col]
            crop = image[(h_img - h):(h_img - y), x:w]

            # Height and width of the cropped image
            h_box, w_box = crop.shape

            # Checks if the crop is too small or too large
            if h_box != 0 and w_box != 0:
                # Checks if the crop is too small or too large
                if h_box > (1 / h_box * 100) and w_box > (1 / h_box * 100):
                    # If the segment is larger than 40 pixels wide
                    if w_box > 30:

                        # checks if the box is a large letter
                        if class_letter_checker(crop) > 90:
                            # Saves each segmented letter as a Letter object with the correct coordinate values
                            cropped_letter = Letter(crop, x, y, w, h)

                            # appends the cropped letter to the array
                            segmented_letters.append(cropped_letter)
                        else:
                            for i in word_splitter(crop):
                                # Saves each segmented letter as a Letter object with the correct coordinate values
                                cropped_letter = Letter(i.image, x + i.x, y, x + i.w, h)

                                # appends the cropped letter to the array
                                segmented_letters.append(cropped_letter)

                    # Found single letter
                    else:
                        # Saves each segmented letter as a Letter object with the correct coordinate values
                        cropped_letter = Letter(crop, x, y, w, h)

                        # appends the cropped letter to the array
                        segmented_letters.append(cropped_letter)
        # Saves the image with all the rectangles
        return segmented_letters

    # Method that is run if the background in the image isnt varied
    def segment_clear_background(self, image):
        # Reads image of scroll
        img = image

        # Grayscales image
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Does adaptive histogram equalization
        clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(80, 80))
        equalized = clahe.apply(gray)

        # otsu thresholding
        _, otsu = cv2.threshold(equalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # closing
        inverted_img = cv2.bitwise_not(otsu)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        closed_img = cv2.morphologyEx(inverted_img, cv2.MORPH_CLOSE, kernel)

        inverted_back = cv2.bitwise_not(closed_img)

        # Denoises the closed otsu image
        de_noise_otsu = cv2.fastNlMeansDenoising(inverted_back, h=60.0, templateWindowSize=7, searchWindowSize=21)

        return self.segment_letters(de_noise_otsu)

    # Method that is run if the background in the image is varied
    def segment_varied_background(self, image):
        # Reads image of scroll
        img = image

        # Grayscales image
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Adaptive binarization
        binarize_im = cv2.adaptiveThreshold(src=gray, maxValue=255, adaptiveMethod=cv2.ADAPTIVE_THRESH_MEAN_C,
                                           thresholdType=cv2.THRESH_BINARY, blockSize=39, C=15)

        # Opening
        inverted_img = cv2.bitwise_not(binarize_im)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

        opened_img = cv2.morphologyEx(inverted_img, cv2.MORPH_OPEN, kernel)

        inverted_back = cv2.bitwise_not(opened_img)

        # Closing
        inverted_img = cv2.bitwise_not(inverted_back)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        closed_img = cv2.morphologyEx(inverted_img, cv2.MORPH_CLOSE, kernel)

        inverted_back = cv2.bitwise_not(closed_img)

        # Noise removal
        de_noise_otsu = cv2.fastNlMeansDenoising(inverted_back, h=60.0, templateWindowSize=7, searchWindowSize=21)

        return self.segment_letters(de_noise_otsu)


class Classifier:
    def __init__(self, model, input_size=100):
        self.input_size = input_size

        # Setup model
        self.model = Convolutional(input_size)
        self.model.load_state_dict(torch.load(model, map_location=torch.device('cpu')))
        self.model.eval()

        # Setup classes
        self.classes = ['ALEF', 'BET', 'GIMEL', 'DALET', 'HE', 'VAV', 'ZAYIN', 'HET', 'TET', 'YOD', 'KAF', 'LAMED',
                        'MEM', 'NUN', 'SAMEKH', 'AYIN', 'PE', 'TSADI', 'QOF', 'RESH', 'SHIN', 'TAV']
        self.names = None
        self.values = None

    def ___load_images(self, letters):
        image_batch = np.zeros((len(letters), self.input_size, self.input_size))
        for i, letter in enumerate(letters):
            if letter.image is not None:
                # Load image from array
                image = Image.fromarray(letter.image)

                # Fix the dimensions of the image
                new_image = Image.new(image.mode, (100, 100), 255)
                x, y = int((100 / 2)) - int(image.width / 2), int(100 / 2) - int(image.height / 2)
                new_image.paste(image, (x, y))

                #  Converts back into numpy array
                np_image = np.array(new_image) / 255
                image_batch[i] = np_image

        return image_batch

    def SimplyClassify(self, image):
        # Fix the dimensions of the image
        image = Image.fromarray(image)
        new_image = Image.new(image.mode, (100, 100), 255)
        x, y = int((100 / 2)) - int(image.width / 2), int(100 / 2) - int(image.height / 2)
        new_image.paste(image, (x, y))
        np_image = np.array(new_image) / 255

        # Convert the numpy arrays into tensors
        image = torch.from_numpy(np_image).float()

        # Fix the shape of the array
        image = image.unsqueeze(0).unsqueeze(0)
        # Predict
        result = self.model(image)
        result = result[0]
        # Convert the predictions to a numpy array

        result = nnf.softmax(result, dim=0)
        result = result.detach().numpy()
        confidence = np.argmax(result)
        prediction = self.classes[confidence]
        return prediction, result[confidence] * 100

    def Classify(self, letters):

        images = self.___load_images(letters)

        # Convert the numpy arrays into tensors
        images = torch.from_numpy(images).float()

        # Fix the shape of the array
        images = images.unsqueeze(1)

        # Predict
        results = self.model(images)

        # Convert the predictions to a numpy array

        for i, result in enumerate(results):
            result = nnf.softmax(result, dim=0)
            result = result.detach().numpy()

            confidence = np.argmax(result)
            prediction = self.classes[confidence]
            letters[i].add_label(prediction, math.trunc(result[confidence] * 100))
        return letters

    def getDict(self):
        return self.names, self.values


class Convolutional(nn.Module):
    def __init__(self, input_size):
        super(Convolutional, self).__init__()
        # Convolutional layers and Max pooling with activation functions
        self.convolutional = nn.Sequential(
            nn.Conv2d(1, 6, 5),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(6, 16, 5),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )

        # Fully connected layer with activation functions
        size = int((input_size / 4) - 3)
        self.fullyconnected = nn.Sequential(
            nn.Linear(16 * size * size, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.Sigmoid(),
            nn.Linear(128, 22)
        )

    def forward(self, x):
        x = self.convolutional(x)
        x = torch.flatten(x, 1)
        x = self.fullyconnected(x)
        return x
