"""Classification utils"""
import torch as th
import torch.nn.functional as F


@th.no_grad()
def accuracy(y_true: th.Tensor, y_pred: th.Tensor) -> float:
    """Compute accuracy of class predictions

    Args:
        y_true: (batch_size,)
        y_pred: (batch_size,)

    Returns:
        acc: average accuracy
    """
    accs = y_true == y_pred
    return accs.float().mean().item()


@th.no_grad()
def entropy(prob_vec: th.Tensor) -> float:
    """Compute entropy of a probability vector

    Args:
        prob_vec: (batch_size, num_classes)

    Returns:
        average entropy
    """
    entropy = -th.sum(prob_vec * th.log(prob_vec), dim=1)
    return entropy.mean().item()


def logits_to_log_prob(logits):
    """Convert logits to log probability vector

    Args:
        logits: (batch_size, num_classes) in R^n

    Returns:
        log_prob_vec: (batch_size, num_classes)
    """
    return F.log_softmax(logits, dim=1)


@th.no_grad()
def logits_to_label(logits):
    """Convert logits to hard label

    Args:
        logits: (batch_size, num_classes)

    Returns:
        labels: (batch_size, num_classes)
    """
    return th.argmax(logits, dim=1)
