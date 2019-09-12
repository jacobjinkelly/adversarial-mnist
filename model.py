from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys
import os

from tensorflow.examples.tutorials.mnist import input_data
from scipy.misc import imsave

import tensorflow as tf

"""From Deep MNIST for experts tutorial:
https://www.tensorflow.org/get_started/mnist/pros
https://github.com/tensorflow/tensorflow/blob/r1.4/tensorflow/examples/tutorials/mnist/mnist_deep.py

"""

"""Helper functions for saving model checkpoints.
From https://jhui.github.io/2017/03/08/TensorFlow-variable-sharing/
"""
def load_model(session, saver, checkpoint_dir):
    session.run(tf.global_variables_initializer())
    ckpt = tf.train.get_checkpoint_state(checkpoint_dir)
    if ckpt and ckpt.model_checkpoint_path:
        ckpt_name = os.path.basename(ckpt.model_checkpoint_path)
        saver.restore(session, os.path.join(checkpoint_dir, ckpt_name))
        return True
    else:
        return False

def save_model(session, saver, checkpoint_dir, step):
    dir = os.path.join(checkpoint_dir, "model")
    saver.save(session, dir, global_step=step)

FLAGS = None

def deepnn(x):
    """deepnn builds the graph for a deep net for classifying digits.

    Args:
        x: an input tensor with the dimensions (N_examples, 784), where 784
        is the number of pixels in a standard MNIST image

    Returns:
        A tuple (y, keep_prob). y is a tensor of shape (N_examples, 10), with
        values equal to the logits of classifying the digits into one of 10
        classes (the digits 0-9). keep_prob is a scalar placeholder for the
        probability of dropout.
    """
    # Reshape to use within a cnn.
    # Last dimension is for "features" - there is only one here, since grayscale
    # First signifies any size (i.e. any batch size)
    with tf.name_scope('reshape'):
        x_image = tf.reshape(x, [-1, 28, 28, 1])

    # First convolutional layer - maps one grayscale (i.e. one feature map) to 32 feature maps
    with tf.name_scope('conv1'):
        W_conv1 = weight_variable([5, 5, 1, 32])
        b_conv1 = bias_variable([32])
        h_conv1 = tf.nn.relu(conv2d(x_image, W_conv1) + b_conv1)

    # Pooling layer - downsamples by 2X
    # i.e. our image size is now 14x14
    with tf.name_scope('pool1'):
        h_pool1 = max_pool_2x2(h_conv1)

    # Second convolutional layer - maps 32 feature maps to 64
    with tf.name_scope('conv2'):
        W_conv2 = weight_variable([5, 5, 32, 64])
        b_conv2 = bias_variable([64])
        h_conv2 = tf.nn.relu(conv2d(h_pool1, W_conv2) + b_conv2)

    # Second pooling layer
    # so our image size is now 7x7
    with tf.name_scope('pool2'):
        h_pool2 = max_pool_2x2(h_conv2)

    # Fully connected layer 1 -- after two rounds of downsampling, our 28x28
    # image is down to 7x7x64 feature maps -- maps this to 1024 features
    with tf.name_scope('fc1'):
        W_fc1 = weight_variable([7*7*64, 1024])
        b_fc1 = bias_variable([1024])

        h_pool2_flat = tf.reshape(h_pool2, [-1, 7*7*64])
        h_fc1 = tf.nn.relu(tf.matmul(h_pool2_flat, W_fc1) + b_fc1)

    # Dropout -- controls the complexity of the model, prevents co-adaptation
    # of features
    with tf.name_scope('dropout'):
        # placeholder so that we can turn dropout on during training, off during
        # test
        keep_prob = tf.placeholder(tf.float32)
        h_fc1_drop = tf.nn.dropout(h_fc1, keep_prob)

    # Map the 1024 features to 10 classes, one for each digit
    with tf.name_scope('fc2'):
        W_fc2 = weight_variable([1024, 10])
        b_fc2 = bias_variable([10])
        y_conv = tf.matmul(h_fc1_drop, W_fc2) + b_fc2

    return y_conv, keep_prob

# use stride of 1, zero padding (so input and output same dimension)
def conv2d(x, W):
    """conv2d returns a 2d convolution layer with full stride."""
    return tf.nn.conv2d(x, W, strides = [1, 1, 1, 1], padding = "SAME")

# pool over 2x2 blocks
def max_pool_2x2(x):
    """max_pool_2x2 downsamples a feature map by 2X"""
    return tf.nn.max_pool(x, ksize = [1, 2, 2, 1], strides = [1, 2, 2, 1],
                                                            padding = "SAME")

# Initialize weights with some noise for symmetry breaking and avoid 0 gradient
def weight_variable(shape):
    """weight_variable generates a weight variable of a given shape."""
    initial = tf.truncated_normal(shape, stddev = 0.1)
    return tf.Variable(initial)

# Initialize slightly positive bias because use ReLU
def bias_variable(shape):
    """bias_variable generates a bias variable of a given shape."""
    initial = tf.constant(0.1, shape = shape)
    return tf.Variable(initial)

def main(_):
    # Import data
    mnist = input_data.read_data_sets(FLAGS.data_dir, one_hot = True)

    # Create the model
    x = tf.placeholder(tf.float32, [None, 784])

    # Define loss and optimizer
    y_ = tf.placeholder(tf.float32, [None, 10])

    # Build the graph for the deepnet
    y_conv, keep_prob = deepnn(x)

    with tf.name_scope('loss'):
        cross_entropy = tf.nn.softmax_cross_entropy_with_logits(
            labels = y_,
            logits = y_conv
        )
    cross_entropy = tf.reduce_mean(cross_entropy)

    global_step = tf.Variable(0, name = "global_step", trainable = False, \
                                                            dtype = tf.int32)

    with tf.name_scope('adam_optimizer'):
        train_step = tf.train.AdamOptimizer(1e-4).minimize(cross_entropy, \
                                                    global_step = global_step)

    with tf.name_scope('accuracy'):
        correct_prediction = tf.equal(tf.argmax(y_, 1), tf.argmax(y_conv, 1))
        correct_prediction = tf.cast(correct_prediction, tf.float32)
    accuracy = tf.reduce_mean(correct_prediction)

    with tf.name_scope('correct_twos'):
        correct_prediction = tf.equal(tf.argmax(y_, 1), tf.argmax(y_conv, 1))
        is_two = tf.equal(tf.argmax(y_, 1), 2)
    correct_twos = tf.logical_and(correct_prediction, is_two)

    EPSILON = tf.constant(.25)
    ITERS = 100

    # save to disk, load in
    adversarial_ex = tf.Variable(mnist.test.images)

    adversarial_gradients = tf.gradients(xs = x, ys = cross_entropy)

    adversarial_ex_op = tf.assign(adversarial_ex, tf.squeeze(adversarial_ex +
                                 (EPSILON/tf.constant(float(ITERS))) * tf.sign(adversarial_gradients)))

    # using with block means tf.Session() automatically destroyed when exit
    with tf.Session() as sess:

        # create saver to restore and save variables into checkpoints
        saver = tf.train.Saver()

        # restores previous model, if there is one saved in a checkpoint
        load_model(sess, saver, "./checkpoint")

        while sess.run(global_step) <= 1000:

            batch = mnist.train.next_batch(50)

            if sess.run(global_step) % 100 == 0:
                train_accuracy = accuracy.eval(feed_dict =
                    {x: batch[0],
                    y_: batch[1],
                    keep_prob: 1}
                )
                print("step %d, train_accuracy %g" % (sess.run(global_step), \
                                                                train_accuracy))
                if sess.run(global_step) % 1000 == 0:
                    # save model in checkpoint
                    save_model(sess, saver, "./checkpoint", global_step)

            train_step.run(feed_dict =
                {x: batch[0],
                y_: batch[1],
                keep_prob: 0.5}
            )

        print('test accuracy %g' % accuracy.eval(feed_dict =
            {x: mnist.test.images,
            y_: mnist.test.labels,
            keep_prob: 1}
        ))

        for i in range(ITERS):
            print(i)
            sess.run(adversarial_ex_op, feed_dict = {x: sess.run(adversarial_ex),
                                                    y_: mnist.test.labels,
                                                    keep_prob: 1})

        # True iff example predicted correctly
        correct_prediction = tf.equal(tf.argmax(y_conv, 1), tf.argmax(y_, 1))
        # True iff example predicted with confidence >= 20%
        confidence = tf.greater_equal(tf.reduce_max(y_conv, 1), [50 for _ in range(len(mnist.test.labels))])

        # predict incorrectly with >= 20% confidence
        incorrect_confidence = tf.logical_and(tf.logical_not(correct_prediction), confidence)

        # original images predicted correctly
        original_prediction = correct_prediction.eval(feed_dict =
            {x: mnist.test.images,
            y_: mnist.test.labels,
            keep_prob: 1
        })

        # adversarially pertubed images predicted incorrectly w/ >=20% confidence
        adv_prediction = incorrect_confidence.eval(feed_dict =
            {x: sess.run(adversarial_ex),
            y_: mnist.test.labels,
            keep_prob: 1
        })

        # original predicted correctly, adversarial predicted incorrectly w/ >= 20% confidence
        successful_adv = tf.logical_and(original_prediction, adv_prediction)

        original_prediction_count = tf.count_nonzero(original_prediction)
        adv_prediction_count = tf.count_nonzero(adv_prediction)
        successful_adv_count = tf.count_nonzero(successful_adv)

        print(sess.run([original_prediction_count, adv_prediction_count, successful_adv_count]))

        # count the number of 'successful' adversarial examples
        # count = 0
        # successful_adv = successful_adv.eval()
        # for i in range(len(successful_adv)):
        #     if successful_adv[i]:
        #         count += 1
        # print (count)
        # only 1256, on higher confidences (>= 40%) get 0

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--data_dir', type=str,
                      default='/tmp/tensorflow/mnist/input_data',
                      help='Directory for storing input data')
  FLAGS, unparsed = parser.parse_known_args()
  tf.app.run(main=main, argv=[sys.argv[0]] + unparsed)
