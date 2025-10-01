from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np
from sklearn.model_selection import StratifiedKFold
from scipy import stats


@dataclass
class CrossValResult:
    folds: int
    accuracies: List[float]
    mean_accuracy: float
    ci95: Tuple[float, float]


def stratified_cv_accuracy(
    texts: List[str],
    labels: List[str],
    predict_fn,
    fit_fn=None,
    folds: int = 5,
    random_state: int = 42
) -> CrossValResult:
    """
    Generic stratified cross-validation for a (fit, predict) text classifier.
    predict_fn: callable(model, X) -> y_pred
    fit_fn: callable(X_train, y_train) -> model
    If fit_fn is None, predict_fn must internally handle training per fold.
    """
    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=random_state)
    accuracies: List[float] = []

    X = np.array(texts)
    y = np.array(labels)

    for train_idx, test_idx in skf.split(X, y):
        X_train, X_test = X[train_idx].tolist(), X[test_idx].tolist()
        y_train, y_test = y[train_idx].tolist(), y[test_idx].tolist()

        if fit_fn is not None:
            model = fit_fn(X_train, y_train)
            y_pred = predict_fn(model, X_test)
        else:
            y_pred = predict_fn(X_train, y_train, X_test)

        acc = (np.array(y_pred) == np.array(y_test)).mean() if y_test else 0.0
        accuracies.append(float(acc))

    mean_acc = float(np.mean(accuracies)) if accuracies else 0.0
    ci = mean_confidence_interval(accuracies)
    return CrossValResult(folds=folds, accuracies=accuracies, mean_accuracy=mean_acc, ci95=ci)


def mean_confidence_interval(data: List[float], confidence: float = 0.95) -> Tuple[float, float]:
    if not data:
        return (0.0, 0.0)
    a = np.array(data, dtype=float)
    n = len(a)
    m = np.mean(a)
    se = stats.sem(a) if n > 1 else 0.0
    h = se * stats.t.ppf((1 + confidence) / 2., n - 1) if n > 1 else 0.0
    return (float(m - h), float(m + h))


def mcnemar_test(contingency: List[List[int]]) -> Dict[str, Any]:
    """
    McNemar's test for paired nominal data (e.g., two classifiers on the same items).
    contingency = [[a, b], [c, d]] where:
      a: both correct, b: model1 correct only, c: model2 correct only, d: both wrong
    """
    table = np.array(contingency)
    b = table[0, 1]
    c = table[1, 0]
    statistic = (abs(b - c) - 1)**2 / (b + c) if (b + c) > 0 else 0.0
    p_value = 1 - stats.chi2.cdf(statistic, df=1) if (b + c) > 0 else 1.0
    return {
        'statistic': float(statistic),
        'p_value': float(p_value)
    }








