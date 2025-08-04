let stream = null;
const video = document.getElementById("video");
const padStatus = document.getElementById("pad-status");

document.getElementById("openCam").addEventListener("click", async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = stream;
  } catch (e) {
    alert("Could not open camera: " + e.message);
  }
});

document.getElementById("stopCam").addEventListener("click", () => {
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    video.srcObject = null;
    stream = null;
  }
});

// Placeholder wiring for other buttons:
document.getElementById("loadImage").addEventListener("click", () => {
  document.getElementById("image-status").textContent = "Image loaded (placeholder)";
});

document.getElementById("loadRef").addEventListener("click", () => {
  document.getElementById("ref-status").textContent = "Reference loaded (placeholder)";
});

document.getElementById("checkSpectrum").addEventListener("click", () => {
  alert("Check Spectrum clicked");
});

document.getElementById("phaseDiff").addEventListener("click", () => {
  alert("Phase Difference clicked");
});

document.getElementById("selectROI").addEventListener("click", () => {
  alert("Select ROI clicked");
});

document.getElementById("runAll").addEventListener("click", () => {
  alert("Run All sequence started");
});

document.getElementById("2dbtn").addEventListener("click", () => {
  alert("2dbtn clicked");
});

document.getElementById("3dbtn").addEventListener("click", () => {
  alert("3dbtn clicked");
});

document.getElementById("1dbtn").addEventListener("click", () => {
  alert("1dbtn clicked");
});

// Directional pad logic
const quads = document.querySelectorAll(".quad");
const center = document.querySelector(".center");

function highlight(dir) {
  quads.forEach(q => q.classList.toggle("active", q.dataset.dir === dir));
}

quads.forEach(q => {
  q.addEventListener("click", () => {
    const d = q.dataset.dir;
    padStatus.textContent = `Direction: ${d}`;
    highlight(d);
    // TODO: send command to backend or move stage
    console.log("Clicked", d);
  });
});

center.addEventListener("click", () => {
  padStatus.textContent = "Home";
  highlight(null);
  console.log("Home pressed");
});
