import os
import shutil


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def move_if_exists(src: str, dst: str):
    if os.path.exists(src):
        ensure_dir(os.path.dirname(dst))
        shutil.move(src, dst)
        print(f"Moved {src} -> {dst}")


def main():
    results_root = os.getenv('RESULTS_ROOT', 'results')
    ensure_dir(results_root)
    ensure_dir(os.path.join(results_root, 'reports'))
    ensure_dir(os.path.join(results_root, 'benchmarks'))
    ensure_dir(os.path.join(results_root, 'experiments'))
    ensure_dir(os.path.join(results_root, 'figures'))

    move_if_exists('evaluation_report.html', os.path.join(results_root, 'reports', 'evaluation_report.html'))
    move_if_exists('evaluation_report.html.pdf', os.path.join(results_root, 'reports', 'evaluation_report.html.pdf'))
    move_if_exists('evaluation_results.json', os.path.join(results_root, 'reports', 'evaluation_results.json'))
    move_if_exists('log_analysis_dashboard.html', os.path.join(results_root, 'reports', 'log_analysis_dashboard.html'))


if __name__ == '__main__':
    main()








