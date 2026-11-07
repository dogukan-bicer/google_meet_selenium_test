# Google Meet Quality Test Framework

This repository contains a desktop application and research scripts for collecting and comparing image and audio samples from browser based video meetings. It was developed as part of a master's thesis project.

## Desktop application

### Requirements

- macOS (the local Grid launcher is configured for macOS)
- Python 3.10 or newer with Tkinter
- Java 11 or newer
- Brave Browser or Google Chrome installed in `/Applications`

### Install and launch

```bash
git clone https://github.com/dogukan-bicer/google_meet_selenium_test.git
cd google_meet_selenium_test
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
./run_ui.command
```

The app starts a local Selenium Grid standalone server and registers the installed Brave or Chrome browser as a node. Selenium Server is obtained through Selenium Manager and cached under `~/.cache/selenium`. The Grid UI is available at <http://127.0.0.1:4444/ui/> while the server is running. Local Grid traffic bypasses desktop proxy settings. Run `./stop_local_grid.command` to stop the local server.

Enter Google account details in the app when needed. No account credentials are stored in the source code. Meeting automation depends on the current Google Meet interface and account settings.

The base requirements are sufficient to open the UI and use the Grid controls. Install optional model dependencies for the relevant analysis features:

```bash
python -m pip install -r requirements-vision.txt
python -m pip install -r requirements-audio.txt
```

Image models may download model weights on first use. The TRILL audio comparison also downloads its model on first use. For environments that cannot access model hosting services, use the classical metrics or provide the model files through the relevant libraries' documented cache mechanisms.

## Research scripts

Scripts operate on files under `dataset/nits_iqa/` and write outputs under `dataset/nits_iqa/results/`.

```bash
# Recompute correlation summaries from the included score CSV and MOS workbook
python scripts/00_quick_plcc_srocc.py

# Recompute image metrics for the image pairs currently present in the dataset folders
python scripts/01_full_nits_iqa.py

# Explore metric decisions against MOS-derived quality labels (not software faults)
python scripts/02_decision_analysis.py --mos-threshold 60

# Benchmark available image metrics on the current machine
python scripts/03_perf_benchmark.py
```

Scripts `00_quick_plcc_srocc.py` and `02_decision_analysis.py` use the base requirements. Scripts `01_full_nits_iqa.py` and `03_perf_benchmark.py` require image-model packages; install `requirements-vision.txt` first. `requirements-research.txt` bundles the vision stack and plotting/support packages.

The decision-analysis command labels MOS values below the selected cutoff as low perceived quality; this proxy does not represent labeled software defects. The full-dataset score CSV is included, while only the sample image pairs in `dataset/nits_iqa/ref/` and `que/` are available for recomputing image metrics. Deep learning models and dataset/model downloads can require substantial storage, memory, and network access. Results depend on the metric implementation, model versions, hardware, and input files.

## Repository layout

```text
dataset/
  conference_test_images/    Example meeting images
  nits_iqa/                  Included image samples and saved analysis results
scripts/                     Dataset analysis and benchmarking scripts
selenium_grid_app/           Tkinter UI and Selenium Grid integration
test_cases/                  Thirty documented manual scenarios and sample media
requirements*.txt            Base and optional dependency groups
run_ui.command               macOS desktop launcher
```

The dataset folder currently contains only the files present in this repository; it should not be treated as a complete copy of an upstream benchmark. Verify the source and redistribution terms for each third party dataset and sample media before redistributing them.

## Scope and reproducibility

The included scripts and result files are research artifacts. The image folders contain the samples present in this repository; scripts can be rerun on those available files. Results depend on the dataset files, metric/model versions, dependencies, hardware, and run configuration. Record those details when producing new results.

The manuscript and any separate editor/reviewer decision letter are not included in this software repository. This README documents the application and its included artifacts.
## License

The source code is licensed under the GNU Affero General Public License v3.0; see [LICENSE](LICENSE). This code license does not automatically grant redistribution rights for third party datasets, model weights, or sample media.

## Citation

If you use this work, cite the associated thesis or publication using its final bibliographic record. A final DOI or publication reference is not included in this repository.
