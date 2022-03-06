import sys, os
from pathlib import Path
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QGridLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap


class DropZone(QLabel):
    def __init__(self):
        super().__init__()
        # Sets the alignment of the text to center
        self.setAlignment(Qt.AlignCenter)
        self.setText('\n\n Drop DSS Image Here \n\n')

        # Sets a border around the label
        self.setStyleSheet('''
            QLabel{
                border: 4px dashed #aaa
            }
        ''')

    # Method that removes the Image from the drop zone
    def removeImage(self):
        # Checks if there actually is an image to remove or not
        if super().pixmap() is None:
            # Takes away the borders so that the message box wont contain weird borders
            self.setStyleSheet('''
                        QLabel{
                            border: None
                        }
                    ''')
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self, "No Image Displayed", "There is no image displayed")
            # Puts the borders back again
            self.setStyleSheet('''
                        QLabel{
                            border: 4px dashed #aaa
                        }
                    ''')
        else:
            self.setAlignment(Qt.AlignCenter)
            self.setText('\n\n Drop DSS Image Here \n\n')
            self.setStyleSheet('''
                        QLabel{
                            border: 4px dashed #aaa
                        }
                    ''')

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
        super().setPixmap(QPixmap(fname[0]))

    def setPixmap(self, image):
        super().setPixmap(image)


class AppDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DSS classifier")
        self.setGeometry(0, 0, 800, 800)
        self.setAcceptDrops(True)

        # Creates a QVBoxLayout
        self.grid = QGridLayout()

        # Creates an instance of the DropZone class
        self.photoViewer = DropZone()
        self.grid.addWidget(self.photoViewer, 0, 0, 1, 2)

        # Creates a button for opening the file explorer to upload an image
        self.browseButton = QtWidgets.QPushButton(self)
        self.browseButton.setText("Browse Images")
        self.browseButton.clicked.connect(self.photoViewer.explore)

        # Puts the button in the grid
        self.grid.addWidget(self.browseButton, 1, 0)

        # Creates a button for removing the image
        self.removeButton = QtWidgets.QPushButton(self)
        self.removeButton.setText("Remove Image")
        self.removeButton.clicked.connect(self.photoViewer.removeImage)

        # Puts the button in the grid
        self.grid.addWidget(self.removeButton, 1, 1)

        self.label = QLabel("---------------------------------------------------------"
                            "---------------------------------------------------------"
                            "---------------------------------------------------------")
        self.label.setAlignment(Qt.AlignCenter)
        self.grid.addWidget(self.label, 2, 0, 1, 2)

        self.grid.setRowStretch(0, 18)
        self.grid.setRowStretch(1, 1)
        self.grid.setRowStretch(2, 1)
        self.grid.setRowStretch(3, 1)

        # Creates a button for cropping the image
        self.cropButton = QtWidgets.QPushButton(self)
        self.cropButton.setText("Crop Image")
        # self.removeButton.clicked.connect(<some_function>)

        # Puts the button in the grid
        self.grid.addWidget(self.cropButton, 3, 0)

        # Creates a button for classifying the image
        self.classifyButton = QtWidgets.QPushButton(self)
        self.classifyButton.setText("Classify Image")
        # self.removeButton.clicked.connect(<some_function>)

        # Puts the button in the grid
        self.grid.addWidget(self.classifyButton, 3, 1)

        self.setLayout(self.grid)

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
                self.set_image(file_path)
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()
            # A message box will appear telling the user that the file type must be jpg or png
            msg = QtWidgets.QMessageBox()
            msg.information(self, "Wrong File Type", "The file must be of type jpg or png")

    # Methods to set image in the photoViewer
    def set_image(self, file_path):
        self.photoViewer.setPixmap(QPixmap(file_path))


app = QApplication(sys.argv)
demo = AppDemo()
demo.show()
sys.exit(app.exec_())