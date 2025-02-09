import os
import sys

import numpy as np
from PIL import Image
from PyQt5.QtCore import QRect
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QBrush, QColor, QFont, QFontMetrics
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit, QLabel, QFileDialog, \
    QProgressBar
# pyinstaller --onefile --windowed steganography_gui.py

class Worker(QThread):
    update_progress = pyqtSignal(int)
    finished = pyqtSignal(str)

    def __init__(self, img_path, data=None, mode='encode'):
        super().__init__()

        self.img_path = img_path
        self.data = data
        self.mode = mode

    def run(self):
        if self.mode == 'encode':
            self.encode_image(self.img_path, self.data)
        else:
            decoded_data = self.decode_image(self.img_path)
            self.finished.emit(decoded_data)  # Emit the decoded data when done

    def encode_image(self, img_path, data):
        img = Image.open(img_path)
        data_bytes = data.encode('utf-8')
        data_bin = ''.join([format(byte, '08b') for byte in data_bytes])
        data_bin += '00000000'  # 终止符

        if len(data_bin) > img.size[0] * img.size[1] * 3:
            raise ValueError("数据太大，无法隐藏在图片中")

        data_index = 0
        image_array = np.array(img)
        total_pixels = img.size[0] * img.size[1]
        processed_pixels = 0

        for row in image_array:
            for pixel in row:
                for i in range(3):  # RGB
                    if data_index < len(data_bin):
                        pixel[i] = pixel[i] & ~1 | int(data_bin[data_index])
                        data_index += 1
                processed_pixels += 1
                if processed_pixels % 500 == 0:
                    progress_percentage = int((processed_pixels / total_pixels) * 100)
                    self.update_progress.emit(progress_percentage)  # 发射进度更新信号

        self.update_progress.emit(100)  # 确保在结束时发射100%

        # encoded_img = Image.fromarray(image_array)

        # 尝试从环境变量获取路径
        save_path = os.getenv('ENCODE_PYQT_IMG')
        if not save_path:
            # 如果环境变量未设置，使用桌面路径
            desktop = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
            save_path = desktop

        # 确保路径以斜杠结束
        if not save_path.endswith(os.path.sep):
            save_path += os.path.sep

        # 定义加密图片的文件名
        encoded_img_filename = "encoded_image.png"
        # 完整的保存路径
        encoded_img_path = os.path.join(save_path, encoded_img_filename)

        # 加密操作完成后，保存加密后的图片
        encoded_img = Image.fromarray(image_array)
        encoded_img.save(encoded_img_path)

        # 加密完成后，发射包含保存路径的信号
        self.finished.emit(encoded_img_path)  # 发射包含保存图片路径的完成信号

        #
        # encoded_img.save("encoded_image.png")
        # self.finished.emit(encoded_img)

    def decode_image(self, img_path):
        img = Image.open(img_path)
        image_array = np.array(img)

        binary_data = ""
        total_pixels = img.size[0] * img.size[1]
        processed_pixels = 0

        for row in image_array:
            for pixel in row:
                for i in range(3):  # 遍历RGB
                    binary_data += str(pixel[i] & 1)
                    processed_pixels += 1 / 3
                if processed_pixels % 500 < 1:  # 更新进度
                    progress_percentage = int((processed_pixels / total_pixels) * 100)
                    self.update_progress.emit(progress_percentage)

        # 确保在结束时进度为100%
        self.update_progress.emit(100)

        bytes_list = [binary_data[i: i + 8] for i in range(0, len(binary_data), 8)]

        data_bytes = bytearray()
        for byte in bytes_list:
            data_bytes.append(int(byte, 2))
            if data_bytes[-1] == 0:  # 检测到终止符
                break

        data_str = data_bytes[:-1].decode('utf-8')  # 删除终止符
        print("\nDecoding complete.")  # 完成后换行
        return data_str


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'PyQt Steganography'
        self.initUI()

        # 初始化计时器
        self.encode_blink_timer = QTimer()
        self.decode_blink_timer = QTimer()

        # 设置计时器信号和槽
        self.encode_blink_timer.timeout.connect(self.blink_encode_button)
        self.decode_blink_timer.timeout.connect(self.blink_decode_button)

        # 设置闪烁状态
        self.encode_blink_state = False
        self.decode_blink_state = False

    def initUI(self):
        self.setWindowTitle(self.title)
        layout = QVBoxLayout()
        # self.label = QLabel('Select an image and enter text to encode or decode.', self)
        # layout.addWidget(self.label)
        self.label = ClickableLabel('Select an image and enter text to encode or decode.')
        layout.addWidget(self.label)

        self.textEdit = QTextEdit(self)
        layout.addWidget(self.textEdit)

        self.progressBar = RoundedProgressBar(self)
        layout.addWidget(self.progressBar)

        self.btn_encode = QPushButton('Encode Text', self)
        self.btn_encode.clicked.connect(self.encode)

        layout.addWidget(self.btn_encode)

        self.btn_decode = QPushButton('Decode Text', self)
        self.btn_decode.clicked.connect(self.decode)
        layout.addWidget(self.btn_decode)

        self.setLayout(layout)
        self.setStyleSheet("""
                    QTextEdit, QPushButton, QLabel,QProgressBar {
                        border-radius: 10px;
                    }
                    QPushButton {
                        background-color: #87CEEB;
                        padding: 5px;
                    }
                    QTextEdit {
                        background-color: #F0F8FF;
                        padding: 5px;
                    }
                    QProgressBar {
                        border: 2px solid grey;
                        border-radius: 10px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #FFA000;
                        width: 10px;
                        margin: 0.5px;
                        border-radius: 10px;
                    }
                    QLabel {
                        qproperty-alignment: 'AlignCenter';
                    }
                """)

    def advanceProgressBar(self):
        curVal = self.progressBar.value()
        maxVal = self.progressBar.maximum()
        nextVal = curVal + 10 if curVal + 10 <= maxVal else 0
        self.progressBar.setValue(nextVal)

    def encode(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Select Image for Encoding", "",
                                                  "PNG Files (*.png);;All Files (*)")
        if filePath:
            self.label.setText("正在加密...")
            data = self.textEdit.toPlainText()
            self.worker = Worker(filePath, data=data, mode='encode')
            self.worker.update_progress.connect(self.progressBar.setValue)
            self.worker.finished.connect(self.encode_finished)  # 连接加密完成的处理函数
            self.worker.start()
            self.encode_blink_timer.start(500)

    def decode(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Select Image for Decoding", "",
                                                  "PNG Files (*.png);;All Files (*)")
        if filePath:
            # 设置进度条颜色为红色
            self.label.setText("正在解密...")
            self.textEdit.setPlainText("")
            self.progressBar.setStyleSheet(
                "QProgressBar {text-align: center;} QProgressBar::chunk {background-color: red;}")
            self.worker = Worker(filePath, mode='decode')
            self.worker.update_progress.connect(self.progressBar.setValue)
            self.worker.finished.connect(self.showDecodedData)
            self.worker.start()
        self.decode_blink_timer.start(500)  # 每500毫秒切换一次状态

    # def showDecodedData(self, decoded_data):
    #     self.textEdit.setPlainText(decoded_data)
    #     # 重置进度条样式，如果需要
    #     self.progressBar.setStyleSheet("")

    def blink_encode_button(self):
        # 切换加密按钮的样式
        if self.encode_blink_state:
            self.btn_encode.setStyleSheet("background-color: lightgrey;")
        else:
            self.btn_encode.setStyleSheet("background-color: yellow;")
        self.encode_blink_state = not self.encode_blink_state

    def blink_decode_button(self):
        # 切换解密按钮的样式
        if self.decode_blink_state:
            self.btn_decode.setStyleSheet("background-color: lightgrey;")
        else:
            self.btn_decode.setStyleSheet("background-color: yellow;")
        self.decode_blink_state = not self.decode_blink_state

    def showDecodedData(self, decoded_data):
        # 显示解密数据，并停止解密按钮的闪烁
        # self.textEdit.setPlainText(decoded_data)
        # self.decode_blink_timer.stop()
        # self.btn_decode.setStyleSheet("")  # 恢复原始样式

        self.decode_blink_timer.stop()
        self.btn_decode.setStyleSheet("")
        self.textEdit.setPlainText("解密后的信息:" + decoded_data)
        self.label.setText("解密完成。")

    def encode_finished(self, message):
        # 加密完成的处理
        self.encode_blink_timer.stop()  # 停止加密按钮的闪烁
        self.btn_encode.setStyleSheet("")  # 恢复原始样式
        self.label.setText("图片保存在:" + message)  # 可选：更新标签显示加密完成的消息
        self.textEdit.setPlainText("加密完成。")


class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super(ClickableLabel, self).__init__(parent)

    def mousePressEvent(self, event):
        # 检查是否为左键点击
        if event.button() == Qt.LeftButton:
            self.copyTextToClipboard()

    def copyTextToClipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text())
        print(f"Copied to clipboard: {self.text()}")


class RoundedProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super(RoundedProgressBar, self).__init__(parent)
        self.setMinimum(0)
        self.setMaximum(100)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 开启抗锯齿

        # 绘制进度条背景
        bgRect = QRect(0, 0, self.width(), self.height())
        bgColor = QColor(230, 230, 230)  # 进度条背景颜色
        painter.setBrush(QBrush(bgColor))
        painter.setPen(Qt.NoPen)  # 无边框
        painter.drawRoundedRect(bgRect, 10, 10)  # 背景圆角

        # 绘制进度
        if self.value() > 0:
            progressRect = QRect(0, 0, int((self.width() - 4) * self.value() / self.maximum()), self.height())
            progressColor = QColor(255, 160, 0)  # 进度条颜色
            painter.setBrush(QBrush(progressColor))
            painter.drawRoundedRect(progressRect.adjusted(2, 2, -2, -2), 8, 8)  # 进度圆角

            try:
                # 绘制进度百分比文本
                font = QFont()
                painter.setFont(font)
                penColor = QColor(0, 0, 0)  # 文本颜色
                painter.setPen(penColor)
                progressText = f"{self.value()}%"
                fontMetrics = QFontMetrics(font)
                textWidth = fontMetrics.width(progressText)
                textHeight = fontMetrics.height()
                painter.drawText(int(self.width() / 2 - textWidth / 2), int(self.height() / 2 + textHeight / 3),
                                 progressText)


            except Exception as e:
                print(e)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())
