# Object Detection and Segmentation — Beyond "What Is This?"

*Classifying a whole image as "cat" is only the beginning of computer vision. Real applications need to know where the cat is, how many objects there are, and sometimes exactly which pixels belong to each one. Object detection and segmentation answer those harder questions, and they power self-driving cars, medical imaging, and photo editing. This post covers the main vision tasks beyond classification and how they build on the CNN foundation.*

Posts 3–4 built CNNs for image *classification* ("what is this image?"). This post covers the richer tasks that most real vision applications actually need — localizing and delineating objects — and shows how they extend the CNN. Understanding the task hierarchy (classification → detection → segmentation) is understanding what computer vision can actually do.

## The task hierarchy

Vision tasks form a ladder of increasing spatial detail, and knowing which rung your problem is on determines the approach:

- **Image classification** — one label for the whole image ("this is a cat"). The simplest task (posts 3–4), but it assumes one dominant subject and tells you nothing about *where* or *how many*.
- **Object detection** — find *all* objects in the image, each with a **bounding box** (a rectangle) and a class label: "a cat here, a dog there, a person in the corner." This answers *what* and *where* and *how many* — a huge step up, and what most applications need (a self-driving car must locate every pedestrian and vehicle, not just know "there's a street scene").
- **Semantic segmentation** — label *every pixel* with a class: this pixel is "road," that one is "car," this one is "sky." A dense, pixel-level understanding of the whole scene, but it doesn't distinguish *individual* objects (all cars are just "car" pixels).
- **Instance segmentation** — the most detailed: label every pixel *and* separate individual objects ("car #1's pixels" vs "car #2's pixels"). It combines detection (individual objects) with segmentation (exact pixels), giving the richest understanding.

The ladder goes from *what* (classification) to *what + where + how many* (detection) to *what + exact shape* (segmentation) to *what + exact shape + which instance* (instance segmentation). More detail is more useful but harder and more expensive — so you pick the least-detailed task that solves your problem (a defect-presence check needs only classification; an autonomous vehicle needs detection or segmentation).

## How detection and segmentation work

These harder tasks build on the CNN *backbone* (posts 3–4) — the learned feature hierarchy — and add machinery to produce spatial outputs:

- **Object detection** approaches split into two families worth knowing. **Two-stage detectors** (the R-CNN family) first *propose* candidate regions that might contain objects, then classify and refine each — accurate but slower. **One-stage detectors** (YOLO, SSD) skip the proposal step and predict boxes and classes directly in a single pass over the image — faster, enabling **real-time** detection (YOLO — "You Only Look Once" — is the famous example). The trade-off is the recurring one: two-stage = more accurate, one-stage = faster/real-time, and you choose by whether you need speed (live video, robotics) or maximum accuracy.
- **Semantic segmentation** uses **fully convolutional** architectures that take an image and output a same-sized grid of per-pixel class predictions. The classic design (encoder-decoder, e.g. U-Net) first *downsamples* to capture context (what's in the scene) then *upsamples* back to full resolution to produce the dense pixel labels — U-Net in particular is a workhorse in **medical imaging**.
- **Instance segmentation** extends detection: a model like Mask R-CNN detects each object (box + class) *and* predicts a pixel mask within each box — combining the two capabilities.

The unifying idea: all of these reuse the CNN's learned features (so they inherit the representation power of posts 3–4) and add task-specific "heads" that turn those features into the spatial output the task needs — boxes, pixel maps, or masks. You don't start from scratch for detection or segmentation; you build on a pretrained backbone (post 7), which is why the CNN foundation matters so much.

## Where these tasks matter — and the practical picture

Detection and segmentation are where computer vision meets high-stakes applications:

- **Autonomous vehicles** — detect and often segment every pedestrian, vehicle, lane, and sign in real time. This is detection/segmentation at its most demanding (real-time, safety-critical), and it's why fast one-stage detectors matter.
- **Medical imaging** — segment tumors, organs, and lesions pixel-by-pixel in scans (U-Net's home turf), where precise delineation directly supports diagnosis and treatment planning.
- **Satellite and aerial imagery** — segment land use, detect buildings/roads/crops, monitor change.
- **Retail, manufacturing, robotics** — detect and locate products, defects, and objects to grasp.
- **Photo and video editing** — segment subjects for background removal, effects, and the "select subject" tools in consumer software.

The practical reality mirrors the rest of the series: you rarely build these from scratch. You take a **pretrained model** (a YOLO for detection, a U-Net or Mask R-CNN for segmentation) and fine-tune it on your data (post 7), because training these from zero needs enormous labeled data and compute. The key skills are choosing the right *task* (the least detail that solves your problem — classification vs detection vs segmentation), choosing the right *speed/accuracy trade-off* (one-stage vs two-stage), and getting the *labeled data* — which for detection and segmentation is expensive (bounding boxes and especially pixel masks are costly to annotate), often the real bottleneck. Understanding the task hierarchy and how each builds on the CNN lets you scope a vision problem correctly: decide what spatial detail you actually need, pick a proven architecture for it, and invest where it counts — usually in data and in matching the task to the real requirement.

The throughline: beyond whole-image **classification** ("what is this?"), real vision climbs a **task hierarchy** of increasing spatial detail — **object detection** (every object's **bounding box** + class: what + where + how many), **semantic segmentation** (label *every pixel* by class — dense scene understanding, but not individual objects), and **instance segmentation** (every pixel *and* separate instances — the richest). All **build on the CNN backbone** (posts 3–4) plus task-specific heads: detection splits into **two-stage** (R-CNN — accurate, slower) vs **one-stage** (YOLO/SSD — real-time) detectors (speed-vs-accuracy trade-off), segmentation uses **fully-convolutional encoder-decoders** (U-Net — a medical-imaging workhorse), and instance segmentation (Mask R-CNN) combines both. They power **autonomous vehicles, medical imaging, satellite imagery, robotics, and photo editing** — and in practice you **fine-tune a pretrained model** (post 7), so the key skills are choosing the **least-detailed task that solves the problem**, the right **speed/accuracy trade-off**, and getting the **expensive labeled data** (boxes/masks) that's usually the real bottleneck.

## Key takeaways

- Vision tasks form a **hierarchy** of spatial detail: **classification** (one label for the image — *what*), **object detection** (per-object **bounding box** + class — *what + where + how many*), **semantic segmentation** (per-**pixel** class — dense scene labeling, but not individual objects), **instance segmentation** (per-pixel *and* per-instance — richest). Pick the **least-detailed task that solves your problem** (more detail = more useful but harder/costlier).
- **Object detection** splits into **two-stage** (R-CNN family — propose regions then classify; accurate, slower) and **one-stage** (YOLO/SSD — predict boxes+classes in one pass; **real-time**) — the speed-vs-accuracy trade-off, chosen by whether you need live speed (vehicles, robotics) or max accuracy.
- **Semantic segmentation** uses **fully-convolutional encoder-decoder** nets (downsample for context, upsample to full-resolution pixel labels; **U-Net** is a medical-imaging workhorse); **instance segmentation** (Mask R-CNN) extends detection with a per-object pixel **mask**.
- All **build on the CNN backbone** (posts 3–4) + task-specific heads that turn learned features into spatial outputs (boxes/pixel-maps/masks) — you don't start from scratch, you build on the representation power of the CNN.
- They power high-stakes applications — **autonomous vehicles** (real-time detection/segmentation), **medical imaging** (U-Net tumor/organ segmentation), **satellite imagery, robotics, photo editing** — and in practice you **fine-tune pretrained models** (YOLO, U-Net, Mask R-CNN; post 7); the key skills are **choosing the right task and speed/accuracy trade-off** and getting the **expensive labeled data** (boxes and especially pixel masks), usually the real bottleneck.

## Further reading

- [Object detection — locating objects with bounding boxes](https://en.wikipedia.org/wiki/Object_detection)
- [Image segmentation — labeling images at the pixel level](https://en.wikipedia.org/wiki/Image_segmentation)
