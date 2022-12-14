# importing libraries

from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
import collections
import json
import numpy
from torchvision import datasets
from torch.utils.data import DataLoader
from PIL import Image
import cv2
import time
import os

# initializing MTCNN and InceptionResnetV1


mtcnn0 = MTCNN(image_size=240, margin=0, keep_all=False,
               min_face_size=40)  # keep_all=False
mtcnn = MTCNN(image_size=240, margin=0, keep_all=True,
              min_face_size=40)  # keep_all=True
resnet = InceptionResnetV1(pretrained='vggface2').eval()

f = open("file.txt")  # pull from DB instead of file
load_data = json.load(f)

for n in load_data:
    load_data[n] = torch.Tensor(load_data[n])

embedding_list = []
name_list = []
for key in load_data:
    length = len(load_data[key])
    names_temp = [key for _ in range(length)]
    images_temp = [matrix for matrix in load_data[key]]
    name_list.extend(names_temp)
    embedding_list.extend(images_temp)

print('Enter your name :')
new_user = input()

cam = cv2.VideoCapture(0)

while True:
    ret, frame = cam.read()
    if not ret:
        print("fail to grab frame, try again")
        break

    img = Image.fromarray(frame)
    img_cropped_list, prob_list = mtcnn(img, return_prob=True)

    if img_cropped_list is not None:
        boxes, _ = mtcnn.detect(img)

        for i, prob in enumerate(prob_list):
            if prob > 0.90:
                emb = resnet(img_cropped_list[i].unsqueeze(0)).detach()

                dist_list = []  # list of matched distances, minimum distance is used to identify the person

                for idx, emb_db in enumerate(embedding_list):
                    dist = torch.dist(emb, emb_db).item()
                    dist_list.append(dist)

                min_dist = min(dist_list)  # get minumum dist value
                min_dist_idx = dist_list.index(
                    min_dist)  # get minumum dist index
                # get name corrosponding to minimum dist
                name = name_list[min_dist_idx]

                box = boxes[i]

                original_frame = frame.copy()  # storing copy of frame before drawing on it

                if min_dist < 0.90:
                    frame = cv2.putText(frame, name + ' ' + str(min_dist), (int(box[0]), int(box[1])), cv2.FONT_HERSHEY_SIMPLEX,
                                        1, (0, 255, 0), 1, cv2.LINE_AA)

                frame = cv2.rectangle(frame, (int(box[0]), int(
                    box[1])), (int(box[2]), int(box[3])), (255, 0, 0), 2)

    cv2.imshow("IMG", frame)

    k = cv2.waitKey(1)
    if k % 256 == 27:  # ESC
        # package all the data into dictionary and write it
        output = collections.defaultdict()
        nameHist = set()
        for i, name in enumerate(name_list):
            if name not in nameHist:
                nameHist.add(name)
                output[name] = []
            output[name].append(embedding_list[i].tolist())
        print('Esc pressed, closing...')

        # write to DB
        with open('file.txt', 'w') as file:
            file.write(json.dumps(output))
        break

    elif k % 256 == 32:  # space to save image
        name_list.append(new_user)
        embedding_list.append(emb)

        img_name = "photos/{}/{}.jpg".format(name, int(time.time()))
        print(" saved: {}".format(img_name))

cam.release()
cv2.destroyAllWindows()
