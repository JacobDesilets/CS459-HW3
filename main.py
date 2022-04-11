import sys, cv2, os
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRect, QMutex
from PyQt6.QtGui import QImage, QPixmap, QPainter
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QHBoxLayout
from io import BytesIO
from gtts import gTTS
import playsound
import speech_recognition as sr

# face recognition
detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# GLOBALS
audio_queue = []
mutex = QMutex()

class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.face_rect = None
        self.nw_quad = QRect(0, 0, 320, 240)
        self.ne_quad = QRect(321, 0, 319, 240)
        self.sw_quad = QRect(0, 241, 320, 239)
        self.se_quad = QRect(321, 241, 319, 239)
        self.quads = [self.nw_quad, self.ne_quad, self.sw_quad, self.se_quad]
        self.face_position = None


        self.layout = QVBoxLayout()
        self.layout_h = QHBoxLayout()

        self.setWindowTitle("CS459 Homework 3")

        self.feed_label = QLabel()
        self.feed_label.setPixmap(QPixmap('nodata.png'))
        self.layout.addWidget(self.feed_label)

        self.status_label = QLabel()
        self.status_label.setText("Status")
        self.layout_h.addWidget(self.status_label)

        self.cancel_btn = QPushButton("Take photo")
        self.cancel_btn.clicked.connect(self.cancel_feed)
        self.layout_h.addWidget(self.cancel_btn)

        self.webcam_thread = WebcamWorker()
        self.webcam_thread.start()
        self.webcam_thread.img_update.connect(self.img_update_slot)
        self.webcam_thread.face_update.connect(self.face_update_slot)

        self.tts_thread = TtsWorker()
        self.tts_thread.start()

        self.layout.addLayout(self.layout_h)
        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

    def play_tts(self, text):
        mutex.lock()
        audio_queue.append(text)
        mutex.unlock()

    def img_update_slot(self, img):
        self.feed_label.setPixmap(QPixmap.fromImage(img))

    def face_update_slot(self, rect):
        if not rect:  # If face not detected
            self.status_label.setText('No face detected')
            return

        new_face_position = ''

        self.face_rect = rect
        for i, quad in enumerate(self.quads):
            center = self.face_rect.center()
            if quad.contains(center):
                match i:
                    case 0:
                        self.status_label.setText('Top Left')
                        new_face_position = 'Top Left'
                    case 1:
                        self.status_label.setText('Top Right')
                        new_face_position = 'Top Right'
                    case 2:
                        self.status_label.setText('Bottom Left')
                        new_face_position = 'Bottom Left'
                    case 3:
                        self.status_label.setText('Bottom Right')
                        new_face_position = 'Bottom Right'
                if new_face_position != self.face_position:
                    print('New face pos!')
                    self.play_tts(new_face_position)
                    self.face_position = new_face_position

    # activate after receiving position from the user
    def cancel_feed(self):
        self.webcam_thread.stop()


class WebcamWorker(QThread):
    img_update = pyqtSignal(QImage)
    face_update = pyqtSignal(object)

    def run(self):
        self.thread_active = True
        capture = cv2.VideoCapture(0)

        while self.thread_active:
            ret, self.frame = capture.read()
            if ret:
                img = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
                flipped_img = cv2.flip(img, 1)
                faces = detector.detectMultiScale(flipped_img, 1.3, 5)
                if len(faces) == 0:  # If face not detected
                    self.face_update.emit(None)
                for (x, y, w, h) in faces:
                    cv2.rectangle(flipped_img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    self.face_update.emit(QRect(x, y, w, h))
                output = QImage(flipped_img.data, flipped_img.shape[1], flipped_img.shape[0], QImage.Format.Format_RGB888).scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)
            else:
                output = QImage.load('nodata.png')

            self.img_update.emit(output)
        capture.release()

    def stop(self):
        #self.img_update.emit(QImage.load('nodata.png'))
        #self.thread_active = False
        #self.quit()

        selfie = cv2.flip(self.frame, 1)
        cv2.imwrite('selfie.png', selfie)


class TtsWorker(QThread):

    def __init__(self):
        super().__init__()
        print('TTS thread init')
        self.thread_active = True

    def run(self):
        while self.thread_active:
            mutex.lock()
            if audio_queue:
                speech = audio_queue[0]
                audio_queue.pop(0)
                mutex.unlock()
                tts = gTTS(text=speech, lang='en')
                filename = 'speech.mp3'
                tts.save(filename)
                playsound.playsound(Path(__file__).with_name(filename))
            else:
                mutex.unlock()

    def stop(self):
        self.thread_active = False
        self.quit()


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()