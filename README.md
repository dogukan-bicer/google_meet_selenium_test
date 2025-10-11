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

