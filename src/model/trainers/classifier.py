from typing import Tuple
from collections.abc import Callable
import torch as th
import torch.nn as nn
import pytorch_lightning as pl

from src.utils.metrics import accuracy, hard_label_from_logit


def _process_labelled_batch(batch, device) -> Tuple[int, th.Tensor, th.Tensor]:
    """Hack to handle multiple formats of dataloaders"""
    if isinstance(batch, dict):
        batch_size = batch["x"].size(0)
        x = batch["x"].to(device)
        y = batch["labels"].long().to(device)
    else:
        # Discard label
        x, y = batch
        x = x.to(device)
        y = y.long().to(device)
        batch_size = x.size(0)
    return batch_size, x, y


class DiffusionClassifier(pl.LightningModule):
    """Trainer for learning classification model p(y | x_t),
    where x_t is a noisy sample from a forward diffusion process."""

    def __init__(self, model: nn.Module, loss_f: Callable, noise_scheduler):
        super().__init__()
        self.model = model
        self.loss_f = loss_f
        self.noise_scheduler = noise_scheduler

        # Default Initialization
        self.train_loss = 0.0
        self.val_loss = 0.0
        self.val_acc = 0.0
        self.i_batch_train = 0
        self.i_batch_val = 0
        self.i_epoch = 0

    def training_step(self, batch, batch_idx):
        batch_size, x, y = _process_labelled_batch(batch, self.device)
        # Algorithm 1 line 3: sample t uniformally for every example in the batch
        T = self.noise_scheduler.time_steps.size(0)
        ts = th.randint(0, T, (batch_size,), device=self.device).long()

        noise = th.randn_like(x)
        x_noisy = self.noise_scheduler.q_sample(x_0=x, ts=ts, noise=noise)
        predicted_y = self.model(x_noisy, ts)
        loss = self.loss_f(predicted_y, y)
        self.log("train_loss", loss)
        self.train_loss += loss.detach().cpu().item()
        self.i_batch_train += 1
        return loss

    def on_train_epoch_end(self):
        print(" {}. Train Loss: {}".format(self.i_epoch, self.train_loss / self.i_batch_train))
        self.train_loss = 0.0
        self.i_batch_train = 0
        self.i_epoch += 1

    def configure_optimizers(self):
        optimizer = th.optim.Adam(self.parameters(), lr=1e-3)
        scheduler = th.optim.lr_scheduler.StepLR(optimizer, 1, gamma=0.99)
        return [optimizer], [scheduler]

    def validation_step(self, batch, batch_idx):
        batch_size, x, y = _process_labelled_batch(batch, self.device)

        rng_state = th.get_rng_state()
        th.manual_seed(self.i_batch_val)

        # Algorithm 1 line 3: sample t uniformally for every example in the batch
        T = self.noise_scheduler.time_steps.size(0)
        ts = th.randint(0, T, (batch_size,), device=self.device).long()

        noise = th.randn_like(x)
        th.set_rng_state(rng_state)

        x_noisy = self.noise_scheduler.q_sample(x_0=x, ts=ts, noise=noise)
        logits = self.model(x_noisy, ts)

        loss = self.loss_f(logits, y)
        acc = accuracy(hard_label_from_logit(logits), y)
        self.log("val_loss", loss)
        self.log("acc", acc)
        self.val_loss += loss.detach().cpu().item()
        self.val_acc += acc.detach().cpu().item()
        self.i_batch_val += 1
        return loss

    def on_validation_epoch_end(self):
        print(
            f" {self.i_epoch}. Validation Loss: {self.val_loss / self.i_batch_val}, Validation accuracy: {self.val_acc / self.i_batch_val}"
        )
        self.val_loss = 0.0
        self.val_acc = 0.0
        self.i_batch_val = 0
