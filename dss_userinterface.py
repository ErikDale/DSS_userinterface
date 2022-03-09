import sys, os
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QGridLayout, QRubberBand, QSizePolicy, QScrollArea, \
    QMainWindow, QVBoxLayout, QAction, QShortcut, QGraphicsView, QFileDialog
from PyQt5.QtCore import Qt, QRect, QSize, QPoint, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QKeySequence, QFont, QPainter, QBrush, QPalette


# Gotten alot from: https://stackoverflow.com/questions/35508711/how-to-enable-pan-and-zoom-in-a-qgraphicsview
# Class that represents the photoviewer object
class PhotoViewer(QtWidgets.QGraphicsView):
    photoClicked = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        # The zoom level
        self.zoom = 0
        # Boolean to check is image is displayed or not
        self.empty = True
        self.scene = QtWidgets.QGraphicsScene(self)
        self.photo = QtWidgets.QGraphicsPixmapItem()
        self.scene.addItem(self.photo)
        self.setScene(self.scene)

        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("gray")))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        # Creates the rubberband
        self.rubberBandItem = QtWidgets.QRubberBand(
            QtWidgets.QRubberBand.Rectangle
        )
        self.rubberBandItemGeometry = None
        item = self.scene.addWidget(self.rubberBandItem)
        item.setZValue(-1)
        self.draggable = False
        self.rubberBandItem.hide()
        self.origin = QtCore.QPoint()
        self.rubberBool = False

        self.rectangle = None

        self.isCropped = False

    # Method for removing image from pixmap
    def removeItem(self):
        self.scene.removeItem(self.rectangle)
        pixmap = QPixmap()
        self.photo.setPixmap(pixmap)

    # Method to check if pixmap has image or not
    def hasPhoto(self):
        return not self.empty

    # Method to set a photo in the pixmap
    def setPhotoWithRectangle(self, rectangle=True, pixmap=None):
        if rectangle:
            self.zoom = 0
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
            self.zoom = 0
            if pixmap and not pixmap.isNull():
                self.empty = False
                self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
                self.photo.setPixmap(pixmap)
            else:
                self.empty = True
                self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
                self.photo.setPixmap(QtGui.QPixmap())

    # Method to set a photo in the pixmap
    def setPhoto(self, pixmap=None):
        self.zoom = 0
        if pixmap and not pixmap.isNull():
            self.empty = False
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.photo.setPixmap(pixmap)
            # Setting the image at the exact location it was cropped, to keep its coordinates
            self.photo.setPos(self.rubberBandItemGeometry.x(), self.rubberBandItemGeometry.y())
        else:
            self.empty = True
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self.photo.setPixmap(QtGui.QPixmap())

    # Method that handles the zooming functionality
    def wheelEvent(self, event):
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                factor = 1.20
                self.zoom += 1
            else:
                factor = 0.8
                self.zoom -= 1
            if self.zoom > -8:
                self.scale(factor, factor)
            else:
                self.zoom = 0

    # Methods that toggles on and off the different drag modes
    def toggleDragMode(self):
        if self.dragMode() == QtWidgets.QGraphicsView.ScrollHandDrag:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        elif not self.photo.pixmap().isNull():
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    # Method that handles what happens when the mouse is pressed
    def mousePressEvent(self, event):
        if self.rubberBool:
            self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
            self.origin = self.mapToScene(event.pos()).toPoint()
            self.rubberBandItem.setGeometry(
                QtCore.QRect(self.origin, QtCore.QSize())
            )
            self.rubberBandItem.show()
            self.draggable = True
            super(PhotoViewer, self).mousePressEvent(event)
        else:
            if self.photo.isUnderMouse():
                self.photoClicked.emit(self.mapToScene(event.pos()).toPoint())
            super(PhotoViewer, self).mousePressEvent(event)

    # Method that takes care of what happens when the mouse is moved
    def mouseMoveEvent(self, event):
        if self.rubberBool:
            if self.draggable:
                end_pos = self.mapToScene(event.pos()).toPoint()
                self.rubberBandItem.setGeometry(
                    QtCore.QRect(self.origin, end_pos).normalized()
                )
                self.rubberBandItem.show()

        elif not self.photo.pixmap().isNull() and not self.rubberBool:
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        super(PhotoViewer, self).mouseMoveEvent(event)

    # Method that happens when the left-click is released
    def mouseReleaseEvent(self, event):
        if self.rubberBool:
            end_pos = self.mapToScene(event.pos()).toPoint()
            self.rubberBandItem.setGeometry(
                QtCore.QRect(self.origin, end_pos).normalized()
            )
            self.draggable = False
            # Getting the cropped area and storing it in the pixmap
            self.rubberBandItemGeometry = self.rubberBandItem.geometry()
            crop = self.photo.pixmap().copy(self.rubberBandItemGeometry)
            self.setPhoto(crop)
            self.rubberBandItem.hide()
            self.rubberBool = False
            self.isCropped = True
        elif not self.photo.pixmap().isNull() and not self.rubberBool:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        super(PhotoViewer, self).mouseMoveEvent(event)


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
        self.fileNameLabel = QLabel()
        self.fileNameLabel.setAlignment(Qt.AlignCenter)
        self.fileNameLabel.setText("Drop image here")
        # Sets a border around the label
        self.fileNameLabel.setStyleSheet('''
                                    QLabel{
                                        border: 4px dashed #aaa
                                    }
                                ''')

        self.grid.addWidget(self.fileNameLabel, 0, 0, 1, 2)

        # Creates an instance of the PhotoViewer class
        self.photoViewer = PhotoViewer(self)

        # Adds the photoViewer in the grid
        self.grid.addWidget(self.photoViewer, 1, 0, 1, 2)

        # Creates a button for opening the file explorer to upload an image
        self.browseButton = QtWidgets.QPushButton(self)
        self.browseButton.setText("Open Images")
        self.browseButton.clicked.connect(self.explore)
        self.browseButton.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.browseButton, 2, 0)

        # Creates a button for removing the image
        self.removeButton = QtWidgets.QPushButton(self)
        self.removeButton.setText("Remove Image")
        self.removeButton.clicked.connect(self.removeImage)
        self.removeButton.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.removeButton, 2, 1)

        # Creates an empty label
        self.emptyLabel = QLabel()
        self.emptyLabel.setAlignment(Qt.AlignCenter)
        self.emptyLabel.setStyleSheet('''
                                    QLabel{
                                        border: 4px dashed #aaa
                                    }
                                ''')

        self.uncropButton = QtWidgets.QPushButton()
        self.uncropButton.setText("Uncrop Image")
        self.uncropButton.setFont(QFont('Arial', 12))
        self.uncropButton.clicked.connect(self.uncropImage)

        self.grid.addWidget(self.uncropButton, 3, 1)

        self.grid.setRowStretch(0, 3)
        self.grid.setRowStretch(1, 18)
        self.grid.setRowStretch(2, 1)
        self.grid.setRowStretch(3, 1)

        # Creates a button for cropping the image
        self.cropButton = QtWidgets.QPushButton(self)
        self.cropButton.setText("Crop Image")
        self.cropButton.clicked.connect(self.rubberBandOn)
        self.cropButton.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.cropButton, 3, 0)

        # Creates a button for classifying the image
        self.classifyButton = QtWidgets.QPushButton(self)
        self.classifyButton.setText("Classify Image")
        # self.classifyButton.clicked.connect(<some_function>)
        self.classifyButton.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.classifyButton, 4, 0)

        # Creates a button for saving the image
        self.saveButton = QtWidgets.QPushButton(self)
        self.saveButton.setText("Save Image")
        self.saveButton.clicked.connect(self.saveImage)
        self.saveButton.setFont(QFont('Arial', 12))

        # Puts the button in the grid
        self.grid.addWidget(self.saveButton, 4, 1)

        # Creates a help button that opens a help menu for the user
        self.helpButton = QtWidgets.QPushButton()
        self.helpButton.setText("Help")
        self.helpButton.setFont(QFont('Arial', 12))
        self.helpButton.clicked.connect(self.helpBox)
        self.grid.addWidget(self.helpButton, 5, 0, 1, 2)

        self.setLayout(self.grid)

        self.createShortCuts()

        self.imagePath = None

    def saveImage(self):
        if self.photoViewer.empty is True:
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photoViewer, "No Image To Save", "There is no image to save")
        else:
            # Selecting file path
            filePath, _ = QFileDialog.getSaveFileName(self, "Save Image", "",
                                                      "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")

            # If file path is blank return back
            if filePath == "":
                return

            # Saving image at desired path
            pixmap = self.photoViewer.photo.pixmap()
            image = pixmap.toImage()
            image.save(filePath)

    # Methos that makes the user able to uncrop an image
    def uncropImage(self):
        # Checks if there actually is an image to crop or not
        if self.photoViewer.empty is True:
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photoViewer, "No Image Displayed", "There is no image displayed")
        elif not self.photoViewer.isCropped:
            # A message box will appear telling the user that the image is not cropped
            msg = QtWidgets.QMessageBox()
            msg.information(self.photoViewer, "No Crop", "The image has not been cropped yet")
        else:
            self.photoViewer.photo.setPos(0, 0)
            self.photoViewer.setPhotoWithRectangle(pixmap=QPixmap(self.imagePath), rectangle=False)
            self.photoViewer.isCropped = False

    # Method that displays a help box to the user
    def helpBox(self):
        # A message box will appear telling the user that there is no image displayed
        msg = QtWidgets.QMessageBox()
        msg.information(self, "Help", "Shortcuts: \n-Exit app: Ctrl+Q\n-Open images: Ctrl+O\n-Remove image: "
                                      "Ctrl+R\n-Crop image: Ctrl+W\n-Open help menu: Ctrl+H\n-Uncrop image: "
                                      "Ctrl+U\n-Save image: Ctrl+S") 

    # Method that creates shortcuts for the user
    def createShortCuts(self):
        exitShort = QShortcut(QKeySequence("Ctrl+Q"), self)
        exitShort.activated.connect(self.close)

        browseShort = QShortcut(QKeySequence("Ctrl+O"), self)
        browseShort.activated.connect(self.explore)

        removeShort = QShortcut(QKeySequence("Ctrl+R"), self)
        removeShort.activated.connect(self.removeImage)

        cropShort = QShortcut(QKeySequence("Ctrl+W"), self)
        cropShort.activated.connect(self.rubberBandOn)

        helpShort = QShortcut(QKeySequence("Ctrl+H"), self)
        helpShort.activated.connect(self.helpBox)

        uncropShort = QShortcut(QKeySequence("Ctrl+U"), self)
        uncropShort.activated.connect(self.uncropImage)

        saveShort = QShortcut(QKeySequence("Ctrl+S"), self)
        saveShort.activated.connect(self.saveImage)

    # Method that sets rubberBool to true, so that the rubberBand is shown
    def rubberBandOn(self):
        # Checks if there actually is an image to crop or not
        if self.photoViewer.empty is True:
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self.photoViewer, "No Image Displayed", "There is no image displayed")
        else:
            self.photoViewer.rubberBool = True

    # Method to open file explorer and choose an image
    def explore(self):
        # Gets the path of the Pictures folder
        path = Path.home()
        pathStr = str(path) + os.path.sep + "Pictures"

        # Checks if the computer has a directory called %HOMEPATH%\Pictures
        if os.path.exists(pathStr):
            # Opens the file explorer in
            fileName = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', pathStr,
                                                          'JPG files (*.jpg);;PNG files (*.png)')
        # If the computer doesn't have a file like that it will open the file explorer in the %HOMEPATH%
        else:
            fileName = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', str(path),
                                                          'JPG files (*.jpg);;PNG files (*.png)')

        # Check if the user has specified a path or just closed the file explorer
        if fileName[0] != "":
            self.imagePath = fileName[0]
            # Displays the image in the photoViewer label
            self.photoViewer.setPhotoWithRectangle(pixmap=QPixmap(fileName[0]))
            # Setting the position of the image to the upper right corner of the pixmap
            self.photoViewer.photo.setPos(0, 0)
            # Fetches the filename from the path and sets it as the header
            pathList = str(fileName[0]).split("/")
            self.fileNameLabel.setText("Filename: " + pathList[-1])

    # Method that removes the Image from the drop zone
    def removeImage(self):
        # Checks if there actually is an image to remove or not
        if self.photoViewer.empty is True:
            # A message box will appear telling the user that there is no image displayed
            msg = QtWidgets.QMessageBox()
            msg.information(self, "No Image Displayed", "There is no image displayed")
        else:
            # Empties the fileNameLabel
            self.fileNameLabel.setText("Drop image here")
            # Removes the image
            self.photoViewer.removeItem()
            self.photoViewer.empty = True
            # Sets ruberBool to false so that you cannot crop when no image is displayed
            self.photoViewer.rubberBool = False
            # Setting the position of the image to the upper right corner of the pixmap
            self.photoViewer.photo.setPos(0, 0)

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
        filePath = event.mimeData().urls()[0].toLocalFile()
        _, extension = os.path.splitext(filePath)
        # If the file is not of type png or jpg an error message will apear
        if extension == ".png" or extension == ".PNG" or extension == ".JPG" or extension == ".jpg" or \
                extension == ".JPEG" or extension == ".jpeg":
            if event.mimeData().hasImage:
                event.setDropAction(Qt.CopyAction)
                filePath = event.mimeData().urls()[0].toLocalFile()
                self.imagePath = filePath
                # Displays the image in the photoViewer label
                self.photoViewer.setPhotoWithRectangle(pixmap=QPixmap(filePath))
                # Setting the position of the image to the upper right corner of the pixmap
                self.photoViewer.photo.setPos(0, 0)
                # Fetches the filename from the path and sets it as the header
                pathList = str(filePath).split("/")
                self.fileNameLabel.setText("Filename: " + pathList[-1])
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()
            # A message box will appear telling the user that the file type must be jpg or png
            msg = QtWidgets.QMessageBox()
            msg.information(self, "Wrong File Type", "The file must be of type jpg or png")


# Starts the application
app = QApplication(sys.argv)
demo = App()
demo.show()
sys.exit(app.exec_())
