import sys, cv2

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget

# face recognition
detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.layout = QVBoxLayout()

        self.setWindowTitle("CS459 Homework 3")

        self.feed_label = QLabel()
        self.feed_label.setPixmap(QPixmap('nodata.png'))
        self.layout.addWidget(self.feed_label)

        self.cancel_btn = QPushButton()
        self.cancel_btn.clicked.connect(self.cancel_feed)
        self.layout.addWidget(self.cancel_btn)

        self.webcam_thread = WebcamWorker()
        self.webcam_thread.start()
        self.webcam_thread.img_update.connect(self.img_update_slot)

        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

    def img_update_slot(self, img):
        self.feed_label.setPixmap(QPixmap.fromImage(img))

    def cancel_feed(self):
        self.webcam_thread.stop()


class WebcamWorker(QThread):
    img_update = pyqtSignal(QImage)

    def run(self):
        self.thread_active = True
        capture = cv2.VideoCapture(0)

        while self.thread_active:
            ret, frame = capture.read()
            if ret:
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                flipped_img = cv2.flip(img, 1)
                faces = detector.detectMultiScale(flipped_img, 1.3, 5)
                for (x, y, w, h) in faces:
                    cv2.rectangle(flipped_img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                output = QImage(flipped_img.data, flipped_img.shape[1], flipped_img.shape[0], QImage.Format.Format_RGB888).scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)
            else:
                output = QImage.load('nodata.png')

            self.img_update.emit(output)
        capture.release()

    def stop(self):
        #self.img_update.emit(QImage.load('nodata.png'))
        self.thread_active = False
        self.quit()


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()