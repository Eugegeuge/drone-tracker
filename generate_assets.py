import cv2
import numpy as np

# 1. Create Background (Grey 2000x2000 map)
bg_size = 2000
# Make it grey (100) instead of white (255) to avoid "all white" look
background = np.ones((bg_size, bg_size, 3), dtype=np.uint8) * 100

# Draw a grid
for i in range(0, bg_size, 100):
    cv2.line(background, (i, 0), (i, bg_size), (150, 150, 150), 1)
    cv2.line(background, (0, i), (bg_size, i), (150, 150, 150), 1)

# Draw some "walls" or obstacles
cv2.rectangle(background, (500, 500), (600, 1500), (50, 50, 50), -1)
cv2.rectangle(background, (1400, 500), (1500, 1500), (50, 50, 50), -1)

cv2.imwrite('assets/background.png', background)
print("Generated assets/background.png")

# Note: person.png is now provided by the AI generator, so we don't overwrite it here.
# But if it's missing, we could generate a fallback.
import os
if not os.path.exists('assets/person.png'):
    print("Warning: assets/person.png not found. Creating fallback.")
    person_h, person_w = 200, 100
    person = np.zeros((person_h, person_w, 3), dtype=np.uint8)
    person[:, :] = (255, 255, 255) 
    cv2.circle(person, (50, 40), 30, (0, 0, 0), -1)
    cv2.rectangle(person, (20, 70), (80, 180), (0, 0, 0), -1)
    cv2.imwrite('assets/person.png', person)
