"""
流式布局
"""

from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtWidgets import QLayout, QSizePolicy, QWidget, QLayoutItem

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self.setSpacing(spacing)

        self.item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, a0):
        self.item_list.append(a0)

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Horizontal | Qt.Vertical)  # type: ignore

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, a0):
        height = self.doLayout(QRect(0, 0, a0, 0), True)
        return height

    def setGeometry(self, a0):
        super().setGeometry(a0)
        self.doLayout(a0, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())

        margins = self.getContentsMargins()
        if margins:
            margin = margins[0] or 0
            size += QSize(2 * margin, 2 * margin)
        return size

    def doLayout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0

        for item in self.item_list:
            wid = item.widget()
            space_x = self.spacing() + wid.style().layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)  # type: ignore
            space_y = self.spacing() + wid.style().layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)  # type: ignore
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(x, y, item.sizeHint().width(), item.sizeHint().height()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()