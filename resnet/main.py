'''Train CIFAR10 with PyTorch.'''
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torch.backends.cudnn as cudnn

import torchvision
import torchvision.transforms as transforms

import os
import argparse

from models import *
from utils import progress_bar
from utils import format_time
from models.resnet_bibd import *
from models.resnet_gc import *
from models.resnet_bibd_gc import *
from models.resnet_exit import *

import time
import numpy as np


parser = argparse.ArgumentParser(description='PyTorch CIFAR10 Training')
parser.add_argument('--lr', default=0.1, type=float, help='learning rate')
parser.add_argument('--resume', '-r', action='store_true', help='resume from checkpoint')
parser.add_argument('--en', default=1, type=int, help='the number of the exits')
parser.add_argument('--epoch', default=30, type=int, help='the number of the exits')
args = parser.parse_args()
num_exit = args.en

device = 'cpu'

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print('Device: {}'.format(device))

best_acc = 0  # best test accuracy
start_epoch = 0  # start from epoch 0 or last checkpoint epoch

# Data
print('==> Preparing data..')
transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

trainset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=transform_train)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=128, shuffle=True, num_workers=2)

testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform_test)
testloader = torch.utils.data.DataLoader(testset, batch_size=100, shuffle=False, num_workers=2)

classes = ('plane', 'car', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck')

# Model
print('==> Building model..')
# net = VGG('VGG19')
# net = ResNet18()
# net = BResNet18()
# net = PreActResNet18()
# net = GoogLeNet()
# net = DenseNet121()
# net = ResNeXt29_2x64d()
# net = MobileNet()
# net = MobileNetV2()
# net = DPN92()
# net = ShuffleNetG2()
# net = SENet18()
# net = ShuffleNetV2(1)
# net = EfficientNetB0()
# net = ResNeXt29_2x64d_bibd()
# net = ResNet_gc()
# net = ResNet_bibd_gc() # If you want to run with groups = t, change the code of line 192 in bibd_layer.py with in Groups = t.
net = ResNet_3exit()
net = net.to(device)

print(net)

# This may not work on the CS280 AI cluster
if device == 'cuda':
    print('Running using torch.nn.DataParallel...')
    net = torch.nn.DataParallel(net)
    cudnn.benchmark = True


if args.resume:
    # Load checkpoint.
    print('==> Resuming from checkpoint..')
    assert os.path.isdir('checkpoint'), 'Error: no checkpoint directory found!'
    checkpoint = torch.load('./checkpoint/ckpt.pth')
    net.load_state_dict(checkpoint['net'])
    best_acc = checkpoint['acc']
    start_epoch = checkpoint['epoch']

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(net.parameters(), lr=args.lr, momentum=0.9, weight_decay=5e-4)


def train(epoch):
    print('\nEpoch: %d' % epoch)
    net.train()
    train_loss = 0
    correct = np.zeros(num_exit)
    total = 0
    for batch_idx, (inputs, targets) in enumerate(trainloader):
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = net(inputs)
        if type(outputs) == np.ndarray:
            assert outputs.shape[0] == num_exit, 'Error: Check the parameter en!'
            #mask = np.array([9 * 0.1 ** (num_exit - i) for i in range(num_exit)])
            #scores = outputs.dot(mask)
            scores = 0.9 * outputs[2] + 0.09 * outputs[1] + 0.009 * outputs[0]
            
        else:
            assert  num_exit == 1, 'Error: Check the parameter en!'
            scores = outputs
        # if batch_idx == 1:
        #     print ('scores.size:', scores.size())
        
        loss = criterion(scores, targets)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()
        
        if num_exit == 1:
            _, predicted = outputs.max(1)
            correct[0] += predicted.eq(targets).sum().item()
        else:
            for i in range(num_exit):
                _, predicted = outputs[i].max(1)
                correct[i] += predicted.eq(targets).sum().item()
            
        total += targets.size(0)
        
        msg = 'Loss: %.2f' % (train_loss / (batch_idx + 1))
        for i in range(num_exit):
            msg = msg + '| Ex%d: %.2f%%' % (i + 1, 100. * correct[i] / total)

        progress_bar(batch_idx, len(trainloader), msg)


def test(epoch):
    global best_acc
    net.eval()
    test_loss = 0
    correct = np.zeros(num_exit)
    total = 0
    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(testloader):
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = net(inputs)
            scores = outputs.sum(axis = 0)
            
            if num_exit == 1:
                _, predicted = outputs.max(1)
                correct[0] += predicted.eq(targets).sum().item()
            else:
                for i in range(num_exit):
                    _, predicted = outputs[i].max(1)
                    correct[i] += predicted.eq(targets).sum().item()
                
            total += targets.size(0)
         
        msg = ''
        for i in range(num_exit):
            msg = msg + '| Ex%d Acc: %.2f%%' % (i + 1, 100. * correct[i] / total)
        print(msg)
        
    # Save checkpoint
    acc = 100.0 * correct[num_exit-1] / total
    if acc > best_acc:
        print('Saving...')
        state = {
            'net': net.state_dict(),
            'acc': acc,
            'epoch': epoch,
        }
        if not os.path.isdir('checkpoint'):
            os.mkdir('checkpoint')
        torch.save(state, './checkpoint/ckpt.pth')
        best_acc = acc

begin_time = time.time()
for ep in range(start_epoch, start_epoch+args.epoch):
    train(ep)
    test(ep)
end_time = time.time()
print('Total time usage: {}'.format(format_time(end_time - begin_time)))
