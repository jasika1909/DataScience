# 📡 Sampling Theorem Project

## Signals and Systems

---

## 📌 Project Overview

This project is based on the **Sampling Theorem**, one of the most fundamental concepts in **Signals and Systems** and **Digital Signal Processing (DSP)**. The project demonstrates how a continuous-time signal can be converted into a discrete-time signal using sampling techniques and how proper sampling ensures accurate signal reconstruction.

The main goal of this project is to study the principles of signal sampling, Nyquist rate, aliasing, and reconstruction of signals through simulation and visualization.

---

## 🎯 Objectives

* Understand the concept of sampling in signals
* Study the Sampling Theorem
* Learn about Nyquist Rate and Nyquist Interval
* Understand aliasing and its effects
* Demonstrate signal reconstruction
* Visualize sampled signals using plots
* Analyze under-sampling and over-sampling cases

---

## 📖 Theory Background

### 📌 Sampling Theorem

The **Sampling Theorem** states that:

A continuous-time signal can be completely reconstructed from its samples if the sampling frequency is greater than or equal to twice the highest frequency present in the signal.

Mathematically:

**fs ≥ 2fm**

Where:

* **fs** = Sampling Frequency
* **fm** = Maximum Frequency of Signal

This minimum sampling frequency is called the **Nyquist Rate**. If the signal is sampled below this rate, distortion known as **aliasing** occurs. ([Testbook][1])

---

### 📌 Nyquist Rate

The Nyquist Rate is defined as:

**Nyquist Rate = 2 × Highest Frequency**

Sampling at this rate ensures accurate reconstruction of the original signal without loss of information. ([Encyclopedia Britannica][2])

---

### 📌 Aliasing

Aliasing occurs when the sampling frequency is less than twice the highest frequency of the signal. This causes distortion, where high-frequency components appear as lower frequencies in the reconstructed signal. ([GeeksforGeeks][3])

---

## 🛠️ Technologies Used

* **Programming Language:** Python 🐍
* **Libraries Used:**

  * NumPy
  * Matplotlib
  * SciPy (if used)
  * Math Library

---

## 📊 Project Workflow

### Step 1: Generate Continuous Signal

A continuous-time signal such as a sine wave is generated using mathematical equations.

Example:

```python
t = np.linspace(0, 1, 1000)
signal = np.sin(2 * np.pi * f * t)
```

---

### Step 2: Sampling the Signal

The continuous signal is sampled at different sampling frequencies.

Cases analyzed:

* Sampling below Nyquist Rate (Under Sampling)
* Sampling at Nyquist Rate
* Sampling above Nyquist Rate (Over Sampling)

---

### Step 3: Visualization

Plots are created to visualize:

* Original Signal
* Sampled Signal
* Reconstructed Signal
* Aliasing Effects

---

### Step 4: Signal Reconstruction

Reconstruction is performed using interpolation methods to recover the original signal.

---

## 📈 Expected Output

The project generates graphs showing:

* Continuous Signal Waveform
* Sampled Signal Points
* Aliased Signal (when undersampled)
* Properly Reconstructed Signal

---

## 📷 Sample Results

(Add your output graphs here)

Example:

images/original_signal.png
images/sampled_signal.png
images/aliasing_effect.png
images/reconstructed_signal.png

---

## 📁 Project Structure

```bash
Sampling_theorem/
│
├── sampling_theorem.py        # Python source code
├── sampling_theorem.ipynb    # Jupyter Notebook
├── README.md                 # Project Documentation
└── images/                   # Output graphs (optional)
```

---

## 🚀 How to Run This Project

Follow these steps to run the project:

### Step 1: Clone Repository

```bash
git clone https://github.com/jasika1909/DataScience.git
```

---

### Step 2: Navigate to Project Folder

```bash
cd DataScience/Sampling_theorem
```

---

### Step 3: Install Required Libraries

```bash
pip install numpy matplotlib scipy
```

---

### Step 4: Run the Program

For Python script:

```bash
python sampling_theorem.py
```

OR

For Jupyter Notebook:

```bash
jupyter notebook
```

Open:

```bash
sampling_theorem.ipynb
```

---

## 📊 Key Concepts Demonstrated

* Continuous-Time Signal
* Discrete-Time Signal
* Sampling Process
* Nyquist Rate
* Nyquist Interval
* Aliasing
* Signal Reconstruction

---

## 🎓 Applications of Sampling Theorem

Sampling theorem is widely used in:

* Digital Communication Systems
* Audio Signal Processing
* Image Processing
* Video Streaming
* Medical Signal Processing (ECG, EEG)
* Wireless Communication

These applications rely on proper sampling to accurately convert analog signals into digital form for processing and storage. ([MathWorks][4])

---

## 🎯 Learning Outcomes

After completing this project, the following concepts are clearly understood:

* Importance of proper sampling rate
* Effects of aliasing
* Relationship between sampling frequency and signal frequency
* Practical implementation of sampling theorem
* Visualization of digital signal processing concepts

---

## 🔮 Future Enhancements

Possible improvements:

* Add real-time signal simulation
* Implement GUI using Tkinter
* Add interactive sampling control
* Extend project to audio signal sampling
* Add Fourier Transform visualization

---

## 👩‍💻 Author

**Name:** Jasika Awasthi
**Course:** Signals and Systems
**Project Type:** Academic Mini Project

---

## ⭐ Conclusion

This project successfully demonstrates the fundamental concepts of the Sampling Theorem and its importance in digital signal processing. By analyzing different sampling frequencies and observing aliasing effects, the project provides a clear understanding of how signals are sampled and reconstructed in real-world systems.

---

[1]: https://testbook.com/electrical-engineering/sampling-theorem-in-signals-and-systems?utm_source=chatgpt.com "Sampling Theorem in Signals and Systems: Know Statement, Proof & Applications"
[2]: https://www.britannica.com/topic/sampling-theorem?utm_source=chatgpt.com "Sampling theorem | communications | Britannica"
[3]: https://www.geeksforgeeks.org/nyquist-sampling-theorem/?utm_source=chatgpt.com "Nyquist Sampling Theorem - GeeksforGeeks"
[4]: https://in.mathworks.com/discovery/nyquist-theorem.html?utm_source=chatgpt.com "What Is the Nyquist Theorem - MATLAB & Simulink"
