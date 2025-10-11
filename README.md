# Google Meet Selenium Test — Automated Video Conferencing Quality Assessment

**Repository:** [github.com/dogukan-bicer/google_meet_selenium_test](https://github.com/dogukan-bicer/google_meet_selenium_test)  
**Author:** Doğukan Biçer  
**Year:** 2025  
**Keywords:** Selenium Grid, WebRTC, Google Meet, Video Quality, Audio Quality, DINOv2, TRILLsson, Objective Assessment

---

## 🧩 Overview

This repository contains the implementation of an **automated test framework** designed to evaluate **video and audio quality** in Google Meet sessions using **Selenium Grid**.  
The project was developed as part of a **graduate thesis** focused on building an **objective, scalable, and repeatable** system for assessing video conferencing performance without relying solely on human evaluation.

Traditional manual tests often depend on subjective feedback or pixel-level metrics that fail to capture the true user experience.  
This system addresses that gap by integrating **deep learning-based image and audio similarity metrics** with **automated browser-based testing**.

---

## 🎯 Motivation

During the COVID-19 pandemic, video conferencing platforms became essential for communication, education, and business.  
Local studies, such as that by **S. Öztürk et al. (2021)**, evaluated the functionality, performance, and usability of domestic WebRTC-based systems.  
However, those tests primarily relied on human perception and did not include **objective evaluations of image or sound quality**.

This project builds upon that foundation by focusing on **quantitative, machine-driven evaluation**.  
It bridges the gap between **subjective user experience** and **objective computational metrics**.

---

## 🚀 Project Goals

- Automate Google Meet testing using Selenium Grid nodes.  
- Capture and analyze **screen recordings** and **audio streams** in real time.  
- Evaluate video and audio quality using:
  - Classical metrics (e.g., **SSIM** — Structural Similarity Index Measure, **PSNR** — Peak Signal-to-Noise Ratio)
  - Deep learning-based metrics (**DINOv2**, **OpenCLIP**, **DISTS**, and **TRILLsson** for audio)
- Validate results on **NITE-IQA**, a human-rated image quality dataset.
- Develop a **reproducible and scalable** evaluation system for future WebRTC testing research.

---

## 🧠 Conceptual Background

### Video Quality Metrics
- **SSIM (Structural Similarity Index Measure)** — compares image luminance, contrast, and structure.  
- **PSNR (Peak Signal-to-Noise Ratio)** — measures pixel-wise similarity, less correlated with human perception.  
- **DINOv2** — extracts high-level semantic image features; captures perceptual differences like face or object distortions.  
- **OpenCLIP** — uses contrastive embeddings that align image and semantic meaning.  
- **DISTS (Deep Image Structure and Texture Similarity)** — measures both structural and textural consistency.

### Audio Quality Metric
- **TRILLsson (Distilled Universal Paralinguistic Speech Representations)** — captures perceptual and emotional properties of speech for sound comparison.

---

## ⚙️ System Architecture

┌──────────────────────────┐
│ Selenium Hub │
│ (Test orchestration API) │
└──────────┬───────────────┘
│
┌───────┴────────┐
│ Selenium Nodes │ (multiple)
│ (Chrome / Edge) │
└───────┬────────┘
│
Run Google Meet
Capture Streams
│
┌─────┴──────┐
│ FFmpeg │ → Records video/audio locally
│ Recorder │
└─────┬──────┘
│
Post-Processing
(Frame extraction, metrics)
│
┌─────┴──────┐
│ Analysis │ → Compute SSIM, DINOv2, TRILLsson, etc.
└────────────┘

yaml
Kodu kopyala

---

## 📦 Repository Structure

.
├── README.md
├── requirements.txt
├── docker/
│ └── docker-compose.yml # Optional: run Selenium Grid via Docker
├── grid/
│ ├── start_grid.sh # Starts Selenium Hub and Nodes
│ └── stop_grid.sh
├── tests/
│ └── run_test.py # Main Google Meet test automation script
├── recorders/
│ └── ffmpeg_record.sh # Capture screen and audio
├── analysis/
│ ├── extract_frames.py
│ ├── compute_metrics.py
│ └── aggregate_results.py
├── configs/
│ └── grid_config.json
└── results/
└── session01_metrics.csv

yaml
Kodu kopyala

---

## 🧰 Installation

### Requirements
- Python ≥ 3.8  
- Selenium ≥ 4.0  
- FFmpeg (for recording)  
- Chrome / Chromium + ChromeDriver  
- (Optional) Docker + Docker Compose  

### Setup
```bash
git clone https://github.com/dogukan-bicer/google_meet_selenium_test.git
cd google_meet_selenium_test

python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
Example requirements.txt:

nginx
Kodu kopyala
selenium
opencv-python
numpy
pandas
torch
tqdm
librosa
ffmpeg-python
scipy
🧪 Running Selenium Grid (via Docker)
Start the Selenium Hub and Chrome Node containers:

bash
Kodu kopyala
docker-compose -f docker/docker-compose.yml up -d
Access the Grid UI:
👉 http://localhost:4444/ui/

Example docker/docker-compose.yml:

yaml
Kodu kopyala
version: "3"
services:
  selenium-hub:
    image: selenium/hub:4.8.0
    ports:
      - "4444:4444"

  chrome-node:
    image: selenium/node-chrome:4.8.0
    depends_on:
      - selenium-hub
    environment:
      - SE_EVENT_BUS_HOST=selenium-hub
      - SE_EVENT_BUS_PUBLISH_PORT=4442
      - SE_EVENT_BUS_SUBSCRIBE_PORT=4443
🧭 Running a Test Scenario
Example command:

bash
Kodu kopyala
python tests/run_test.py \
  --grid-url http://localhost:4444 \
  --browser chrome \
  --meeting-url "https://meet.google.com/your-meeting" \
  --record-dir ./recordings/session01
The script:

Connects to the Selenium Grid hub.

Launches Google Meet on remote nodes.

Performs actions (join meeting, mute/unmute, camera toggle).

Starts FFmpeg-based recording.

Saves video/audio streams locally for later analysis.

🎥 Recording Example (FFmpeg)
Example command used on each Node:

bash
Kodu kopyala
ffmpeg -y -video_size 1280x720 -f x11grab -i :0.0 \
-f pulse -i default -c:v libx264 -preset ultrafast \
-c:a aac recordings/session01/screen.mp4
📊 Quality Analysis
After recording, compute visual/audio metrics:

bash
Kodu kopyala
python analysis/extract_frames.py --input ./recordings/session01
python analysis/compute_metrics.py \
  --frames ./recordings/session01/frames \
  --reference ./datasets/nite_iqa/reference \
  --metrics ssim,psnr,dinov2,dists \
  --out ./results/session01_metrics.csv
The script outputs a CSV file summarizing the similarity results per frame or clip.

🧮 Metrics Used
Metric	Type	Description
SSIM	Classical	Structural Similarity Index Measure (structure, contrast, luminance)
PSNR	Classical	Peak Signal-to-Noise Ratio, derived from MSE
DINOv2	Deep	Self-supervised vision transformer embeddings
OpenCLIP	Deep	Image-text alignment features
DISTS	Deep	Deep Image Structure and Texture Similarity
TRILLsson	Deep	Audio embedding capturing paralinguistic cues

📚 Dataset Evaluation
All metrics were validated against the NITE-IQA dataset — a human-rated image quality benchmark.
Each metric’s output was compared to Mean Opinion Scores (MOS) to assess correlation with human perception.

This approach allows:

Objective evaluation of deep vs. classical methods.

Insight into which metric better represents perceptual video degradation.

🧾 Reproducing Thesis Experiments
To replicate results from the thesis:

bash
Kodu kopyala
bash grid/start_grid.sh
python orchestrate/run_experiments.py --config configs/experiment.yml
python analysis/aggregate_results.py --input results/ --out final_report.csv
Outputs include:

Metric values per scenario

Correlation scores (Pearson, Spearman)

Final report table summarizing results

🧠 Key Contributions
Developed a fully automated framework for video conferencing quality testing.

Combined Selenium Grid, FFmpeg, and deep learning-based metrics in a single system.

Demonstrated how objective quality assessment can replace or complement human evaluations.

Conducted extensive experiments on NITE-IQA and real-world Google Meet recordings.

Provided an open, extensible foundation for future WebRTC and multimedia testing research.

📄 License
vbnet
Kodu kopyala
MIT License
© 2025 Doğukan Biçer
🔗 Citation
If you use this code, please cite:

D. Biçer, “Objective Quality Assessment of Video Conferencing Systems Using Deep Learning-Based Metrics,” Master’s Thesis, 2025.

📬 Contact
For questions or collaboration:
📧 github.com/dogukan-bicer

🌟 Acknowledgements
This work was inspired by S. Öztürk et al. (2021) — “Functionality, Performance and Usability Tests of WebRTC-Based Video Conferencing Products,” which laid the foundation for domestic video conferencing test automation efforts during the COVID-19 pandemic.
