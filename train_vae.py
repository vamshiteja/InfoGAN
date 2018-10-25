import numpy as np
import tensorflow as tf

import argparse
import time
import os
import cPickle
import pickle
import cv2

from model.conv_vae import ConvVAE

from utils.loader import load_batched_data

os.environ['CUDA_VISIBLE_DEVICES'] = '1'


def load_mammo_data(datapath):
  '''
    Function to load data
  '''
  with open(datapath,"rb") as f:
    data = pickle.load(f)

  normal = np.array(data['normal'])
  cancer = np.array(data['cancer'])
  data = np.concatenate((normal,cancer),axis=0)
  return data

def load_kaggle_data(datapath):
  '''
    Function to load data
  '''
  with open(datapath,"rb") as f:
    data = pickle.load(f)

  a = np.array(data['1'])
  b = np.array(data['2'])
  c = np.array(data['3'])
  data = np.concatenate((a,b,c),axis=0)
  return data

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--training_epochs', type=int, default=300,
                     help='training epochs')
  parser.add_argument('--display_step', type=int, default=5,
                     help='display step')
  parser.add_argument('--checkpoint_step', type=int, default=5,
                     help='checkpoint step')
  parser.add_argument('--batch_size', type=int, default=64,
                     help='batch size')
  parser.add_argument('--z_dim', type=int, default=100,
                     help='z dim')
  parser.add_argument('--learning_rate', type=float, default=0.0002,
                     help='learning rate')
  parser.add_argument('--dataset', type=str, default='mammo',
                      help='dataset')
  parser.add_argument('--imsize', type=int, default=256,
                      help='imsize')
  parser.add_argument('--num_channels', type=int, default=3,
                      help='num_channels')
  parser.add_argument('--std', type=float, default=0.0,
                      help='num_channels')
  parser.add_argument('--restore',type=int, default=0, help='restore')
  args = parser.parse_args()
  return train(args)

def train(args):

  learning_rate = args.learning_rate
  batch_size = args.batch_size
  training_epochs = args.training_epochs
  display_step = args.display_step
  checkpoint_step = args.checkpoint_step # save training results every check point step
  z_dim = args.z_dim # number of latent variables.

  dataset = args.dataset
  imsize  = args.imsize

  if(dataset=='mammo'):
    datapath = "./datasets/mammo_cancer/dataset_mammo_train_"+str(imsize)+".pickle"
    data = load_mammo_data(datapath)
  elif(dataset=='kaggle'):
    datapath = "./datasets/kaggle_cancer/dataset_kaggle_train_"+str(imsize)+".pickle"
    data = load_kaggle_data(datapath)

  checkpoint_dir = "./checkpoints/vae"
  if not os.path.exists(checkpoint_dir):
    os.makedirs(checkpoint_dir)

  #with open(os.path.join(dirname, 'config.pkl'), 'w') as f:
   # cPickle.dump(args, f)

  vae = ConvVAE(learning_rate=learning_rate, imsize=imsize,batch_size=batch_size, z_dim = z_dim, args=args)

  n_samples = data.shape[0]

  # load previously trained model if appilcable
  checkpoint_dir = "./checkpoints/vae"
  ckpt = tf.train.get_checkpoint_state(checkpoint_dir)
  if ckpt and args.restore:
    vae.load_model(checkpoint_dir)

  # Training cycle
  for epoch in range(training_epochs):
    avg_cost = 0.
    total_batch = int(n_samples / batch_size)
    # Loop over all batches
    for i in range(total_batch):
      batch_xs = next(load_batched_data(data,args.batch_size,args.imsize,args.num_channels))
      for j in range(args.batch_size):
    batch_xs[j] = (batch_xs[j]+1.0)/2.0
      # Fit training using batch data
      cost, l2_loss, kl_loss = vae.partial_fit(batch_xs)
      
      # Display logs per epoch step
      if i % display_step == 0:
        print "Epoch:", '%04d' % (epoch+1), \
              "batch:", '%04d' % (i), \
        "cost:" , "{:.6f}".format(cost), \
              "l2_loss =", "{:.6f}".format(l2_loss), \
              "kl_loss =", "{:.6f}".format(kl_loss)
  
  recons = vae.reconstruct(batch_xs)
  for j in range(args.batch_size):
    img_d = recons[j]*255.0
    img_d = img_d.astype(int)
          img_d = img_d.astype(np.uint8)
    act   = batch_xs[j]*255.0
    act   = act.astype(int)
        act   = act.astype(np.uint8)
    if not os.path.exists("out/vae_"+args.dataset+"_"+str(args.std)):
      os.makedirs("out/vae_"+args.dataset+"_"+str(args.std))
    cv2.imwrite('out/vae_{}_{}/iter_{}_{}_recons.png'.format(args.dataset, args.std,str(epoch),str(j)),img_d)
    cv2.imwrite('out/vae_{}_{}/iter_{}_{}_actual.png'.format(args.dataset, args.std,str(epoch),str(j)),act)
  
      # Compute average loss
      avg_cost += cost / n_samples * batch_size

    # Display logs per epoch step
    print "Epoch:", '%04d' % (epoch+1), \
          "cost=", "{:.6f}".format(avg_cost)

    # save model
    if epoch > 0 and epoch % checkpoint_step == 0:
      checkpoint_path = os.path.join(checkpoint_dir, dataset+'_model.ckpt')
      vae.save_model(checkpoint_path, epoch)
      print "model saved to {}".format(checkpoint_path)

  # save model one last time, under zero label to denote finish.
  vae.save_model(checkpoint_path, 0)

  return vae

if __name__ == '__main__':
  main()
