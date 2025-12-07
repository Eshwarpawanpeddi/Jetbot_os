class FaceRenderingSystem:
    def __init__(self):
        self.eye_color = (255, 255, 255)  # Default white
        self.eyebrow_position = 0
        self.mouth_expression = 'neutral'
        self.emotions = {
            'happy': self.happy_expression,
            'sad': self.sad_expression,
            'angry': self.angry_expression,
            'surprised': self.surprised_expression,
        }

    def set_eye_color(self, r, g, b):
        self.eye_color = (r, g, b)

    def raise_eyebrows(self):
        self.eyebrow_position += 1

    def lower_eyebrows(self):
        self.eyebrow_position -= 1

    def set_mouth_expression(self, expression):
        if expression in self.emotions:
            self.mouth_expression = expression
            self.emotions[expression]()

    def happy_expression(self):
        print('Creating happy mouth animation.')

    def sad_expression(self):
        print('Creating sad mouth animation.')

    def angry_expression(self):
        print('Creating angry mouth animation.')

    def surprised_expression(self):
        print('Creating surprised mouth animation.')

    def render_face(self):
        print(f'Face rendered with eye color {self.eye_color}, eyebrows at {self.eyebrow_position}, mouth is {self.mouth_expression}.')

# Example usage:
if __name__ == '__main__':
    face = FaceRenderingSystem()
    face.set_eye_color(0, 0, 255)  # Set eyes to blue
    face.raise_eyebrows()
    face.set_mouth_expression('happy')
    face.render_face()