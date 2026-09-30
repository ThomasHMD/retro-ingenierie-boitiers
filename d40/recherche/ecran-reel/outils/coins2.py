import cv2, numpy as np, sys
im = cv2.imread(sys.argv[1])
hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
h, s, v = hsv[...,0].astype(int)*2, hsv[...,1], hsv[...,2]
# écran : bleu, vert ou très clair peu saturé (colonne blanche) ; la peau (teinte < 50°) est exclue
m = (((h > 80) & (h < 260) & (s > 60) & (v > 60)) | ((v > 200) & (s < 40))).astype(np.uint8) * 255
m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5,5),np.uint8))
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((31,31),np.uint8))
cs,_ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
c = max(cs, key=cv2.contourArea)
hull = cv2.convexHull(c)
for eps in [0.01,0.015,0.02,0.03,0.04,0.05]:
    a = cv2.approxPolyDP(hull, eps*cv2.arcLength(hull,True), True)
    if len(a)==4: break
print(len(a), a.reshape(-1,2).tolist(), cv2.contourArea(c))
