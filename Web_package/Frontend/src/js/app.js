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

document.getElementById("phaseDiff").addEventListener("click", sendParams);


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


async function sendParams() {
    const formData = new FormData();
    formData.append("wavelength", document.getElementById("wavelength").value);
    formData.append("pixel_size", document.getElementById("pixelSize").value);
    formData.append("magnification", document.getElementById("magnification").value);
    formData.append("delta_ri", document.getElementById("ri").value);
    formData.append("dc_remove", document.getElementById("skipPixels").value);
    formData.append("filter_type", document.getElementById("filterType").value);
    formData.append("filter_size", document.getElementById("filterSize").value);
    formData.append("beam_type", document.getElementById("beams").value);
    formData.append("threshold_strength", "1.0");

    const imageFile = document.getElementById("imageFile").files[0];
    const refFile = document.getElementById("refFile").files[0];
    if (!imageFile || !refFile) {
        alert("Please select both image and reference files.");
        return;
    }
    formData.append("image", imageFile);
    formData.append("reference", refFile);

    try {
        const response = await fetch("http://192.168.1.121:8000/run_phase_difference", {
            method: "POST",
            body: formData
        });
        if (!response.ok) throw new Error("Server error " + response.status);

        const data = await response.json();
        console.log("Phase Map Data:", data.phase_map);
        alert("Phase difference computed successfully!");
    } catch (error) {
        console.error("Error:", error);
        alert("Error: " + error.message);
    }
}
