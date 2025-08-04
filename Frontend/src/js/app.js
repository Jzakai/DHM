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

document.getElementById("phaseDiff").addEventListener("click", sendParams);

async function sendParams() {
    const params = {
        wavelength: parseFloat(document.getElementById("wavelength").value),
        pixel_size: parseFloat(document.getElementById("pixelSize").value),
        magnification: parseFloat(document.getElementById("magnification").value),
        delta_ri: parseFloat(document.getElementById("ri").value),
        dc_remove: parseInt(document.getElementById("skipPixels").value),
        filter_type: document.getElementById("filterType").value,
        filter_size: parseInt(document.getElementById("filterSize").value),
        beam_type: document.getElementById("beams").value,
        threshold_strength: 1.0  // Or read from UI if needed
    };

    try {
        const response = await fetch("http://127.0.0.1:8000/set_params", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(params)
        });

        const data = await response.json();
        console.log("Server Response:", data);
        alert("Parameters sent successfully!");
    } catch (error) {
        console.error("Error sending params:", error);
    }
}
