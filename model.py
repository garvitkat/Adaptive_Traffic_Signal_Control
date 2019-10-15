import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'  # kill warning about tensorflow
import random
import numpy as np
import keras
from collections import deque
from keras.layers import Input, Conv2D, Flatten, Dense
from keras.models import Model

class DQNAgent:
    def __init__(self):
        self.gamma = 0.75   # discount rate
        self.epsilon = 0.1  # exploration rate
        self.learningRate = 0.001
        self.memory = deque(maxlen=200)
        self.model = self.model_build()
        self.actionSize = 2

    def model_build(self):
        # Neural Net for Deep-Q learning Model
        input1 = Input(shape=(12, 12, 1))
        x1 = Conv2D(16, (4, 4), strides=(2, 2), activation='relu')(input1)
        x1 = Conv2D(32, (2, 2), strides=(1, 1), activation='relu')(x1)
        x1 = Flatten()(x1)

        input2 = Input(shape=(12, 12, 1))
        x2 = Conv2D(16, (4, 4), strides=(2, 2), activation='relu')(input2)
        x2 = Conv2D(32, (2, 2), strides=(1, 1), activation='relu')(x2)
        x2 = Flatten()(x2)

        input3 = Input(shape=(2, 1))
        x3 = Flatten()(input3)

        x = keras.layers.concatenate([x1, x2, x3])
        x = Dense(128, activation='relu')(x)
        x = Dense(64, activation='relu')(x)
        x = Dense(2, activation='linear')(x)

        model = Model(inputs=[input1, input2, input3], outputs=[x])
        model.compile(optimizer=keras.optimizers.RMSprop(
            lr=self.learningRate), loss='mse')

        return model

    def remeberState(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.actionSize)
        actualValues = self.model.predict(state)

        return np.argmax(actualValues[0])  # returns action

    def replay(self, batch_size):
        minibatch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            target = reward
            if not done:
                target = (reward + self.gamma *
                          np.amax(self.model.predict(next_state)[0]))
            target_f = self.model.predict(state)
            target_f[0][action] = target
            self.model.fit(state, target_f, epochs=1, verbose=0)

    def load(self, name):
        self.model.load_weights(name)

    def save(self, name):
        self.model.save_weights(name)