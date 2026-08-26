# Video and Beyond

*Video is where multimodal AI gets genuinely hard. It's not just images — it's images over time, plus audio, at a scale that dwarfs a single picture. The temporal dimension adds motion, causality, and continuity that a still frame can't capture, and the sheer data volume strains everything. Video is also the frontier where the most impressive recent generation results have appeared, and where multimodal AI is actively pushing forward. Understanding video — and the other modalities beyond the core ones — shows where the field is heading.*

This post covers **video** — the modality that adds *time* to vision — and other modalities *beyond* the core text/image/audio: video understanding and generation, why the temporal dimension is hard, and the broader landscape of modalities (3D, sensor data, and more). It's the frontier-facing post, showing where multimodal AI extends beyond the established modalities. Video builds on everything prior (vision, generation, audio) while adding the challenge of time.

## Video: vision plus time

**Video** is a sequence of images (frames) over time, usually with audio — so it combines vision with a *temporal* dimension (and often audio). This makes it both richer and much harder than still images:

- **Video = frames over time (+ audio).** A video is many images in sequence, capturing *motion and change* over time, typically accompanied by audio. So video inherently combines *multiple* modalities and adds *time* — it's vision (each frame) plus temporal dynamics (across frames) plus audio. Understanding or generating video means handling all of this together.
- **The temporal dimension adds a lot.** Time brings *motion, change, causality, and continuity* — things a single image can't capture. Understanding video requires grasping *what happens over time* (actions, events, cause and effect, how things move and change), not just what's in a frame. This temporal understanding is a genuine additional challenge beyond static vision. A video isn't just more images; it's about what unfolds.
- **It's the richest common modality.** Video is arguably the richest everyday modality — combining visual, temporal, and audio information — and it's abundant (huge amounts of video exist). This richness makes it valuable (video understanding/generation unlocks a lot) but also makes it the hardest of the common modalities to handle well. It's where multimodal AI's ambitions and difficulties are both greatest.

Video is vision plus time (plus audio) — a sequence of frames capturing motion and change — making it the richest and hardest common modality, requiring temporal understanding beyond static vision. Its two capabilities, understanding and generation, both build on earlier posts while grappling with time and scale.

## Video understanding and generation

The two core video capabilities — *understanding* video and *generating* it — extend the vision capabilities into the temporal dimension:

- **Video understanding.** Models can *understand* video — recognizing actions and events, describing what happens over time, answering questions about a video, summarizing it, and reasoning about temporal content. This extends VLM-style understanding (from the vision-language post) to *temporal* visual content: not just "what's in this image?" but "what happens in this video?" It requires processing many frames and grasping their temporal relationships, which is computationally and conceptually harder than single images. Multimodal models increasingly handle video input, reasoning over what unfolds.
- **Video generation.** Models can *generate* video — creating video clips from text descriptions (text-to-video), extending the text-to-image capability into motion. This is one of the most impressive and rapidly-advancing recent capabilities: generating coherent, temporally-consistent video from a prompt. It's much harder than image generation because the frames must be *temporally coherent* (consistent, smoothly moving, physically plausible over time), not just individually good. Techniques build on image generation (diffusion, from the generation post) extended to the temporal dimension. Video generation is a frontier where results have advanced strikingly.
- **Temporal coherence is the crux.** For both understanding and generation, the *temporal* aspect is the hard part: understanding requires grasping change over time; generation requires *producing* consistent, coherent change over time (objects persisting, motion being smooth and plausible). Getting temporal coherence right — things staying consistent and moving believably across frames — is the central challenge that distinguishes video from images. It's why video lags images in maturity but is advancing fast.

Video understanding (recognizing actions/events, reasoning about what happens over time) and video generation (creating temporally-coherent video from text, extending diffusion to motion) both extend vision capabilities into time — with *temporal coherence* the central, hard challenge. Video generation especially is a rapidly-advancing frontier. But video's difficulty is compounded by its sheer scale.

## Why video is hard: the scale challenge

Beyond temporal coherence, video is hard because of its **scale** — the sheer volume of data — which strains computation and training:

- **Video is enormous data.** A single video contains *many* frames (dozens per second), each an image — so a short video is equivalent to *thousands* of images, plus audio. Processing or generating video means handling vastly more data than a single image, which is computationally *expensive* (memory, compute) at every stage. The data volume is a fundamental challenge.
- **It strains computation.** The scale makes video models *expensive* to train and run — processing long sequences of high-dimensional frames pushes against compute and memory limits. This is a major reason video AI lags image AI: the same techniques become far costlier at video scale, requiring efficiency innovations (like the latent-space approaches from the generation post, extended to video) to be feasible. Efficiency is central to making video tractable.
- **Long-range temporal modeling is hard.** Understanding or generating *longer* videos requires modeling relationships over *long* time spans (what happened earlier affecting later) — long-range temporal dependencies that are hard to capture and expensive to compute (long sequences strain attention, echoing the context-length challenges of LLMs). Coherent *long* video is especially hard; short clips are more tractable. Length compounds every challenge.

Video is hard because of scale (a video is thousands of images plus audio — enormous data straining compute and memory) on top of temporal coherence and long-range temporal modeling. These challenges are why video AI lags images but is a very active frontier — advances often come from efficiency innovations that make video scale tractable. Video is the hardest common modality, but not the only frontier.

## Beyond the core modalities

Multimodal AI extends *beyond* text, image, audio, and video to *other* modalities — showing how general the approach is and where the field is heading:

- **3D and spatial data.** Models increasingly handle *3D* content (3D shapes, scenes, generating 3D objects from text) and *spatial* understanding — important for graphics, robotics, AR/VR, and design. 3D generation (text-to-3D) extends the generative capabilities into three dimensions, another frontier.
- **Sensor and scientific data.** The multimodal approach extends to *sensor* data (from robotics, IoT, autonomous vehicles — lidar, depth, etc.) and *scientific* data (medical images, genomic data, protein structures, remote sensing). Treating diverse data types as modalities to understand and connect brings AI to specialized domains (medicine, science, robotics), where multimodal models combine, say, images and text/reports, or fuse multiple sensor streams. The recipe generalizes to many data types.
- **Embodied and robotic multimodality.** *Robotics* is deeply multimodal — a robot perceives via cameras (vision), sensors, and sometimes audio, and acts in the world. Multimodal AI (especially vision-language-action models that connect perception to action) is central to robotics and embodied AI, an important frontier where multimodal models control physical systems. Perception-to-action is multimodal AI in the physical world.
- **The pattern generalizes.** The key insight across all these: the *same* multimodal recipe — represent a modality as a sequence/embedding, use transformers, train at scale on paired data, connect modalities in shared/aligned spaces, generate via shared techniques — extends to essentially *any* modality. This generality is why multimodal AI keeps expanding to new data types. Almost anything can be treated as a modality and brought into the multimodal framework. That generality is the deep story.

Multimodal AI extends beyond the core modalities to 3D/spatial data, sensor and scientific data, and embodied/robotic multimodality — showing that the same recipe generalizes to essentially any modality. Video (vision plus time) is the hardest common modality (temporal coherence plus scale) and a fast-advancing frontier, and beyond it, multimodal AI keeps expanding. Next, the final post: building with multimodal AI and the any-to-any future.

## Key takeaways

- Video is vision plus time (plus audio) — a sequence of frames capturing motion and change — making it the richest and hardest common modality, requiring *temporal* understanding (actions, events, causality, continuity over time) beyond what a static image captures.
- Video understanding (recognizing actions/events, reasoning about what happens over time — extending VLM understanding to temporal content) and video generation (creating temporally-coherent video from text, extending diffusion to motion — a rapidly-advancing frontier) both extend vision into time, with *temporal coherence* (consistent, plausible change across frames) the central hard challenge.
- Video is also hard because of scale: a short video equals thousands of images plus audio — enormous data that strains compute and memory at every stage (a key reason video AI lags image AI) — and long videos require expensive long-range temporal modeling, so efficiency innovations (latent-space approaches) are central to making video tractable.
- Multimodal AI extends beyond core modalities to 3D/spatial data (text-to-3D, spatial understanding), sensor and scientific data (robotics/IoT sensors, medical/genomic/scientific data), and embodied/robotic multimodality (vision-language-action models connecting perception to action in the physical world).
- The deep story is generality: the same multimodal recipe (represent as sequence/embedding, use transformers, train at scale on paired data, connect in shared spaces, generate via shared techniques) extends to essentially *any* modality — which is why multimodal AI keeps expanding to new data types, treating almost anything as a modality to understand and connect.

## Further reading

- [Text-to-video model (Wikipedia)](https://en.wikipedia.org/wiki/Text-to-video_model)
- [Diffusion model — the generative technique extended to video (Wikipedia)](https://en.wikipedia.org/wiki/Diffusion_model)
- [Audio and speech (previous post)](/blog/posts/mm-06-audio-and-speech.html)
