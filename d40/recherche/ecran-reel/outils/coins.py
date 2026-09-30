import cv2, numpy as np, sys
im = cv2.imread(sys.argv[1])
hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
v = hsv[:,:,2]
m = (v > int(sys.argv[2]) if len(sys.argv) > 2 else v > 90).astype(np.uint8) * 255
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((25,25),np.uint8))
cs,_ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
c = max(cs, key=cv2.contourArea)
hull = cv2.convexHull(c)
for eps in [0.01,0.02,0.03,0.04,0.05]:
    a = cv2.approxPolyDP(hull, eps*cv2.arcLength(hull,True), True)
    if len(a)==4: break
print(len(a), a.reshape(-1,2).tolist(), cv2.contourArea(c))
