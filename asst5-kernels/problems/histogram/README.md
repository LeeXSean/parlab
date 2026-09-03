# Multi-channel Histogram

Efficient multi-channel histogramming is a fundamental operation in many GPU workloads. When many threads and channels compete to update the same histogram bins, naïve approaches suffer from excessive atomic contention and poor memory access patterns. Optimizing this computation highlights key GPU programming concepts such as parallelism, shared memory, and synchronization. A well-designed histogram kernel becomes a high-performance building block that benefits downstream tasks like image processing, feature extraction, and data preprocessing.

---

## Input

- **num_bins**  
  Number of histogram bins.

- **array**  
  A tensor of shape **`[length, num_channels]`** containing integer values in the range `[0, num_bins - 1]`.

### Test Case Parameters

- **num_bins:** `256`  
- **array shape:** `[1048576, 512]`

---

## Output

- **histogram**  
  A tensor of shape **`[num_channels, num_bins]`**, where  
  `histogram[c][b]` is the number of times value **b** appears in channel **c**.

### Test Case Output Shape

- **histogram:** `[512, 256]`

---

In short, for each channel of the input tensor, the kernel produces a discrete histogram summarizing the value distribution across all entries in that channel.