#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
@Author  :   Peike Li
@Contact :   peike.li@yahoo.com
@File    :   simple_extractor.py
@Time    :   8/30/19 8:59 PM
@Desc    :   Simple Extractor
@License :   This source code is licensed under the license found in the
             LICENSE file in the root directory of this source tree.
"""

import os
import torch
import argparse
import numpy as np
import shutil
import glob
import cv2
from PIL import Image
from tqdm import tqdm

from torch.utils.data import DataLoader
import torchvision.transforms as transforms

import networks
from utils.transforms import transform_logits
from datasets.simple_extractor_dataset import SimpleFolderDataset

dataset_settings = {
    'lip': {
        'input_size': [473, 473],
        'num_classes': 20,
        'label': ['Background', 'Hat', 'Hair', 'Glove', 'Sunglasses', 'Upper-clothes', 'Dress', 'Coat',
                  'Socks', 'Pants', 'Jumpsuits', 'Scarf', 'Skirt', 'Face', 'Left-arm', 'Right-arm',
                  'Left-leg', 'Right-leg', 'Left-shoe', 'Right-shoe']
    },
    'atr': {
        'input_size': [512, 512],
        'num_classes': 18,
        'label': ['Background', 'Hat', 'Hair', 'Sunglasses', 'Upper-clothes', 'Skirt', 'Pants', 'Dress', 'Belt',
                  'Left-shoe', 'Right-shoe', 'Face', 'Left-leg', 'Right-leg', 'Left-arm', 'Right-arm', 'Bag', 'Scarf']
    },
    'pascal': {
        'input_size': [512, 512],
        'num_classes': 7,
        'label': ['Background', 'Head', 'Torso', 'Upper Arms', 'Lower Arms', 'Upper Legs', 'Lower Legs'],
    }
}


def get_arguments():
    """Parse all the arguments provided from the CLI.
    Returns:
      A list of parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Self Correction for Human Parsing")

    parser.add_argument("--dataset", type=str, default='lip', choices=['lip', 'atr', 'pascal'])
    parser.add_argument("--model-restore", type=str, default='', help="restore pretrained model parameters.")
    parser.add_argument("--gpu", type=str, default='0', help="choose gpu device.")
    parser.add_argument("--input-image-dir", type=str, default='input_image', help="path of input image folder.")
    parser.add_argument("--input-cloth-dir", type=str, default='input_cloth', help="path of input cloth folder.")
    parser.add_argument("--input-keypoint-dir", type=str, default='input_keypoint', help="path of input keypoint folder.")
    parser.add_argument("--output-cloth-dir", type=str, default='Data_preprocessing/test_color', help="path of output cloth folder.")
    parser.add_argument("--output-edge-dir", type=str, default='Data_preprocessing/test_edge', help="path of output edge folder.")
    parser.add_argument("--output-image-dir", type=str, default='Data_preprocessing/test_img', help="path of output image folder.")
    parser.add_argument("--output-label-dir", type=str, default='Data_preprocessing/test_label', help="path of output label folder.")
    parser.add_argument("--output-keypoint-dir", type=str, default='Data_preprocessing/test_pose', help="path of output keypoint folder.")
    parser.add_argument("--logits", action='store_true', default=False, help="whether to save the logits.")

    return parser.parse_args()


def get_palette(num_cls):
    """ Returns the color map for visualizing the segmentation mask.
    Args:
        num_cls: Number of classes
    Returns:
        The color map
    """
    n = num_cls
    palette = [0] * (n * 3)
    for j in range(0, n):
        lab = j
        palette[j * 3 + 0] = 0
        palette[j * 3 + 1] = 0
        palette[j * 3 + 2] = 0
        i = 0
        while lab:
            palette[j * 3 + 0] |= (((lab >> 0) & 1) << (7 - i))
            palette[j * 3 + 1] |= (((lab >> 1) & 1) << (7 - i))
            palette[j * 3 + 2] |= (((lab >> 2) & 1) << (7 - i))
            i += 1
            lab >>= 3
    return palette


def main():
    args = get_arguments()

    gpus = [int(i) for i in args.gpu.split(',')]
    assert len(gpus) == 1
    if not args.gpu == 'None':
        os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu

    num_classes = dataset_settings[args.dataset]['num_classes']
    input_size = dataset_settings[args.dataset]['input_size']
    label = dataset_settings[args.dataset]['label']
    print("Evaluating total class number {} with {}".format(num_classes, label))

    model = networks.init_model('resnet101', num_classes=num_classes, pretrained=None)

    state_dict = torch.load(args.model_restore)['state_dict']
    from collections import OrderedDict
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = k[7:]  # remove `module.`
        new_state_dict[name] = v
    model.load_state_dict(new_state_dict)
    model.cpu()
    model.eval()

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.406, 0.456, 0.485], std=[0.225, 0.224, 0.229])
    ])
    img_dataset = SimpleFolderDataset(root=args.input_image_dir, input_size=input_size, transform=transform)
    img_dataloader = DataLoader(img_dataset)
    cloth_dataset = SimpleFolderDataset(root=args.input_cloth_dir, input_size=input_size, transform=transform)
    cloth_dataloader = DataLoader(cloth_dataset)
    if not os.path.exists(args.output_label_dir):
        os.makedirs(args.output_label_dir)
    if not os.path.exists(args.output_cloth_dir):
        os.makedirs(args.output_cloth_dir)
    if not os.path.exists(args.output_edge_dir):
        os.makedirs(args.output_edge_dir)
    if not os.path.exists(args.output_image_dir):
        os.makedirs(args.output_image_dir)
    if not os.path.exists(args.output_keypoint_dir):
        os.makedirs(args.output_keypoint_dir)
    path_to_img_dataset='input_image'
    filename_list = glob.glob(os.path.join(path_to_img_dataset,"*.jpg"))
    for p in filename_list:
        filename = p.split('/')
        img = cv2.imread(p)
        cv2.imwrite('Data_preprocessing/test_img/'+filename[1],img)
    path_to_cloth_dataset='input_cloth'
    filename_list = glob.glob(os.path.join(path_to_cloth_dataset,"*.jpg"))
    for p in filename_list:
        filename = p.split('/')
        img = cv2.imread(p)
        cv2.imwrite('Data_preprocessing/test_color/'+filename[1],img)
        img_gray=cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret ,img_gray = cv2.threshold(img_gray, 254, 255, cv2.THRESH_BINARY_INV)
        img_gray = cv2.medianBlur(img_gray, 25)
        img_gray=cv2.resize(img_gray,(192,256),interpolation=cv2.INTER_AREA)
        cv2.imwrite('Data_preprocessing/test_edge/'+filename[1],img_gray)
    path_to_img_dataset='input_keypoint'
    filename_list = glob.glob(os.path.join(path_to_img_dataset,"*.json"))
    for p in filename_list:
        filename = p.split('/')
        shutil.move(p,'Data_preprocessing/test_pose/'+filename[1])
        
    
    palette = get_palette(num_classes)
    with torch.no_grad():
        for idx, batch in enumerate(tqdm(img_dataloader)):
            image, meta = batch
            img_name = meta['name'][0]
            c = meta['center'].numpy()[0]
            s = meta['scale'].numpy()[0]
            w = meta['width'].numpy()[0]
            h = meta['height'].numpy()[0]

            output = model(image.cpu()) 
            upsample = torch.nn.Upsample(size=input_size, mode='bilinear', align_corners=True)
            upsample_output = upsample(output[0][-1][0].unsqueeze(0))
            upsample_output = upsample_output.squeeze()
            upsample_output = upsample_output.permute(1, 2, 0)  # CHW -> HWC

            logits_result = transform_logits(upsample_output.data.cpu().numpy(), c, s, w, h, input_size=input_size)
            parsing_result = np.argmax(logits_result, axis=2)
            #background
            parsing_result=np.where(parsing_result==0,0,parsing_result)
            #Pants
            parsing_result=np.where(parsing_result==9,8,parsing_result)
            parsing_result=np.where(parsing_result==12,8,parsing_result)
            #hair
            parsing_result=np.where(parsing_result==2,1,parsing_result)
            #face
            parsing_result=np.where(parsing_result==4,12,parsing_result)
            parsing_result=np.where(parsing_result==13,12,parsing_result)
            #upper-cloth
            parsing_result=np.where(parsing_result==5,4,parsing_result)
            parsing_result=np.where(parsing_result==6,4,parsing_result)
            parsing_result=np.where(parsing_result==7,4,parsing_result)
            parsing_result=np.where(parsing_result==10,4,parsing_result)
            #Left-shoe
            parsing_result=np.where(parsing_result==18,5,parsing_result)
            #Right-shoe
            parsing_result=np.where(parsing_result==19,6,parsing_result)
            #Left_leg
            parsing_result=np.where(parsing_result==16,9,parsing_result)
            #Right_leg
            parsing_result=np.where(parsing_result==17,10,parsing_result)
            #Left_arm
            parsing_result=np.where(parsing_result==14,11,parsing_result)
            #Right_arm
            parsing_result=np.where(parsing_result==15,13,parsing_result)
            parsing_result_path = os.path.join(args.output_label_dir, img_name[:-4] + '.png')
            output_img = Image.fromarray(np.asarray(parsing_result, dtype=np.uint8))
            output_img.save(parsing_result_path)
            if args.logits:
                logits_result_path = os.path.join(args.output_label_dir, img_name[:-4] + '.npy')
                np.save(logits_result_path, logits_result)
    return


if __name__ == '__main__':
    main()
