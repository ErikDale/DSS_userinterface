import sys, os
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QGridLayout, QRubberBand, QSizePolicy, QScrollArea, \
    QMainWindow, QVBoxLayout, QAction, QShortcut
from PyQt5.QtCore import Qt, QRect, QSize, QPoint
from PyQt5.QtGui import QPixmap, QImage, QKeySequence, QFont
import cv2


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("QLabel{font-size: 12pt;}")
        self.setWindowTitle("DSS classifier")
        self.setGeometry(0, 0, 1200, 800)
        self.setAcceptDrops(True)

        # Creates a QVBoxLayout
        self.grid = QGridLayout()

        # Creates a help button that opens a help menu for the user
        self.helpButton = QtWidgets.QPushButton()
        self.helpButton.setText("Help")
        self.helpButton.setFont(QFont('Arial', 12))
        self.helpButton.clicked.connect(self.helpBox)
        self.grid.addWidget(self.helpButton, 0, 0, 1, 2)

        # Creates a label telling the user how to zoom in and out
        self.helpLabel = QLabel()
        self.helpLabel.setAlignment(Qt.AlignCenter)
        self.helpLabel.setText("To zoom in press 'ctrl++', to zoom out press 'ctrl+-'")
        self.grid.addWidget(self.helpLabel, 1, 0, 1, 2)

        # Creates a label that should contain the name of the file uploaded
        self.fileNameLabel = QLabel()
        self.fileNameLabel.setAlignment(Qt.AlignCenter)
        self.grid.addWidget(self.fileNameLabel, 2, 0, 1, 2)

        # Creates a label that will act as the photoviewer
        self.photoViewer = QLabel()
        self.photoViewer.scaleFactor = 1.0
        # Sets the alignment of the text to center
        self.photoViewer.setAlignment(Qt.AlignCenter)
        self.photoViewer.setText('\n\n Drop DSS image here \n\n')

        # Sets a border around the label
        self.photoViewer.setStyleSheet('''
                    QLabel{
                        border: 4px dashed #aaa
                    }
                ''')
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.photoViewer)
        self.scrollArea.setAlignment(Qt.AlignCenter)
        self.scrollArea.setWidgetResizable(True)
        # self.scrollArea.setVisible(True)
        self.grid.addWidget(self.scrollArea, 3, 0, 1, 2)

        # Creates a button for opening the file explorer to upload an image
        self.browseButton = QtWidgets.QPushButton(self)
        self.browseButton.setText("Browse Images")
        self.browseButton.clicked.connect(self.explore)
        self.browseButton.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.browseButton, 4, 0)

        # Creates a button for removing the image
        self.removeButton = QtWidgets.QPushButton(self)
        self.removeButton.setText("Remove Image")
        self.removeButton.clicked.connect(self.removeImage)
        self.removeButton.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.removeButton, 4, 1)

        self.emptyLabel = QLabel("---------------------------------------------------------"
                                 "---------------------------------------------------------"
                                 "---------------------------------------------------------")
        self.emptyLabel.setAlignment(Qt.AlignCenter)
        self.grid.addWidget(self.emptyLabel, 5, 0, 1, 2)

        self.grid.setRowStretch(3, 18)
        self.grid.setRowStretch(4, 1)
        self.grid.setRowStretch(5, 1)
        self.grid.setRowStretch(6, 1)

        # Creates a button for cropping the image
        self.cropButton = QtWidgets.QPushButton(self)
        self.cropButton.setText("Crop Image")
        self.cropButton.clicked.connect(self.rubberBandOn)
        self.cropButton.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.cropButton, 6, 0)

        # Creates a button for classifying the image
        self.classifyButton = QtWidgets.QPushButton(self)
        self.classifyButton.setText("Classify Image")
        # self.removeButton.clicked.connect(<some_function>)
        self.classifyButton.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.classifyButton, 6, 1)

        self.setLayout(self.grid)
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self.photoViewer)
        self.origin = None
        self.rubberBool = False

        self.createShortCuts()

    # Method that displays a help box to the user
    def helpBox(self):
        # A message box will appear telling the user that there is no image displayed
        msg = QtWidgets.QMessageBox()
        msg.information(self, "Help", "Shortcuts: \n-Exit app: Ctrl+Q\n-Zoom in: Ctrl++\n-Zoom out: "
                                      "Ctrl+-")

    # Method that creates shortcuts for the user
    def createShortCuts(self):
        exitShort = QShortcut(QKeySequence("Ctrl+Q"), self)
        exitShort.activated.connect(self.close)

        zoomInShort = QShortcut(QKeySequence("Ctrl++"), self)
        zoomInShort.activated.connect(self.zoomIn)

        zoomOutShort = QShortcut(QKeySequence("Ctrl+-"), self)
        zoomOutShort.activated.connect(self.zoomOut)

    # Method that sets rubberBool to true, so that the rubberBand is shown
    def rubberBandOn(self):
        # Checks if there actually is an image to crop or not
        if QLabel.pixmap(self.photoViewer) is None:
            # Takes away the borders so that the message box wont contain weird borders
            self.photoViewer.setStyleSheet('''
                                QLabel{
                                    border: None
                                }
                            ''')
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photoViewer, "No Image Displayed", "There is no image displayed")
            # Puts the borders back again
            self.photoViewer.setStyleSheet('''
                                QLabel{
                                    border: 4px dashed #aaa
                                }
                            ''')
        else:
            self.rubberBool = True

    def mousePressEvent(self, event):
        self.origin = event.pos()
        if not self.rubberBand:
            self.rubberBand = QRubberBand(QRubberBand.Rectangle, self.photoViewer)
        if self.rubberBool:
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()

    def mouseMoveEvent(self, event):
        if self.rubberBool:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if self.rubberBool:
            crop = self.photoViewer.pixmap().copy(self.rubberBand.geometry())
            self.photoViewer.setPixmap(crop)
            self.rubberBand.hide()

    # Method to open file explorer and choose an image
    def explore(self):
        # Gets the path of the Pictures folder
        path = Path.home()
        pathStr = str(path) + os.path.sep + "Pictures"

        # Checks if the computer has a directory called %HOMEPATH%\Pictures
        if os.path.exists(pathStr):
            # Opens the file explorer in
            fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', pathStr,
                                                          'JPG files (*.jpg);;PNG files (*.png)')
        # If the computer doesn't have a file like that it will open the file explorer in the %HOMEPATH%
        else:
            fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', str(path),
                                                          'JPG files (*.jpg);;PNG files (*.png)')

        # Check if the user has specified a path or just closed the file explorer
        if fname[0] != "":
            # Displays the image in the photoViewer label
            self.set_image(fname[0])

            # Fetches the filename from the path and sets it as the header
            pathList = str(fname[0]).split("/")
            self.fileNameLabel.setText("Filename: " + pathList[-1])

    # Method that removes the Image from the drop zone
    def removeImage(self):
        # Checks if there actually is an image to remove or not
        if QLabel.pixmap(self.photoViewer) is None:
            # Takes away the borders so that the message box wont contain weird borders
            self.photoViewer.setStyleSheet('''
                        QLabel{
                            border: None
                        }
                    ''')
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photoViewer, "No Image Displayed", "There is no image displayed")
            # Puts the borders back again
            self.photoViewer.setStyleSheet('''
                        QLabel{
                            border: 4px dashed #aaa
                        }
                    ''')
        else:
            self.fileNameLabel.setText("")
            self.photoViewer.setAlignment(Qt.AlignCenter)
            self.photoViewer.setText('\n\n Drop DSS Image Here \n\n')
            self.photoViewer.setStyleSheet('''
                        QLabel{
                            border: 4px dashed #aaa
                        }
                    ''')

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
        # Gets the file extension of the chosen file
        file_path = event.mimeData().urls()[0].toLocalFile()
        _, extension = os.path.splitext(file_path)
        # If the file is not of type png or jpg an error message will apear
        if extension == ".png" or extension == ".PNG" or extension == ".JPG" or extension == ".jpg" or \
                extension == ".JPEG" or extension == ".jpeg":
            if event.mimeData().hasImage:
                event.setDropAction(Qt.CopyAction)
                file_path = event.mimeData().urls()[0].toLocalFile()

                # Displays the image in the photoViewer label
                self.set_image(file_path)

                # Fetches the filename from the path and sets it as the header
                pathList = str(file_path).split("/")
                self.fileNameLabel.setText("Filename: " + pathList[-1])
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()
            # A message box will appear telling the user that the file type must be jpg or png
            msg = QtWidgets.QMessageBox()
            msg.information(self, "Wrong File Type", "The file must be of type jpg or png")

    def scaleImage(self, factor):
        self.photoViewer.scaleFactor = factor
        print(self.photoViewer.scaleFactor)
        width = self.photoViewer.pixmap().width()
        height = self.photoViewer.pixmap().height()
        pixmap = self.photoViewer.pixmap().scaled(width * self.photoViewer.scaleFactor,
                                                  height * self.photoViewer.scaleFactor, Qt.KeepAspectRatio)
        # self.photoViewer.resize(self.photoViewer.scaleFactor * self.photoViewer.pixmap().size())
        self.photoViewer.setPixmap(pixmap)

        self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
        self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value()
                               + ((factor - 1) * scrollBar.pageStep() / 2)))

    def zoomIn(self):
        self.scaleImage(1.25)

    def zoomOut(self):
        self.scaleImage(0.8)

    def normalSize(self):
        self.photoViewer.adjustSize()
        self.photoViewer.scaleFactor = 1.0

    # Methods to set image in the photoViewer
    def set_image(self, img_path):
        # pixmap = QPixmap(img_path)
        # pixmap = pixmap.scaled(1150, 600, Qt.KeepAspectRatio)
        self.photoViewer.scaleFactor = 1.0
        self.photoViewer.setPixmap(QPixmap(img_path))

    # Methods to set image in the photoViewer
    def set_image2(self, img):
        # pixmap = QPixmap(img_path)
        # pixmap = pixmap.scaled(1150, 600, Qt.KeepAspectRatio)
        self.photoViewer.setPixmap(QPixmap.fromImage(img))

    # Method that resizes an image, but keeps the aspect ratio
    def image_resize(self, image, width=None, height=None, inter=cv2.INTER_AREA):
        # initialize the dimensions of the image to be resized and
        # grab the image size
        dim = None
        (h, w) = image.shape[:2]

        # if both the width and height are None, then return the
        # original image
        if width is None and height is None:
            return image

        # check to see if the width is None
        if width is None:
            # calculate the ratio of the height and construct the
            # dimensions
            r = height / float(h)
            dim = (int(w * r), height)

        # otherwise, the height is None
        else:
            # calculate the ratio of the width and construct the
            # dimensions
            r = width / float(w)
            dim = (width, int(h * r))

        # resize the image
        resized = cv2.resize(image, dim, interpolation=inter)

        # return the resized image
        return resized


app = QApplication(sys.argv)
demo = App()
demo.show()
sys.exit(app.exec_())
