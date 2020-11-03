#!/usr/bin/env python3

import numpy as np

from rl.callbacks import Callback

class DQNHistory(Callback):
    def __init__(self):
        super(DQNHistory, self).__init__()
        self.metrics = []
        self.infos = []
        self.info_names = None
        self.history = {}
        self.episode = []

    def on_train_begin(self, logs=None):
        self.step = []

    def on_episode_end(self, episode, logs):
        self.episode.append(episode)

        metrics = np.array(self.metrics)
        if not np.isnan(metrics).all():  # not all values are means
            means = np.nanmean(self.metrics, axis=0)
            assert means.shape == (len(self.model.metrics_names),)
            for name, mean in zip(self.model.metrics_names, means):
                self.history.setdefault(name, []).append(mean)
        else:
            for name in self.model.metrics_names:
                self.history.setdefault(name, []).append(None)
        
        if len(self.infos) > 0:
            infos = np.array(self.infos)
            if not np.isnan(infos).all():  # not all values are means
                means = np.nanmean(self.infos, axis=0)
                assert means.shape == (len(self.info_names),)
                for name, mean in zip(self.info_names, means):
                    self.history.setdefault(name, []).append(mean)
            else:
                for name in self.model.info_names:
                    self.history.setdefault(name, []).append(None)

        self.history.setdefault("episode_rewards", []).append(logs["episode_reward"])

    def on_step_end(self, step, logs):
        if self.info_names is None:
            self.info_names = logs['info'].keys()

        self.metrics.append(logs['metrics'])
        if len(self.info_names) > 0:
            self.infos.append([logs['info'][k] for k in self.info_names])
