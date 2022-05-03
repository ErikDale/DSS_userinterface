import sys, os
import glob
import traceback
from pathlib import Path

import cv2
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QGridLayout, QShortcut, QFileDialog
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QRunnable, QObject, QThreadPool
from PyQt5.QtGui import QPixmap, QKeySequence, QFont, QMovie

import segmentation_to_classifier as segToClass

import numpy as np
from PIL import Image

import qimage2ndarray


# Gotten a lot from: https://stackoverflow.com/questions/35508711/how-to-enable-pan-and-zoom-in-a-qgraphicsview
# Class that represents the photoviewer object
class PhotoViewer(QtWidgets.QGraphicsView):
    photo_clicked = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        # Makes it so that it accepts drops
        self.setAcceptDrops(True)
        # Boolean to check is image is displayed or not
        self.empty = True
        self.scene = QtWidgets.QGraphicsScene(self)
        self.photo = QtWidgets.QGraphicsPixmapItem()
        self.scene.addItem(self.photo)
        self.zoom_label = QLabel()
        self.setScene(self.scene)

        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("gray")))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        # Creates the rubberband
        self.rubber_band_item = QtWidgets.QRubberBand(
            QtWidgets.QRubberBand.Rectangle
        )
        self.rubber_band_item_geometry = None
        item = self.scene.addWidget(self.rubber_band_item)
        item.setZValue(-1)
        self.draggable = False
        self.rubber_band_item.hide()
        self.origin = QtCore.QPoint()
        self.rubber_bool = False

        self.rectangle = None

        self.is_cropped = False
        self.zoom_level = 100

    # Method for removing image from pixmap
    def remove_item(self):
        # Clears the scene
        self.scene.clear()
        self.photo = QtWidgets.QGraphicsPixmapItem()
        self.scene.addItem(self.photo)
        pixmap = QPixmap()
        self.photo.setPixmap(pixmap)
        # Creates the rubberband
        self.rubber_band_item = QtWidgets.QRubberBand(
            QtWidgets.QRubberBand.Rectangle
        )
        self.rubber_band_item_geometry = None
        item = self.scene.addWidget(self.rubber_band_item)
        item.setZValue(-1)
        self.draggable = False
        self.rubber_band_item.hide()

    # Method to check if pixmap has image or not
    def has_photo(self):
        return not self.empty

    # Method to set a photo in the pixmap
    def set_photo_with_rectangle(self, rectangle=True, pixmap=None):
        if rectangle:
            if pixmap and not pixmap.isNull():
                self.empty = False
                self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
                # Creates a rectangle and adds it to the background of the image
                self.rectangle = QtWidgets.QGraphicsRectItem(QtCore.QRectF(0, 0, pixmap.width(), pixmap.height()))
                self.scene.addItem(self.rectangle)
                # Giving color to the rectangle
                self.rectangle.setBrush(Qt.white)
                self.rectangle.setZValue(-1)
                self.photo.setPixmap(pixmap)
            else:
                self.empty = True
                self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
                self.photo.setPixmap(QtGui.QPixmap())
        else:
            if pixmap and not pixmap.isNull():
                self.empty = False
                self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
                self.photo.setPixmap(pixmap)
            else:
                self.empty = True
                self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
                self.photo.setPixmap(QtGui.QPixmap())

    # Method to set a photo in the pixmap
    def set_photo(self, pixmap=None):
        if pixmap and not pixmap.isNull():
            self.empty = False
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.photo.setPixmap(pixmap)
            # Setting the image at the exact location it was cropped, to keep its coordinates
            self.photo.setPos(self.rubber_band_item_geometry.x(), self.rubber_band_item_geometry.y())
        else:
            self.empty = True
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self.photo.setPixmap(QtGui.QPixmap())

    # Method that handles the zooming functionality
    def wheelEvent(self, event):
        if self.has_photo():
            if event.angleDelta().y() > 0:
                factor = 1.20
                old_zoom = self.zoom_level
                new_zoom = self.zoom_level * factor
                self.zoom_level += (new_zoom - old_zoom)
                self.zoom_label.setText("Zoom level: " + str(int(self.zoom_level)) + "%")
                self.scale(factor, factor)
            else:
                factor = 0.8
                old_zoom = self.zoom_level
                new_zoom = self.zoom_level * factor
                self.zoom_level += (new_zoom - old_zoom)
                self.zoom_label.setText("Zoom level: " + str(int(self.zoom_level)) + "%")
                self.scale(factor, factor)

    # Methods that toggles on and off the different drag modes
    def toggle_drag_mode(self):
        if self.dragMode() == QtWidgets.QGraphicsView.ScrollHandDrag:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        elif not self.photo.pixmap().isNull():
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    # Method that handles what happens when the mouse is pressed
    def mousePressEvent(self, event):
        if self.rubber_bool:
            self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
            self.origin = self.mapToScene(event.pos()).toPoint()
            self.rubber_band_item.setGeometry(
                QtCore.QRect(self.origin, QtCore.QSize())
            )
            self.rubber_band_item.show()
            self.draggable = True
            super(PhotoViewer, self).mousePressEvent(event)
        else:
            if self.photo.isUnderMouse():
                self.photo_clicked.emit(self.mapToScene(event.pos()).toPoint())
            super(PhotoViewer, self).mousePressEvent(event)

    # Method that takes care of what happens when the mouse is moved
    def mouseMoveEvent(self, event):
        if self.rubber_bool:
            if self.draggable:
                end_pos = self.mapToScene(event.pos()).toPoint()
                self.rubber_band_item.setGeometry(
                    QtCore.QRect(self.origin, end_pos).normalized()
                )
                self.rubber_band_item.show()

        elif not self.photo.pixmap().isNull() and not self.rubber_bool:
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        super(PhotoViewer, self).mouseMoveEvent(event)

    # Method that happens when the left-click is released
    def mouseReleaseEvent(self, event):
        if self.rubber_bool:
            end_pos = self.mapToScene(event.pos()).toPoint()
            self.rubber_band_item.setGeometry(
                QtCore.QRect(self.origin, end_pos).normalized()
            )
            self.draggable = False
            # Getting the cropped area and storing it in the pixmap
            self.rubber_band_item_geometry = self.rubber_band_item.geometry()
            crop = self.photo.pixmap().copy(self.rubber_band_item_geometry)
            self.set_photo(crop)
            self.rubber_band_item.hide()
            self.rubber_bool = False
            self.is_cropped = True
        elif not self.photo.pixmap().isNull() and not self.rubber_bool:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        super(PhotoViewer, self).mouseMoveEvent(event)


# Class that allows for multithreading in the gui
# Heavily inspired by this:
# https://stackoverflow.com/questions/63393099/how-to-display-a-loading-animated-gif-while-a-code-is-executing-in-backend-of-my
class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    add_photo = pyqtSignal()
    add_cropped_photo = pyqtSignal()


# Class that allows for multithreading in the gui
# Heavily inspired by this:
# https://stackoverflow.com/questions/63393099/how-to-display-a-loading-animated-gif-while-a-code-is-executing-in-backend-of-my
class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


# Class that represents a timed message box that will appear when classification is done
# Heavily inspired by this:
# https://stackoverflow.com/questions/40932639/pyqt-messagebox-automatically-closing-after-few-secondshttps://stackoverflow.com/questions/40932639/pyqt-messagebox-automatically-closing-after-few-seconds
class TimerMessageBox(QtWidgets.QMessageBox):
    def __init__(self, title, text, timeout=2, parent=None):
        super(TimerMessageBox, self).__init__(parent)
        self.setWindowTitle(title)
        self.time_to_wait = timeout
        self.setText(text)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.change_content)
        self.timer.start()

    def change_content(self):
        self.time_to_wait -= 1
        if self.time_to_wait <= 0:
            self.close()

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()


# Class that represents radiobuttons where the user can change between two different
# image enhancement processes for their image
class GroupBox(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.selected_yes = False
        self.layout = QtWidgets.QGridLayout(self)
        self.groupbox = QtWidgets.QGroupBox("Does the DSS image have varying background?")
        self.layout.addWidget(self.groupbox)

        self.hbox = QtWidgets.QHBoxLayout()
        self.groupbox.setLayout(self.hbox)
        self.yes_radiobutton = QtWidgets.QRadioButton("Yes")
        self.no_radiobutton = QtWidgets.QRadioButton("No")

        self.yes_radiobutton.toggled.connect(self.yes_selected)
        self.no_radiobutton.toggled.connect(self.no_selected)

        self.no_radiobutton.toggle()

        self.hbox.addWidget(self.yes_radiobutton, alignment=QtCore.Qt.AlignTop)
        self.hbox.addWidget(self.no_radiobutton, alignment=QtCore.Qt.AlignTop)
        self.hbox.addStretch()
        self.layout.setColumnStretch(1, 1)
        self.layout.setRowStretch(1, 1)

    def yes_selected(self):
        self.selected_yes = True

    def no_selected(self):
        self.selected_yes = False


# Class that represents the application
class App(QWidget):
    def __init__(self):
        super().__init__()
        # Sets the style, title and shape of the application
        self.setStyleSheet("QLabel{font-size: 12pt;}")
        self.setWindowTitle("DSS Classifier")
        self.setGeometry(0, 0, 1200, 800)
        self.setAcceptDrops(True)

        # Creates a QGridLayout
        self.grid = QGridLayout()

        # Creates a label that should contain the name of the file uploaded
        self.file_name_label = QLabel()
        self.file_name_label.setAlignment(Qt.AlignCenter)
        self.file_name_label.setText("Drop image here")
        # Sets a border around the label
        self.file_name_label.setStyleSheet('''
                                    QLabel{
                                        border: 4px dashed #aaa
                                    }
                                ''')

        self.grid.addWidget(self.file_name_label, 0, 0, 1, 2)

        # Creates an instance of the PhotoViewer class
        self.photo_viewer = PhotoViewer(self)

        # Creates an instance of the LoadingLabel class
        self.loading_label = QLabel(self)
        self.movie = QMovie(self.loading_label)
        self.movie.setFileName('loading.gif')
        self.movie.jumpToFrame(0)
        self.loading_label.setMovie(self.movie)
        self.loading_label.hide()

        self.grid.addWidget(self.loading_label, 1, 0)

        self.group_box = GroupBox()
        self.grid.addWidget(self.group_box, 2, 0, 1, 2)
        self.group_box.hide()

        self.zoom_label = self.photo_viewer.zoom_label
        self.zoom_label.setAlignment(Qt.AlignRight)
        self.grid.addWidget(self.zoom_label, 1, 1)

        # Adds the photoViewer in the grid
        self.grid.addWidget(self.photo_viewer, 3, 0, 1, 2)

        # Creates a button for opening the file explorer to upload an image
        self.browse_button = QtWidgets.QPushButton(self)
        self.browse_button.setText("Open Images")
        self.browse_button.clicked.connect(self.explore)
        self.browse_button.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.browse_button, 4, 0)

        # Creates a button for removing the image
        self.remove_button = QtWidgets.QPushButton(self)
        self.remove_button.setText("Remove Image")
        self.remove_button.clicked.connect(self.remove_image)
        self.remove_button.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.remove_button, 4, 1)

        # Creates an empty label
        self.empty_label = QLabel()
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet('''
                                    QLabel{
                                        border: 4px dashed #aaa
                                    }
                                ''')

        self.uncrop_button = QtWidgets.QPushButton()
        self.uncrop_button.setText("Uncrop Image")
        self.uncrop_button.setFont(QFont('Arial', 12))
        self.uncrop_button.clicked.connect(self.uncrop_image)

        self.grid.addWidget(self.uncrop_button, 5, 1)

        self.grid.setRowStretch(0, 3)
        self.grid.setRowStretch(3, 18)
        self.grid.setRowStretch(4, 1)
        self.grid.setRowStretch(5, 1)

        # Creates a button for cropping the image
        self.crop_button = QtWidgets.QPushButton(self)
        self.crop_button.setText("Crop Image")
        self.crop_button.clicked.connect(self.rubber_band_on)
        self.crop_button.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.crop_button, 5, 0)

        # Creates a button for classifying the image
        self.classify_button = QtWidgets.QPushButton(self)
        self.classify_button.setText("Classify Image")
        self.classify_button.clicked.connect(self.button_classify)
        self.classify_button.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.classify_button, 6, 0)

        # Creates a button for saving letters in image
        self.text_button = QtWidgets.QPushButton(self)
        self.text_button.setText("Save Letters")
        self.text_button.clicked.connect(self.crop_letters)
        self.text_button.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.text_button, 6, 1)

        # Creates a button for saving the image
        self.save_button = QtWidgets.QPushButton(self)
        self.save_button.setText("Save Image")
        self.save_button.clicked.connect(self.save_image)
        self.save_button.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.save_button, 7, 0)

        # Creates a help button that opens a help menu for the user
        self.help_button = QtWidgets.QPushButton()
        self.help_button.setText("Help")
        self.help_button.setFont(QFont('Arial', 12))
        self.help_button.clicked.connect(self.help_box)
        self.grid.addWidget(self.help_button, 7, 1)

        self.setLayout(self.grid)

        # Creates shortcuts to the gui
        self.create_short_cuts()

        # Image path of the image that is currently displayed
        self.image_path = None

        # Allows for multithreading
        self.thread_pool = QThreadPool()
        self.worker = Worker(None)

        self.segmented_letters = []

        self.img = None

        self.classified = False

        self.results_from_classifier = None

    # Method that saves the letters that the segmentation detected when doing classification
    def crop_letters(self):
        if self.photo_viewer.empty is True:
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photo_viewer, "No Image Displayed", "There is no image displayed")
        elif not self.classified:
            # A message box will appear telling the user that the image has not yet been classified
            msg = QtWidgets.QMessageBox()
            msg.information(self.photo_viewer, "Not Classified", "The image has not yet been classified")
        else:
            if not self.photo_viewer.is_cropped:
                # Reading the image
                img = cv2.imread(self.image_path)
            else:
                img = cv2.imread("./classified_img.png")
            if len(img.shape) == 3:
                h_img, w_img, _ = img.shape
            else:
                h_img, w_img = img.shape
            # Removing the images that are in the letters folder if any
            files = glob.glob("./letters/*.png")
            for f in files:
                os.remove(f)
            i = 0
            # Saving the letters in the image to the letters folder.
            for letter in self.results_from_classifier:
                x = letter.x
                y = letter.y
                w = letter.w
                h = letter.h
                crop = img[(h_img-h):(h_img-y), x:w]
                name = "./letters/" + str(letter.label) + str(i) + ".png"
                cv2.imwrite(name, crop)
                i += 1
            # A message box will appear telling the user that there is no image displayed
            msg = TimerMessageBox("Saved", "The cropped letters have been saved in the 'letters' folder", parent=self.photo_viewer)
            msg.exec_()

    def add_photo_to_scene(self):
        im = Image.fromarray(self.img)
        im.save("./classified_img.png")

        self.photo_viewer.set_photo_with_rectangle(pixmap=QPixmap("./classified_img.png"), rectangle=False)

    def add_cropped_photo_to_scene(self):
        im = Image.fromarray(self.img)
        im.save("./classified_img.png")

        self.photo_viewer.set_photo(pixmap=QPixmap("./classified_img.png"))

    # Method that is run when the classify thread is done
    def thread_complete(self):
        # Enabling the buttons again
        self.classify_button.setDisabled(False)
        self.browse_button.setDisabled(False)
        self.remove_button.setDisabled(False)
        self.crop_button.setDisabled(False)
        self.uncrop_button.setDisabled(False)
        self.save_button.setDisabled(False)
        self.help_button.setDisabled(False)
        self.text_button.setDisabled(False)
        self.group_box.setDisabled(False)
        # Stops the loading gif
        self.movie.stop()
        self.loading_label.hide()
        if len(self.segmented_letters) == 0:
            # A message box will appear telling the user that there is no image displayed
            msg = TimerMessageBox("No Letters Detected", "No hebrew letters were detected", parent=self.photo_viewer)
            msg.exec_()
        else:
            # A message box will appear telling the user that there is no image displayed
            msg = TimerMessageBox("Classified", "The image has been classified", parent=self.photo_viewer)
            msg.exec_()

    # This is the method that runs when the classify button is pressed. It uses multithreading to
    # let the loading icon spin when the image is being classified.
    def button_classify(self):
        if self.photo_viewer.empty is True:
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photo_viewer, "No Image Displayed", "There is no image to classify")
        else:
            # Disabling the buttons
            self.classify_button.setDisabled(True)
            self.browse_button.setDisabled(True)
            self.remove_button.setDisabled(True)
            self.crop_button.setDisabled(True)
            self.uncrop_button.setDisabled(True)
            self.save_button.setDisabled(True)
            self.help_button.setDisabled(True)
            self.text_button.setDisabled(True)
            self.group_box.setDisabled(True)
            # Starts the animation of the loading gif
            self.loading_label.show()
            self.movie.start()

            # Starts the classify method that classifies the image
            self.worker = Worker(self.classify)
            self.worker.signals.finished.connect(self.thread_complete)
            self.worker.signals.add_photo.connect(self.add_photo_to_scene)
            self.worker.signals.add_cropped_photo.connect(self.add_cropped_photo_to_scene)

            self.thread_pool.start(self.worker)

    # Method that classifies an image.
    def classify(self):
        # Checks if there is an image to classify
        if self.photo_viewer.empty is True:
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photo_viewer, "No Image Displayed", "There is no image to classify")
        else:
            # Uses the machine learning model we have made and pytesseract to segment and classify
            # the letters
            segmenter = segToClass.Segmentor()
            # img = cv2.imread(self.image_path)

            # Gets the image from the pixmap
            qimg = self.photo_viewer.photo.pixmap().toImage()

            # Converts it to an numpy.ndarray
            img_array = qimage2ndarray.rgb_view(qimg)

            # For some reason it has to be copied as uint8 to avoid errors
            self.img = img_array.astype(np.uint8).copy()

            # Gets the height of the image
            h_img = self.img.shape[0]

            self.segmented_letters.clear()
            # Checking if the "yes" radiobutton is toggled on or off
            if self.group_box.selected_yes:
                self.segmented_letters = segmenter.segment_varied_background(self.img)
            else:
                self.segmented_letters = segmenter.segment_clear_background(self.img)

            classifier = segToClass.Classifier("./default_2.model")
            self.results_from_classifier = classifier.Classify(self.segmented_letters)

            # Draws the squares around the letters
            i = 0
            for letter in self.results_from_classifier:
                letter_height = letter.h - letter.y
                width = letter.w
                height = letter.h
                x = letter.x
                y = letter.y
                cv2.rectangle(self.img, (x, h_img - y), (width, h_img - height), (0, 0, 0), 1)

                text = str(letter.label) + " " + str(letter.confidence) + "%"
                # Alternates between writing the label on top and under the boxes
                if i % 2 == 0:
                    cv2.putText(self.img, text=text, org=(x, (h_img - y) + 10),
                                fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=0.5, color=(0, 0, 0), thickness=1)
                else:
                    cv2.putText(self.img, text=text, org=(x, ((h_img - y) - letter_height) - 4),
                                fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=0.5, color=(0, 0, 0), thickness=1)

                i += 1
            if self.photo_viewer.rubber_band_item_geometry is not None:
                self.worker.signals.add_cropped_photo.emit()
            else:
                self.worker.signals.add_photo.emit()

            self.classified = True

    # Method that saves the image to file
    def save_image(self):
        if self.photo_viewer.empty is True:
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photo_viewer, "No Image To Save", "There is no image to save")
        else:
            # Selecting file path
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "",
                                                      "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")

            # If file path is blank return back
            if file_path == "":
                return

            # Saving image at desired path
            pixmap = self.photo_viewer.photo.pixmap()
            image = pixmap.toImage()
            image.save(file_path)

    # Methos that makes the user able to uncrop an image
    def uncrop_image(self):
        # Checks if there actually is an image to crop or not
        if self.photo_viewer.empty is True:
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photo_viewer, "No Image Displayed", "There is no image displayed")
        elif not self.photo_viewer.is_cropped:
            # A message box will appear telling the user that the image is not cropped
            msg = QtWidgets.QMessageBox()
            msg.information(self.photo_viewer, "No Crop", "The image has not been cropped yet")
        else:
            self.photo_viewer.photo.setPos(0, 0)
            self.photo_viewer.set_photo_with_rectangle(pixmap=QPixmap(self.image_path), rectangle=False)
            self.photo_viewer.is_cropped = False
            self.photo_viewer.rubber_band_item_geometry = None
            self.classified = False

    # Method that displays a help box to the user
    def help_box(self):
        # A message box will appear telling the user that there is no image displayed
        msg = QtWidgets.QMessageBox()
        msg.information(self, "Help", "Use rgb or grayscale dead sea scroll images.\n"
                                      "When you save the letters on the scroll image it will be "
                                      "saved in a folder called 'letters' in the application folder.\n"
                                      "Classifying big scroll images might take a couple of minutes.\n"
                                      "If the scroll image has varying background, meaning stains or darker areas "
                                      "in the background, please select the 'Yes' radio button. If the image has a clean, "
                                      "white background, please select the 'No' radio button.\n"
                                      "Shortcuts: \n-Exit app: Ctrl+Q\n-Open images: Ctrl+O\n-Remove image: "
                                      "Ctrl+R\n-Crop image: Ctrl+W\n-Open help menu: Ctrl+H\n-Uncrop image: "
                                      "Ctrl+U\n-Save image: Ctrl+S\n-Classify image: Ctrl+C\n-Crop letters: Ctrl+L")

    # Method that creates shortcuts for the user
    def create_short_cuts(self):
        exit_short = QShortcut(QKeySequence("Ctrl+Q"), self)
        exit_short.activated.connect(self.close)

        browse_short = QShortcut(QKeySequence("Ctrl+O"), self)
        browse_short.activated.connect(self.explore)

        remove_short = QShortcut(QKeySequence("Ctrl+R"), self)
        remove_short.activated.connect(self.remove_image)

        crop_short = QShortcut(QKeySequence("Ctrl+W"), self)
        crop_short.activated.connect(self.rubber_band_on)

        help_short = QShortcut(QKeySequence("Ctrl+H"), self)
        help_short.activated.connect(self.help_box)

        uncrop_short = QShortcut(QKeySequence("Ctrl+U"), self)
        uncrop_short.activated.connect(self.uncrop_image)

        save_short = QShortcut(QKeySequence("Ctrl+S"), self)
        save_short.activated.connect(self.save_image)

        classify_short = QShortcut(QKeySequence("Ctrl+C"), self)
        classify_short.activated.connect(self.button_classify)

        crop_letters_short = QShortcut(QKeySequence("Ctrl+L"), self)
        crop_letters_short.activated.connect(self.crop_letters)

    # Method that sets rubberBool to true, so that the rubberBand is shown
    def rubber_band_on(self):
        # Checks if there actually is an image to crop or not
        if self.photo_viewer.empty is True:
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photo_viewer, "No Image Displayed", "There is no image displayed")
        else:
            self.photo_viewer.rubber_bool = True

    # Method to open file explorer and choose an image
    def explore(self):
        if self.photo_viewer.empty is True:
            # Gets the path of the Pictures folder
            path = Path.home()
            path_str = str(path) + os.path.sep + "Pictures"

            # Checks if the computer has a directory called %HOMEPATH%\Pictures
            if os.path.exists(path_str):
                # Opens the file explorer in
                file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', path_str,
                                                                 'JPG files (*.jpg);;PNG files (*.png)')
            # If the computer doesn't have a directory like that it will open the file explorer in the %HOMEPATH%
            else:
                file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', str(path),
                                                                 'JPG files (*.jpg);;PNG files (*.png)')

            # Check if the user has specified a path or just closed the file explorer
            if file_name[0] != "":
                self.image_path = file_name[0]
                # Displays the image in the photoViewer label
                self.photo_viewer.set_photo_with_rectangle(pixmap=QPixmap(file_name[0]))
                # Setting the position of the image to the upper right corner of the pixmap
                self.photo_viewer.photo.setPos(0, 0)
                # Fetches the filename from the path and sets it as the header
                path_list = str(file_name[0]).split("/")
                self.file_name_label.setText("Filename: " + path_list[-1])

                # Sets the zoomlevel of the image
                self.photo_viewer.zoom_label.setText("Zoom level: " + str(int(self.photo_viewer.zoom_level)) + "%")

                # Displays the group box
                self.group_box.show()
        else:
            # A message box will appear telling the user that there is already an image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photo_viewer, "Image Displayed", "There is already an image displayed.\nRemove it to "
                                                                 "open another one.")

    # Method that removes the Image from the drop zone
    def remove_image(self):
        # Checks if there actually is an image to remove or not
        if self.photo_viewer.empty is True:
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self, "No Image Displayed", "There is no image displayed")
        else:
            # Empties the fileNameLabel
            self.file_name_label.setText("Drop image here")
            # Removes the image
            self.photo_viewer.remove_item()
            self.photo_viewer.empty = True
            # Sets ruberBool to false so that you cannot crop when no image is displayed
            self.photo_viewer.rubber_bool = False
            # Setting the position of the image to the upper right corner of the pixmap
            self.photo_viewer.photo.setPos(0, 0)

            self.zoom_label.setText("")
            # Hides the group box
            self.group_box.hide()

            self.classified = False

    # Checks if the file that enters the drop zone is an image
    def dragEnterEvent(self, event):
        if event.mimeData().hasImage:
            event.accept()
        else:
            event.ignore()

    # Checks if the file that is dragged over the drop zone is an image
    def dragMoveEvent(self, event):
        if event.mimeData().hasImage:
            event.accept()
        else:
            event.ignore()

    # Method that is run when you drop an image in the drop zone
    def dropEvent(self, event):
        if self.photo_viewer.empty is True:
            # Gets the file extension of the chosen file
            file_path = event.mimeData().urls()[0].toLocalFile()
            _, extension = os.path.splitext(file_path)
            # If the file is not of type png or jpg an error message will apear
            if extension == ".png" or extension == ".PNG" or extension == ".JPG" or extension == ".jpg" or \
                    extension == ".JPEG" or extension == ".jpeg":
                if event.mimeData().hasImage:
                    event.setDropAction(Qt.CopyAction)
                    file_path = event.mimeData().urls()[0].toLocalFile()
                    self.image_path = file_path
                    # Displays the image in the photoViewer label
                    self.photo_viewer.set_photo_with_rectangle(pixmap=QPixmap(file_path))
                    # Setting the position of the image to the upper right corner of the pixmap
                    self.photo_viewer.photo.setPos(0, 0)
                    # Fetches the filename from the path and sets it as the header
                    path_list = str(file_path).split("/")
                    self.file_name_label.setText("Filename: " + path_list[-1])

                    # Sets the zoomlevel of the image
                    self.photo_viewer.zoom_label.setText("Zoom level: " + str(int(self.photo_viewer.zoom_level)) + "%")

                    # Displays the group box
                    self.group_box.show()
                    event.accept()
                else:
                    event.ignore()
            else:
                event.ignore()
                # A message box will appear telling the user that the file type must be jpg or png
                msg = QtWidgets.QMessageBox()
                msg.information(self, "Wrong File Type", "The file must be of type jpg or png")
        else:
            # A message box will appear telling the user that there is already an image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photo_viewer, "Image Displayed", "There is already an image displayed.\nRemove it to "
                                                                 "open another one.")


# Starts the application
app = QApplication(sys.argv)
demo = App()
demo.show()
sys.exit(app.exec_())
