#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 12:50:21 2019

@author: peterawest
"""

import random
import torch
import numpy as np
import math


from torch import nn
MAX_LENGTH = 100
sm = torch.nn.Softmax(dim=0)



sig = torch.nn.Sigmoid()




sig = torch.nn.Sigmoid()


class LogReg_PT(nn.Module):
    def __init__(self, input_dim, PW = False):
        super(LogReg_PT, self).__init__()
        
        self.PW = PW
        
        if self.PW:
            self.linear = torch.nn.Linear(input_dim + 1, 1)
        else:
            self.linear = torch.nn.Linear(input_dim, 1)
        
    def forward(self, x):
        
        if self.PW:
            input_tens = torch.cat([torch.tensor(x[0]).float(),torch.tensor([x[1]]).float()] )
            outputs = self.linear(input_tens)
            
        else:
            outputs = self.linear(torch.tensor(x).float())
        return sig(outputs)
        

class LogReg_PT_propensity_model():
    
    def __init__(self, n_it = 100000, val_interval = 1000, batch_size = 1, lr = 0.001, input_dim = 768,
                 experiment_name = 'LR', PW = False):
        self.model = LogReg_PT(input_dim,PW = PW)
        
        self.batch_size = batch_size
        self.val_interval = val_interval
        self.n_it = n_it # number of training iterations
        self.lr = lr
        
        assert(val_interval < n_it)
        
        self.experiment_name = experiment_name
    
    def fit(self, dataset):
        self.learning_curve = []
        opt = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        opt.zero_grad()
        
        min_val_loss = None
        
        
        ### loop over sgd iterations
        for it, (x,label,_) in enumerate(dataset.train_epoch(size=self.n_it)):
            
#            ex = random.randint(0, len(X_train) - 1)
#            x = X_train[ex]
#            label = Z_train[ex]
            
            
            logit = self.model.forward(x)
            loss = -(float(label)*torch.log(logit) + float(1-label)*torch.log(1-logit))
            
            if math.isnan(loss.item()):
                
                print('Is NAN! iteration: {}',format(it))
                
                self.lr = self.lr/2.
                print('reloading model, dropping lr to {}'.format(self.lr))
                self.load_best()
                opt = torch.optim.Adam(self.model.parameters(), lr=self.lr)
                opt.zero_grad()
                
                continue
            
            loss.backward()
            
            if (it % self.batch_size == 0) and it > 0:
                torch.cuda.empty_cache()
                opt.step()
                opt.zero_grad()
                torch.cuda.empty_cache()
                
            if (it % self.val_interval == 0):
                torch.cuda.empty_cache()
                with torch.no_grad():
                    #print('starting validation')
                    val_loss = 0
                    for val_i, (x, label,_)  in enumerate(dataset.valid_epoch()):
#                        x = X_val[val_i]
#                        label = Z_val[val_i]

                        logit = self.model.forward(x)
                        loss = -(float(label)*torch.log(logit) + float((1-label))*torch.log(1-logit))

                        val_loss += float(loss.item())
                    self.learning_curve += [val_loss]

                    #print('val_loss: {}'.format(val_loss))
                    if min_val_loss is None or val_loss < min_val_loss:
                        min_val_loss = val_loss
                        self.save_best()
#                        torch.save(self.model.state_dict(),'best.pt')
                    elif val_loss > 1.5*min_val_loss:
                        break
                    
                
        self.load_best()
        
    def load_best(self):
        self.model.load_state_dict(torch.load('{}_best.pt'.format(self.experiment_name)))
        
    def save_best(self):
        torch.save(self.model.state_dict(),'{}_best.pt'.format(self.experiment_name)) 
        
    def score(self, X):
        n_ex = len(X)
        scores = np.zeros(n_ex)
        
        
        for i in range(len(X)):
            x = X[i]

            with torch.no_grad():
                logit = self.model.forward(x).item()
            scores[i] = logit
        return scores
                    
