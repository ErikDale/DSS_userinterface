import sys, os
from pathlib import Path
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap


class ImageLabel(QLabel):
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

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setText('\n\n Drop DSS Image Here \n\n')
        self.setStyleSheet('''
            QLabel{
                border: 4px dashed #aaa
            }
        ''')
        self.btn = QtWidgets.QPushButton(self)
        self.btn.setText("Browse Images")
        self.btn.clicked.connect(self.explore)
        self.btn.setGeometry(125, 200, 150, 25)

    def setPixmap(self, image):
        super().setPixmap(image)


class AppDemo(QWidget):
    def __init__(self):
        super().__init__()
        # self.resize(400, 400)
        self.setWindowTitle("DSS classifier")
        self.setGeometry(400, 400, 400, 400)
        self.setAcceptDrops(True)

        self.mainLayout = QVBoxLayout()

        self.photoViewer = ImageLabel()
        self.mainLayout.addWidget(self.photoViewer)

        self.setLayout(self.mainLayout)

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
        if extension == ".png" or extension == ".PNG" or extension == ".JPG" or extension == ".jpg" or extension == ".JPEG" or extension == ".jpeg":
                if event.mimeData().hasImage:
                    event.setDropAction(Qt.CopyAction)
                    file_path = event.mimeData().urls()[0].toLocalFile()
                    self.set_image(file_path)
                    event.accept()
                else:
                    event.ignore()
        else:
            event.ignore()
            msg = QtWidgets.QMessageBox()
            msg.information(self, "Wrong File Type", "The file must be of type jpg or png")

    # Methods to set image in the photoViewer
    def set_image(self, file_path):
        self.photoViewer.setPixmap(QPixmap(file_path))


app = QApplication(sys.argv)
demo = AppDemo()
demo.show()
sys.exit(app.exec_())