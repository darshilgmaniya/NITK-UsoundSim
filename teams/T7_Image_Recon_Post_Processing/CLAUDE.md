# Project: Post Image Processing of Ultrasound Images

Owner: Darshil Maniya (262SP009), M.Tech Signal Processing and Machine Learning, NITK Surathkal.
Part of the NITK-UsoundSim team project. This repo covers ONLY the post-processing module.

## Task

Input  = a raw grayscale B-mode ultrasound image (already formed by the scanner).
Output = the best possible clean image: speckle removed, edges kept, good contrast.

Do NOT implement beamforming, envelope detection, log compression, scan conversion
or any image formation. Those belong to other teams.

## Rules

- Build ONE Jupyter notebook: `262SP009_Post_Image_Processing_v2.ipynb`
- Write it as Google Colab cells (pip installs at the top; must also run in Colab).
- Each section = one short markdown cell + code cells.
- Classical image processing only. No deep learning for now.
- Fixed random seed everywhere.
- Simple, readable code. Target ~450-550 lines total.
- Never invent or hardcode results. Every number must come from actually running
  the code. If something fails or is too slow, say so honestly.
- After each step, run the new cells and report the outputs.
- Do only the step requested in the current prompt.
- Dataset downloads: verify they really work. If a dataset needs login
  (e.g. Kaggle credentials), add a clear upload/credentials cell and continue
  with the datasets that do work.

## Plan (each step is given as a separate prompt)

1. Data loading - 4 organs (breast: BUSI, thyroid, kidney, liver), 20 images each,
   with lesion/organ masks, longest side max 512 px
2. Preprocessing - remove text/rulers, auto scan-area mask, normalize
3. Quality metrics - ENL, speckle index, CNR, gCNR, edge sharpness at lesion border, runtime
4. Despeckle filters - Median, Lee, SRAD, NLM, Wavelet, OBNLM, BM3D, Guided, Bilateral, TV
5. Compare on breast only - 10 tune / 10 test, pick params with best CNR while
   edge sharpness >= 90% of raw; results table (mean +/- std)
6. Improve - hybrid method, edge-aware enhancement, auto-tuning from estimated noise level
7. Final - test on thyroid, kidney, liver WITHOUT re-tuning; final
   `post_process(img, method="auto", enhance=False)`; honest conclusion;
   restart and run all with zero errors

## How "best" is decided

Most speckle removal and highest lesion contrast (gCNR), with the rule that edge
sharpness at the lesion border stays at least 90% of the raw image. Report runtime too.
