#!/usr/bin/env python3

import numpy as np

from rl.callbacks import Callback

class DQNHistory(Callback):
    def __init__(self):
        super(DQNHistory, self).__init__()
        self.history = {}
        self.episode = []
        self.current_step = 0

    def on_episode_end(self, episode, logs):
        self.episode.append(episode)
        self.history.setdefault("episode_rewards", []).append(logs["episode_reward"])
        self.history.setdefault("loss", []).append(logs["val_loss"])
        self.history.setdefault("mae", []).append(logs["mae"])
        self.history.setdefault("mean_q", []).append(logs["mean_q"])
        self.history.setdefault("mean_eps", []).append(logs["mean_eps"])

    def on_step_end(self, step, logs):
        self.current_step += 1
