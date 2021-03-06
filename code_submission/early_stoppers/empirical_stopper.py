from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

import numpy as np

from early_stoppers import Stopper

logger = logging.getLogger('code_submission')

# current implementation: run WINDOW_SIZE steps at least
WINDOW_SIZE = 20


class EmpiricalStopper(Stopper):

    def __init__(self, min_step=30, max_step=500):
        self._min_step = max(min_step, WINDOW_SIZE)
        self._max_step = max_step
        self.performance_windows = [None for i in range(WINDOW_SIZE)]
        self.index = 0
        self.max_acc = -float('inf')
        super(EmpiricalStopper, self).__init__()

    def should_early_stop(self, train_info, valid_info):
        self._cur_step += 1
        self.max_acc = max(self.max_acc, valid_info['accuracy'])
        cur_performance = -valid_info['loss']
        # cur_performance = valid_info['accuracy']
        if self._cur_step > self._min_step and \
                cur_performance < np.mean(self.performance_windows):
            logger.info("early stop at {} epoch".format(self._cur_step))
            return True
        self.performance_windows[self.index] = cur_performance
        self.index = (self.index + 1) % WINDOW_SIZE
        return self._cur_step >= self._max_step

    def should_log(self, train_info, valid_info):
        return valid_info['accuracy'] > self.max_acc

    def reset(self):
        self._cur_step = 0
        self.index = 0
        self.performance_windows = [None for i in range(WINDOW_SIZE)]
        self.max_acc = -float('inf')
