import torch
from torch.autograd import Variable, Function
import torch.nn as nn
import numpy as np


# class bibdLinear(Function):
#     def __init__(self, mask):
#         super(bibdLinear, self).__init__()
#         self.mask = mask


#     @staticmethod
#     def forward(cxt, input, weight):
#         cxt.save_for_backward(input, weight)
#         extendWeights = weight.clone()
#         extendWeights.mul_(self.mask.data)
#         output = input.mm(extendWeights.t())
#         return output


#     @staticmethod
#     def backward(cxt, grad_output):
#         input, weight = cxt.saved_tensors
#         grad_input = grad_weight  = None
#         extendWeights = weight.clone()
#         extendWeights.mul_(self.mask.data)

#         if self.needs_input_grad[0]:
#             grad_input = grad_output.mm(extendWeights)
#         if self.needs_input_grad[1]:
#             grad_weight = grad_output.clone().t().mm(input)
#             grad_weight.mul_(self.mask.data)

#         return grad_input, grad_weight


class BibdLinear(torch.nn.Module):
    def __init__(self, input_features, output_features, number_of_block):
        super(BibdLinear, self).__init__()
        self.input_features = input_features
        self.output_features = output_features

        self.weight = nn.Parameter(data=torch.Tensor(output_features, input_features), requires_grad=True)

        self.mask = torch.from_numpy(generate_bibd_mask(number_of_block).T)

        self.mask =  self.mask.cuda()
        nn.init.kaiming_normal_(self.weight.data,mode='fan_in')
        self.mask =  nn.Parameter(self.mask.cuda())
        self.mask.requires_grad = False


    def forward(self, x):
        # return bibdLinear(self.mask)(x, self.weight)
        copy = self.weight.clone()
        copy.mul_(self.mask.data)
        return x.matmul(copy.t())


def generate_bibd_mask(r):
    '''
    Given r as a prime power, generate mask with size (r*(r+1), r*r)
    For example when r = 2, the mask is 
    [[1. 1. 0. 0.]
     [0. 0. 1. 1.]
     [1. 0. 1. 0.]
     [0. 1. 0. 1.]
     [1. 0. 0. 1.]
     [0. 1. 1. 0.]]
    '''

    mask = np.zeros([r * (r + 1), r * r])

    allgrids = []
    for k in range(1, r):
        grid = []
        for i in range(r):
            row = []
            for j in range(r):
                a = ((k * i + j) % r) + (r * i)
                row.append(a)
            grid.append(row)
        mols = np.array(grid).T
        allgrids.append(mols)

    for m in range(r):
        for n in range(r * m, r * m + r):
            mask[m][n] = 1

    for m in range(r, r * 2):
        for n in range(r):
            mask[m][(m - r) + r * n] = 1

    for m in range(r - 1):
        for n in range(r):
            for o in range(r):
                mask[r * (m + 2) + n][allgrids[m][n][o]] = 1
                
    return mask