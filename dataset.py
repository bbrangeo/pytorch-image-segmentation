import torch
from torch.utils.data.dataset import Dataset
import utils

import glob
import numpy as np
import cv2
from PIL import Image
import random
import argparse
import itertools

CAMVID_MEAN = [0.41189489566336, 0.4251328133025, 0.4326707089857]
CAMVID_STD = [0.27413549931506, 0.28506257482912, 0.28284674400252]

from torch.utils.data.sampler import SubsetRandomSampler

import sys
import os
from optparse import OptionParser
import numpy as np

import torch
import torch.backends.cudnn as cudnn
import torch.nn as nn
from torch import optim

from eval import eval_net
from unet import Unet

def getImageArr( path , width , height , imgNorm="divide" , odering='channels_first' ):

	try:
		img = cv2.imread(path, 1)
		debug = img.copy()
		if imgNorm == "divide":
			img = cv2.resize(img, ( width , height ))
			img = img.astype(np.float32)
			img = img/255.0
			img = (img-CAMVID_MEAN)/CAMVID_STD

		if odering == 'channels_first':
			img = np.rollaxis(img, 2, 0)
		return img, debug
	except Exception as e:
		print (path , e)
		img = np.zeros((  height , width  , 3 ))
		if odering == 'channels_first':
			img = np.rollaxis(img, 2, 0)
		return img, debug


def getSegmentationArr( path , nClasses ,  width , height  ):

	seg_labels = np.zeros((  height , width  , nClasses ))
	try:
		img = cv2.imread(path, 1)
		img = cv2.resize(img, ( width , height ))
		img = img[:, : , 0]
		debug = img.copy()
		for c in range(nClasses):
			seg_labels[: , : , c ] = (img == c ).astype(int)

	except Exception as e:
		print (e)
		
	seg_labels = np.reshape(seg_labels, ( width*height , nClasses ))
	return seg_labels,debug

		
class MyCustomDataset(Dataset):
	def __init__(self, images_path="dataset/dataset1/images_prepped_train/", segs_path="dataset/dataset1/annotations_prepped_train/",
				 n_classes=10, input_width=480,input_height=360, transforms=None,scale=0.5):
		
		self.images_path = images_path
		self.segs_path = segs_path
		self.n_classes = n_classes
		self.input_width = input_width
		self.input_height = input_height
		self.transforms = transforms

		assert self.images_path[-1] == '/'
		assert self.segs_path[-1] == '/'
	
		images = glob.glob(self.images_path + "*.jpg") + glob.glob(self.images_path + "*.png") +  glob.glob(self.images_path + "*.jpeg")
		images.sort()
		segmentations = glob.glob(self.segs_path + "*.jpg") + glob.glob(self.segs_path + "*.png") +  glob.glob(self.segs_path + "*.jpeg")
		segmentations.sort()

		assert len( images ) == len(segmentations)

		X = []
		Y = []
		Z = []
		for img,seg in (zip(images,segmentations)):
			assert(  img.split('/')[-1].split(".")[0] ==  seg.split('/')[-1].split(".")[0])
			#img, debug = getImageArr(img , input_width , input_height )
			img, label = self.resize_crop_squared(img_path=img,seg_path=seg,scale=scale)			
			Z.append(img)
			X.append(np.transpose(self.normalize_std(img), axes=[2, 0, 1]))
			Y.append(label)


		self.imgs = np.array(X)
		self.imgs_original = np.array(Z)
		self.labels = np.array(Y)		
		self.input_width = self.labels[0].shape[1]
		self.input_height = self.labels[0].shape[0]

	def __getitem__(self, index):
		return (self.imgs[index], self.labels[index],self.imgs_original[index])

	def __len__(self):
		return len(self.imgs)

	def resize_and_crop(self, pilimg, scale=0.5, final_height=None):
		w = pilimg.size[0]
		h = pilimg.size[1]
		newW = int(w * scale)
		newH = int(h * scale)

		if not final_height:
			diff = 0
		else:
			diff = newH - final_height

		img = pilimg.resize((newW, newH))
		img = img.crop((0, diff // 2, newW, newH - diff // 2))
		return np.array(img, dtype=np.float32)

	def resize_crop_squared(self, img_path, seg_path, scale=0.5):
		img = self.resize_and_crop(Image.open(img_path), scale=scale)
		label = self.resize_and_crop(Image.open(seg_path), scale=scale)
		
		h = img.shape[0]
		pos = 1 if random.random() > 0.5 else 0
		if pos == 0:
			img = img[:, :h]
			label = label[:, :h]
		else:
			img = img[:, -h:]
			label = label[:, -h:]	
		return img, label

	def normalize_std(self,x):
		return ((x / 255.0)-CAMVID_MEAN)/CAMVID_STD

if __name__ == "__main__":	
	images_path = "dataset/dataset1/images_prepped_train/"
	segs_path = "dataset/dataset1/annotations_prepped_train/"
	batch_size = 1
	n_classes = 10
	input_width = 480
	input_height = 360
	custom_dataset = MyCustomDataset(images_path=images_path, segs_path=segs_path, n_classes=n_classes, input_width=input_width,input_height=input_height)

	a,b = custom_dataset.__getitem__(5)
	print(a.shape,b.shape)

	net = Unet(input_channels=3,input_width=480, input_height=360, n_classes=12)#Unet(n_channels=3, n_classes=1)
	net.cuda()

	'''
	train_net(net=net,
		  epochs=2,
		  batch_size=4,
		  lr=0.1,
		  img_scale=0.5,dataset=custom_dataset)
	'''