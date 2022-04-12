import sys, cv2, os
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRect, QMutex, QRunnable
from PyQt6.QtGui import QImage, QPixmap, QPainter
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QHBoxLayout
from gtts import gTTS
import playsound
import speech_recognition as sr

# face recognition
detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# GLOBALS
tts_queue = []
tts_queue_lock = QMutex()


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.face_rect = None
        self.nw_quad = QRect(0, 0, 320, 240)
        self.ne_quad = QRect(321, 0, 319, 240)
        self.sw_quad = QRect(0, 241, 320, 239)
        self.se_quad = QRect(321, 241, 319, 239)
        self.quads = [self.nw_quad, self.ne_quad, self.sw_quad, self.se_quad]
        self.face_positions = ['top left', 'top right', 'bottom left', 'bottom right']
        self.face_position = None
        self.face_target = 'bottom right'
        self.target_reached = False

        # self.setStyleSheet('MainWindow {background-color : #4db3a0;}')

        self.layout = QVBoxLayout()
        self.layout_h = QHBoxLayout()

        self.setWindowTitle("CS459 Homework 3")

        self.feed_label = QLabel()
        self.feed_label.setPixmap(QPixmap('nodata.png'))
        self.layout.addWidget(self.feed_label)

        self.status_label = QLabel()
        self.status_label.setText('Position')
        self.layout_h.addWidget(self.status_label)

        self.target_label = QLabel()
        self.target_label.setText(f'Target: {self.face_target}')
        # self.target_label.setStyleSheet('QLabel {background-color : black; color : white;}')
        self.layout_h.addWidget(self.target_label)

        self.cancel_btn = QPushButton("Take photo")
        self.cancel_btn.clicked.connect(self.take_photo)
        self.layout_h.addWidget(self.cancel_btn)

        self.webcam_thread = WebcamWorker()
        self.webcam_thread.start()
        self.webcam_thread.img_update_signal.connect(self.img_update_slot)
        self.webcam_thread.face_update_signal.connect(self.face_update_slot)

        self.tts_thread = TtsWorker()
        self.tts_thread.start()
        self.tts_thread.done_speaking_signal.connect(self.take_photo_slot)

        self.sst_thread = SttWorker()
        self.sst_thread.start()
        self.sst_thread.speech_signal.connect(self.speech_slot)

        self.layout.addLayout(self.layout_h)
        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

    def speech_slot(self, text):
        if text.lower() in self.face_positions:
            self.face_target = text.lower()
            self.play_tts(f'Target set to {text}')
            self.target_label.setText(text)
            self.guide_to_target()

    def play_tts(self, text):
        tts_queue_lock.lock()
        tts_queue.append(text)
        tts_queue_lock.unlock()

    def img_update_slot(self, img):
        self.feed_label.setPixmap(QPixmap.fromImage(img))

    def guide_to_target(self):
        pos = self.face_positions.index(self.face_position)
        target = self.face_positions.index(self.face_target)
        '''
        0   1
        2   3
        '''
        if pos == target:
            self.target_reached = True
            self.take_photo()
        elif (pos < 2 and target < 2) or (pos > 1 and target > 1):  # If pos and target are on the same row
            if pos < target:
                self.play_tts('Move right')
            else:
                self.play_tts('Move left')
        else:
            if target - pos == 2:
                self.play_tts('Move down')
            elif target - pos == -2:
                self.play_tts('Move up')
            elif (target - pos == 1) or (target - pos == -3):
                self.play_tts('Move left')
            elif (target - pos == -1) or (target - pos == 3):
                self.play_tts('Move right')

    def face_update_slot(self, rect):
        if not rect:  # If face not detected
            self.status_label.setText('No face detected')
            return

        new_face_position = ''

        self.face_rect = rect
        for i, quad in enumerate(self.quads):
            center = self.face_rect.center()
            if quad.contains(center):
                if i == 0:
                    self.status_label.setText('top left')
                    new_face_position = 'top left'
                elif i == 1:
                    self.status_label.setText('top right')
                    new_face_position = 'top right'
                elif i == 2:
                    self.status_label.setText('bottom left')
                    new_face_position = 'bottom left'
                elif i == 3:
                    self.status_label.setText('bottom right')
                    new_face_position = 'bottom right'

                if new_face_position != self.face_position:
                    # print('New face pos!')
                    self.face_position = new_face_position
                    self.guide_to_target()

    # activate after receiving position from the user
    def take_photo(self):
        self.play_tts('Taking Selfie')
        self.webcam_thread.capture()

    def take_photo_slot(self, text):
        if text == 'Taking Selfie':
            self.webcam_thread.capture()


class WebcamWorker(QThread):
    img_update_signal = pyqtSignal(QImage)
    face_update_signal = pyqtSignal(object)

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
                    self.face_update_signal.emit(None)
                for (x, y, w, h) in faces:
                    cv2.rectangle(flipped_img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    self.face_update_signal.emit(QRect(x, y, w, h))
                output = QImage(flipped_img.data, flipped_img.shape[1], flipped_img.shape[0], QImage.Format.Format_RGB888).scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)
            else:
                output = QImage.load('nodata.png')

            self.img_update_signal.emit(output)
        capture.release()

    def capture(self):
        selfie = cv2.flip(self.frame, 1)
        cv2.imwrite('selfie.png', selfie)


class TtsWorker(QThread):

    done_speaking_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        print('TTS thread init')
        self.thread_active = True

    def run(self):
        while self.thread_active:
            tts_queue_lock.lock()
            if tts_queue:
                speech = tts_queue[0]
                tts_queue.pop(0)
                tts_queue_lock.unlock()
                tts = gTTS(text=speech, lang='en')
                filename = 'speech.mp3'
                tts.save(filename)
                f = Path(__file__).with_name(filename)
                path = 'D:\\Projects\CS459\CS459-HW3\speech.mp3'
                try:
                    playsound.playsound(f)
                except Exception as e:
                    print(e)
                self.done_speaking_signal.emit(speech)
            else:
                tts_queue_lock.unlock()

    def stop(self):
        self.thread_active = False
        self.quit()


class SttWorker(QThread):

    speech_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.thread_active = True
        print('SST thread init')

    def run(self):
        pass
        r = sr.Recognizer()
        while self.thread_active:
            try:
                with sr.Microphone() as source:
                    pass
                    r.adjust_for_ambient_noise(source, duration=0.2)
                    audio = r.listen(source)
                    text = r.recognize_google(audio)
                    text = text.lower()
                    self.speech_signal.emit(text)
                    print(text)
            except Exception as e:
                print(e)


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()