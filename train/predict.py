from __future__ import division, print_function, absolute_import
import tensorflow as tf
import numpy as np
import collections
import os
import datetime as dt
import cPickle
from model import *
import argparse

#########################################
parser = argparse.ArgumentParser(description='predict')

## required
parser.add_argument('beta', type=float, help='2nd order regularizer')
parser.add_argument('dim', type=int, help='hidden dimension')
## optional
parser.add_argument('name', type=str, help='dataset name, e.g. earthquake, email, twitter rand-1, rand-2')


args = parser.parse_args()

b = args.beta
dim = args.dim
data_name = args.name

#####################################
if args.name == 'earthquake':
    N = 648
    sub_name = 'eq_1997-2018'
    dia = 13
elif args.name == 'email':
    N = 2634
    sub_name = 'enron_0'
    dia = 11
elif args.name == 'twitter':
    N = 393
    sub_name = 'safrica'
    dia = 8
elif args.name == 'rand-1':
    N = 291
    sub_name = 'rand_0'
    dia = 57
elif args.name == 'rand-2':
    N = 1599
    sub_name = 'rand_0'
    dia = 23
else:
    raise Exception('Unknown dataset. Please provide your own dataset.')


time_step = 32 # 32 events
n_window = 30 # 30 months (30 * 30 days)
batch_size = 1

num_layers_event = 2
hidden_size_event = dim
num_layers_bg = 2
hidden_size_bg = N
embedd_dim = dim

event_path = 'data/event_%s_test.pkl' % (sub_name)
model_path = 'checkpoint/%s' % (sub_name)
embedding_path = 'checkpoint/embedding.pkl'
shortest_path = 'data/shortest.pkl'
background_path = 'data/background_%s_test.pkl' % (sub_name)
timeseries_path = 'data/timeseries_%s.pkl' % (sub_name)



dist_fake_path = 'dist_fake.pkl'

dropout=0.5
init_scale=0.05

is_training = False

# 2nd order stat regulation
dvg = 'kl'
diameter = dia # graph diameter
scale = 0.1   # kde scale
ord = 2       # norm order
beta = b   # regulation weight


#################
# initialization
#################
tf.reset_default_graph()

with open(embedding_path, 'r') as file:
    embedd = cPickle.load(file)

with open(event_path, 'r') as file:
    event = cPickle.load(file)

with open(background_path, 'r') as file:
    background = cPickle.load(file)

with open(shortest_path, 'r') as file:
    shortest = cPickle.load(file)

with open(timeseries_path, 'r') as file:
    base_rate = cPickle.load(file)


input_obj = Input(event, background, batch_size)

m = Model(embedd, base_rate, shortest, is_training, batch_size, time_step, n_window, N,
            hidden_size_event, num_layers_event, hidden_size_bg, num_layers_bg,
            dropout=dropout, init_scale=init_scale,
            dvg=dvg, diameter=diameter, scale=scale, ord=ord, beta=beta)



init_op = tf.global_variables_initializer()

saver = tf.train.Saver()


##############
# testing
###################
with tf.Session() as sess:
    # restore the trained model
    saver.restore(sess, model_path)


    dist_fake = []
    seq_real_dist = []
    for step in range(input_obj.epoch_size):
        current_state_event = np.zeros((num_layers_event, 2, batch_size, hidden_size_event))
        current_state_bg = np.zeros((num_layers_bg, 2, batch_size, hidden_size_bg))

        next_example, next_label, next_bg = input_obj.next_batch()

        dist = sess.run(m.softmax_out, feed_dict={m.x:next_example, m.y:next_label, m.z:next_bg, m.init_state_event: current_state_event, m.init_state_bg: current_state_bg})

        dist = dist[-1]

        dist_fake.append(dist)


    with open(dist_fake_path, 'w') as file:
        cPickle.dump(np.array(dist_fake), file)

