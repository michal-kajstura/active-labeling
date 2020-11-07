import math
from typing import Dict

import pytorch_lightning as pl
import torch
import torch.nn.functional as F
from pytorch_lightning.metrics import Metric
from torch import nn
from torch.optim import Adam

from active_labeling.active_learning.models.monte_carlo_approximation import BAYESIAN_SAMPLE_DIM, \
    MonteCarloWrapper


class TrainingSystem(pl.LightningModule):
    def __init__(self,
                 model: MonteCarloWrapper,
                 metrics: Dict[str, Metric],
                 learning_rate: float = 1e-3):
        super().__init__()
        self._model = model
        self._loss = nn.CrossEntropyLoss()
        self.metrics = metrics
        self._learning_rate = learning_rate

    def forward(self, x, **kwargs):
        return self._model(x, **kwargs)

    def training_step(self, batch, batch_idx):
        images, labels = batch['image'], batch['label']
        logits = self.forward(images, sample_size=1).squeeze(BAYESIAN_SAMPLE_DIM)
        # logits = F.log_softmax(logits, dim=1)
        loss = self._loss(logits, labels)
        return loss

    def validation_step(self, batch, batch_idx):
        images, labels = batch['image'], batch['label']
        with torch.no_grad():
            logits = self.forward(images)
            # logits = F.log_softmax(logits, dim=1)
            # prediction = torch.logsumexp(
            #     logits, dim=BAYESIAN_SAMPLE_DIM) #- math.log(self._model.sample_size)

        y_pred = logits.argmax(-1)
        return y_pred.detach(), labels.detach()

    def on_validation_epoch_start(self) -> None:
        for metric in self.metrics.values():
            metric.reset()

    def validation_epoch_end(self, batches):
        for name, metric_func in self.metrics.items():
            for y_pred, y_true in batches:
                metric_func.update(y_pred, y_true)
            self.log(name, metric_func.compute())

    def configure_optimizers(self):
        return Adam(self._model.parameters(), lr=self._learning_rate)