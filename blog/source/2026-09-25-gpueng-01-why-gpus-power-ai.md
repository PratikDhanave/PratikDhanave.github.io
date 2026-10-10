# Why GPUs Power AI — The Hardware Underneath Inference

*Every large language model runs on a GPU, but most engineers treat the GPU as a black box that "does the math fast." Understanding why it's fast — and, more usefully, why it's often not as fast as its spec sheet promises — is the foundation of inference engineering. This series works below the serving layer: not how to run an inference server, but how the silicon actually executes a model and where the real bottlenecks live.*

This series is the hardware-and-kernel companion to the [LLM Inference and Serving](/blog/series/llm-inference-and-serving/) series. That one covers how to *serve* models fast — batching, KV cache, serving engines. This one goes one layer down: how a GPU is built, why it's the right tool for neural networks, and the physical limits that govern every optimization you'll ever make. Post 1 builds the mental model of the hardware itself.

## Why not a CPU?

A CPU is built for *latency on one task*: a handful of powerful cores, large caches, sophisticated branch prediction and out-of-order execution, all optimized to finish a single sequential thread of instructions as fast as possible. That's exactly wrong for neural networks, whose core operation is **matrix multiplication** — millions of identical multiply-add operations with no dependencies between them.

A **GPU** inverts the CPU's priorities. Instead of a few complex cores, it packs *thousands* of simple arithmetic units that all do the same operation on different data at the same time. It trades single-thread speed for raw parallel throughput. A matrix multiply of two large matrices is embarrassingly parallel — every output element is an independent dot product — so it maps almost perfectly onto thousands of units running in lockstep. This is why GPUs, originally built to shade millions of pixels in parallel, turned out to be the ideal engine for deep learning: pixels and neurons are both "do the same simple math a million times" problems. The field even has a name for using graphics hardware this way — **general-purpose computing on GPUs (GPGPU)**.

## Inside the GPU: SMs, cores, and tensor cores

A modern GPU is a hierarchy built for parallelism:
- **Streaming Multiprocessors (SMs)** — the GPU's repeated building block; a high-end chip has dozens to over a hundred. Each SM is an independent parallel engine with its own execution units, registers, and a small fast scratchpad (*shared memory*).
- **CUDA cores** — within each SM, many simple arithmetic units that execute the actual floating-point multiply-adds, thousands across the whole chip.
- **Tensor cores** — specialized units that do a small *matrix* multiply-accumulate in a single operation rather than one scalar multiply at a time. Since transformers are almost entirely matrix multiplies, tensor cores are where most of an LLM's compute actually happens, and they're the reason newer GPUs are dramatically faster at AI than their raw core count suggests.

The organizing principle: **massive parallelism through replication of simple units.** A GPU doesn't make any single operation fast — it makes *doing a million of them at once* fast. Keeping all those units busy is the entire art of GPU performance, and it's harder than it sounds, which is what the rest of this series is about.

## The spec sheet lies (a little)

A GPU's headline number is its peak throughput — tens or hundreds of *teraFLOPS* (trillions of floating-point operations per second). It's tempting to divide your model's FLOP count by that number and predict the runtime. **This is almost always wildly optimistic**, and understanding why is the single most important idea in inference engineering.

Peak FLOPS assumes every arithmetic unit is busy every cycle. In reality, the units spend most of their time *waiting for data* — because feeding thousands of cores requires moving enormous amounts of data from memory, and memory is far slower than arithmetic. A GPU that can do 1000 TFLOPS but can only read its memory at a few terabytes per second will, on many real workloads, sit mostly idle waiting for numbers to arrive. The gap between peak compute and achievable compute is the **memory wall**, and LLM inference runs straight into it.

So the hardware story is a setup for a reversal: GPUs are fast at arithmetic, but arithmetic is rarely the bottleneck. The bottleneck is *memory bandwidth* — getting data to the compute units — which is exactly where post 2 goes. Internalizing "compute is cheap, data movement is expensive" reframes every optimization in this series: most of them are not about doing less math, but about moving less data.

The takeaway: GPUs power AI because neural networks are built on **matrix multiplication** — massively parallel, dependency-free arithmetic — and a GPU trades the CPU's fast-single-thread design for *thousands of simple units* (organized into **SMs**, with **tensor cores** doing matrix multiply-accumulate directly) that run the same operation on different data at once. But peak **FLOPS** is a near-fiction in practice: the units spend most of their time waiting for data because memory is far slower than compute — the **memory wall**. The governing intuition for the whole series: compute is cheap, data movement is expensive, and inference engineering is mostly about moving less data.

## Key takeaways

- Neural networks are dominated by **matrix multiplication** — millions of independent multiply-adds — which is *embarrassingly parallel*; a GPU is built for exactly this, trading the CPU's fast single thread for **thousands of simple units running in lockstep** (the GPGPU idea).
- A GPU is a hierarchy: **Streaming Multiprocessors (SMs)** (dozens+ independent parallel engines, each with registers and fast *shared memory*), **CUDA cores** (simple scalar arithmetic units), and **tensor cores** (do a small *matrix* multiply-accumulate per op — where most of an LLM's compute happens).
- The organizing principle is **parallelism by replication**: the GPU makes *doing a million operations at once* fast, not any single operation — so keeping the units busy is the whole challenge.
- Peak **FLOPS** (teraFLOPS on the spec sheet) assumes every unit is busy every cycle; real workloads fall far short because units **wait for data** — the **memory wall** between fast compute and slow memory.
- The series' governing intuition: **compute is cheap, data movement is expensive** — most inference optimizations reduce *data movement*, not arithmetic (set up in post 2's memory hierarchy).

## Further reading

- [Graphics processing unit — architecture and purpose](https://en.wikipedia.org/wiki/Graphics_processing_unit)
- [General-purpose computing on GPUs (GPGPU) — using GPUs for non-graphics compute](https://en.wikipedia.org/wiki/General-purpose_computing_on_graphics_processing_units)
