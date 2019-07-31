import tensorflow as tf
import numpy as np
import cPickle
import ipdb
class Detector():
    def __init__(self, weight_file_path, n_labels, trainable=True):
        self.image_mean = [103.939, 116.779, 123.68]
        self.n_labels = n_labels
        self.trainable = trainable

        with open(weight_file_path) as f:
            self.pretrained_weights = cPickle.load(f)

    def get_weight( self, layer_name):
        layer = self.pretrained_weights[layer_name]
        return layer[0]

    def get_bias( self, layer_name ):
        layer = self.pretrained_weights[layer_name]
        return layer[1]

    def get_conv_weight( self, name ):
        f = self.get_weight( name )
        return f.transpose(( 2,3,1,0 ))

    def conv_layer( self, bottom, name ):
        with tf.variable_scope(name) as scope:

            w = self.get_conv_weight(name)
            b = self.get_bias(name)

            conv_weights = tf.get_variable(
                    "W",
                    shape=w.shape,
                    initializer=tf.constant_initializer(w)
                    )
            conv_biases = tf.get_variable(
                    "b",
                    shape=b.shape,
                    initializer=tf.constant_initializer(b)
                    )

            conv = tf.nn.conv2d( bottom, conv_weights, [1,1,1,1], padding='SAME')
            bias = tf.nn.bias_add( conv, conv_biases )
            relu = tf.nn.relu( bias, name=name )

        return relu

    def new_conv_layer( self, bottom, filter_shape, name ):
        with tf.variable_scope( name ) as scope:
            w = tf.get_variable(
                    "W",
                    shape=filter_shape,
                    initializer=tf.random_normal_initializer(0., 0.01))
            b = tf.get_variable(
                    "b",
                    shape=filter_shape[-1],
                    initializer=tf.constant_initializer(0.))

            conv = tf.nn.conv2d( bottom, w, [1,1,1,1], padding='SAME')
            bias = tf.nn.bias_add(conv, b)

        return bias #relu

    def fc_layer(self, bottom, name, create=False):
        shape = bottom.get_shape().as_list()
        # dim = np.prod( shape[1:] )
        dim = 1
        for d in shape[1:]:
            dim *= d
        x = tf.reshape(bottom, [-1, dim])

        cw = self.get_weight(name)
        b = self.get_bias(name)

        if name == "fc6":
            cw = cw.reshape((4096, 512, 7,7))
            cw = cw.transpose((2,3,1,0))
            cw = cw.reshape((25088,4096))
        else:
            cw = cw.transpose((1,0))

        with tf.variable_scope(name) as scope:
            cw = tf.get_variable(
                    "W",
                    shape=cw.shape,
                    initializer=tf.constant_initializer(cw))
            b = tf.get_variable(
                    "b",
                    shape=b.shape,
                    initializer=tf.constant_initializer(b))

            fc = tf.nn.bias_add( tf.matmul( x, cw ), b, name=scope.name)
        #fc = tf.nn.bias_add( tf.matmul( x, cw ), b)
        # weights = self.get_weight(name)
        # biases = self.get_bias(name)

        # # Fully connected layer. Note that the '+' operation automatically
        # # broadcasts the biases.
        # fc = tf.nn.bias_add(tf.matmul(x, weights), biases)
        #print('name:', name, 'shape:', np.shape(fc))
        return fc

    def new_fc_layer( self, bottom, input_size, output_size, name ):
        shape = bottom.get_shape().to_list()
        dim = np.prod( shape[1:] )
        x = tf.reshape( bottom, [-1, dim])

        with tf.variable_scope(name) as scope:
            w = tf.get_variable(
                    "W",
                    shape=[input_size, output_size],
                    initializer=tf.random_normal_initializer(0., 0.01))
            b = tf.get_variable(
                    "b",
                    shape=[output_size],
                    initializer=tf.constant_initializer(0.))
            fc = tf.nn.bias_add( tf.matmul(x, w), b, name=scope.name)

        return fc

    def inference( self, rgb, train_mode=False ):
        rgb *= 255.0
        r, g, b = tf.split(rgb, 3, 3)
        bgr = tf.concat(
            [
                b-self.image_mean[0],
                g-self.image_mean[1],
                r-self.image_mean[2]
            ], 3)

        relu1_1 = self.conv_layer( bgr, "conv1_1" )
        relu1_2 = self.conv_layer( relu1_1, "conv1_2" )

        pool1 = tf.nn.max_pool(relu1_2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1],
                                         padding='SAME', name='pool1')

        relu2_1 = self.conv_layer(pool1, "conv2_1")
        relu2_2 = self.conv_layer(relu2_1, "conv2_2")
        pool2 = tf.nn.max_pool(relu2_2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1],
                               padding='SAME', name='pool2')

        relu3_1 = self.conv_layer( pool2, "conv3_1")
        relu3_2 = self.conv_layer( relu3_1, "conv3_2")
        relu3_3 = self.conv_layer( relu3_2, "conv3_3")
        pool3 = tf.nn.max_pool(relu3_3, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1],
                               padding='SAME', name='pool3')

        relu4_1 = self.conv_layer( pool3, "conv4_1")
        relu4_2 = self.conv_layer( relu4_1, "conv4_2")
        relu4_3 = self.conv_layer( relu4_2, "conv4_3")
        pool4 = tf.nn.max_pool(relu4_3, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1],
                               padding='SAME', name='pool4')

        relu5_1 = self.conv_layer( pool4, "conv5_1")
        relu5_2 = self.conv_layer( relu5_1, "conv5_2")
        relu5_3 = self.conv_layer( relu5_2, "conv5_3")
        pool5 = tf.nn.max_pool(relu5_3, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1],
                               padding='SAME', name='pool5')
        #print('name:','relu5_3', "shape:", np.shape(relu5_3))
        #print('name:','pool5', "shape:", np.shape(pool5))

        fc6 = self.fc_layer(pool5, "fc6")
        assert fc6.get_shape().as_list()[1:] == [4096]
        relu6 = tf.nn.relu(fc6)

        if train_mode is not False:
            relu6 = tf.cond(train_mode, lambda: tf.nn.dropout(relu6, 0.5), lambda: relu6)
        elif self.trainable:
            relu6 = tf.nn.dropout(relu6, 0.5)


        fc7 = self.fc_layer(relu6, "fc7")
        relu7 = tf.nn.relu(fc7)

        if train_mode is not False:
            relu7 = tf.cond(train_mode, lambda: tf.nn.dropout(relu7, 0.5), lambda: relu7)
        elif self.trainable:
            relu7 = tf.nn.dropout(relu7, 0.5)

        fc8 = self.fc_layer(relu7, "fc8")

        # prob = tf.nn.softmax(fc8, name="prob")
        # Old version	
        # conv6 = self.new_conv_layer( relu5_3, [3,3,512,1024], "conv6") # [filter_height * filter_width * in_channels, output_channels].
        # print(np.shape(conv6)) #(?, 14, 14, 1024)
        # gap = tf.reduce_mean( conv6, [1,2] )
        # print(np.shape(gap)) #(?, 1024) reduce axis=1 and axis=2 by calculating mean
        
        # phai tao moi vi trong pre-trained model khong co GAP
        with tf.variable_scope("GAP"):
            gap_w = tf.get_variable(
                    "W",
                    shape=[1000, self.n_labels],
                    initializer=tf.random_normal_initializer(0., 0.01))

        output = tf.matmul( fc8, gap_w)

        return pool1, pool2, pool3, pool4, relu5_3, fc8, output

    def get_classmap(self, label, conv5):
        conv5_resized = tf.image.resize_bilinear( conv5, [224, 224] )
        with tf.variable_scope("GAP", reuse=True):
            label_w = tf.gather(tf.transpose(tf.get_variable("W")), label)
            label_w = tf.reshape( label_w, [-1, 1000, 1] ) # [batch_size, 1024, 1]

        conv5_resized = tf.reshape(conv5_resized, [-1, 224*224, 1000]) # [batch_size, 224*224, 1024]

        classmap = tf.matmul( conv5_resized, label_w )
        classmap = tf.reshape( classmap, [-1, 224,224] )
        return classmap






