import numpy as np
from typing import List, Dict, Tuple, Any
from sklearn.metrics import roc_curve, auc, precision_recall_curve
from sklearn.preprocessing import label_binarize
from sklearn.model_selection import learning_curve
import scipy.stats as stats
from scipy.stats import ttest_rel, wilcoxon, mannwhitneyu


class StatisticalAnalyzer:
    def __init__(self):
        self.significance_level = 0.05

    def calculate_roc_auc_multiclass(self, y_true: List[str], y_pred_proba: np.ndarray, classes: List[str]) -> Dict[str, float]:
        y_idx = [classes.index(y) if y in classes else 0 for y in y_true]
        y_true_bin = label_binarize(y_idx, classes=list(range(len(classes))))
        roc_auc_scores: Dict[str, float] = {}
        for i, class_name in enumerate(classes):
            if y_true_bin.shape[1] > 1:
                fpr, tpr, _ = roc_curve(y_true_bin[:, i], y_pred_proba[:, i])
                roc_auc_scores[class_name] = float(auc(fpr, tpr))
            else:
                fpr, tpr, _ = roc_curve(y_true_bin, y_pred_proba)
                roc_auc_scores[class_name] = float(auc(fpr, tpr))
        return roc_auc_scores

    def perform_power_analysis(self, effect_size: float, alpha: float = 0.05, power: float = 0.8) -> int:
        from statsmodels.stats.power import TTestIndPower
        calc = TTestIndPower()
        n = calc.solve_power(effect_size=effect_size, alpha=alpha, power=power, alternative='two-sided')
        return int(np.ceil(n)) if n else 0

    def compare_classifiers_statistical(self, results1: List[float], results2: List[float], paired: bool = True) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            'mean_diff': float(np.mean(results1) - np.mean(results2)),
            'std_diff': float(np.std(np.array(results1) - np.array(results2))) if paired else None,
            'effect_size': float(self._calculate_cohens_d(results1, results2)),
            'statistical_tests': {}
        }
        if paired:
            t_stat, t_p = ttest_rel(results1, results2)
            res['statistical_tests']['paired_t_test'] = {'statistic': float(t_stat), 'p_value': float(t_p), 'significant': bool(t_p < self.significance_level)}
            w_stat, w_p = wilcoxon(results1, results2)
            res['statistical_tests']['wilcoxon_test'] = {'statistic': float(w_stat), 'p_value': float(w_p), 'significant': bool(w_p < self.significance_level)}
        else:
            t_stat, t_p = stats.ttest_ind(results1, results2)
            res['statistical_tests']['independent_t_test'] = {'statistic': float(t_stat), 'p_value': float(t_p), 'significant': bool(t_p < self.significance_level)}
            u_stat, u_p = mannwhitneyu(results1, results2, alternative='two-sided')
            res['statistical_tests']['mann_whitney_u'] = {'statistic': float(u_stat), 'p_value': float(u_p), 'significant': bool(u_p < self.significance_level)}
        return res

    def _calculate_cohens_d(self, group1: List[float], group2: List[float]) -> float:
        mean1, mean2 = np.mean(group1), np.mean(group2)
        std1, std2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
        n1, n2 = len(group1), len(group2)
        pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2)) if (n1 + n2 - 2) > 0 else 0.0
        if pooled_std == 0:
            return 0.0
        return float((mean1 - mean2) / pooled_std)

    def generate_learning_curves(self, estimator, X, y, cv=5, scoring='accuracy'):
        train_sizes, train_scores, val_scores = learning_curve(estimator, X, y, cv=cv, scoring=scoring, n_jobs=-1, train_sizes=np.linspace(0.1, 1.0, 10))
        return {
            'train_sizes': train_sizes.tolist(),
            'train_scores': {'mean': np.mean(train_scores, axis=1).tolist(), 'std': np.std(train_scores, axis=1).tolist()},
            'validation_scores': {'mean': np.mean(val_scores, axis=1).tolist(), 'std': np.std(val_scores, axis=1).tolist()}
        }

    def calculate_confidence_intervals_bootstrap(self, data: np.ndarray, statistic_func=np.mean, confidence_level: float = 0.95, n_bootstrap: int = 1000) -> Dict[str, float]:
        rng = np.random.default_rng(42)
        stats_samples = [float(statistic_func(rng.choice(data, size=len(data), replace=True))) for _ in range(n_bootstrap)]
        alpha = 1 - confidence_level
        return {
            'statistic': float(statistic_func(data)),
            'lower_ci': float(np.percentile(stats_samples, (alpha/2) * 100)),
            'upper_ci': float(np.percentile(stats_samples, (1 - alpha/2) * 100)),
            'confidence_level': confidence_level
        }

    def perform_permutation_test(self, group1: List[float], group2: List[float], n_permutations: int = 1000) -> Dict[str, Any]:
        observed_diff = float(np.mean(group1) - np.mean(group2))
        combined = np.array(group1 + group2)
        rng = np.random.default_rng(42)
        diffs = []
        for _ in range(n_permutations):
            rng.shuffle(combined)
            perm1 = combined[:len(group1)]
            perm2 = combined[len(group1):]
            diffs.append(float(np.mean(perm1) - np.mean(perm2)))
        p_value = float(np.mean(np.abs(diffs) >= abs(observed_diff)))
        return {'observed_difference': observed_diff, 'p_value': p_value, 'significant': bool(p_value < self.significance_level)}

    def expected_calibration_error(self, confidences: List[float], correctness: List[int], bins: int = 10) -> float:
        import numpy as np
        if not confidences:
            return 0.0
        conf = np.clip(np.array(confidences, dtype=float), 0.0, 1.0)
        corr = np.array(correctness, dtype=float)
        bin_edges = np.linspace(0.0, 1.0, bins+1)
        ece = 0.0
        for i in range(bins):
            lo, hi = bin_edges[i], bin_edges[i+1]
            idx = (conf >= lo) & (conf < hi if i < bins-1 else conf <= hi)
            if idx.any():
                bin_conf = conf[idx].mean()
                bin_acc = corr[idx].mean()
                ece += (idx.mean()) * abs(bin_acc - bin_conf)
        return float(ece)

    def brier_score(self, confidences: List[float], correctness: List[int]) -> float:
        import numpy as np
        conf = np.clip(np.array(confidences, dtype=float), 0.0, 1.0)
        corr = np.array(correctness, dtype=float)
        return float(np.mean((conf - corr) ** 2))

    def analyze_variance_components(self, data, factors: List[str], response: str) -> Dict[str, Any]:
        from scipy.stats import f_oneway
        results: Dict[str, Any] = {}
        for factor in factors:
            groups = [group[response].values for _, group in data.groupby(factor)]
            if len(groups) >= 2:
                f_stat, p_value = f_oneway(*groups)
                results[factor] = {'f_statistic': float(f_stat), 'p_value': float(p_value), 'significant': bool(p_value < self.significance_level)}
        return results


class BayesianAnalyzer:
    def bayesian_accuracy_estimation(self, correct: int, total: int, prior_alpha: float = 1, prior_beta: float = 1) -> Dict[str, float]:
        posterior_alpha = prior_alpha + correct
        posterior_beta = prior_beta + (total - correct)
        posterior_mean = posterior_alpha / (posterior_alpha + posterior_beta)
        posterior_var = (posterior_alpha * posterior_beta) / (((posterior_alpha + posterior_beta) ** 2) * (posterior_alpha + posterior_beta + 1))
        from scipy.stats import beta
        ci = beta.interval(0.95, posterior_alpha, posterior_beta)
        return {'posterior_mean': float(posterior_mean), 'posterior_variance': float(posterior_var), 'credible_interval_95': (float(ci[0]), float(ci[1])), 'posterior_alpha': float(posterior_alpha), 'posterior_beta': float(posterior_beta)}

    def model_comparison_bayes_factor(self, data1: List[float], data2: List[float]) -> float:
        mean1, var1 = float(np.mean(data1)), float(np.var(data1))
        mean2, var2 = float(np.mean(data2)), float(np.var(data2))
        if var1 <= 0 or var2 <= 0:
            return 1.0
        log_bf = 0.5 * np.log(var2 / var1) + (len(data1) - 1) * 0.5 * np.log(var1) - (len(data2) - 1) * 0.5 * np.log(var2)
        return float(np.exp(log_bf))


