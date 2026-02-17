from collections import deque

class MovingAverage:
    def __init__(self, window_size=5):
        self.window = deque(maxlen=window_size)

    def update(self, value):
        self.window.append(value)
        return sum(self.window) / len(self.window)
    
class ExponentialSmoothing:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.last = None

    def update(self, value):
        if self.last is None:
            self.last = value
        else:
            self.last = self.alpha * value + (1 - self.alpha) * self.last
        return self.last
