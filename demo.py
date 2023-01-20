import os.path

from torchvision import transforms, models
import torch
from timm.models import create_model
from torch import nn
from PIL import Image
from pathlib import Path
from tqdm import tqdm
from shutil import copyfile
from datasets import build_transform
import argparse
import utils
import cv2

import models.convnext
import models.convnext_isotropic

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
cls_names=['其他', '高质量涩图', '多人', '低质量缩略图']

def str2bool(v):
    """
    Converts string to bool type; enables command line
    arguments in the format of '--arg1 true --arg2 false'
    """
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def get_args_parser():
    parser = argparse.ArgumentParser('ConvNeXt training and evaluation script for image classification', add_help=False)

    # Model parameters
    parser.add_argument('--model', default='convnext_tiny', type=str, metavar='MODEL',
                        help='Name of model to train')
    parser.add_argument('--drop_path', type=float, default=0, metavar='PCT',
                        help='Drop path rate (default: 0.0)')
    parser.add_argument('--input_size', default=384, type=int,
                        help='image input size')

    # Evaluation parameters
    parser.add_argument('--crop_pct', type=float, default=None)
    parser.add_argument('--pos_thr', type=list, default=[0.8, 0.55, 0.2])

    # Dataset parameters
    parser.add_argument('--nb_classes', default=3, type=int,
                        help='number of the classification types')
    parser.add_argument('--imagenet_default_mean_and_std', type=str2bool, default=True)
    parser.add_argument('--out_dir', default='demo_2',
                        help='path where to save, empty for no saving')
    parser.add_argument('--img_dir', default='images_2',
                        help='path where to save, empty for no saving')

    parser.add_argument('--ckpt', default='ckpt/checkpoint-best_t5.pth', help='resume from checkpoint')

    return parser

@torch.no_grad()
def demo(img_list, args):
    transform = build_transform(False, args)

    net = create_model(
        args.model,
        pretrained=False,
        num_classes=args.nb_classes,
        drop_path_rate=args.drop_path,
        )
    #net.load_state_dict(torch.load(args.ckpt)['model'])
    utils.load_state_dict(net, torch.load(args.ckpt), prefix='')
    net = net.to(device)
    net.eval()

    for path in tqdm(img_list):
        #pimg = Image.open(path).convert('RGB')
        pimg = transforms.ToPILImage()(cv2.imread(path))
        img = transform(pimg).to(device).unsqueeze(0)

        pred = net(img)
        cls = pred.view(-1).argmax().item()

        conf = torch.softmax(pred, dim=-1)[0, cls]

        print(path, cls, cls_names[cls], conf)

        if cls==0:
            if conf>0.8:
                os.makedirs(f'./{args.out_dir}/trash{cls}', exist_ok=True)
                copyfile(path, os.path.join(args.out_dir, f'trash{cls}', os.path.basename(path)[:-4]+'.png'))
                continue
        #pimg.save(os.path.join(out_dir, str(cls), os.path.basename(path)[:-4]+'.png'))
        copyfile(path, os.path.join(args.out_dir, cls_names[cls], os.path.basename(path)[:-4]+'.png'))

def get_imgs(root):
    root=Path(root)

    imgs = [str(x) for x in (root).iterdir() if str(x).lower().endswith('.jpg') or str(x).lower().endswith('.png')]
    return imgs

if __name__ == '__main__':
    parser = argparse.ArgumentParser('ConvNeXt demo script', parents=[get_args_parser()])
    args = parser.parse_args()

    for name in cls_names:
        os.makedirs(f'./{args.out_dir}/{name}', exist_ok=True)

    imgs=get_imgs(f'./{args.img_dir}/')
    #imgs=['./imgs/t1.jpg', './imgs/t2.jpg', './imgs/t3.jpg']

    demo(imgs, args)
